#!/usr/bin/env python3
"""Build R131 ROM diagnostics using Marsdev/SGDK in disposable workspaces."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PAGES = [8, 10, 16, 24, 30]
ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--pages', type=int, nargs='+', choices=PAGES, default=PAGES)
    a = ap.parse_args()
    out = a.output.resolve()
    public = ROOT.parents[1]
    if out == public or public in out.parents:
        ap.error('Output directory must be outside the public Git repository')
    gdk = Path(os.environ.get('GDK', str(Path.home() / 'mars/m68k-elf')))
    assert (gdk / 'makefile.gen').is_file(), f'Cannot locate SGDK makefile: {gdk}'
    assert (gdk / 'lib/libmd.a').is_file(), f'Cannot locate SGDK lib: {gdk}'
    assert (gdk / 'bin/m68k-elf-gcc').is_file(), f'Cannot locate Marsdev gcc: {gdk}'
    out.mkdir(parents=True, exist_ok=True)
    results = []
    env = os.environ.copy()
    env['GDK'] = str(gdk)
    env['PREFIX'] = 'm68k-elf-'
    env['PATH'] = str(gdk / 'bin') + os.pathsep + env['PATH']
    for pages in a.pages:
        with tempfile.TemporaryDirectory(prefix='r131-') as d:
            work = Path(d)
            (work / 'src').mkdir()
            src = (ROOT / 'r131_main.c').read_text()
            line = '#define R131_PAGES 8'
            assert src.count(line) == 1
            (work / 'src/main.c').write_text(src.replace(line, f'#define R131_PAGES {pages}'))
            (work / 'Makefile').write_text('include $(GDK)/makefile.gen\n')
            subprocess.run(['make', '-j2'], cwd=work, env=env, check=True)
            base = work / 'out/rom.bin'
            if not base.is_file():
                raise RuntimeError(f'SGDK did not create {base}')
            stem = f'r131-ssf-{pages // 2}m.bin' if pages > 8 else 'r131-standard-4m.bin'
            target = out / stem
            proc = subprocess.run([
                sys.executable, str(ROOT / 'r131_pack.py'), '--base', str(base),
                '--pages', str(pages), '--out', str(target)
            ], check=True, text=True, capture_output=True)
            results.append(json.loads(proc.stdout))
    (out / 'R131-MANIFEST.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
