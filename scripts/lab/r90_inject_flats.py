#!/usr/bin/env python3
"""Inject only Claudio's eight flat arrays after the unmodified R77 generator."""
from pathlib import Path
import argparse,hashlib,json,re
EXPECTED='38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc'
NAMES=tuple(f'{tag}_flat_{side}' for tag in ('r77_h','r76_a','r76_l','r76_n') for side in ('even','odd'))
def replace_arrays(text,arrays):
 assert set(arrays)==set(NAMES),'unexpected arrays'
 edits=[]
 for name in NAMES:
  values=arrays[name];assert len(values)==256 and all(type(v)==int and 1<=v<=15 for v in values),name
  hits=list(re.finditer(r'\b'+name+r'\[256\]\s*=\s*\{([^{}]*)\}',text,re.S));assert len(hits)==1,(name,len(hits))
  m=hits[0];old=re.findall(r'0x[0-9a-fA-F]+|\d+',m[1]);assert len(old)==256,name
  edits.append((m.start(1),m.end(1),','.join(map(str,values))))
 result=text
 for a,b,v in sorted(edits,reverse=True):result=result[:a]+v+result[b:]
 def masked(s):
  for n in NAMES:s=re.sub(r'(\b'+n+r'\[256\]\s*=\s*\{)[^{}]*(\})',r'\1FLATS\2',s)
  return s
 assert masked(result)==masked(text),'non-flat bytes changed'
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');a=p.parse_args()
 path=Path('src/r59_color_tables.h');original=path.read_bytes();sha=hashlib.sha256(original).hexdigest()
 assert sha==EXPECTED,('STOP: generated palette tables differ from Claudio analysis; new analysis required',sha)
 payload=json.loads(Path('assets/r90-flat-luts-lf050.json').read_text());assert payload['r89_tables_sha256']==EXPECTED
 updated=replace_arrays(original.decode(),payload['arrays']).encode()
 if not a.verify_only:path.write_bytes(updated)
 report={'source_sha256':sha,'result_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'changed_arrays':[] if a.verify_only else list(NAMES),'non_flat_bytes_identical':True}
 Path('src/r90_flats_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
