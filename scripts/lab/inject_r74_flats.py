#!/usr/bin/env python3
"""Replace only R73 fixed-mode flat mapping, preserving wall/sprite and CRAM tables."""
from pathlib import Path
import sys
mode=sys.argv[1]
assert mode in ('ctl','f1','f2','f3')
p=Path('src/r59_color_tables.h')
s=p.read_text()
for side in ('even','odd'):
    key='#define r73_flat_'+side+' r52_'+side
    assert s.count(key)==1,key
    if mode!='ctl':s=s.replace(key,'#define r73_flat_'+side+' r74_flat_'+side)
if mode!='ctl':
    needle='static const R59ColorTables r59_color_tables'
    assert s.count(needle)==1
    s=s.replace(needle,'#include "r74_flat_tables.h"\n'+needle)
p.write_text(s)
assert '-DFLAT_WALL' not in Path('scripts/lab/build_r35_linear.fish').read_text()
print('R74',mode,'flat LUT selected; wall and composed LUT aliases preserved')
