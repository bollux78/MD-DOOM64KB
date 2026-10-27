#!/usr/bin/env python3
"""Replace R74 selected flat-only aliases with R75 hybrid; preserve L3 walls/CRAM."""
from pathlib import Path
p=Path('src/r59_color_tables.h');s=p.read_text()
for parity in ('even','odd'):
    needle='#define r73_flat_'+parity+' r74_flat_'+parity
    assert s.count(needle)==1,needle
    s=s.replace(needle,'#define r73_flat_'+parity+' r75_flat_'+parity)
needle='#include "r74_flat_tables.h"'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n#include "r75_hybrid_flats.h"')
p.write_text(s)
print('R75 L3 CRAM+walls with hybrid A2-target flats selected')
