from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,os,time,json
root=Path.cwd();out=root/'dread-palette-size';tool=root/'dread-gameplay/experiments/DREAD_MD/d01/tools/conv.py';wad=root/'pixel4-control/scripts/doom1.wad';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',DREAD_NPAL='1',DREAD_PAL_ROUNDS='1')
def convert(n):
 d=out/f'E1M{n}';d.mkdir(exist_ok=True);t=time.time()
 with (d/'conversion.log').open('w') as log:subprocess.run(['python3',str(tool),str(wad),f'E1M{n}',str(d),'--row-only','--tex-pad','32'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 return {'map':f'E1M{n}','seconds':round(time.time()-t,1)}
results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for f in as_completed([pool.submit(convert,n) for n in range(1,10)]):
  r=f.result();results.append(r);print(json.dumps(r),flush=True)
(out/'conversion-timing.json').write_text(json.dumps(results,indent=2))
