#!/usr/bin/env python3
"""Regression: audit must reject missing/failed nm, missing/invalid ELF evidence."""
import os, pathlib, subprocess, sys, tempfile
root=pathlib.Path(__file__).resolve().parents[2]
audit=root/'scripts/lab/r20_layout_audit.py'
with tempfile.TemporaryDirectory() as tmp:
    p=pathlib.Path(tmp); (p/'bin').mkdir(); nm=p/'bin/m68k-elf-nm'
    for i in ('a','b'):
        (p/f'flags-{i}.txt').write_text('-DVIEWWINDOWWIDTH=38 -DDOOM_R20_STACKGUARD')
        (p/f'{i}.elf').write_bytes(b'fixture')
    nm.write_text('#!/bin/sh\nexit 1\n'); nm.chmod(0o755)
    env=dict(os.environ, DOOM_MD_GDK=str(p))
    def run(): return subprocess.run([sys.executable,str(audit),str(p),'a','b'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert run().returncode != 0, 'failed nm was accepted'
    nm.write_text('#!/bin/sh\necho fixture\nexit 0\n')
    assert run().returncode != 0, 'missing RAM symbol was accepted'
    nm.write_text('#!/bin/sh\necho "e0ffe000 B _bend"\necho "00010000 00000080 t R_Subsector"\n')
    assert run().returncode == 0, 'valid evidence rejected'
    (p/'b.elf').unlink()
    assert run().returncode != 0, 'missing ELF was accepted'
print('PASS R20a fail-closed audit regression')
