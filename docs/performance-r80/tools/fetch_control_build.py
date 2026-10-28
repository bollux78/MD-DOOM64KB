#!/usr/bin/env python3
"""Fetch immutable R79 controls from GitHub Actions using an authenticated gh CLI.
Downloads the original six-ROM artifact to a temporary directory, keeps only
control files and verifies the two control ROMs before publishing them locally.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
RUN='40597005254';REPO='bollux78/MD-DOOM64KB';ARTIFACT='doom-md-r79-shadow-6-roms'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'control-build');a=p.parse_args()
    gh=shutil.which('gh')
    if not gh:p.error('gh CLI required; alternatively use the connected GitHub artifact-download tool')
    with tempfile.TemporaryDirectory(prefix='md-doom-r79-control-') as td:
        tmp=Path(td)
        subprocess.run([gh,'run','download',RUN,'--repo',REPO,'--name',ARTIFACT,'--dir',str(tmp)],check=True)
        rows=[r for r in json.loads((tmp/'MANIFEST.json').read_text()) if r['variant'].startswith('r79-base-')]
        assert [r['variant'] for r in rows]==['r79-base-pf','r79-base-pl']
        for r in rows:
            b=(tmp/r['rom']).read_bytes()
            assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['rom']
        a.out.mkdir(parents=True,exist_ok=True)
        for f in tmp.iterdir():
            if f.is_file() and 'r79-base-' in f.name:shutil.copyfile(f,a.out/f.name)
        (a.out/'MANIFEST.json').write_text(json.dumps(rows,indent=2)+'\n')
        print('Verified R79 PERF/PLAY ROMs and downloaded their ELFs/flags to',a.out)
if __name__=='__main__':main()
