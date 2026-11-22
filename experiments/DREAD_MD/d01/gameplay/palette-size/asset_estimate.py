from pathlib import Path
import os,subprocess,re,struct,json,base64
root=Path.cwd();tools=root/'dread-gameplay/experiments/DREAD_MD/d01/tools';out=root/'dread-palette-size';env=dict(os.environ,PYTHONPATH=str(tools),OPENBLAS_NUM_THREADS='1')
# Prepare candidate weapon art only: no m68k compiler, linker or ROM build.
s=(tools/'gen_gameplay_assets.py').read_text();helper='''
def dither_indices(a):
 mask=a>=0;work=pal[np.maximum(a,0)].copy();dst=np.zeros(a.shape,np.uint8)
 for yy in range(a.shape[0]):
  for xx in range(a.shape[1]):
   if not mask[yy,xx]:continue
   col=np.clip(work[yy,xx],0,255);idx=int(((rgb-col)**2).sum(1).argmin());dst[yy,xx]=idx+1;err=np.clip(col-rgb[idx],-64,64)
   for dx,dy,weight in [(1,0,7/16),(-1,1,3/16),(0,1,5/16),(1,1,1/16)]:
    x,y=xx+dx,yy+dy
    if 0<=x<a.shape[1] and y<a.shape[0] and mask[y,x]:work[y,x]+=err*weight
 return dst
'''
s=s.replace('pieces=[',helper+'\nframes=[dither_indices(a) for a in frames]\npieces=[').replace('int(lut[a[py+cy*8+y,px+cx*8+x]])','int(a[py+cy*8+y,px+cx*8+x])').replace('weap_y=64','weap_y=68')
# Only convert the weapon section; SFX/metadata do not change.
s=s[:s.index('# XGM2 data must start')];(out/'candidate_weapons.py').write_text(s)
for name,script in [('weapon-current',tools/'gen_gameplay_assets.py'),('weapon-dither',out/'candidate_weapons.py')]:
 d=out/name;d.mkdir(exist_ok=True);subprocess.run(['python3',str(script),str(root/'pixel4-control/scripts/doom1.wad'),str(d)],env=env,check=True,stdout=subprocess.DEVNULL)
 data=(d/'weapon.c').read_text();sizes={}
 for kind,n,count in re.findall(r'const (uint16_t|uint32_t) (weap_\w+)\[(\d+)\]',data):sizes[n]=int(count)*(4 if kind=='uint32_t' else 2)
 print(name,json.dumps(sizes),flush=True)
# Existing music arrangement -> final XGM2 data, data conversion only.
payload=json.loads((root/'dread-gameplay/assets/r25-music.json').read_text());track=next(t for t in payload['tracks'] if t['name']=='End')
import sys;sys.path.insert(0,str(root/'dread-gameplay/scripts/lab'));from prepare_r25_music import decode,validate
raw=decode(base64.b64decode(track['zgm']));validate(raw);vgm=out/'ending.vgm';vgm.write_bytes(raw)
subprocess.run(['java','-jar',str(root/'r128-local-sgdk/bin/xgm2tool.jar'),str(vgm),str(out/'ending.xgc'),'-s'],check=True,stdout=(out/'music-conversion.log').open('w'),stderr=subprocess.STDOUT)
print('ending_music_xgm2_bytes',(out/'ending.xgc').stat().st_size,flush=True)
