#!/usr/bin/env python3
"""Preserve exact successful outputs from run39045298927/commit5731747.
Engine sources and options for these 36 ROMs are unchanged. Only the last
full-combination diagnostic name exceeded the existing 30-char ID limit.
A sealed SHA256 per BIN/ELF/flag/log prevents reusing incomplete outputs.
"""
import pathlib,json,hashlib
root=pathlib.Path(__file__).resolve().parents[2];d=root/'dist/r20h'
manifest=json.loads((root/'scripts/lab/r20h_reuse.json').read_text())
assert len(manifest)==144
for name,digest in manifest.items():
 assert pathlib.Path(name).name==name
 assert hashlib.sha256((d/name).read_bytes()).hexdigest()==digest,name
# Drop incomplete/renamed outputs before any final flag or set audit.
for p in d.iterdir():
 if p.is_file() and p.name not in manifest:p.unlink()
ids=sorted(pathlib.Path(n).stem for n in manifest if n.endswith('.bin'));assert len(ids)==36
(d/'.reuse-verified').write_text('\n'.join(ids)+'\n')
print('PASS sealed SHA256 for 36 BINs and their matching 36 ELFs/flags/logs')
