from pathlib import Path
import json,sys,zipfile
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
rows={}
for v in ['CONTROL','FERRET160','FERRET80']:
 candidates=[x.parent.parent for x in root.rglob('manifest.json') if x.parent.name=='release' and json.loads(x.read_text()).get('variant')==v]
 assert len(candidates)==1,(v,candidates)
 p=candidates[0]
 rows[v]={str(m):json.loads((p/f'bench-mode{m}.json').read_text()) for m in [1,2]}
lines=['# C7: Ferret-derived renderer versus CONTROL','','NTSC Genesis; DEMO3 E1M7; source-native graphics in Ferret variants.','Gameplay AI active only in mode 2. Different images are expected; hashes are not a correctness proof.','','| Variant | Render FPS | Combat FPS | Render speed vs CONTROL |','|---|---:|---:|---:|']
for v,r in rows.items():
 gain=(rows['CONTROL']['1']['vblanks']/r['1']['vblanks']-1)*100
 lines.append(f"| {v} | {r['1']['fps']:.3f} | {r['2']['fps']:.3f} | {gain:+.2f}% |")
(out/'RESULTADOS.md').write_text('\n'.join(lines)+'\n');(out/'results.json').write_text(json.dumps(rows,indent=2))
with zipfile.ZipFile(out/'C7-Ferret-Nove-Mapas.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in root.rglob('*'):
  if p.is_file() and (p.suffix in ['.bin','.elf','.json','.log','.png'] or p.name.endswith('.md')):z.write(p,str(p.relative_to(root)))
 for name in ['RESULTADOS.md','results.json']:z.write(out/name,name)
