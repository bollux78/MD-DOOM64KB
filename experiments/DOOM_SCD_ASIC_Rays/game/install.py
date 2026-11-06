"""Install the E1M1 async ray experiment in a disposable build."""
from pathlib import Path
import shutil
import subprocess

here = Path(__file__).resolve().parent
asic = here.parent
transport = asic.parent / "DOOM_SCD_Bench03D_Transport" / "tools"
tools = Path.home() / "mars/m68k-elf/bin"
build = Path("build")
build.mkdir(exist_ok=True)
capture = Path.home() / "Projetos/Personal/scd-asic-rays/run-42299359419-1/e1m1-sight.json"
wad = Path("scripts/doom1.wad")
subprocess.run(["python3", asic / "replay/prepare.py", wad, capture, build / "ray-assets.bin", "mixed"], check=True)
subprocess.run([tools / "m68k-elf-as", "-m68000", here / "sub.s", "-o", build / "ray-sub.o"], check=True)
subprocess.run([tools / "m68k-elf-gcc", "-m68000", "-O2", "-ffreestanding", "-fno-builtin",
                "-c", here / "sub_game.c", "-o", build / "ray-game.o"], check=True)
subprocess.run([tools / "m68k-elf-gcc", "-m68000", "-nostdlib", "-Wl,-Ttext=0,-e,subcpu_vectors",
                "-o", build / "ray-sub.elf", build / "ray-sub.o", build / "ray-game.o", "-lgcc"], check=True)
subprocess.run([tools / "m68k-elf-objcopy", "-O", "binary", build / "ray-sub.elf",
                build / "ray-sub.bin"], check=True)
subprocess.run(["python3", transport / "make_sub_header.py", build / "ray-sub.bin",
                "src/scd_probe_sub.h"], check=True)
shutil.copyfile(build / "ray-assets.h", "src/ray_origin.h")
for filename in ("ray_game.c", "ray_game.h"):
    shutil.copyfile(here / filename, Path("src") / filename)


def replace(filename, old, new):
    path = Path("src") / filename
    source = path.read_text()
    assert source.count(old) == 1, (filename, old)
    path.write_text(source.replace(old, new))


def include(filename, header):
    replace(filename, f'#include "{header}"', f'#include "{header}"\n#include "ray_game.h"')


include("i_genesis.c", "d_main.h")
replace("i_genesis.c", "\tD_DoomMain(argc, argv);", "\tSCD_RayBoot();\n\tD_DoomMain(argc, argv);")
include("d_main.c", "d_main.h")
replace("d_main.c", '#include "ray_game.h"', '#include "ray_game.h"\n#include "i_vtext.h"')
replace("d_main.c", "\tV_DrawRawFullScreen(titlepicnum);", '''\tV_DrawRawFullScreen(titlepicnum);
    V_DrawString(1, 1, 12, !(scd_ray_mode & 1u) ? "SCD SIGHT: NATIVE" :
                 scd_ray_available ? "SCD SIGHT: ASIC" : "SCD SIGHT: FALLBACK");''')

include("p_tick.c", "globdata.h")
replace("p_tick.c", "               // not if this is an intermission screen",
        "  SCD_RayBegin(_g_gametic, _g_gamemap);\n"
        "               // not if this is an intermission screen")
replace("p_tick.c", "  P_MapEnd();", "  P_MapEnd();\n  SCD_RayEnd();")

include("p_sight.c", "globdata.h")
replace("p_sight.c", '#include "ray_game.h"', '#include "ray_game.h"\n#include "d_player.h"')
signature = "boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)"
replace("p_sight.c", signature, "static " + signature.replace("P_CheckSight", "P_CheckSightNative"))
replace("p_sight.c", "  // An unobstructed LOS is possible.",
        """  /* Cache, REJECT and the same-subsector shortcut have priority. */
  if ((scd_ray_mode & 1u) && scd_ray_available && t2 == _g_player.mo &&
      (t1->flags & MF_COUNTKILL) &&
      SCD_RayQuery((uintptr_t)t1, t1->x, t1->y, t2->x, t2->y))
  {
    prevr = false;
    return false;
  }

  // An unobstructed LOS is possible.""")
with Path("src/p_sight.c").open("a") as file:
    file.write("""

boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)
{
    if (!scd_ray_profile || !scd_ray_available)
        return P_CheckSightNative(t1, t2);
    const uint16_t start = SCD_RayClock();
    const boolean visible = P_CheckSightNative(t1, t2);
    SCD_RayProfile(start);
    return visible;
}
""")
