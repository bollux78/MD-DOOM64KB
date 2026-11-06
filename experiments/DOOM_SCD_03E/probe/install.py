"""Install the optional startup probe into a disposable R128 build checkout."""
from pathlib import Path
import shutil
import subprocess

here = Path(__file__).resolve().parent
tools = Path.home() / "mars/m68k-elf/bin"
transport = here.parents[1] / "DOOM_SCD_Bench03D_Transport" / "tools"
subprocess.run([tools / "m68k-elf-as", "-m68000", here / "sub.s", "-o", "scd-sub.o"], check=True)
subprocess.run([tools / "m68k-elf-ld", "-Ttext=0", "-e", "0", "-o", "scd-sub.elf", "scd-sub.o"], check=True)
subprocess.run([tools / "m68k-elf-objcopy", "-O", "binary", "scd-sub.elf", "scd-sub.bin"], check=True)
subprocess.run(["python3", transport / "make_sub_header.py", "scd-sub.bin", "src/scd_probe_sub.h"], check=True)
for name in ("scd_probe.c", "scd_probe.h"):
    shutil.copyfile(here / name, Path("src") / name)


def replace(path, old, new):
    path = Path(path)
    content = path.read_text()
    assert content.count(old) == 1, (path, old)
    path.write_text(content.replace(old, new))


replace("src/i_genesis.c", "\tD_DoomMain(argc, argv);",
        "\tSCD_Probe();\n\tD_DoomMain(argc, argv);")
replace("src/i_genesis.c", '#include "d_main.h"',
        '#include "d_main.h"\n#include "scd_probe.h"')
replace("src/d_main.c", '#include "d_main.h"',
        '#include "d_main.h"\n#include "scd_probe.h"\n#include "i_vtext.h"')
replace("src/d_main.c", "\tV_DrawRawFullScreen(titlepicnum);",
        '\tV_DrawRawFullScreen(titlepicnum);\n'
        '\tV_DrawString(1, 1, 12, scd_available ? "SEGA CD: ON" : "SEGA CD: OFF");')
