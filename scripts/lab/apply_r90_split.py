#!/usr/bin/env python3
"""R90 split palettes (prototype A), applied after apply_r89.py in a disposable copy.

Upper half of the 3D view (sample rows < R90_SPLIT_ROW) keeps R89 exactly: PAL0/PAL1, R89 LUTs.
Lower half: the framebuffer words of tile rows >= R90_SPLIT_ROW/2 carry palette bit 0x4000, so
plane A shows PAL2 and plane B PAL3 with the same pair tiles; the renderer splits each column at
R90_SPLIT_ROW and draws the lower part with r90_bottom_tables (gen_r90_split.py).
VBlank writes the bottom palettes into CRAM lines 2/3; an HInt at the first line after the view
restores the HUD palettes (hudw_fpal/hudw_pal). CRAM dots may appear on that line (accepted).
Outside GS_LEVEL nothing changes: no HInt, no attribute bits, CRAM 2/3 left with the HUD palettes.
"""
from pathlib import Path
import os, re

def patch(f, a, b, count=1):
    p = Path(f); s = p.read_text(); n = s.count(a)
    assert n == count, (f, a[:90], n)
    p.write_text(s.replace(a, b))

V = 'src/r22_video.inc'
TAG = os.environ.get('R90_NAME', 'split')

# (a) generator inside the build, right after the R77 profile tables exist
patch('scripts/lab/build_r35_linear.fish',
      '                        python3 scripts/lab/test_r77.py --generated; or exit 1\n',
      '                        python3 scripts/lab/test_r77.py --generated; or exit 1\n'
      '                        python3 scripts/lab/gen_r90_split.py --wad scripts/doom1.wad --src src; or exit 1\n')

# (b) region-aware tables; VBlank top palettes stay explicit R89
patch(V, '#define R59_CURRENT (r59_color_tables[r59_color_mode])\n',
'''#include "r90_split_tables.h"
/* R90 split: region 1 while a column part below R90_SPLIT_ROW is drawn; live while the
 * framebuffer carries the PAL2/PAL3 bits; hint while the HUD-restoring HInt is enabled. */
static struct {uint8_t region,live,hint;} r90_s;
typedef char r90_state_size[(sizeof(r90_s)==3u)?1:-1];
static void R90_SetAttr(uint8_t on);
#define R59_TOP (r59_color_tables[r59_color_mode])
#define R59_CURRENT ((r90_s.region?r90_bottom_tables:r59_color_tables)[r59_color_mode])
''')
patch(V, '#define R79_PAL0 (R59_CURRENT.pal0)\n#define R79_PAL1 (R59_CURRENT.pal1)\n',
         '#define R79_PAL0 (R59_TOP.pal0)\n#define R79_PAL1 (R59_TOP.pal1)\n')

# (c) second frame context for the lower half
patch(V, 'static r64a_ctx_t r64a_ctx;\n', 'static r64a_ctx_t r64a_ctx, r64a_ctx_b;\n')
patch(V, 'void R64A_FrameBegin(void){ R64A_Fill(&r64a_ctx); }\nvoid R64A_FrameEnd(void){ r64a_ctx.comp[0]=0; }\n',
'''void R64A_FrameBegin(void){
    R64A_Fill(&r64a_ctx); r90_s.region=1; R64A_Fill(&r64a_ctx_b); r90_s.region=0;
    R90_SetAttr(_g_gamestate==GS_LEVEL);
}
void R64A_FrameEnd(void){ r64a_ctx.comp[0]=0; r64a_ctx_b.comp[0]=0; }
''')
patch(V, '    if(r64a_ctx.comp[0]) return &r64a_ctx;\n',
         '    if(r90_s.region){ if(r64a_ctx_b.comp[0]) return &r64a_ctx_b; }\n    else if(r64a_ctx.comp[0]) return &r64a_ctx;\n')

