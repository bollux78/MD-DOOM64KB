"""Original two-room fixture and independent continuous ray/plane oracle.
No Ferret calibration, WAD assets or native projection functions in oracle.
Solid colors deliberately isolate geometry; texture UV test is separate.
"""
import ctypes as C, json, math, pathlib, struct, sys
P=pathlib.Path
from export_scene import WAD,Resources
from test_demo import Stats,U8
def make(p):
    def rec(fmt,rs):return b"".join(struct.pack(fmt,*r) for r in rs)
    # Sixteen distinct RGB colors, 16 identical entries each. Median cut
    # preserves the groups; no original palettes or graphics.
    colors=[(0,0,0),(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(255,255,255),(146,0,0),(0,146,0),(0,0,146),(146,146,0),(146,0,146),(0,146,146),(146,146,146),(255,146,0)]
    pal=bytes(v for c in colors for _ in range(16) for v in c)
    def patch(c):
        col=bytes([0,64,0])+bytes([c*16])*64+b"\0\xff"
        return struct.pack("<hhhh",64,64,32,64)+rec("<I",[(264+i*len(col),) for i in range(64)])+col*64
    names=[f"P{i}".encode() for i in range(1,10)]
    tex=[struct.pack("<8sIhhIHhhHhh",f"T{i}".encode(),0,64,64,0,1,0,0,i-1,0,0) for i in range(1,10)]
    table=struct.pack("<I",len(tex))+rec("<I",[(4+4*len(tex)+sum(map(len,tex[:i])),) for i in range(len(tex))])+b"".join(tex)
    v=[(-256,-96),(-256,128),(0,128),(0,-96),(192,128),(192,-96)]
    # clockwise west room, then east room; shared edge direction north->south.
    lines=[(0,1,1,0,0,0,65535),(1,2,1,0,0,1,65535),(2,3,4,0,0,2,4),(3,0,1,0,0,3,65535),(2,4,1,0,0,5,65535),(4,5,1,0,0,6,65535),(5,3,1,0,0,7,65535)]
    sides=[(0,0,b"-",b"-",b"T1",0),(0,0,b"-",b"-",b"T2",0),(0,0,b"T7",b"T8",b"-",0),(0,0,b"-",b"-",b"T3",0),(0,0,b"T7",b"T8",b"-",1),(0,0,b"-",b"-",b"T4",1),(0,0,b"-",b"-",b"T5",1),(0,0,b"-",b"-",b"T6",1)]
    segs=[(0,1,0,0,0,0),(1,2,0,1,0,0),(2,3,0,2,0,0),(3,0,0,3,0,0),(3,2,0,2,1,0),(2,4,0,4,0,0),(4,5,0,5,0,0),(5,3,0,6,0,0)]
    # side_value = -y_dir*x; x<0 -> side 1 when direction +Y.
    nodes=[(0,0,0,1,128,-96,0,192,128,-96,-256,0,32769,32768)]
    sectors=[(0,144,b"F10",b"F11",160,0,0),(24,96,b"F12",b"F13",160,0,0)]
    entries=[("PLAYPAL",pal),("PNAMES",struct.pack("<I",len(names))+rec("<8s",[(x,) for x in names])),("TEXTURE1",table)]
    entries.extend((n.decode(),patch(i)) for i,n in enumerate(names,1))
    entries += [("F_START",b"")]+[(f"F{i}",bytes([16*i])*4096) for i in range(10,14)]+[("F_END",b""),("E1M1",b""),("THINGS",rec("<hhHHH",[(-120,20,0,1,7)])),("LINEDEFS",rec("<HHHHHHH",lines)),("SIDEDEFS",rec("<hh8s8s8sH",sides)),("VERTEXES",rec("<hh",v)),("SEGS",rec("<HHHHHH",segs)),("SSECTORS",rec("<HH",[(4,0),(4,4)])),("NODES",rec("<hhhhhhhhhhhhHH",nodes)),("SECTORS",rec("<hh8s8shhh",sectors)),("REJECT",b"\0"),("BLOCKMAP",b"")]
    data=bytearray(b"PWAD"+bytes(8));directory=[]
    for k,b in entries:directory.append((len(data),len(b),k.encode()));data.extend(b)
    off=len(data);data.extend(rec("<II8s",directory));struct.pack_into("<II",data,4,len(entries),off);p.write_bytes(data)
POSES=[(-120,20,41,a) for a in (0,90,180,270)]+[(80,-20,65,a) for a in (0,90,180,270)]
def ray(pose,px,py):
    x,y,z,a=pose;rad=math.radians(a)
    # x screen increases towards camera right; horizontal focal length 80.
    sx=(px-80)/80;dz=(36.5-py)/80
    dx=math.cos(rad)+sx*math.sin(rad);dy=math.sin(rad)-sx*math.cos(rad)
    west=x<0
    for _ in range(2):
        left,right,lo,hi,fl,ce,flc,cec=(-256,0,-96,128,0,144,10,11) if west else (0,192,-96,128,24,96,12,13)
        hits=[]
        if dx<-1e-9:hits.append(((left-x)/dx,1 if west else 9,"west"))
        if dx>1e-9:hits.append(((right-x)/dx,9 if west else 5,"east"))
        if dy<-1e-9:hits.append(((lo-y)/dy,3 if west else 6,"south"))
        if dy>1e-9:hits.append(((hi-y)/dy,2 if west else 4,"north"))
        if dz<-1e-9:hits.append(((fl-z)/dz,flc,"plane"))
        if dz>1e-9:hits.append(((ce-z)/dz,cec,"plane"))
        t,col,kind=min((h for h in hits if h[0]>1e-6),key=lambda h:h[0])
        if col!=9:return col
        zz=z+t*dz
        if zz<24:return 8
        if zz>96:return 7
        x+=dx*(t+1e-4);y+=dy*(t+1e-4);z+=dz*(t+1e-4);west=not west
    raise AssertionError("ray escaped fixture")
def verify(out):
    r=Resources(WAD(out/"fixture.wad"));lut=[r.lut[i*16] for i in range(16)]
    assert len(set(lut))==16,("palette collision",lut)
    lib=C.CDLL(str(out/"demo-host.so"));f=lib.fr_demo_frame
    f.argtypes=[C.c_uint,C.POINTER(Stats),C.POINTER(U8),C.POINTER(U8)];f.restype=C.c_int
    rows=[]
    for i,pose in enumerate(POSES):
        s=Stats();fb=(U8*11520)();tiles=(U8*23040)();assert f(i,C.byref(s),fb,tiles)==0
        compared=matches=0;bad={};expected_colors=set()
        for y in range(3,69):
            for x in range(3,157):
                # Avoid boundaries that can vary due to fixed-point rounding.
                ids={ray(pose,x+dx,y+dy) for dx in (-3,0,3) for dy in (-3,0,3)}
                if len(ids)!=1:continue
                col=ids.pop();expected_colors.add(col);v=fb[(x//2)*144+(x&1)+2*y]
                compared+=1;matches+=v==lut[col]
                if v!=lut[col]:bad[f"{col}->{v//17}"]=bad.get(f"{col}->{v//17}",0)+1
        rows.append({"pose":pose,"compared":compared,"matched":matches,"fraction":matches/max(1,compared),"expected_colors":sorted(expected_colors),"mismatches":bad,"raster_errors":s.errors,"closed":s.closed})
    result={"poses":rows,"pass":all(x["fraction"]>=.98 and x["raster_errors"]==0 and x["closed"]==160 for x in rows),"scope":"independent ray/plane oracle; solid materials, not UV accuracy"}
    (out/"geometry-oracle.json").write_text(json.dumps(result,indent=2));print("GEOMETRY ORACLE "+json.dumps(result),flush=True)
    return result
if __name__=="__main__":
    if not verify(P(sys.argv[1]))["pass"]:sys.exit(2)
