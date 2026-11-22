#!/usr/bin/env python3
"""Reserve PAL3[15] for white text; remap its old dark red to nearest HUD red."""
import re,sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text()
m=re.search(r'hudw_pal\[16\] = \{([^}]+)\}',s);pal=[int(x,16) for x in re.findall(r'0x[0-9A-Fa-f]+',m[1])]
def rgb(c):return (c&14,(c>>4)&14,(c>>8)&14)
a=rgb(pal[15]);target=min(range(15),key=lambda i:sum((x-y)**2 for x,y in zip(a,rgb(pal[i]))))
t=re.search(r'(hudw_tiles\[\d+\]\[8\] = \{)(.*?)(\};)',s,re.S)
def remap(m):
 v=int(m[0],16);return '0x%08X'%sum((target if ((v>>(k*4))&15)==15 else ((v>>(k*4))&15))<<(k*4) for k in range(8))
s=s[:t.start(2)]+re.sub(r'0x[0-9A-Fa-f]{8}',remap,t[2])+s[t.end(2):]
pal[15]=0xeee;s=re.sub(r'hudw_pal\[16\] = \{[^}]+\}', 'hudw_pal[16] = {'+','.join('0x%04X'%v for v in pal)+'}',s);p.write_text(s)
