#!/usr/bin/env python3
"""R52-AB frozen offline seeds from external audit4, with opaque-black repair.
No NumPy or runtime optimizer; deterministic ROM tables, no added WRAM.
WARNING: repaired seeds differ from audit4 simulation. Rerun visual QA.
"""
from pathlib import Path
import argparse, collections, json, runpy
ROOT=Path(__file__).resolve().parents[2]
SEEDS={
'n25':{
'p0':[9,73,3,42,106,99,230,120,206,134,203,76,94,27,69],
'p1':[13,106,99,38,3,158,71,237,205,42,94,73,117,137,9],
'e':'0003d00001100cc10dddeeeeeeeeeeee0eee7744444444440ddddddaafffffff0fffaaaaa222cc21011ddddddddddddd0d6666333335558808888888888110da0aaaaaaaaaccccca0aaac2ccaacccccc088fffff7ddeee7707777777777774dd0dbbbbbbbbbbb99d0fffffffff777dd80888877771119900000ffbbbb9a00000',
'o':'0005b2000ffffe110bbb777777777777077744444444aaaa0bbbbbb777777777077777777ccccc110ffbbbbbbbbbbbbb0bb33333552222dd0dddddddd6666fbb0bbb333eeeeeeee30eecc111336655220dd777777bb7774404444444444444bb0b9999999999999b0777777777777bbd0dddd774411188880807799999e00000'},
'l32':{
'p0':[38,137,106,42,99,120,3,124,206,94,201,215,37,76,71],
'p1':[42,203,158,3,70,106,99,182,119,94,122,235,73,13,129],
'e':'0307a0000e388ee80cccccccccc22222022233ddd11114440aaaaacccccccccc0ccccfc22fffe11e048aaaaaaaaaaaaa0a5555557733336606666666e66838aa0aaaaa555572277a0557eeeea666277e0cccccf6dacccfdd0dddddddd14dd1aa0abbbbbbbbbb908c0cccccccccfffaac0ccccfff88889999000ccbbbbdf00000',
'o':'0c04a60006bcceee0aaaaaaaa7788888088888eee111c1c10fffffaaffffffff0fff75755333d33e03eaaaaaaaaaaaaa0aa7774444466699099999999b3bb0ff0ff555555ddbbdd50555deee5777bbb609999958bfaa788808888888888111aa0ab32222222c222a0ff5555555888ff9099998888eeec0660005988882700000'}}
def nums(items,width=24):
    return ',\n'.join('  '+','.join(str(x) for x in items[i:i+width]) for i in range(0,len(items),width))
def repair(indices,src,src0,palette):
    counts=collections.Counter(indices)
    replace=min(range(1,16),key=lambda k:(counts[k],k))
    other=[i for i in range(1,16) if i!=replace]
    def d(a,b):return sum((a[j]-b[j])**2 for j in range(3))
    prior=palette[src[replace-1]]
    nearest=min(other,key=lambda i:d(prior,palette[src[i-1]]))
    changed=[replace if i==0 else nearest if i==replace else i for i in indices]
    original=src[replace-1]
    src[replace-1]=src0
    assert len(changed)==256 and all(1<=i<=15 for i in changed)
    return changed,{'slot':replace,'former_source':original,'replacement_source':src0,
                    'remapped_original_slot_to':nearest,'zero_count':counts[0],
                    'replaced_slot_count':counts[replace]}
def run(profile):
    z=SEEDS[profile]
    pal=runpy.run_path(str(ROOT/'scripts/genpal.py'))
    raw=pal['load_playpal']()
    source=[pal['decode_subpal'](raw,i) for i in range(14)]
    p0=z['p0'][:];p1=z['p1'][:]
    even=[int(c,16) for c in z['e']]
    odd=[int(c,16) for c in z['o']]
    assert len(p0)==len(p1)==15 and len(even)==len(odd)==256
    even,fix0=repair(even,p0,0,source[0])
    odd,fix1=repair(odd,p1,0,source[0])
    conv=pal['gen_color']
    cram0=[[0]+[conv(source[s][i]) for i in p0] for s in range(14)]
    cram1=[[0]+[conv(source[s][i]) for i in p1] for s in range(14)]
    assert all(len(row)==16 for row in cram0+cram1)
    # Index zero is VDP transparency. Every gameplay sample must use 1..15.
    head=['/* R52-AB generated from audited seeds. Never modify by hand. */',
          '#ifndef R52_AB_TABLES_H','#define R52_AB_TABLES_H',
          '#include <stdint.h>']
    for name,values,typ in [('r52_even',even,'uint8_t'),('r52_odd',odd,'uint8_t')]:
        head.append('static const '+typ+' '+name+'[256]={\n'+nums(values)+'\n};')
    for name,rows in [('r52_pal0',cram0),('r52_pal1',cram1)]:
        head.append('static const uint16_t '+name+'[14][16]={')
        for row in rows:head.append(' {'+','.join(str(x) for x in row)+'},')
        head.append('};')
    head.append('#endif')
    (ROOT/'src/r52_ab_tables.h').write_text('\n'.join(head)+'\n')
    report={'profile':profile,'source':'External R52 audit4, AB near25/luma32',
            'opaque_black_repair':{'even':fix0,'odd':fix1},
            'metrics_note':'Original simulated DeltaE values DO NOT apply after slot repair',
            'maps_have_zero':False,'pal0_source_indices':p0,'pal1_source_indices':p1,
            'pal0_unique':len(set(cram0[0][1:])),
            'pal1_unique':len(set(cram1[0][1:])),
            'combined_unique':len(set(cram0[0][1:]+cram1[0][1:]))}
    (ROOT/'src/r52_ab_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('R52-AB tables',profile,'nonzero maps',len(even),len(odd),'repair',fix0,fix1)
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--profile',choices=sorted(SEEDS),required=True)
    args=ap.parse_args()
    run(args.profile)
