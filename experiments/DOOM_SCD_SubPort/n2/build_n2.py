#!/usr/bin/env python3
"""N2: Sega CD renders the E1M1 spawn with the whole R128 engine (SRAM-in-RAM model) and the
native column back end; MD serves the WAD and shows the frames; START -> R128 on MD.
Usage: build_n2.py TREE OUT"""
import os, re, shutil, struct, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
common = here.parent
tree, out = (Path(a).resolve() for a in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
opt = (tree / "out/.render_options").read_text().split()
PROF = int(os.environ.get("N2_PROF", "0"))
defs = [o for o in opt if o.startswith("-D") and (PROF & 64 or not o.startswith("-DDOOM_R12_RECIP"))] + ["-DSCD_SRAM_BASE=((unsigned long)scd_sram)", "-DN2_PROF=" + os.environ.get("N2_PROF", "0")]

# 1. Patched source copy: cartridge SRAM -> sub PRG-RAM (same odd-lane layout), no mapper writes.
src = out / "src-n2"
if src.exists(): shutil.rmtree(src)
shutil.copytree(tree / "src", src)
for f in src.rglob("*"):
    if f.suffix not in (".c", ".h", ".inc"): continue
    t = f.read_text(errors="replace"); o = t
    t = t.replace("#define R22_SRAM_BASE 0x00200000UL", "#define R22_SRAM_BASE SCD_SRAM_BASE")
    t = t.replace("#define DOOM_SRAM_FIRST 0x0020F001UL", "#define DOOM_SRAM_FIRST (SCD_SRAM_BASE+0xF001UL)")
    t = t.replace("#define DOOM_SRAM_FIRST 0x00200001UL", "#define DOOM_SRAM_FIRST (SCD_SRAM_BASE+1UL)")
    t = t.replace("#define DOOM_SRAM_CONTROL 0x00A130F1UL", "#define DOOM_SRAM_CONTROL (SCD_SRAM_BASE+0x11FFEUL)")
    t = t.replace("(*(volatile uint8_t*)0x00A130F1UL=1)", "((void)0)").replace("(*(volatile uint8_t*)0x00A130F1UL=0)", "((void)0)")
    if t != o:
        # the emulated SRAM is a linker-placed array (inside the checked PRG-RAM map), not a fixed address
        f.write_text("extern unsigned char scd_sram[];\n" + t)
(src / "g_game.c").write_text((src / "g_game.c").read_text() +
    "\nvoid N2_InitGame(void){G_InitNew(sk_medium,1);}\n"
    "void N2_SetCommand(int8_t f,int8_t s,int16_t a,uint8_t b){netcmd.forwardmove=f;netcmd.sidemove=s;netcmd.angleturn=a;netcmd.buttons=b;}\n")
(src / "r_data.c").write_text((src / "r_data.c").read_text() + '''
void SCD_MetadataInit(void){ }
''')

# 2. R84 subset for E1M1: only the composed columns of textures on E1M1 sides.
hdr = (src / "r84_columns.h").read_text()
def arr(name):
    m = re.search(r"static const \w+ " + name + r"\[\]=\{([^}]*)\};", hdr)
    return [int(x.rstrip("u")) for x in m.group(1).split(",") if x.strip()]
pool, offs, starts = bytes(arr("r84_pixels")), arr("r84_offsets"), arr("r84_starts")
wad = (tree / "scripts/doom64.wad").read_bytes()
n, dirofs = struct.unpack_from(">hI", wad, 4)[0], struct.unpack_from(">I", wad, 8)[0]
lumps = []
for i in range(n):
    o = dirofs + i * 16; p, z = struct.unpack_from(">IH", wad, o)
    lumps.append((wad[o + 8:o + 16].rstrip(b"\0").decode("latin1"), p, z))
names = [l[0] for l in lumps]
m = names.index("E1M1")
side = next(i for i in range(m + 1, m + 12) if names[i] == "SIDEDEFS")
_, p, z = lumps[side]
used = set()
for o in range(p, p + z - z % 7, 7):
    x, y, top, bottom, mid, sec = struct.unpack_from(">hBbbbB", wad, o)
    for t in (top, bottom, mid):
        if t > 0: used.add(t)
newpool = bytearray(bytes([0xB0]) * 128)   # entry 0: visible "missing column" marker
remap = {}
for t in sorted(used):
    if t >= len(starts): continue
    end = starts[t + 1] if t + 1 < len(starts) else len(offs)
    for e in range(starts[t], end):
        o = offs[e]
        if o == 0xFFFFFFFF: continue
        if o not in remap:
            remap[o] = len(newpool); newpool.extend(pool[o:o + 128])
newoffs = [remap.get(o, 0) if o != 0xFFFFFFFF else o for o in offs]
hdr = re.sub(r"static const uint8_t r84_pixels\[\]=\{[^}]*\};", "static const uint8_t r84_pixels[]={" + ",".join(str(v) for v in newpool) + "};", hdr)
hdr = re.sub(r"static const uint32_t r84_offsets\[\]=\{[^}]*\};", "static const uint32_t r84_offsets[]={" + ",".join(str(v) + "u" for v in newoffs) + "};", hdr)
(src / "r84_columns.h").write_text(hdr)
print("N2 R84 subset: textures %d, columns %d, bytes %d (full pool %d)" % (len(used), len(remap), len(newpool), len(pool)))

# 3. Sub transport/WAD client with the FRAME call; smaller WAD cache.
w = out / "sub"; w.mkdir(exist_ok=True)
tr = (common / "scd_sub_transport.c").read_text()
a = "            SCD_SUB_REG16(SCD_SUB_DONE_REG)=seq;\n            M15_BUSY(0);return 0;"
assert tr.count(a) == 1
tr = tr.replace(a, "            n2_bad[0]=version;n2_bad[1]=cmd;n2_bad[2]=got_seq;n2_bad[3]=status;n2_bad[4]=(uint16_t)got_len;n2_bad[5]=seq;\n" + a)
tr = tr.replace("static uint16_t sub_seq", "uint16_t n2_bad[6];\nstatic uint16_t sub_seq")
b2 = "    if (!p || length!=bytes) return 0;"
assert tr.count(b2) == 1
tr = tr.replace(b2, "    if (!p || length!=bytes) { n2_bad[4]=length; n2_bad[5]=p?0xEEEE:0xDDDD; return 0; }")
tr += '''
int SCD_SubFrame(uint16_t arg, uint8_t out[16])
{
    uint16_t len = 0;
    const volatile uint8_t *p = scd_exchange(SCD_CMD_FRAME, arg, &len);
    if (!p || len != 16) return 0;
    for (uint16_t i = 0; i < 16; i++) out[i] = p[i];
    return 1;
}
'''
(w / "transport.c").write_text(tr)
ww = (common / "scd_sub_w_wad.c").read_text().replace("#define SCD_WAD_CACHE_BYTES (128UL * 1024UL)", "#define SCD_WAD_CACHE_BYTES (" + os.environ.get("N2_WAD_CACHE", "96") + "UL * 1024UL)")
ww = ww.replace('I_Error("SCD LUMP TRANSFER FAILED %d", n);',
    '{ extern uint16_t n2_bad[6]; extern uint32_t SCD_SubTimeouts(void); I_Error("X%d Z%u T%lu L%u K%X S%u", n, (unsigned)size, (unsigned long)SCD_SubTimeouts(), n2_bad[4], n2_bad[5], n2_bad[2]); }')
ww = ww.replace('I_Error("SCD LUMP %.8s NOT FOUND", name);',
    '{ static char nf[26] = "LUMP NOT FOUND: "; for (uint16_t j = 0; j < 8u; j++) nf[16 + j] = name[j] ? name[j] : 32; nf[24] = 0; I_Error(nf); }')
(w / "w_wad_client.c").write_text(ww)

cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"), "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
          "-m68000", "-O2", "-fno-builtin", "-ffreestanding", "-fomit-frame-pointer", "-fms-extensions",
          "-ffunction-sections", "-fdata-sections", "-std=gnu11", "-w",
          "-I" + str(src), "-I" + str(common), "-I" + str(tree / "compat")] + defs
