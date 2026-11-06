"""Install the isolated logic coprocessor probes into the R128 build."""
from pathlib import Path
import shutil
import subprocess

here = Path(__file__).resolve().parent
tools = Path.home() / "mars/m68k-elf/bin"
transport = here.parents[1] / "DOOM_SCD_Bench03D_Transport" / "tools"
subprocess.run([tools / "m68k-elf-as", "-m68000", here / "sub.s",
                "-o", "scd-sub.o"], check=True)
subprocess.run([tools / "m68k-elf-gcc", "-m68000", "-O2", "-fwrapv",
                "-ffreestanding", "-fno-builtin", "-c", here / "sub_logic.c",
                "-o", "scd-logic.o"], check=True)
subprocess.run([tools / "m68k-elf-gcc", "-m68000", "-nostdlib", "-Wl,-Ttext=0,-e,0",
                "-o", "scd-sub.elf", "scd-sub.o", "scd-logic.o", "-lgcc"], check=True)
subprocess.run([tools / "m68k-elf-objcopy", "-O", "binary", "scd-sub.elf",
                "scd-sub.bin"], check=True)
subprocess.run(["python3", transport / "make_sub_header.py", "scd-sub.bin",
                "src/scd_probe_sub.h"], check=True)
for filename in ("main_logic.c", "logic_packet.h"):
    shutil.copyfile(here / filename, Path("src") / filename)


def replace(filename, old, new):
    path = Path("src") / filename
    source = path.read_text()
    assert source.count(old) == 1, (filename, old)
    path.write_text(source.replace(old, new))


def include(filename, header):
    replace(filename, f'#include "{header}"',
            f'#include "{header}"\n#include "logic_packet.h"')


include("i_genesis.c", "d_main.h")
replace("i_genesis.c", "\tD_DoomMain(argc, argv);",
        "\tSCD_Probe();\n\tD_DoomMain(argc, argv);")
include("d_main.c", "d_main.h")
replace("d_main.c", "\tV_DrawRawFullScreen(titlepicnum);", '''\tV_DrawRawFullScreen(titlepicnum);
    {
        const uint8_t mode = scd_logic_mode & 7u;
        const char *label = !mode ? "SCD LOGIC: NATIVE" :
                            !scd_available ? "SCD LOGIC: FALLBACK" :
                            mode == SCD_SIGHT ? "SCD LOGIC: SIGHT" :
                            mode == SCD_SOUND ? "SCD LOGIC: SOUND" :
                            mode == SCD_RAYS ? "SCD LOGIC: RAYS" : "SCD LOGIC: ALL";
        V_DrawString(1, 1, 12, label);
    }''')
replace("d_main.c", '#include "logic_packet.h"',
        '#include "logic_packet.h"\n#include "i_vtext.h"')

include("p_setup.c", "p_setup.h")
replace("p_setup.c", "void P_SetupLevel(int16_t map)\n{",
        "void P_SetupLevel(int16_t map)\n{\n    scd_logic_loaded = 0;")

include("p_sight.c", "globdata.h")
replace("p_sight.c", "boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)", '''
/* Keep the original per-line/portal clipping and validcount writes on the MD. */
static int SCD_CrossBSP(void)
{
    if (!scd_available || !(scd_logic_mode & SCD_SIGHT) ||
        numnodes <= 0 || numnodes > MAX_NODES)
        return -1;
    volatile LogicPacket *p = SCD_LogicPacket();
    if (!(scd_logic_loaded & SCD_SIGHT))
    {
        for (uint16_t i = 0; i < numnodes; ++i)
        {
            const mapnode_t __far *node = &nodes[i];
            p->data.nodes[i] = (LogicNode){node->x, node->y, node->dx, node->dy,
                                          {node->children[0], node->children[1]}};
        }
        if (!SCD_LogicCall(LOAD_NODES, numnodes))
            return -1;
        scd_logic_loaded |= SCD_SIGHT;
    }
    p->data.sight.x1 = los.strace.x;
    p->data.sight.y1 = los.strace.y;
    p->data.sight.x2 = los.t2x;
    p->data.sight.y2 = los.t2y;
    if (!SCD_LogicCall(SIGHT_BSP, 0) || !p->result || p->result > MAX_LEAVES)
        return -1;
    for (uint16_t i = 0; i < p->result; ++i)
        if (!P_CrossSubsector(p->data.sight.leaf[i]))
            return 0;
    return 1;
}

boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)''')
replace("p_sight.c", "  prevr = P_CrossBSPNode(numnodes-1);",
        "  const int result = SCD_CrossBSP();\n"
        "  prevr = result < 0 ? P_CrossBSPNode(numnodes-1) : result;")

