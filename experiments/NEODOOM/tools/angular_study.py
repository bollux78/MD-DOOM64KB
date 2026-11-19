"""Sample first intersections of original E1M1 linedefs. Singleton is empirical."""
import struct,sys,zlib,math
from pathlib import Path
import numpy as np
from doom_wad import directory
e=directory(Path(sys.argv[1]).read_bytes())
d=dict(e[next(i for i,v in enumerate(e) if v[0]=='E1M1')+1:][:10])
v=np.array(list(struct.iter_unpack('<hh',d['VERTEXES'])))
lines=np.array(list(struct.iter_unpack('<7H',d['LINEDEFS'])))
a=v[lines[:,0]]; delta=v[lines[:,1]]-a
# All linedefs, even open ones. Single first hit need not finish a column.
def hits(x,y,angles):
    rx=np.cos(angles)[:,None]; ry=np.sin(angles)[:,None]
    vx=a[:,0]-x;vy=a[:,1]-y
    den=rx*delta[:,1]-ry*delta[:,0]
    with np.errstate(divide='ignore',invalid='ignore'):
        t=(vx*delta[:,1]-vy*delta[:,0])/den
        u=(vx*ry-vy*rx)/den
    t=np.where((t>1e-6)&(u>=0)&(u<=1),t,np.inf)
    return np.where(np.isfinite(t.min(axis=1)),t.argmin(axis=1),65535)
scenes={'porta':[(1536-i,-2496,0) for i in range(16,65,4)],'sala':[(1056,-3616,i) for i in range(0,360,5)],'janela':[(1376+i,-3152,180) for i in range(16,97,4)],'caminhada':[(1056,-3616+i,90) for i in range(0,97,4)]}
for size in (16,32,64):
    rows={};nb=128
    for poses in scenes.values():
        for x,y,h in poses:
            key=(x//size,y//size)
            if key in rows:continue
            samples=[]
            for fx in (.02,.5,.98):
                for fy in (.02,.5,.98):
                    for phase in (.02,.5,.98):
                        samples.append(hits((key[0]+fx)*size,(key[1]+fy)*size,(np.arange(nb)+phase)*math.tau/nb))
            rows[key]=[set(col) for col in np.array(samples).T]
    print('cell',size)
    for name,poses in scenes.items():
        n=single=opaque=miss=0
        for x,y,h in poses:
            angles=np.radians(h)+np.arctan((35.5-np.arange(72))/36)
            exact=hits(x,y,angles)
            for i,j in zip((angles*nb/math.tau).astype(float).__mod__(nb).astype(int),exact):
                ids=rows[x//size,y//size][i];n+=1;single+=len(ids)==1;miss+=j not in ids
                opaque+=len(ids)==1 and j in ids and j!=65535 and lines[j,6]==65535
        print(name,n,'single %.1f opaque %.1f missing %.1f'%tuple(100*k/n for k in (single,opaque,miss)))
    lists={};refs=[]
    for row in rows.values():
        for ids in row:
            k=tuple(sorted(ids));refs.append(lists.setdefault(k,len(lists)))
    print('sampled cells',len(rows),'bytes',2*len(refs)+sum(2+2*len(k) for k in lists),'full dense index KiB',round((math.floor(v[:,0].max()/size)-math.floor(v[:,0].min()/size)+1)*(math.floor(v[:,1].max()/size)-math.floor(v[:,1].min()/size)+1)*256/1024,1))