sources = sorted(p for p in src.glob("*.c") if p.name not in ("w_wad.c", "i_genesisv.c", "i_genesis.c", "r25_music.c"))
sources += sorted(p for p in src.glob("*.s"))
sources += [common / "m2/scd_draw.c", common / "m2/scd_n1_platform.c", common / "s1e/engine_libc.c",
            common / "s1d/scd_sub_system.c", common / "s1a/sub_libc.c", w / "transport.c", w / "w_wad_client.c", here / "n2_sub_main.c", here / "prof_inst.c"]
objs = []
for s in sources:
    obj = w / (s.name + ".o")
    extra = ["-x", "assembler-with-cpp", "-Wa,--register-prefix-optional,--bitwise-or"] if s.suffix == ".s" else []
    zone = ["-DSCD_SUB_ZONE_BYTES=" + os.environ.get("N2_ZONE", "98304")] if s.name == "scd_sub_system.c" else []
    # Speed where it matters (renderer, -O3 like the MD build), size elsewhere (-Os) to fit PRG-RAM.
    hot = s.name.startswith("r_" if not PROF & 128 else "r") or s.name in ("scd_draw.c", "tables.c")
    opt_flags = (["-O3", "-fno-web", "-fno-gcse"] if hot else ["-Os"]) if os.environ.get("N2_OPT", "split") == "split" else []
    if int(os.environ.get("N2_PROF", "0")) & 2 and s.suffix == ".c" and (s.name.startswith("r") or s.name == "scd_draw.c") and s.name != "r20_stackguard.c":
        opt_flags = (["-O2"] if os.environ.get("N2_PROF_O2") else opt_flags) + ["-finstrument-functions"]
    r = subprocess.run([b("gcc")] + cflags + opt_flags + zone + extra + ["-c", str(s), "-o", str(obj)], cwd=str(tree), capture_output=True, text=True)
    if r.returncode:
        print("N2 compile FAIL", s.name, r.stderr[-2000:]); raise SystemExit(1)
    objs.append(str(obj))
