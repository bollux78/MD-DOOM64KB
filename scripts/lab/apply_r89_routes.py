#!/usr/bin/env python3
"""Isolated renderer/process experiments on approved R89; no AI changes."""
from pathlib import Path
import os
mode=os.environ['R89_ROUTE']
MODES=('control','cull','clip','cache','rom','map','spatial','video','all')
assert mode in MODES,mode
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:90],s.count(a));p.write_text(s.replace(a,b))
def selected(x):return mode in (x,'all')
f='src/m_text.c'
# Same menu in control and every candidate. Symbolic parent indices survive insertion.
patch(f,'  newgame = 0,','  newgame = 0,\n#if defined(DOOM_R59_COLOR_VIEW)\n  quick_color,\n#endif')
patch(f,'  {1,"New Game",  M_NewGame},','  {1,"New Game",  M_NewGame},\n#if defined(DOOM_R59_COLOR_VIEW)\n  {2,"Color mode:", M_ChangeColorMode},\n#endif')
patch(f,'  (R22_TEXTWIDTH - 9) / 2,8,','  5,6,')
patch(f,'\tV_DrawString((R22_TEXTWIDTH - 4) / 2, 1, 14, "DOOM");','''\tV_DrawString((R22_TEXTWIDTH - 4) / 2, 1, 14, "DOOM");
#if defined(DOOM_R59_COLOR_VIEW)
    static const char names[6][12]={"CM6        ","Balanced   ","Tolerant   ","Accents    ","A4 Tolerant","A4 Accents "};
    V_DrawString(MainDef.x+12,MainDef.y+LINEHEIGHT*quick_color,12,names[R59_ColorMode()]);
#endif''')
patch(f,'  &MainDef,1,','  &MainDef,options,')
# Keep Options shortcut as well, useful to existing users.
f='src/r_draw.c'
if selected('cull'):
 patch(f,'    // store information in a vissprite\n    vissprite_t* vis = R_NewVisSprite ();','''#if defined(DOOM_R57_CROP16)
    /* Reject before allocating one of the eight world-sprite slots. */
    if (R57_CROP_ACTIVE && (x1 >= R57_XEND || x2 < R57_XMIN)) return;
#endif
    // store information in a vissprite
    vissprite_t* vis = R_NewVisSprite ();''')
if selected('clip'):
 p=Path(f);s=p.read_text();a=s.index('static void R_DrawSprite (');b=s.index('\n/*',a)
 chunk=s[a:b];chunk=chunk.replace('spr->x1','left').replace('spr->x2','right')
 chunk=chunk.replace('    int16_t* clipbot = floorclip;','''    int16_t left=spr->x1,right=spr->x2;
#if defined(DOOM_R57_CROP16)
    if(R57_CROP_ACTIVE){
        if(left<R57_XMIN)left=R57_XMIN;
        if(right>=R57_XEND)right=R57_XEND-1;
    }
#endif
    if(left>right)return;
    const fixed_t gzt=spr->gz+(((int32_t)spr->patch_topoffset)<<FRACBITS);
    int16_t* clipbot = floorclip;''')
 chunk=chunk.replace('        fixed_t gzt = spr->gz + (((int32_t)spr->patch_topoffset) << FRACBITS);','')
 s=s[:a]+chunk+s[b:];p.write_text(s)
