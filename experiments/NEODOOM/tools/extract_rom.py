#!/usr/bin/env python3
"""Restore the exact audited ROM preserved as compressed text in Git."""
import base64,gzip,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
blob=root/'results/neodoom-p0-e1m1.bin.gz.b64'
rom=gzip.decompress(base64.b64decode(blob.read_bytes()))
expected=json.loads((root/'results/rom-sha256.json').read_text())
assert hashlib.sha256(rom).hexdigest()==expected['neodoom-p0-e1m1.bin']
assert len(rom)==expected['rom_bytes']
(root/'out').mkdir(exist_ok=True)
p=root/'out/neodoom-p0-e1m1.bin';p.write_bytes(rom);print(p)
