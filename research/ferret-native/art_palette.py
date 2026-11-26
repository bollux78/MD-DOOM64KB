"""Map-aware 16-color CRAM art compiler; no original Ferret assets.
A byte represents TWO independent 4-bit displayed pixels. Blended pairs
improve color approximation without reducing the logical grid further.
"""
from collections import Counter
from compiler import Resources,name
import math
def dist(a,b):
    return 2*(a[0]-b[0])**2+3*(a[1]-b[1])**2+(a[2]-b[2])**2
def grid(c):return tuple(round(round(x*7/255)*255/7) for x in c)
def mix(a,b):return tuple((x+y)/2 for x,y in zip(a,b))
class Art(Resources):
    def __init__(self,wad,g):
        super().__init__(wad)
        old=list(self.palette)
        self.rgb=[tuple(wad.get("PLAYPAL")[i:i+3]) for i in range(0,768,3)]
        self.lut=list(range(256));self.cache.clear()
        weights=Counter()
        for l in g["lines"]:
            a,b,_,_,_,s0,s1=l
            length=max(1,round(math.dist(g["vertices"][a],g["vertices"][b])))
            for side in (s0,s1):
                if side==65535:continue
                for raw in g["sides"][side][2:5]:
                    k=name(raw)
                    if k in self.defs:weights[k]+=length
        for k in ("SKY1","SKY2","SKY3","SKY4"):
            if k in self.defs:weights[k]+=512;break
        hist=Counter()
        for k,w in weights.items():
            x,y,rows=self.texture(k)
            h=Counter(v for row in rows for v in row)
            for i,n in h.items():hist[i]+=n*w/(x*y)
        for sector in g["sectors"]:
            for f in sector[2:4]:
                k=name(f)
                if k not in self.flats:continue
                b=wad.at(self.flats[k]);h=Counter(b)
                for i,n in h.items():hist[i]+=n*64/max(1,len(b))
        self.hist=hist
        candidates=sorted({grid(c) for c in self.rgb}|{(0,0,0)})
        items=[(self.rgb[i],w) for i,w in sorted(hist.items()) if w>0]
        assert items
        palette=[(0,0,0)]
        best=[dist(c,palette[0]) for c,w in items]
        # Greedy weighted quantization of actual visible source materials.
        while len(palette)<16:
            p=max((p for p in candidates if p not in palette),
                  key=lambda p:sum(w*max(0,e-dist(c,p)) for (c,w),e in zip(items,best)),default=None)
            if p is None:break
            palette.append(p);best=[min(e,dist(c,p)) for (c,w),e in zip(items,best)]
        while len(palette)<16:palette.append(palette[-1])
        # Coordinate descent, deterministic, keeping black index 0.
        for _ in range(2):
            for j in range(1,16):
                rest=palette[:j]+palette[j+1:]
                e=[min(dist(c,p) for p in rest) for c,w in items]
                palette[j]=min((p for p in candidates if p not in rest),
                    key=lambda p:sum(w*min(v,dist(c,p)) for (c,w),v in zip(items,e)),default=palette[j])
        self.palette=palette
        self.pairs=[(a,b,mix(palette[a],palette[b]),dist(palette[a],palette[b])) for a in range(16) for b in range(a,16)]
        # Penalize high-contrast pairs: less obvious stripes, better visual stability.
        self.pair_lut=[self.encode(c) for c in self.rgb]
        self.lut=self.pair_lut;self.cache.clear()
        denom=sum(w for c,w in items)
        olderr=sum(w*min(dist(c,p) for p in old) for c,w in items)/denom
        newerr=sum(w*min(dist(c,p) for p in palette) for c,w in items)/denom
        pairerr=sum(w*dist(c,mix(palette[self.encode(c)>>4],palette[self.encode(c)&15])) for c,w in items)/denom
        self.report={"legacy_weighted_mse":olderr,"new_solid_weighted_mse":newerr,"pair_blend_weighted_mse":pairerr,"palette":palette,"weighted_source_colors":len(items),"pair_colors":len(set(self.pair_lut)),"scope":"source-material RGB error, not screenshot likeness to original Ferret"}
    def encode(self,c):
        a,b,_,_=min(self.pairs,key=lambda p:dist(c,p[2])+p[3]*.065)
        return a*16+b
    def color(self,k):
        if k not in self.flats:return 0
        b=self.wad.at(self.flats[k])
        if not b:return 0
        h=Counter(b);n=len(b)
        # Preserve average color instead of selecting a single modal index.
        rgb=tuple(sum(self.rgb[i][ch]*v for i,v in h.items())/n for ch in range(3))
        return self.encode(rgb)
    def pair_texture(self,k,z):
        # Preserve the actual 2x2 WAD source footprint before quantizing to a
        # two-pixel pair; use full byte per logical texel, not duplicated nibble.
        old=self.lut;self.lut=list(range(256));self.cache.pop(k,None)
        w,h,rows=self.texture(k)
        self.cache.pop(k,None);self.lut=old
        from functools import lru_cache
        @lru_cache(maxsize=32768)
        def encode4(a,b,c,d):
            rgb=tuple(sum(self.rgb[i][j] for i in (a,b,c,d))/4 for j in range(3))
            return self.encode(rgb)
        return bytes(encode4(rows[(2*y+z)%h][2*x%w],rows[(2*y+z)%h][(2*x+1)%w],
                  rows[(2*y+z+1)%h][2*x%w],rows[(2*y+z+1)%h][(2*x+1)%w]) for x in range(64) for y in range(128))
