#!/usr/bin/env python3
"""Apply playable Freedoom support to the isolated R128 + R133 + R135b build."""
import re
from pathlib import Path


def replace(file, old, new, count=1):
    path = Path(file)
    source = path.read_text()
    assert source.count(old) == count, (file, old, source.count(old))
    path.write_text(source.replace(old, new))


WAD_HEADER = 'src/w_wad.h'
replace(WAD_HEADER, 'void W_Init(void);', '''void W_Init(void);

#define R136_EXTRA_MAP 10
void W_SelectLevelWad(int16_t map);
int16_t W_GetLevelNumForName(const char *name);
uint16_t W_LevelLumpLength(int16_t num);
const void *W_GetLevelLumpByNum(int16_t num);
#define W_GetLevelLumpByName(name) W_GetLevelLumpByNum(W_GetLevelNumForName(name))''')

wad = Path('src/w_wad.c')
wad.write_text(wad.read_text() + '''
/* Page 8 mirrors all linked slot 7 data below $3d0000. Only level reads
 * can see the separate WAD there. Existing renderer WAD access stays intact. */
#define R136_MAP_WAD ((const uint8_t *)0x003D0000UL)
static const filelump_t *level_lumps;
static const uint8_t *level_wad;
static int16_t level_lump_count;

void W_SelectLevelWad(int16_t map)
{
    const int extra = map == R136_EXTRA_MAP;
    *(volatile uint8_t *)0x00A130FFUL = extra ? 8 : 7;
    level_wad = extra ? R136_MAP_WAD : doom_iwad;
    if (extra && *(const volatile uint32_t *)R136_MAP_WAD != 0x49574144UL)
        I_Error("FREEDOOM BANK UNAVAILABLE");
    const wadinfo_t *header = (const wadinfo_t *)level_wad;
    level_lumps = (const filelump_t *)(level_wad + header->infotableofs);
    level_lump_count = header->numlumps;
}

int16_t W_GetLevelNumForName(const char *name)
{
    char key[8] = {0};
    strncpy(key, name, sizeof(key));
    for (int16_t i = 0; i < level_lump_count; i++)
        if (Z_EqualNames(level_lumps[i].name, key))
            return i;
    I_Error("W_GetLevelNumForName: %.8s not found", name);
    return -1;
}

uint16_t W_LevelLumpLength(int16_t num)
{
    return level_lumps[num].size;
}

const void *W_GetLevelLumpByNum(int16_t num)
{
    return level_wad + level_lumps[num].filepos;
}
''')

for file in ('src/p_setup.c', 'src/r24_romthings.c'):
    path = Path(file)
    source = path.read_text()
    for name, level_name in (
        ('W_GetNumForName', 'W_GetLevelNumForName'), ('W_LumpLength', 'W_LevelLumpLength'),
        ('W_GetLumpByNum', 'W_GetLevelLumpByNum'), ('W_GetLumpByName', 'W_GetLevelLumpByName'),
    ):
        source = re.sub(rf'\b{name}(?=\s*\()', level_name, source)
    path.write_text(source)

SETUP = 'src/p_setup.c'
replace(SETUP, '    P_FreeLevelData();\n    R22_MapMark', '    P_FreeLevelData();\n    W_SelectLevelWad(map);\n    R22_MapMark')
for name in ('SUBS', 'LINES', 'SOUND', 'OFFS'):
    replace(SETUP, f'"S%d{name}",_g_gamemap', f'"S%d{name}",_g_gamemap == R136_EXTRA_MAP ? 0 : _g_gamemap')
replace('src/r24_romthings.c', '    char name[9];mapthings=', '    if (map == R136_EXTRA_MAP) map = 0;\n    char name[9];mapthings=')

MENU = 'src/m_text.c'
replace(MENU, 'static void M_NewGame(int16_t choice);', 'static void M_NewGame(int16_t choice);\nstatic void M_ExtraMaps(int16_t choice);')
replace(MENU, '  r81_cheats,\n  main_end', '  r81_cheats,\n  extra_maps,\n  main_end')
replace(MENU, '  {1,"Cheats", R81_OpenCheats},', '  {1,"Cheats", R81_OpenCheats},\n  {1,"Extra Maps", M_ExtraMaps},')
replace(MENU, 'static void M_NewGame(int16_t choice)\n{', '''static void M_ChooseExtraMap(int16_t choice)
{
    UNUSED(choice);
    r24_start_map = R136_EXTRA_MAP;
    M_SetupNextMenu(&NewDef);
    itemOn = 2;
}

static void M_DrawExtraMaps(void)
{
    V_DrawString(10, 2, 12, "EXTRA MAPS");
}

static const menuitem_t ExtraMapMenu[] = {{1, "Freedoom E1M1", M_ChooseExtraMap}};
static const menu_t ExtraMapDef = {1, ExtraMapMenu, M_DrawExtraMaps, 6, 8, &MainDef, extra_maps};

static void M_ExtraMaps(int16_t choice)
{
    UNUSED(choice);
    M_SetupNextMenu(&ExtraMapDef);
    itemOn = 0;
}

static void M_NewGame(int16_t choice)
{''')

GAME = 'src/g_game.c'
replace(GAME, '    if (map > 9)\n        map = 9;', '    if (map > 9 && map != R136_EXTRA_MAP)\n        map = 9;')
replace(GAME, '    G_PlayerFinishLevel();        // take away cards and stuff', '''    if (_g_gamemap == R136_EXTRA_MAP)
    {
        D_StartTitle();
        return;
    }

    G_PlayerFinishLevel();        // take away cards and stuff''')
