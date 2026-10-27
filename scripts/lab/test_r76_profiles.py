#!/usr/bin/env python3
"""R76 build preflight for four fully coordinated hardware color profiles."""
from pathlib import Path
import json,re,runpy
root=Path(__file__).resolve().parents[2]
src=root/'src';tmp=root/'dist/r75_a2_target'
s=(src/'r59_color_tables.h').read_text()
assert '#define R59_COLOR_MODES 4' in s
assert 'static const R59ColorTables r59_color_tables[R59_COLOR_MODES]' in s
gen=runpy.run_path(str(root/'scripts/lab/gen_r74_flats.py'))
array=gen['array']
for tag,orig in [('a',tmp),('l',src)]:
    h=(orig/'r52_ab_tables.h').read_text()
    m=(orig/'r53_micro_tables.h').read_text()
    for bank in (0,1):
        original=array(h,'r52_pal'+str(bank))
        generated=array(s,'r76_'+tag+'_pal'+str(bank))
        assert original.tolist()==generated.tolist() and len(original)==224
        assert all(int(generated[k*16])==0 for k in range(14))
    for side in ('even','odd'):
        assert array(h,'r52_'+side).tolist()==array(s,'r76_'+tag+'_wall_'+side).tolist()
        assert array(h,'r52_comp_'+side).tolist()==array(s,'r76_'+tag+'_comp_'+side).tolist()
        original_partner=array(m,'r53_partner_'+side)
        pairs=array(s,'r76_'+tag+'_pairs_'+side).reshape(16,2)
        assert all(int(pairs[n][0])==n and int(pairs[n][1])==int(original_partner[n]) for n in range(16))
        assert pairs[0].tolist()==[0,0]
for tag in ('a','l','n','b'):
    for side in ('even','odd'):
        values=array(s,'r76_'+tag+'_flat_'+side)
        assert len(values)==256 and max(values)<=15 and min(values)>=0
assert all(array(s,'r76_l_wall_'+side).shape==array(s,'r76_a_wall_'+side).shape for side in ('even','odd'))
assert array(s,'r76_a_pal0').tolist()!=array(s,'r76_l_pal0').tolist(), 'A2 and L3 full CRAM palettes collapsed'
report=json.loads((src/'r76_profiles_report.json').read_text())
assert len(report['modes'])==4
assert report['generated_sha256']
assert 'R59_ChangeColor' in (src/'r22_video.inc').read_text()
menu=(src/'m_text.c').read_text()
assert 'Hybrid Blue' in menu and 'A2 Full' in menu and 'L3 Detail' in menu and 'HN Smooth' in menu
assert 'R76_MenuOverlayFinish' in (src/'r22_video.inc').read_text()
print('PASS R76 full CRAM/LUT/partner identity A2 L3, four menus, persistent Start overlay',flush=True)
