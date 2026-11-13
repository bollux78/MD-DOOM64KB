#!/usr/bin/env python3
"""Build maps.h, compile the menu, and compose the SSF2 ROM:
   bank 0 = menu (512 KB), then each map image padded to 4 banks (2 MB)."""
import subprocess, sys, os
D = os.path.dirname(os.path.abspath(__file__)); os.chdir(D)
T = "/home/claude/mars/m68k-elf/bin/m68k-elf-"
MAPS = [("E1M1", "E1M1  HANGAR"), ("E1M2", "E1M2  NUCLEAR PLANT"), ("E1M4", "E1M4  COMMAND CONTROL"),
        ("E1M5", "E1M5  PHOBOS LAB"), ("E1M9", "E1M9  MILITARY BASE")]
BANK = 0x80000
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/m14x/manifold-doom-menu.bin"
h = ['#define MAP_ENTRY 0x00080200', '#define MAP_COUNT %d' % len(MAPS),
     'struct map_entry { const char *name; unsigned char bank; };',
     'static const struct map_entry maps[] = {']
imgs = []
for i, (m, label) in enumerate(MAPS):
    f = "/tmp/m12/mm_%s/out/release/rom.bin" % m
    data = open(f, "rb").read()
    assert len(data) <= 4 * BANK, (m, len(data))
    imgs.append(data + b"\xff" * (4 * BANK - len(data)))
    h.append('  {"%s", %d},' % (label, 1 + 4 * i))
h.append('};')
# bank self-test table: 8 sample longs per 512 KB slot per map (expected values from the composed images)
import struct
h.append('static const unsigned long bank_expect[%d][4][8] = {' % len(MAPS))
for im in imgs:
    h.append('  {')
    for sl in range(4):
        vals = [struct.unpack(">I", im[sl*BANK + k*0x10000 + 0x1230 : sl*BANK + k*0x10000 + 0x1234])[0] for k in range(8)]
        h.append('    {' + ','.join('0x%08XUL' % v for v in vals) + '},')
    h.append('  },')
h.append('};')
open("maps.h", "w").write("\n".join(h) + "\n")
subprocess.check_call(["python3", "gen_assets.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.check_call([T+"as", "-m68000", "crt0.s", "-o", "/tmp/m14x/crt0.o"])
subprocess.check_call([T+"gcc", "-m68000", "-Os", "-ffreestanding", "-fno-pic", "-nostdlib", "-c", "menu.c", "-o", "/tmp/m14x/menu.o"])
subprocess.check_call([T+"gcc", "-m68000", "-Os", "-ffreestanding", "-fno-pic", "-nostdlib", "-c", "assets.c", "-o", "/tmp/m14x/assets.o"])
subprocess.check_call([T+"ld", "-T", "menu.ld", "/tmp/m14x/crt0.o", "/tmp/m14x/menu.o", "/tmp/m14x/assets.o", "-o", "/tmp/m14x/menu.elf"])
subprocess.check_call([T+"objcopy", "-O", "binary", "/tmp/m14x/menu.elf", "/tmp/m14x/menu.bin"])
menu = open("/tmp/m14x/menu.bin", "rb").read()
assert len(menu) <= BANK, len(menu)
rom = menu + b"\xff" * (BANK - len(menu)) + b"".join(imgs)
open(out, "wb").write(rom)
print("menu bytes", len(menu), "rom bytes", len(rom), "->", out)
