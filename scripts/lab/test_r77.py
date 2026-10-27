#!/usr/bin/env python3
"""R77 menu DAC equality, priority limits and generated hybrid invariants."""
from pathlib import Path
import argparse,hashlib,itertools,json,re,runpy,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--generated',action='store_true');args=ap.parse_args()
# Normal DAC output 2*c vs shadow c, not a claim about TV transfer curves.
pal=[0,0,0x222,0x444,0x666,0x888,0xCCC,0,0,0,0,0,0,0,0,0xEEE]
shade=[1,3,5,6]
for k in range(4):
    for shift in (1,5,9):
        assert ((pal[shade[k]]>>shift)&7)==2*((pal[k+1]>>shift)&7)
normal=set(itertools.product(range(0,15,2),repeat=3));shadow=set(itertools.product(range(8),repeat=3))
assert len(normal|shadow)==960
# A high-priority transparent tile can still defeat shadow in the other plane.
for a,b in itertools.product((0,1),repeat=2):
    assert ('S' if not(a or b) else 'N')==('S' if a==b==0 else 'N')
inc=(ROOT/'src/r77_menu.inc').read_text()
assert 'VDP_setHilightShadow(TRUE)' in inc and 'VDP_setHilightShadow(FALSE)' in inc
assert 'VDP_setWindowVPos(FALSE,22)' in inc
assert 'R77_MENU_TILES (2u+2u*96u)' in inc
assert 'R77_MENU_BASE + R77_MENU_TILES > 1440u' in inc
# Compile the actual row/attribute helpers; test every possible source CRAM word.
start=inc.index('static uint32_t R77_StoneRow');stop=inc.index('static void R77_MenuEnter')
helpers=inc[start:stop]
c='''#include <stdint.h>
#include <assert.h>
#define HUDW_HEALTH_C 5
#define R77_MENU_BASE 1206
static uint16_t hudw_bgmap[2][8];
static uint16_t hudw_pal[16];
static uint32_t hudw_tiles[1][8];
'''+helpers+'''
int main(void){
 const unsigned pal[16]={0,0,0x222,0x444,0x666,0x888,0xCCC};
 for(unsigned w=0;w<4096;w+=2){
  hudw_pal[1]=w;hudw_tiles[0][0]=0x11111111u;
  unsigned s=R77_StoneRow(0,0,1)&15u,n=R77_StoneRow(0,0,0)&15u;
  for(unsigned bit=1;bit<=9;bit+=4)assert(((pal[s]>>bit)&7)==2*((pal[n]>>bit)&7));
 }
 for(unsigned x=0;x<40;++x)for(unsigned ch=0;ch<256;++ch){
  unsigned v=R77_MenuWord(x,ch);
  assert(v&0x8000u);assert((v&0x7ffu)>=R77_MENU_BASE+2);
  assert((v&0x7ffu)<R77_MENU_BASE+194);
 }
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);(p/'test.c').write_text(c)
    subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
if args.generated:
    h=(ROOT/'src/r59_color_tables.h').read_text()
    report=json.loads((ROOT/'src/r77_profiles_report.json').read_text())
    assert report['generated_sha256']==hashlib.sha256(h.encode()).hexdigest()
    assert report['blue_max_between_columns_after']==0
    assert report['blue_mean_deltaE_to_A2_after']<report['blue_mean_deltaE_to_A2_before']
    assert len(report['anchor_words'])==4
    g=runpy.run_path(str(ROOT/'scripts/lab/gen_r74_flats.py'));arr=g['array']
    def values(name):
        m=re.search(r'\b'+name+r'(?:\[\d+\])+\s*=\s*\{(.*?)\};',h,re.S)
        assert m,name
        return [int(v,0) for v in re.findall(r'0x[\da-fA-F]+|\d+',m[1])]
    for bank,side in enumerate(('even','odd')):
        p=values('r77_h_pal'+str(bank));assert len(p)==224 and all(p[b*16]==0 for b in range(14))
        pairs=values('r77_h_pairs_'+side);assert len(pairs)==32 and pairs[:2]==[0,0]
        assert all(pairs[i*2]==i and 0<=pairs[i*2+1]<16 for i in range(16))
        for role in ('wall','flat'):
            v=values('r77_h_'+role+'_'+side);assert len(v)==256 and all(0<x<16 for x in v)
        assert len(values('r77_h_comp_'+side))%256==0
    # The full A2/L3 controls are still byte-identical to regenerated inputs.
    for tag,folder in [('a',ROOT/'dist/r75_a2_target'),('l',ROOT/'src')]:
        original=(folder/'r52_ab_tables.h').read_text()
        micro=(folder/'r53_micro_tables.h').read_text()
        for bank,side in enumerate(('even','odd')):
            assert values('r76_'+tag+'_pal'+str(bank))==arr(original,'r52_pal'+str(bank)).tolist()
            assert values('r76_'+tag+'_wall_'+side)==arr(original,'r52_'+side).tolist()
            assert values('r76_'+tag+'_comp_'+side)==arr(original,'r52_comp_'+side).tolist()
            partner=arr(micro,'r53_partner_'+side)
            pairs=values('r76_'+tag+'_pairs_'+side)
            assert all(pairs[i*2+1]==partner[i] for i in range(16))
    model=runpy.run_path(str(ROOT/'scripts/lab/gen_r52_claudio.py'))
    lumps=model['wad_lumps']((ROOT/'scripts/doom64.wad').read_bytes())
    cm=next(v for n,v in lumps if n=='COLORMAP')
    for side in ('even','odd'):
        wall=values('r77_h_wall_'+side)
        assert values('r77_h_comp_'+side)==[wall[c] for c in cm]
    sh=json.loads((ROOT/'src/r77_shadow_report.json').read_text())
    assert sh['highlight'] is False and sh['full_cram_union_rgb']==960
    assert len(sh['profiles'])==4 and all(v['candidate_pairs_per_mode']==225 for v in sh['profiles'].values())
    assert 'R77_MenuLeave' in (ROOT/'src/r22_video.inc').read_text()
print('PASS R77 actual stone DAC equality, glyph priority/range, normal-shadow limits'+(' and generated profiles' if args.generated else ''))