replace('src/hu_text.c', 'mapnames[_g_gamemap - 1]', 'mapname', 2)
replace('src/hu_text.c', '\tw_title.len       = strlen(mapname);', '''    const char *mapname = _g_gamemap == R136_EXTRA_MAP ? "Freedoom E1M1" : mapnames[_g_gamemap - 1];
\tw_title.len       = strlen(mapname);''')
replace('src/s_sound.c', '    mnum = mus_e1m1 + _g_gamemap-1;', '    mnum = _g_gamemap == R136_EXTRA_MAP ? mus_e1m1 : mus_e1m1 + _g_gamemap - 1;')
replace('src/r81_save_core.inc', ' r81_io_t io;memset(&io,0,sizeof(io));io.objects=R81_SaveScratch();',
        ' if(_g_gamemap==R136_EXTRA_MAP)return "SAVE UNAVAILABLE IN EXTRA MAPS";\n r81_io_t io;memset(&io,0,sizeof(io));io.objects=R81_SaveScratch();')

# A 182-sector REJECT matrix already exceeds INT16_MAX in bit indices.
# The engine's <255-sector limit keeps the full index in an unsigned word.
replace('src/p_sight.c', '  int16_t pnum = (s1-_g_sectors)*_g_numsectors + (s2-_g_sectors);',
        '  uint16_t pnum = (uint16_t)(s1-_g_sectors) * (uint16_t)_g_numsectors + (uint16_t)(s2-_g_sectors);')

BOOT = 'src/d_main.c'
replace(BOOT, '/* The first 4MiB hold the Doom engine/data. Slot 7 is remapped\n'
        '   ONLY during this boot check, before title/gameplay begins.\n'
        '   Extra pages 8 and 9 contain synthetic distinct signatures. */\n'
        '#define R133_SLOT7 (*(volatile uint16_t *)(0x380100ul))',
        '''/* Signatures live past the mirrored base data and the converted WAD. */
volatile uint8_t r136_boot_result;
#define R136_SIGNATURE (*(volatile uint32_t *)0x003FFFF0UL)''')
replace(BOOT, '*(volatile uint32_t *)(0x380100ul)', 'R136_SIGNATURE', 5)
replace(BOOT, '    R133_MAPREG=8;\n    if(R136_SIGNATURE!=R133_Signature(8))ok8=0;',
        '''    R133_MAPREG=8;
    if(R136_SIGNATURE!=R133_Signature(8))ok8=0;
    const uint16_t map_ok = *(const volatile uint32_t *)0x003D0000UL == 0x49574144UL;''')
replace(BOOT, '    VDP_setScreenWidth320();\n    VDP_clearPlane(BG_A,TRUE);', '''    r136_boot_result = ok8 | (ok9 << 1) | (okstress << 2) | (okrestore << 3) | (map_ok << 4);
    VDP_setScreenWidth320();
    VDP_clearPlane(BG_A,TRUE);''')
replace(BOOT, '    VDP_drawText("STARTING DOOM...",10,22);', '''    VDP_drawText(map_ok ? "FREEDOOM E1M1: PASS" : "FREEDOOM E1M1: FAIL", 2, 21);
    VDP_drawText("STARTING DOOM...",10,24);''')
# R136b: the 64-entry list is needed after the BSP pass for sprites and
# masked textures. Opaque geometry and planes must still cover the frame.
renderer = Path('src/r_draw.c')
source = renderer.read_text()
start = source.index('static void R_StoreWallRange(')
end = source.index('static void R_RecalcLineFlags(', start)
wall = source[start:end]
wall = wall.replace('ds_p->', 'ds->')
assert wall.count("    // don't overflow and crash\n") == 1
wall = wall.replace("    // don't overflow and crash\n", '''    const boolean extra_map = _g_gamemap == R136_EXTRA_MAP;
    drawseg_t overflow_drawseg;
    drawseg_t *ds = ds_p;
''')
old = '''    if (ds_p == &_s_drawsegs[MAXDRAWSEGS])
    {
#if defined(RANGECHECK)
        I_Error("Drawsegs overflow.");
#endif
        return; /* R126b: drop the extra wall for this frame */
    }'''
new = '''    if (ds == &_s_drawsegs[MAXDRAWSEGS])
    {
        if (!extra_map)
        {
#if defined(RANGECHECK)
            I_Error("Drawsegs overflow.");
#endif
            return;
        }
        ds = &overflow_drawseg;
    }'''
assert wall.count(old) == 1
wall = wall.replace(old, new)
old = '''    //Openings overflow. Nevermind.
    if(!R_CheckOpenings(start))
        return;'''
new = '''    boolean keep_drawseg = ds != &overflow_drawseg;
    if (extra_map)
    {
        /* Worst case: one masked column and both sprite clips per column. */
        if (lastopening - openings + 3 * (rw_stopx - start) > MAXOPENINGS)
            keep_drawseg = false;
    }
    else if (!R_CheckOpenings(start))
        return;'''
assert wall.count(old) == 1
wall = wall.replace(old, new)
old = 'if (R27_SIDE(sidedef,midtexture))    // masked midtexture'
assert wall.count(old) == 1
wall = wall.replace(old, 'if (keep_drawseg && R27_SIDE(sidedef,midtexture))')
old = '    R_RenderSegLoop(rw_x, segtextured, markfloor, markceiling);'
assert wall.count(old) == 1
wall = wall.replace(old, old + '''
    if (!keep_drawseg)
        return;
''')
old = '    ds_p++;'
assert wall.count(old) == 1
wall = wall.replace(old, '''    /* Invisible to both consumers of the list: reuse the entry. */
    if (!extra_map || ds->silhouette || ds->maskedtexturecol)
        ds_p++;''')
renderer.write_text(source[:start] + wall + source[end:])
print('R136 banked level loader and Extra Maps applied')
