#!/usr/bin/env python3
from pathlib import Path
import sys,subprocess,struct
from r21_heap_model import bend,model
root=Path(sys.argv[1]);report=[]
for variant in sys.argv[2:]:
 name='doom-md-r23-'+variant;b=(root/(name+'.bin')).read_bytes();flags=(root/('flags-'+name+'.txt')).read_text().split()
 assert len(b)<=0x200000,(name,len(b))
 assert b[0x1b0:0x1b2]==b'RA'
 assert '-DDOOM_R22_SRAM_BLOCKLINKS' in flags
 assert ('-DTIMEDEMO' in flags)==(variant=='control')
 assert ('-DDOOM_R23_MAPMEM' in flags)==(variant not in ['control','play-control'])
 m=model(bend(root/(name+'.elf')),alloc=2128,no_init=True)
 assert not m['boot_fail'] and m['after']>=0,(name,m)
 report.append(f'{name}: bytes={len(b)}, heap={m}')
(root/'heap-budget.txt').write_text('\n'.join(report)+'\n');print('\n'.join(report))