# (d) split wrappers around the three column drawers. The original definitions keep their text (the
# R22 host test extracts them by name); a macro renames each one to its core, the wrapper follows it.
SPLIT = """{
    if(!r90_s.live || v->yh<R90_SPLIT_ROW){ %(core)s(%(pre)sv); return; }
    if(v->yl>=R90_SPLIT_ROW){ r90_s.region=1; %(core)s(%(pre)sv); r90_s.region=0; return; }
    draw_column_vars_t t=*v; t.yh=R90_SPLIT_ROW-1; %(core)s(%(pre)s&t);
    t.yh=v->yh; t.yl=R90_SPLIT_ROW; r90_s.region=1; %(core)s(%(pre)s&t); r90_s.region=0;
}
"""
def wrap(sig, name, core, wsig, pre=''):
    s = Path(V).read_text(); assert s.count(sig) == 1, sig
    a = s.index(sig); b = s.index('{', a); d = 0
    for i in range(b, len(s)):
        d += (s[i] == '{') - (s[i] == '}')
        if d == 0: end = i + 1; break
    body = SPLIT % dict(core=core, pre=pre)
    s = (s[:a] + '#define %s %s\n' % (name, core) + s[a:end] + '\n#undef %s\n' % name + wsig + body + s[end:])
    Path(V).write_text(s)
wrap('static void R42_DrawPackedWall(const draw_column_vars_t *v)\n{', 'R42_DrawPackedWall', 'R90_DrawPackedWallCore',
     'static void R42_DrawPackedWall(const draw_column_vars_t *v)\n')
wrap('void R_DrawColumnSprite(const draw_column_vars_t *v) {', 'R_DrawColumnSprite', 'R90_DrawColumnSpriteCore',
     'void R_DrawColumnSprite(const draw_column_vars_t *v)\n')
wrap('void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){', 'R_DrawColumnFlat', 'R90_DrawColumnFlatCore',
     'void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v)\n', pre='c,')

# R59 source test: palettes for CRAM are the explicit top tables now
patch('scripts/lab/test_r59_colorview.py', '"R59_CURRENT.pal0","R59_CURRENT.pal1",', '"R59_TOP.pal0","R59_TOP.pal1",')
patch('scripts/lab/test_r59_colorview.py', 'assert "#define R79_PAL0 (R59_CURRENT.pal0)" in video', 'assert "#define R79_PAL0 (R59_TOP.pal0)" in video')
patch('scripts/lab/test_r59_colorview.py', 'assert "#define R79_PAL1 (R59_CURRENT.pal1)" in video', 'assert "#define R79_PAL1 (R59_TOP.pal1)" in video')

# (e) attribute bits follow the clear
patch(V, 'static void R47_ClearPairBuffer(void)\n{',
'''static void R90_ClearPairBufferCore(void);
static void R47_ClearPairBuffer(void)
{
    R90_ClearPairBufferCore(); r90_s.live=0; R90_SetAttr(_g_gamestate==GS_LEVEL);
}
static void R90_ClearPairBufferCore(void)
{''')
s = Path(V).read_text()
if 'void *R81_SaveScratch(void){R20_StopVideo();return r22_fb.pixels;}' in s:
    patch(V, 'void *R81_SaveScratch(void){R20_StopVideo();return r22_fb.pixels;}',
             'void *R81_SaveScratch(void){R20_StopVideo();r90_s.live=0;return r22_fb.pixels;}')

