"""Independent Doom-format WAD reader and resource compiler.
No Ferret ROM or extracted numeric tables. Output stays local; classic Doom WADs only.
Palette is a deterministic provisional 16-color quantization, not the final art direction.
"""
import struct, pathlib, collections, math, json, re, argparse
P=pathlib.Path
def name(b):return b.split(b"\0",1)[0].decode("ascii").upper()
def need(ok,msg):
    if not ok:raise ValueError(msg)
class WAD:
    def __init__(self,p):
        self.data=P(p).read_bytes();b=self.data
        need(len(b)>=12 and b[:4] in (b"IWAD",b"PWAD"),"not a classic WAD")
        n,off=struct.unpack_from("<II",b,4)
        need(n<=100000 and off<=len(b) and n*16<=len(b)-off,"invalid directory")
        self.entries=[];self.index={}
        for i in range(n):
            a,s,k=struct.unpack_from("<II8s",b,off+16*i)
            need(a<=len(b) and s<=len(b)-a,"invalid lump range")
            k=name(k);self.entries.append((k,a,s));self.index[k]=i
    def at(self,i):
        _,a,s=self.entries[i];return self.data[a:a+s]
    def get(self,k):return self.at(self.index[k])
    def maps(self):return [k for k,_,_ in self.entries if re.fullmatch(r"E[1-9]M[1-9]|MAP[0-9]{2}",k)]
    def map_lumps(self,k):
        i=self.index[k];out={}
        for j in range(i+1,min(i+12,len(self.entries))):
            n=self.entries[j][0]
            if n not in ("THINGS","LINEDEFS","SIDEDEFS","VERTEXES","SEGS","SSECTORS","NODES","SECTORS","REJECT","BLOCKMAP"):break
            out[n]=self.at(j)
        need(all(k in out for k in ("THINGS","LINEDEFS","SIDEDEFS","VERTEXES","SEGS","SSECTORS","NODES","SECTORS")),"missing classic BSP lumps")
        return out
    def marked(self,kind):
        active=False;out={}
        for i,(k,_,s) in enumerate(self.entries):
            if k in (kind+"_START",kind*2+"_START"):active=True;continue
            if k in (kind+"_END",kind*2+"_END"):active=False;continue
            if active and s:out[k]=i
        return out
def records(b,fmt):
    s=struct.Struct(fmt);need(len(b)%s.size==0,"bad record size");return list(s.iter_unpack(b))
def patch(b):
    need(len(b)>=8,"short patch")
    w,h,x,y=struct.unpack_from("<hhhh",b)
    need(0<w<=2048 and 0<h<=2048 and 8+w*4<=len(b),"invalid patch dimensions")
    cols=[]
    for off, in records(b[8:8+w*4],"<I"):
        col=[None]*h;last=-1
        for _ in range(4096):
            need(off<len(b),"truncated patch column");top=b[off];off+=1
            if top==255:break
            need(off+2<=len(b),"truncated post")
            count=b[off];off+=2
            if top<=last:top+=last
            last=top
            need(off+count<len(b),"truncated pixels")
            for j,v in enumerate(b[off:off+count]):
                if 0<=top+j<h:col[top+j]=v
            off+=count+1
        else:raise ValueError("unterminated column")
        cols.append(col)
    return w,h,x,y,cols
