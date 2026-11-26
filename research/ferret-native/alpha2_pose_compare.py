"""Compare FERRET-MD renders with the authentic Alpha2 at the same camera, numbers only.

Coordinate contract (measured on Alpha2 RAM, 26/11/2026):
  Alpha2 x = WAD x, Alpha2 y = WAD y + 3456, Alpha2 z = 1 - eye height,
  Alpha2 angle (0..255) = -Doom angle (Doom angle in degrees, counter-clockwise, 0 = east).
  The FERRET-MD pose angle is the Doom angle in degrees.
Images are the 3D viewport only: Alpha2 rows 16..159, FERRET-MD rows 40..183 (320x144 each).
Metrics per pose (higher is closer, 1.0 = identical):
  edge_corr  Pearson correlation of Sobel edge magnitude on 160x72 luminance (geometry/structure)
  luma_corr  Pearson correlation of 160x72 luminance (layout of light and dark areas)
  color_dist mean RGB distance after 160x72 downscale (palette/brightness; lower is closer)
A baseline is computed against the *wrong* Alpha2 pose to show what "unrelated" looks like.
"""
import json,sys,pathlib
import numpy as np
from PIL import Image
def alpha_to_ferret(x,y,z,a):
    return x,y-3456,1-z,int(round(-a*360/256))%360
def ferret_to_alpha(x,y,eye,deg):
    return x,y+3456,1-eye,int(round(-deg*256/360))%256
def view(path,top):
    im=Image.open(path).convert("RGB").crop((0,top,320,top+144)).resize((160,72),Image.BOX)
    return np.asarray(im,dtype=np.float64)
def edges(g):
    kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]]);p=np.pad(g,1,mode="edge")
    gx=sum(kx[i,j]*p[i:i+g.shape[0],j:j+g.shape[1]] for i in range(3) for j in range(3))
    gy=sum(kx.T[i,j]*p[i:i+g.shape[0],j:j+g.shape[1]] for i in range(3) for j in range(3))
    return np.hypot(gx,gy)
def corr(a,b):
    a=a.ravel()-a.mean();b=b.ravel()-b.mean();d=np.sqrt((a*a).sum()*(b*b).sum())
    return float((a*b).sum()/d) if d else 0.0
def metrics(fa,fb):
    A=view(fa,16);B=view(fb,40)
    la=A@[.299,.587,.114];lb=B@[.299,.587,.114]
    return {"edge_corr":round(corr(edges(la),edges(lb)),3),"luma_corr":round(corr(la,lb),3),
            "color_dist":round(float(np.linalg.norm(A-B,axis=2).mean()),1)}
def main():
    # argv: manifest.json  (list of {"name","alpha":png,"ferret":png})  report.json
    man=json.loads(pathlib.Path(sys.argv[1]).read_text());rows={}
    for i,m in enumerate(man):
        r=metrics(m["alpha"],m["ferret"])
        if len(man)>1:
            w=man[(i+1)%len(man)]
            r["baseline_wrong_pose"]=metrics(w["alpha"],m["ferret"])
        rows[m["name"]]=r
    pathlib.Path(sys.argv[2]).write_text(json.dumps(rows,indent=2))
    print("ALPHA2 POSE COMPARE "+json.dumps(rows),flush=True)
if __name__=="__main__":main()
