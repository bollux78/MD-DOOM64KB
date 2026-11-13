#!/usr/bin/env python3
"""Build maps.h, compile the menu and compose the de-duplicated SSF2 ROM.
   File layout (= CPU address space of the cartridge):
     0x000000  menu (bank 0, fixed slot 0)            | linked by menu.ld
     0x010000  .common block, identical in every map  | slots 0..5, banks 1..5 (identity)
     0x300000+ one block per map (512 KB bank aligned), mapped into slots 6..7
   Each map is linked with md_split.ld (see handoff MANIFOLD-M14-MULTIMAP-4MB.md)."""
import subprocess, sys, os, struct
D = os.path.dirname(os.path.abspath(__file__)); os.chdir(D)
T = "/home/claude/mars/m68k-elf/bin/m68k-elf-"
MAPS = [("E1M1", "E1M1  HANGAR"), ("E1M2", "E1M2  NUCLEAR PLANT"), ("E1M3", "E1M3  TOXIN REFINERY"),
        ("E1M4", "E1M4  COMMAND CONTROL"), ("E1M5", "E1M5  PHOBOS LAB"), ("E1M6", "E1M6  CENTRAL PROC."),
        ("E1M7", "E1M7  COMPUTER STATION"), ("E1M8", "E1M8  PHOBOS ANOMALY"), ("E1M9", "E1M9  MILITARY BASE")]
BANK = 0x80000
COMMON_ORG = 0x10000
MAP_ORG = 0x300000
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/m14x/manifold-doom-menu.bin"
common = None; blocks = []
for m, label in MAPS:
    o = "/tmp/m12/mm_%s/out/release/rom.out" % m
    subprocess.check_call([T+"objcopy", "-O", "binary", "-j", ".common", o, "/tmp/m14x/_c.bin"])
    subprocess.check_call([T+"objcopy", "-O", "binary", "-j", ".maphead", "-j", ".data", "-j", ".mapobjs", o, "/tmp/m14x/_m.bin"])
    c = open("/tmp/m14x/_c.bin", "rb").read(); b = open("/tmp/m14x/_m.bin", "rb").read()
    if common is None: common = c
    assert c == common, "common block differs in " + m
    assert len(b) <= 2 * BANK, (m, len(b))
    blocks.append(b)
assert COMMON_ORG + len(common) <= MAP_ORG, len(common)
rom_tail = b""; banks = []
for b in blocks:
    banks.append((MAP_ORG + len(rom_tail)) // BANK)
    n = (len(b) + BANK - 1) // BANK
    rom_tail += b + b"\xff" * (n * BANK - len(b))
body = bytearray(b"\xff" * MAP_ORG) ; body[COMMON_ORG:COMMON_ORG + len(common)] = common
rom = bytes(body) + rom_tail          # menu is patched in below
# bank self-test table: 8 sample longs per 512 KB slot (1..7) per map
h = ['#define MAP_ENTRY 0x00300200', '#define MAP_COUNT %d' % len(MAPS),
     'struct map_entry { const char *name; unsigned char bank; };', 'static const struct map_entry maps[] = {']
for (m, label), bk in zip(MAPS, banks): h.append('  {"%s", %d},' % (label, bk))
h.append('};')
h.append('static const unsigned long bank_expect[%d][7][8] = {' % len(MAPS))
for bk in banks:
    h.append('  {')
    for sl in range(1, 8):
        bn = sl if sl <= 5 else bk + (sl - 6)
        vals = [struct.unpack(">I", rom[bn*BANK + k*0x10000 + 0x1230: bn*BANK + k*0x10000 + 0x1234].ljust(4, b"\xff"))[0] for k in range(8)]
        h.append('    {' + ','.join('0x%08XUL' % v for v in vals) + '},')
    h.append('  },')
h.append('};')
open("maps.h", "w").write("\n".join(h) + "\n")
subprocess.check_call(["python3", "gen_music.py"])
subprocess.check_call(["python3", "gen_assets.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.check_call([T+"as", "-m68000", "crt0.s", "-o", "/tmp/m14x/crt0.o"])
for s in ("menu.c", "assets.c", "music_data.c"):
    subprocess.check_call([T+"gcc", "-m68000", "-Os", "-ffreestanding", "-fno-pic", "-nostdlib"] + (["-DAUTO_LAUNCH=" + os.environ["AUTO_LAUNCH"]] if os.environ.get("AUTO_LAUNCH") else []) + (["-DTEST_RESUME"] if os.environ.get("TEST_RESUME") else []) + ["-c", s, "-o", "/tmp/m14x/" + s.replace(".c", ".o")])
subprocess.check_call([T+"ld", "-T", "menu.ld", "/tmp/m14x/crt0.o", "/tmp/m14x/menu.o", "/tmp/m14x/assets.o", "/tmp/m14x/music_data.o", "-o", "/tmp/m14x/menu.elf"])
subprocess.check_call([T+"objcopy", "-O", "binary", "/tmp/m14x/menu.elf", "/tmp/m14x/menu.bin"])
menu = open("/tmp/m14x/menu.bin", "rb").read()
assert len(menu) <= COMMON_ORG, len(menu)
rom = menu + rom[len(menu):]
open(out, "wb").write(rom)
print("menu bytes", len(menu), "common", len(common), "banks", banks, "rom bytes", len(rom), "->", out)