subprocess.run([b("as"), "-m68000", str(common / "s1a/sub_boot.s"), "-o", str(w / "boot.o")], check=True)
libgcc = subprocess.check_output([b("gcc"), "-m68000", "-print-libgcc-file-name"], text=True).strip()
elf = w / "n2-sub.elf"
ld_script = common / "s1e/sub_engine.ld"
if int(os.environ.get("N2_PROF", "0")) & 2:   # profiling build: stack use is < 1 KiB, the trace area is unused in N2
    ld_script = w / "sub_engine_prof.ld"
    ld_script.write_text((common / "s1e/sub_engine.ld").read_text().replace("_end < 0x7C000", "_end < 0x7F000"))
r = subprocess.run([b("gcc"), "-m68000", "-nostdlib", "-Wl,--gc-sections", "-Wl,-e,subcpu_vectors",
                    "-Wl,-T," + str(ld_script), "-Wl,--allow-multiple-definition",
                    "-Wl,-Map," + str(w / "n2-sub.map"), "-o", str(elf), str(w / "boot.o")] + objs + [libgcc],
                   capture_output=True, text=True)
undef = sorted(set(re.findall(r"undefined reference to [`'\"]([^'`\"]+)", r.stderr)))
if r.returncode:
    print("N2 sub link FAIL; undefined:", " ".join(undef)); print(r.stderr[-3000:])
    if int(os.environ.get("N2_PROF", "0")) & 2 and not os.environ.get("N2_PROF_O2") and "overlaps" in r.stderr:
        print("N2 profiling build too big at -O3: retrying instrumented files at -O2", flush=True)
        os.environ["N2_PROF_O2"] = "1"; os.execv(sys.executable, [sys.executable] + sys.argv)
    raise SystemExit(1)
sym = {}
for l in subprocess.check_output([b("nm"), "-S", str(elf)], text=True).splitlines():
    f = l.split()
    if len(f) >= 3: sym[f[-1]] = int(f[0], 16)
subprocess.run([b("objcopy"), "-O", "binary", "-R", ".bss", str(elf), str(w / "n2-sub.bin")], check=True)
size = (w / "n2-sub.bin").stat().st_size
print("N2 sub image %d bytes, bss end 0x%X (stack reserve from 0x7C000)" % (size, sym["_end"]))
_dis = subprocess.check_output([b("objdump"), "-d", str(elf)], text=True).splitlines()
print("N2 vectors/isr:\n" + "\n".join(_dis[:12] + [l for l in _dis if l[:9].strip().rstrip(":") and l.strip()[:4] in ("6c:", ) ] ))
_i = next((i for i, l in enumerate(_dis) if "<prof_isr>:" in l), None)
if _i is not None: print("\n".join(_dis[_i:_i + 16]))
for _k, l in enumerate(_dis):
    if "ff8030" in l or "ff8032" in l or "#8704" in l or "#9984" in l: print("\n".join(_dis[max(0, _k - 3):_k + 3])); print("--")