include("p_pspr.c", "globdata.h")
replace("p_pspr.c", "static void P_NoiseAlert(mobj_t __far* emitter)", '''
static int SCD_AlertSectors(sector_t __far *source, mobj_t __far *emitter)
{
    if (!scd_available || !(scd_logic_mode & SCD_SOUND) ||
        _g_numsectors <= 0 || _g_numsectors > MAX_SECTORS)
        return 0;
    volatile LogicPacket *p = SCD_LogicPacket();
    if (!(scd_logic_loaded & SCD_SOUND))
    {
        uint16_t count = 0;
        for (int16_t i = 0; i < _g_numlines; ++i)
        {
            const line_t __far *line = &_g_maplines[i];
            if (!(line->flags & ML_TWOSIDED) || line->sidenum[1] == NO_INDEX)
                continue;
            if (count == MAX_PORTALS)
                return 0;
            const uint16_t a = LN_FRONTSECTOR(line) - _g_sectors;
            const uint16_t b = LN_BACKSECTOR(line) - _g_sectors;
            p->data.portals[count++] = (LogicPortal){a, b, !!(line->flags & ML_SOUNDBLOCK)};
        }
        p->origin = _g_numsectors;
        if (!SCD_LogicCall(LOAD_PORTALS, count))
            return 0;
        scd_logic_loaded |= SCD_SOUND;
    }
    for (int16_t i = 0; i < _g_numsectors; ++i)
    {
        const sector_t __far *sector = &_g_sectors[i];
        p->data.sound.height[i] = (LogicHeight){sector->floorheight, sector->ceilingheight};
    }
    p->origin = source - _g_sectors;
    if (!SCD_LogicCall(SOUND_FLOOD, _g_numsectors))
        return 0;
    for (int16_t i = 0; i < _g_numsectors; ++i)
    {
        const uint8_t cost = p->data.sound.visited[i];
        if (cost)
        {
            sector_t __far *sector = &_g_sectors[i];
            sector->validcount = validcount;
            sector->soundtraversed = cost;
            sector->soundtarget = emitter;
        }
    }
    return 1;
}

static void P_NoiseAlert(mobj_t __far* emitter)''')
replace("p_pspr.c", "  P_RecursiveSound(SUBSECTOR_SECTOR(emitter->subsector), 0, emitter);",
        "  sector_t __far *source = SUBSECTOR_SECTOR(emitter->subsector);\n"
        "  if (!SCD_AlertSectors(source, emitter))\n"
        "    P_RecursiveSound(source, 0, emitter);")

include("p_maputl.c", "globdata.h")
replace("p_maputl.c", "static int8_t R126_VisitPending(traverser_t func)\n{",
        '''static int8_t R126_VisitPending(traverser_t func)
{
  const int16_t count = intercept_p - intercepts;
  if (scd_available && (scd_logic_mode & SCD_RAYS) &&
      count >= 2 && count <= MAX_INTERCEPTS)
    {
      volatile LogicPacket *p = SCD_LogicPacket();
      for (int16_t i = 0; i < count; ++i)
        p->data.ray.frac[i] = intercepts[i].frac;
      if (SCD_LogicCall(SORT_INTERCEPTS, count))
        {
          for (uint16_t i = 0; i < p->result; ++i)
            {
              intercept_t *in = &intercepts[p->data.ray.order[i]];
              if (!func(in))
                return 0;
              in->frac = INT32_MAX;
            }
          if (p->origin)
            return 1;
          intercept_p = intercepts;
          return 2;
        }
    }''')