class Resources:
    def __init__(self,wad):
        self.wad=wad;pal=wad.get("PLAYPAL");need(len(pal)>=768,"short palette")
        colors=list(records(pal[:768],"BBB"))
        boxes=[colors]
        while len(boxes)<16:
            def score(b):return max(max(x[k] for x in b)-min(x[k] for x in b) for k in range(3))*len(b) if len(b)>1 else -1
            box=max(boxes,key=score);boxes.remove(box)
            axis=max(range(3),key=lambda k:max(x[k] for x in box)-min(x[k] for x in box))
            box.sort(key=lambda c:c[axis]);m=len(box)//2;boxes.extend((box[:m],box[m:]))
        self.palette=[tuple(round(sum(c[k] for c in box)/len(box)*7/255)*255//7 for k in range(3)) for box in boxes]
        self.lut=[min(range(16),key=lambda i:sum((c[k]-self.palette[i][k])**2 for k in range(3)))*17 for c in colors]
        pn=wad.get("PNAMES");n=struct.unpack_from("<I",pn)[0];need(4+8*n<=len(pn),"bad PNAMES")
        self.pnames=[name(pn[4+8*i:12+8*i]) for i in range(n)]
        self.defs={}
        for key in ("TEXTURE1","TEXTURE2"):
            if key not in wad.index:continue
            b=wad.get(key);n=struct.unpack_from("<I",b)[0];need(4+n*4<=len(b),"bad texture table")
            for a, in records(b[4:4+4*n],"<I"):
                need(a+22<=len(b),"bad texture header")
                k=name(b[a:a+8]);w,h=struct.unpack_from("<hh",b,a+12);count=struct.unpack_from("<H",b,a+20)[0]
                need(0<w<=2048 and 0<h<=2048 and a+22+count*10<=len(b),"bad texture definition")
                self.defs[k]=(w,h,records(b[a+22:a+22+count*10],"<hhHhh"))
        self.flats=wad.marked("F");self.sprites=wad.marked("S")
        self.cache={};self.patchcache={}
    def color(self,k):
        if k not in self.flats:return 0
        b=self.wad.at(self.flats[k]);hist=collections.Counter(self.lut[x] for x in b)
        return hist.most_common(1)[0][0] if hist else 0
    def texture(self,k):
        if k in self.cache:return self.cache[k]
        w,h,parts=self.defs[k];out=[bytearray(w) for _ in range(h)]
        for dx,dy,i,_,_ in parts:
            need(i<len(self.pnames),"bad patch index")
            p=self.pnames[i]
            if p not in self.patchcache:self.patchcache[p]=patch(self.wad.get(p))
            pw,ph,_,_,cols=self.patchcache[p]
            for x,col in enumerate(cols):
                if not 0<=dx+x<w:continue
                for y,v in enumerate(col):
                    if v is not None and 0<=dy+y<h:out[dy+y][dx+x]=self.lut[v]
        self.cache[k]=(w,h,out);return self.cache[k]
    def packed_texture(self,k,vertical_origin=0):
        # Ferret-compatible 64 columns x 128 bytes, two repeated guard blocks.
        # Horizontal and vertical resampling/tiling is provisional, not art-tuned.
        w,h,rows=self.texture(k)
        tile=bytes(rows[(2*y+vertical_origin)%h][(2*x)%w] for x in range(64) for y in range(128))
        return tile*3,len(tile)
    def sprite(self,k):
        w,h,x,y,cols=patch(self.wad.at(self.sprites[k]))
        # One logical texel per column and row; y is relative to the actor origin.
        # Padded per-column storage permits the core's signed source offsets.
        need(h<=256 and -256<=y<=256,"sprite exceeds provisional vertical format")
        data=bytearray();spans=[];columns=[]
        for col in cols:
            start=len(data);data.extend(bytes(512))
            base=start+256
            first=len(spans);run=None
            for j,v in enumerate(col+[None]):
                if v is not None:
                    data[base+j-y]=self.lut[v]
                    if run is None:run=j
                elif run is not None:
                    spans.append((base,(run-y)*64,(j-y)*64));run=None
            columns.append((first,len(spans)-first))
        return {"width":w,"origin":x,"pixels":bytes(data),"columns":columns,"spans":spans}
def geometry(wad,k):
    m=wad.map_lumps(k)
    v=records(m["VERTEXES"],"<hh")
    lines=records(m["LINEDEFS"],"<HHHHHHH")
    sides=records(m["SIDEDEFS"],"<hh8s8s8sH")
    sectors=records(m["SECTORS"],"<hh8s8shhh")
    segs=records(m["SEGS"],"<HHHHHH")
    subs=records(m["SSECTORS"],"<HH")
    nodes=records(m["NODES"],"<hhhhhhhhhhhhHH")
    things=records(m["THINGS"],"<hhHHH")
    need(v and sectors and subs,"empty map")
    for a,b,_,_,_,r,l in lines:
        need(a<len(v) and b<len(v) and r<len(sides) and (l==65535 or l<len(sides)),"bad linedef")
    for s in sides:need(s[-1]<len(sectors),"bad sector index")
    for a,b,_,l,d,_ in segs:need(a<len(v) and b<len(v) and l<len(lines) and d<2,"bad seg")
    for n,a in subs:need(a+n<=len(segs),"bad subsector")
    for nd in nodes:
        for child in nd[-2:]:need((child&32767)<(len(subs) if child&32768 else len(nodes)),"bad BSP child")
    return dict(vertices=v,lines=lines,sides=sides,sectors=sectors,segs=segs,subsectors=subs,nodes=nodes,things=things)
def bsp_order(g,x,y):
    # Doom's existing BSP: front-to-back fallback. NOT the Ferret's offline PVS.
    nodes=g["nodes"];subs=g["subsectors"];stack=[len(nodes)-1 if nodes else 32768];seen=set()
    while stack:
        i=stack.pop()
        if i&32768:
            s=i&32767
            if i in seen:raise ValueError("BSP repeated leaf")
            seen.add(i);yield s;continue
        if i in seen:raise ValueError("BSP cycle")
        seen.add(i);a,b,dx,dy,*rest=nodes[i]
        side=int((x-a)*dy<=(y-b)*dx)
        c=rest[-2:];stack.extend((c[1-side],c[side]))
def summary(wad):
    r=Resources(wad)
    tex=[r.packed_texture(k) for k in sorted(r.defs)]
    sprites=[r.sprite(k) for k in sorted(r.sprites)]
    maps={}
    for k in wad.maps():
        g=geometry(wad,k);order=list(bsp_order(g,0,0));need(len(order)==len(g["subsectors"]),"unreachable BSP leaf")
        maps[k]={n:len(v) for n,v in g.items()}
    return {"textures":len(tex),"texture_bytes":sum(len(x[0]) for x in tex),"sprites":len(sprites),"sprite_columns":sum(s["width"] for s in sprites),"sprite_spans":sum(len(s["spans"]) for s in sprites),"maps":maps}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("wad",type=P);a=p.parse_args();print(json.dumps(summary(WAD(a.wad))))
