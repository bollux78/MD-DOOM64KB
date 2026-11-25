"""Conservative geometric visibility prototype, independent of Ferret ROM.

A camera cell is a Doom BSP leaf clipped to the map bounds. The offline
compiler stores a pruned traversal program, static backface rejection, and
an optional single-blocker occlusion proof. Uncertain BSP decisions remain
runtime tests. Doors and two-sided lines never act as permanent blockers.

Geometric proofs are not proofs of equivalence to fixed-point projection:
all candidates must be differentially tested before enabling in production.
"""
import math,struct,collections,json
from compiler import need

def cross(a,b,p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
def side_value(nd,p):
    x,y,dx,dy=nd[:4]
    return dx*(p[1]-y)-dy*(p[0]-x)
def corners(box):
    a,b,c,d=box
    return ((a,b),(a,d),(c,b),(c,d))
def clip(poly,nd,side):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        va=side_value(nd,a)*(1 if side else -1)
        vb=side_value(nd,b)*(1 if side else -1)
        if va>=-1e-7:out.append(a)
        if (va<0<vb) or (vb<0<va):
            t=va/(va-vb)
            out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return out
def cells(g):
    vs=g["vertices"];nodes=g["nodes"]
    xmin=min(p[0] for p in vs)-1;xmax=max(p[0] for p in vs)+1
    ymin=min(p[1] for p in vs)-1;ymax=max(p[1] for p in vs)+1
    poly=[(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]
    stack=[(len(nodes)-1 if nodes else 32768,poly,())]
    result={}
    while stack:
        i,p,path=stack.pop()
        if i&32768:
            leaf=i&32767
            if not p:result[leaf]=(None,None,path);continue
            box=(math.floor(min(x for x,y in p))-1,math.floor(min(y for x,y in p))-1,
                 math.ceil(max(x for x,y in p))+1,math.ceil(max(y for x,y in p))+1)
            center=(round(sum(x for x,y in p)/len(p)),round(sum(y for x,y in p)/len(p)))
            result[leaf]=(box,center,path)
        else:
            for s,child in enumerate(nodes[i][-2:]):
                stack.append((child,clip(p,nodes[i],s) if p else [],path+((i,s),)))
    need(len(result)==len(g["subsectors"]),"invalid BSP cell count")
    return result
def find_leaf(g,x,y):
    nodes=g["nodes"];i=len(nodes)-1 if nodes else 32768
    while not i&32768:
        nd=nodes[i];i=nd[-2+int(side_value(nd,(x,y))>=0)]
    return i&32767
def near_safe(a,b,cs):
    # Keep the test inside a conservative signed-word transformation envelope.
    return max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p in (a,b) for q in cs)<=1800
def occludes(a,b,c,d,cs):
    """Every sight ray from the expanded cell box to [c,d] crosses [a,b],
    with a substantial margin. Exact integer signs and rational intersections."""
    dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
    if length2<64*64:return False
    # Right/front side is negative; solid blocker must be in front of every camera.
    v=[cross(a,b,p) for p in cs]
    if max(v)>=0 or min(abs(z) for z in v)**2<32*32*length2:return False
    w=[cross(a,b,p) for p in (c,d)]
    if min(w)<=0 or min(w)**2<8*8*length2:return False
    for p,cp in zip(cs,v):
        for q,cq in zip((c,d),w):
            den=cq-cp
            # Intersection p+(q-p)*(-cp/den), projected onto blocker.
            dotp=(p[0]-a[0])*dx+(p[1]-a[1])*dy
            dotq=(q[0]-a[0])*dx+(q[1]-a[1])*dy
            num=cq*dotp-cp*dotq
            # Require at least 8 map units inside each endpoint.
            if num<=0 or num>=den*length2:return False
            if min(num,den*length2-num)**2<64*length2*den*den:return False
    return True
class Compiler:
    def __init__(self,g):
        self.g=g;self.cells=cells(g);self.segs=[]
        owner={}
        for i,(n,a) in enumerate(g["subsectors"]):
            for j in range(a,a+n):
                need(j not in owner,"overlapping subsectors");owner[j]=i
        need(len(owner)==len(g["segs"]),"unowned seg")
        for j,(a,b,_,lid,d,_) in enumerate(g["segs"]):
            ln=g["lines"][lid];side=ln[5+d];other=ln[6-d]
            solid=side!=65535 and other==65535
            # Never treat a special line or a zero-height front sector as permanent occluder.
            if solid:
                sec=g["sectors"][g["sides"][side][-1]]
                solid=ln[3]==0 and sec[0]<sec[1]
            self.segs.append((g["vertices"][a],g["vertices"][b],owner[j],solid))
        self.paths={i:v[2] for i,v in self.cells.items()}
    def compile_cell(self,i,mode="backface"):
        box,center,_=self.cells[i];g=self.g;nseg=len(self.segs)
        if box is None:return {"box":None,"keep":list(range(nseg)),"program":None,"backface":0,"occluded":0}
        cs=corners(box)
        fixed={}
        for j,nd in enumerate(g["nodes"]):
            v=[side_value(nd,p) for p in cs]
            if min(v)>0:fixed[j]=1
            elif max(v)<0:fixed[j]=0
        def before(j,k):
            a,b=self.segs[j][2],self.segs[k][2]
            if a==b:return j<k
            for (node,s),(node2,t) in zip(self.paths[a],self.paths[b]):
                if node!=node2:raise ValueError("bad BSP path")
                if s!=t:return fixed.get(node)==s
            return False
        # Restrict removals to coordinates for which 68000 signed arithmetic
        # cannot wrap at the endpoints of the geometric test.
        safe=[near_safe(a,b,cs) for a,b,_,_ in self.segs]
        backface=set()
        for j,(a,b,_,_) in enumerate(self.segs):
            if not safe[j]:continue
            length2=(a[0]-b[0])**2+(a[1]-b[1])**2
            v=min(cross(a,b,p) for p in cs)
            if length2 and v>0 and v*v>=16*16*length2:backface.add(j)
        blocked=set()
        if mode in ("occlusion","occlusion96"):
            cx,cy=center
            blockers=[j for j,(a,b,_,solid) in enumerate(self.segs) if solid and safe[j] and j not in backface]
            blockers.sort(key=lambda j:sum((p[0]-cx)**2+(p[1]-cy)**2 for p in self.segs[j][:2]))
            for j,(c,d,_,_) in enumerate(self.segs):
                if not safe[j] or j in backface:continue
                for k in blockers[:96 if mode=="occlusion96" else 24]:
                    if k==j or not before(k,j):continue
                    a,b=self.segs[k][:2]
                    if occludes(a,b,c,d,cs):blocked.add(j);break
        keep=set(range(nseg))-backface-blocked
        def program(node):
            if node&32768:
                leaf=node&32767;n,a=g["subsectors"][leaf]
                return [0,[leaf]] if any(j in keep for j in range(a,a+n)) else None
            c0,c1=g["nodes"][node][-2:]
            a,b=program(c0),program(c1)
            if a is None:return b
            if b is None:return a
            if node not in fixed:return [2,node,a,b]
            if fixed[node]:a,b=b,a
            if a[0]==b[0]==0:return [0,a[1]+b[1]]
            return [1,a,b]
        return {"box":box,"center":center,"keep":sorted(keep),"program":program(len(g["nodes"])-1 if g["nodes"] else 32768),"backface":len(backface),"occluded":len(blocked)}
    def compile(self,mode):
        return {i:self.compile_cell(i,mode) for i in sorted(self.cells)}
def ordered_leaves(g,x,y,p,stats):
    if p is None:return
    if p[0]==0:
        yield from p[1]
    elif p[0]==1:
        yield from ordered_leaves(g,x,y,p[1],stats)
        yield from ordered_leaves(g,x,y,p[2],stats)
    else:
        stats["runtime_bsp_tests"]+=1
        s=int(side_value(g["nodes"][p[1]],(x,y))>=0)
        yield from ordered_leaves(g,x,y,p[2+s],stats)
        yield from ordered_leaves(g,x,y,p[3-s],stats)
def selection(g,x,y,compiled,stats):
    i=find_leaf(g,x,y);c=compiled[i];box=c["box"]
    stats["visibility_cell"]=i
    if box is None or not(box[0]<=x<=box[2] and box[1]<=y<=box[3]):
        return None,None
    stats["offline_candidates"]=len(c["keep"])
    return set(c["keep"]),ordered_leaves(g,x,y,c["program"],stats)
def pack(g,compiled):
    """Target-independent numeric format. Deduplicate masks and traversal
    programs independently; all words big-endian, no pointers or ROM code."""
    masks={};programs={};md=bytearray();pd=bytearray();entries=[]
    def code(p):
        if p is None:return b"\x00"
        if p[0]==0:return b"\x01"+struct.pack(">H",len(p[1]))+b"".join(struct.pack(">H",v) for v in p[1])
        if p[0]==1:return b"\x02"+code(p[1])+code(p[2])
        return b"\x03"+struct.pack(">H",p[1])+code(p[2])+code(p[3])
    for i,c in sorted(compiled.items()):
        mask=bytearray((len(g["segs"])+7)//8)
        for j in c["keep"]:mask[j//8]|=1<<(j%8)
        mask=bytes(mask);p=code(c["program"])
        if mask not in masks:masks[mask]=len(md);md.extend(mask)
        if p not in programs:programs[p]=len(pd);pd.extend(p)
        box=c["box"] or (0,0,0,0)
        entries.append(struct.pack(">iiiiII",*box,masks[mask],programs[p]))
    header=struct.pack(">4sHHIII",b"FRV1",len(compiled),len(g["segs"]),sum(map(len,entries)),len(md),len(pd))
    return header+b"".join(entries)+md+pd,{"unique_masks":len(masks),"unique_programs":len(programs),"mask_bytes":len(md),"program_bytes":len(pd),"cell_bytes":sum(map(len,entries))}


def pack_dag(g,compiled):
    """FRV2: shared DAG of leaf runs, fixed sequences and conditional nodes.
    Binary format: BE header, 16-bit bounded cell boxes, mask index, program ID;
    interned masks; fixed 8-byte nodes. Leaves use the high-bit reference range.
    No decompression allocation is needed at runtime.
    """
    masks={};md=bytearray();nodes=[];intern={};entries=[]
    def node(rec):
        if rec not in intern:
            need(len(nodes)<32767,"FRV2 DAG exceeds 15-bit references")
            intern[rec]=len(nodes);nodes.append(rec)
        return intern[rec]
    def seq(a,b):
        if a==65535:return b
        if b==65535:return a
        return node((1,0,a,b))
    def run(v):
        if not v:return 65535
        if len(v)==1:
            need(v[0]<32767,"leaf exceeds FRV2 reference")
            return 32768|v[0]
        m=len(v)//2
        return seq(run(v[:m]),run(v[m:]))
    def code(p):
        if p is None:return 65535
        if p[0]==0:return run(p[1])
        if p[0]==1:return seq(code(p[1]),code(p[2]))
        return node((2,p[1],code(p[2]),code(p[3])))
    for i,c in sorted(compiled.items()):
        mask=bytearray((len(g["segs"])+7)//8)
        for j in c["keep"]:mask[j//8]|=1<<(j%8)
        mask=bytes(mask)
        if mask not in masks:masks[mask]=len(masks);md.extend(mask)
        box=c["box"] or (0,0,0,0)
        entries.append(struct.pack(">hhhhHH",*box,masks[mask],code(c["program"])))
    header=struct.pack(">4sHHHHI",b"FRV2",len(compiled),len(g["segs"]),len(masks),len(nodes),len(md))
    blob=header+b"".join(entries)+md+b"".join(struct.pack(">HHHH",*n) for n in nodes)
    return blob,{"bytes":len(blob),"unique_masks":len(masks),"dag_nodes":len(nodes),"mask_bytes":len(md),"program_bytes":8*len(nodes),"cell_bytes":12*len(entries)}

def read_dag(g,blob):
    magic,nc,ns,nm,nn,mb=struct.unpack_from(">4sHHHHI",blob)
    need(magic==b"FRV2" and nc==len(g["subsectors"]) and ns==len(g["segs"]),"FRV2 header")
    stride=(ns+7)//8
    mo=16+12*nc;no=mo+mb
    need(mb==nm*stride and len(blob)==no+nn*8,"FRV2 length")
    def cell(i):
        a,b,c,d,m,p=struct.unpack_from(">hhhhHH",blob,16+12*i)
        need(m<nm,"FRV2 mask index")
        mask=blob[mo+m*stride:mo+(m+1)*stride]
        return (a,b,c,d),{j for j in range(ns) if mask[j//8]&(1<<(j%8))},p
    def walk(ref,x,y,stats):
        if ref==65535:return
        if ref&32768:
            yield ref&32767;return
        need(ref<nn,"FRV2 node index")
        op,n,a,b=struct.unpack_from(">HHHH",blob,no+8*ref)
        if op==2:
            stats["runtime_bsp_tests"]+=1
            if side_value(g["nodes"][n],(x,y))>=0:a,b=b,a
        else:need(op==1,"FRV2 opcode")
        yield from walk(a,x,y,stats)
        yield from walk(b,x,y,stats)
    return cell,walk