if selected('cache'):
 needle='#if defined(DOOM_R20_COMPOSITE_HOIST)\n    uint16_t cachekey = R20_FindComposite(prepared, xc);'
 patch(f,needle,'''#if defined(DOOM_R39C_REUSE_CACHE) && !defined(DOOM_SRAM_HOT_SLOTS)
    if(r39c_tmpValid && r39c_tmpEntry==CACHE_ENTRY(xc,texture)) {
#if defined(DOOM_CACHE_STATS)
        doom_cache_hits++;
#endif
        return tmpCache;
    }
#endif
'''+needle)
if selected('rom'):
 patch(f,'static uint8_t r39c_tmpValid;','''static uint8_t r39c_tmpValid;
/* Logical contents of tmpCache can live in ROM until a partial write needs them. */
static const byte *r89_rom_pending;''')
 patch(f,'    r39c_tmpValid=0;','    r39c_tmpValid=0; r89_rom_pending=NULL;')
 patch(f,'        if(baked!=0xffffffffUL)memcpy(tmpCache,r84_pixels+baked,128);\n        else {','''        if(baked!=0xffffffffUL){memcpy(tmpCache,r84_pixels+baked,128);r89_rom_pending=NULL;}
        else {
        if(r89_rom_pending){memcpy(tmpCache,r89_rom_pending,128);r89_rom_pending=NULL;}''')
 needle='''#if defined(DOOM_SRAM_CACHE16) || defined(DOOM_R23_MAPMEM)
    /* Do not alter SRAM's 16-slot hash/replacement scheme.'''
 patch(f,needle,'''    if(cacheEntry==wantedEntry){
        uint32_t baked=r84_offsets[r84_starts[texture]+((uint16_t)xc>>2)];
        if(baked!=0xffffffffUL){
            r89_rom_pending=r84_pixels+baked;
            r39c_tmpValid=0;
            return r89_rom_pending;
        }
        /* SRAM reads shorter than 128 preserve the tail of the previous column. */
        if(r89_rom_pending){memcpy(tmpCache,r89_rom_pending,128);r89_rom_pending=NULL;}
    }
'''+needle)
if selected('map'):
 # ROM-only line records: natural two-byte alignment and power-of-two stride.
 patch('src/r_defs.h','typedef PACKEDATTR_PRE struct line_s','typedef struct line_s')
 patch('src/r_defs.h','} PACKEDATTR_POST line_t;','} line_t;')
 patch('src/r_defs.h','sizeof(line_t) == 31','sizeof(line_t) == 32')
 needle='    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1'
 patch('scripts/lab/build_r35_linear.fish',needle,needle+'\n    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1')
 # Optional SRAM emulator regression understands the candidate's ROM stride.
 p=Path('scripts/lab/test_r81_rom.py');s=p.read_text().replace('lines+31*index','lines+32*index');p.write_text(s)
if selected('spatial'):
 patch('src/r23_mapmem.h','void R23_MapMemoryInit(', 'int R89_VisitLine(void *p,uint16_t count);\nvoid R23_MapMemoryInit(')
 patch('src/r23_mapmem.c','uint32_t R23_MapRead(','''/* Called only for linedata tokens; one mapper window for test-and-set. */
int R89_VisitLine(void *p,uint16_t count){
    uint32_t a=R22_SRAM_BASE+1+2UL*(line_base+(uintptr_t)p-0x210000UL+offsetof(linedata_t,validcount));
    R25_SRAM_BEGIN();
    uint16_t old=R39C_MovepRead16(a);
    if(old!=count)R39C_MovepWrite16(a,count);
    R25_SRAM_END();
    return old!=count;
}
uint32_t R23_MapRead(''')
 patch('src/p_maputl.c','''        if (R23_GET(ld,validcount) == vcount)
            continue;       // line has already been checked

        R23_SET(ld,validcount,vcount);''','''#if defined(DOOM_R23_MAPMEM)
        if(!R89_VisitLine(ld,vcount))continue;
#else
        if(ld->validcount==vcount)continue;
        ld->validcount=vcount;
#endif''')
if selected('video'):
 f='src/r22_video.inc'
 needle='    for(uint16_t y=first_row;y<end_row;y++,srca+=76,srcb+=76,dsta+=128,dstb+=128){'
 patch(f,needle,'''    /* Framebuffer is wholly in the 64-KiB WRAM window: source high is constant.
     * DMA consumes length to zero; every row has fewer than 256 words. */
    *ctrl=0x9400;
    *ctrl=0x9700|((((uint32_t)(uintptr_t)srca)>>17)&127);
    uint32_t source_word=((uint32_t)(uintptr_t)srca)>>1;
    for(uint16_t y=first_row;y<end_row;y++,source_word+=76,dsta+=128,dstb+=128){''')
 p=Path(f);s=p.read_text();a=s.index('    /* Framebuffer is wholly');b=s.index('\n#else\n    #if defined(DOOM_R22_SOLID_TILES)',a);chunk=s[a:b]
 chunk=chunk.replace('uint32_t a=((uint32_t)(uintptr_t)srca)>>1;','uint32_t a=source_word;').replace('a=((uint32_t)(uintptr_t)srcb)>>1;','a=source_word+38;')
 chunk=chunk.replace('*ctrl=0x9300|words_per_row;*ctrl=0x9400;','*ctrl=0x9300|words_per_row;').replace(';*ctrl=0x9700|((a>>16)&127);',';')
 # This source relation is specific to the approved Pair-V format.
 chunk='#if !defined(DOOM_R48_PAIR_V)\n#error R89 video route requires Pair-V\n#endif\n'+chunk
 p.write_text(s[:a]+chunk+s[b:])
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text();assert "('ai-menu',0)" in s;s=s.replace("('ai-menu',0)",repr((mode,0)));p.write_text(s)
print('R89 route',mode,'on approved R89, quick colors, original AI and visuals')
