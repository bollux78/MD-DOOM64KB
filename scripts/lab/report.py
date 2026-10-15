#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--rom', required=True)
parser.add_argument('--mode', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
raw = Path(args.rom).read_bytes()
record = {
    'mode': args.mode,
    'rom_size_bytes': len(raw),
    'rom_sha256': hashlib.sha256(raw).hexdigest(),
    'historical_baseline_fps': 8.13,
    'measured_fps': None,
    'telemetry_status': 'not_implemented'
}
Path(args.output).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