_img = (w / "n2-sub.bin").read_bytes()
for _pat in (b"\x00\x0f\x00\x0f", b"\x00\x1f\x00\x1f"):
    print("N2 pattern", _pat.hex(), [hex(i) for i in range(0, len(_img) - 3, 2) if _img[i:i + 4] == _pat][:24])
print("N2 largest functions:", sorted(((int(l.split()[1], 16), l.split()[3]) for l in subprocess.check_output([b("nm"), "-S", "--size-sort", str(elf)], text=True).splitlines() if len(l.split()) == 4 and l.split()[2] in "Tt"), reverse=True)[:8])
assert size <= 4 * 128 * 1024 and sym["_end"] < (0x7F000 if int(os.environ.get("N2_PROF", "0")) & 2 else 0x7C000)

# 4. MD side.
subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
                str(w / "n2-sub.bin"), str(tree / "src/n2_sub.h")], check=True)
hp = tree / "src/n2_sub.h"
hp.write_text(hp.read_text().replace("SUB_PROGRAM_WORDS", "SUB_PROGRAM_WORDS"))
shutil.copyfile(here / "n2_md.c", tree / "src/n2_md.c")
shutil.copyfile(common / "scd_proto.h", tree / "src/scd_proto.h")
sv = (common / "scd_md_server.c").read_text()
a = "    else if (cmd == SCD_CMD_LUMP)\n        status = prepare_lump(arg, &size);\n"
assert sv.count(a) == 1
sv = sv.replace(a, a + "    else if (cmd == SCD_CMD_FRAME)\n    {\n        volatile uint8_t *pl = (volatile uint8_t *)(SCD_MD_BANK_BASE + SCD_PAYLOAD_OFFSET);\n        for (uint16_t i = 0; i < 16; i++) pl[i] = 0;\n        size = 16; status = 1;\n    }\n")
a = "            transactions++;\n"
assert sv.count(a) == 1
sv = sv.replace(a, "            transactions++;\n            if (cmd == SCD_CMD_FRAME) { extern void N2_MdFrameArrived(uint16_t); N2_MdFrameArrived(arg); }\n")
pass  # server already declares SCD_MdLumpCount
(tree / "src/scd_md_server.c").write_text(sv)
wp = tree / "src/w_wad.c"; ws = wp.read_text()
needle = "const char __far* PUREFUNC W_GetNameForNum(int16_t num)"
if "SCD_MdLumpCount" not in ws:
    assert ws.count(needle) == 1
    ws = ws.replace(needle, "uint16_t SCD_MdLumpCount(void) { const wadinfo_t *header=(const wadinfo_t *)&doom_iwad[0]; return (uint16_t)header->numlumps; }\n\n" + needle)
    wp.write_text(ws)
g = tree / "src/i_genesis.c"; s = g.read_text()
anchor = "\tD_DoomMain(argc, argv);"
assert s.count(anchor) == 1
g.write_text(s.replace(anchor, "\t{ void N2_Test(void); N2_Test(); }\n" + anchor))
env = dict(os.environ, PATH=str(gdk / "bin") + ":" + os.environ["PATH"])
render = " ".join(o for o in opt if o.startswith("-"))
subprocess.run(["make", "GDK=" + str(gdk), "PREFIX=m68k-elf-", "JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 " + render, "LIBGCC=" + libgcc + " -lgcc"], check=True, cwd=str(tree), env=env)
rom = out / "doom-md-scd-n2.bin"
subprocess.run(["python3", "scripts/lab/finish_r35_rom.py", "out/rom.bin", str(out / "linear.bin")], check=True, cwd=str(tree))
tools = common.parent
subprocess.run(["python3", str(tools / "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"), str(out / "linear.bin"), str(rom)], check=True)
subprocess.run(["python3", str(tools / "DOOM_SCD_03E/rom_identity.py"), str(rom)], check=True)
(out / "linear.bin").unlink()
shutil.copyfile(tree / "out/release/rom.out", out / "doom-md-scd-n2.elf")
print("N2 ROM:", rom)