# (f) attribute toggle, VBlank CRAM and HUD-restoring HInt
Path(V).write_text(Path(V).read_text() + '''
/* ---- R90 split palettes ---------------------------------------------------------------- */
#if !defined(HINTERRUPT_CALLBACK)
#error R90 split needs SGDK >= 1.80 (HInt vector jumps straight to the callback)
#endif
#if (R90_SPLIT_ROW & 1) || (R90_SPLIT_ROW < 2) || (R90_SPLIT_ROW >= R22_H) || (R22_FB_BYTES != 22u*152u)
#error R90_SPLIT_ROW must be an even sample row inside the view
#endif
static void R90_SetAttr(uint8_t on)
{
    on=(on!=0);
    if(on==r90_s.live) return;
    uint16_t sr; __asm__ volatile("move.w %%sr,%0\\n\\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");
    /* Pair-V framebuffer: 22 tile rows of 76 words (38 A + 38 B); the high byte comes first. */
    uint8_t *p=r22_fb.pixels+(uint16_t)(R90_SPLIT_ROW/2u)*152u;
    for(uint16_t i=(uint16_t)((R22_H-R90_SPLIT_ROW)/2u*76u);i;--i,p+=2)
        *p=on?(uint8_t)(*p|0x40u):(uint8_t)(*p&~0x40u);
    r90_s.live=on;
    __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");
}
HINTERRUPT_CALLBACK R90_HInt(void)
{
    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;
    volatile uint32_t *data=(volatile uint32_t*)0xC00000;
    const uint32_t *f=(const uint32_t*)(const void*)hudw_fpal, *b=(const uint32_t*)(const void*)hudw_pal;
    *ctrl=0x8F02;
    *(volatile uint32_t*)ctrl=0xC0400000u;          /* CRAM 0x40: lines 2 and 3 */
    data[0]=f[0];data[0]=f[1];data[0]=f[2];data[0]=f[3];data[0]=f[4];data[0]=f[5];data[0]=f[6];data[0]=f[7];
    data[0]=b[0];data[0]=b[1];data[0]=b[2];data[0]=b[3];data[0]=b[4];data[0]=b[5];data[0]=b[6];data[0]=b[7];
}
void R90_VBlank(void)
{
    if(_g_gamestate==GS_LEVEL && *(volatile uint8_t*)&r90_s.live){
        volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;
        volatile uint32_t *data=(volatile uint32_t*)0xC00000;
        const R59ColorTables *t=&r90_bottom_tables[r59_color_mode];
        const uint32_t *p0=(const uint32_t*)(const void*)t->pal0[r77_last_palette];
        const uint32_t *p1=(const uint32_t*)(const void*)t->pal1[r77_last_palette];
        *ctrl=0x8F02;
        *(volatile uint32_t*)ctrl=0xC0400000u;
        for(uint16_t i=0;i<8u;i++) data[0]=p0[i];
        for(uint16_t i=0;i<8u;i++) data[0]=p1[i];
        VDP_setHIntCounter((uint8_t)(R57_YEND*4u-1u));
        if(!r90_s.hint){ SYS_setHIntCallback(R90_HInt); VDP_setHInterrupt(TRUE); r90_s.hint=1; }
    } else if(r90_s.hint){
        /* The HInt of the previous frame already restored the HUD palettes. */
        VDP_setHInterrupt(FALSE); r90_s.hint=0;
    }
}
''')
patch('src/i_genesis.c', 'static void I_VBlankCallback(void)\n{',
      'void R90_VBlank(void);\nstatic void I_VBlankCallback(void)\n{')
patch('src/i_genesis.c', '    R20_VBlankVideo();\n#if defined(DOOM_R20_STACKGUARD)',
      '    R20_VBlankVideo();\n    R90_VBlank();\n#if defined(DOOM_R20_STACKGUARD)')

# (g) name and evidence
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r89-'" in s and "('ai-menu',0)" in s
s = s.replace("'r89-'", "'r90-'").replace("('ai-menu',0)", "(%r,0)" % TAG)
a = "        for table in ('r56_tables.h', 'r59_color_tables.h'):"
assert s.count(a) == 1
s = s.replace(a, "        shutil.copy2(work/'src/r90_split_report.json',dest/(name+'-r90-split-report.json'))\n"
                 "        for table in ('r56_tables.h', 'r59_color_tables.h', 'r90_split_tables.h'):")
p.write_text(s)
print('R90 split palettes: lower view on PAL2/PAL3; ROM name r90-%s' % TAG)
