#!/usr/bin/env python3
"""R73: insert exact R52/R53 colors as fixed mode 0 into R59 table machinery.

Call after gen_r59_colorview.py and gen_r53_micro.py, before compiler.
No other R59 profile is used at runtime; menu entries are disabled separately.
"""
from pathlib import Path
import re,sys
style=sys.argv[1] if len(sys.argv)>1 else "micro25"
assert style in ("solid","micro25","micro25flat2d"),style
root=Path("src")
r52=(root/"r52_ab_tables.h").read_text()
r53=(root/"r53_micro_tables.h").read_text()
r59file=root/"r59_color_tables.h"
r59=r59file.read_text()
for name in ("r52_pal0","r52_pal1","r52_even","r52_odd","r52_comp_even","r52_comp_odd"):
    assert name in r52,name
for name in ("r53_partner_even","r53_partner_odd"):
    assert name in r53,name
# The R53 scheme stores the real colors in R52: indexes 1..15 are CRAM colors,
# and the sample values map directly to that index. Convert into a pair codebook
# with code==CRAM index. Wall/flat/comp maps stay byte-identical to R52.
def partner(name):
    m=re.search(r"\\b"+name+r"\\[16\\]\\s*=\\s*\\{([^}]*)\\}",r53)
    assert m,name
    vals=[int(v) for v in re.findall(r"\\d+",m.group(1))]
    assert len(vals)==16 and vals[0]==0 and all(0<=v<=15 for v in vals)
    return vals
pairs=[]
for key in ("even","odd"):
    partner_map=partner("r53_partner_"+key)
    vals=[f"{{{n},{n if style=='solid' else partner_map[n]}}}" for n in range(16)]
    pairs.append(f"static const uint8_t r73_pairs_{key}[16][2]={{"+",".join(vals)+"};")
preamble="""
/* R73: R52 Luma32 palette/LUT, R53 M25 companion partners. */
#define r73_pal0 ((const uint16_t (*)[16])r52_pal0)
#define r73_pal1 ((const uint16_t (*)[16])r52_pal1)
#define r73_wall_even r52_even
#define r73_wall_odd r52_odd
#define r73_flat_even r52_even
#define r73_flat_odd r52_odd
#define r73_comp_even ((const uint8_t (*)[256])r52_comp_even)
#define r73_comp_odd ((const uint8_t (*)[256])r52_comp_odd)
"""+"\\n".join(pairs)+"\\n"
assert r59.count("static const R59ColorTables r59_color_tables")==1
needle=" {"+", ".join("r56_"+field for field in
    ("pal0","pal1","pairs_even","pairs_odd","wall_even","wall_odd",
     "flat_even","flat_odd","comp_even","comp_odd"))+"},"
replacement=needle.replace("r56_","r73_")
assert r59.count(needle)==1,"R59 initializer contract changed"
r59=r59.replace(needle,replacement)
r59=r59.replace("static const R59ColorTables r59_color_tables",preamble+"\\nstatic const R59ColorTables r59_color_tables")
assert r59.count(replacement)==1
r59file.write_text(r59)
print("R73 palette:",style,"fixed R52/R53 mode 0, partner pairs:",pairs,flush=True)
