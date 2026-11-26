"""DREAD C7 visual-control profile for independent Ferret renderer.
Use the project's established DAC curve, shared 16-color palette, Doom
COLORMAP light buckets and linear-light pair mixing. No original Ferret data.
"""
from collections import Counter
from functools import lru_cache
import json,pathlib,math
from compiler import Resources
DAC=(0,52,87,116,144,172,206,255)
LIGHT_ROWS=(0,5,10,16)
def bucket(light):
    row=max(0,min(31,(255-light)//8))
    return min(LIGHT_ROWS,key=lambda r:abs(r-row))
def mix(a,b):
    return tuple((((x/255)**2.2+(y/255)**2.2)/2)**(1/2.2)*255 for x,y in zip(a,b))
class DreadArt(Resources):
    def __init__(self,wad,g):
        super().__init__(wad)
        root=pathlib.Path(__file__).resolve().parents[2]
        self.levels=json.loads((root/"experiments/DREAD_MD/d01/tools/gameplay_palette.json").read_text())
        assert len(self.levels)==16 and self.levels[0]==[0,0,0]
        self.palette=[tuple(DAC[i] for i in p) for p in self.levels]
        self.rgb=[tuple(wad.get("PLAYPAL")[i:i+3]) for i in range(0,768,3)]
        self.cmap=wad.get("COLORMAP");assert len(self.cmap)>=32*256
        self.lut=list(range(256));self.cache.clear()
        self.pairs=[(a,b,mix(self.palette[a],self.palette[b]),math.dist(self.palette[a],self.palette[b])) for a in range(16) for b in range(a,16)]
        self.report={"profile":"DREAD shared C7 palette, DAC/gamma and COLORMAP","palette_levels":self.levels,"palette":self.palette,"light_rows":LIGHT_ROWS,"mix_penalty":.08,"green_accent_reserved":12}
    @lru_cache(maxsize=65536)
    def encode(self,c,green=False):
        # Use saturated green only for green source texels in acid materials.
        a,b,_,_=min((p for p in self.pairs if green or 12 not in p[:2]),key=lambda p:math.dist(c,p[2])+.08*p[3])
        if sum(self.palette[a])>sum(self.palette[b]):a,b=b,a
        return (a<<4)|b
    def raw(self,k):
        return super().texture(k)
    @lru_cache(maxsize=256)
    def table(self,row,green):
        result=[]
        for i in range(256):
            rgb=self.rgb[self.cmap[row*256+i]]
            allow=green and rgb[1]>=78 and rgb[1]>=rgb[0]+18 and rgb[1]>=rgb[2]+18
            result.append(self.encode(rgb,allow))
        return result
    def texture(self,k):
        # Sky and size queries; leave raw texture cache intact.
        w,h,rows=self.raw(k)
        lut=self.table(0,False)
        return w,h,[bytes(lut[i] for i in r) for r in rows]
    def pair_texture(self,k,z,light=255):
        w,h,rows=self.raw(k)
        lut=self.table(bucket(light),k.startswith("NUKEDGE"))
        # Keep original WAD sample grid at the renderer's fixed 64x128
        # logical layout. Avoid R03 2x2 averaging; compare detail directly.
        return bytes(lut[rows[(2*y+z)%h][(2*x)%w]] for x in range(64) for y in range(128))
    def color(self,k,light=255):
        if k not in self.flats:return 0
        b=self.wad.at(self.flats[k]);hist=Counter(b);n=len(b)
        if not n:return 0
        row=bucket(light)
        rgb=tuple(sum(self.rgb[self.cmap[row*256+i]][ch]*v for i,v in hist.items())/n for ch in range(3))
        return self.encode(rgb,k.startswith("NUKAGE") and rgb[1]>rgb[0]+10 and rgb[1]>rgb[2]+10)
