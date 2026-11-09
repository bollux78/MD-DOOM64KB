#!/usr/bin/env python3
"""N3: R128 on the MD + the Sega CD sub running the same logic in lockstep and rendering the view
with the R128 Pair-V drawers. Usage: build_n3.py TREE OUT   (env N3_AUTOSTART=1: title -> E1M1,
N3_OFF=1: same ROM without the sub, for the baseline)."""
import os, re, shutil, struct, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
common = here.parent
n2 = common / "n2"
tree, out = (Path(a).resolve() for a in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
opt = (tree / "out/.render_options").read_text().split()
defs = [o for o in opt if o.startswith("-D") and not o.startswith("-DDOOM_R12_RECIP")] + \
       ["-DN2_R128_DRAW", "-DN3_SRAM_COMPACT", "-DSCD_SRAM_BASE=0x00200000UL", "-DN3_R59_MODE=" + os.environ.get("N3_R59_MODE", "1")]

if os.environ.get("N3_GREP") or os.environ.get("N3_R84INFO"):
    rx = re.compile(os.environ.get("N3_GREP") or r"r84_(pixels|offsets|starts)|R84_")
    for f in sorted((tree / "src").glob("*")):
        if f.suffix not in (".c", ".inc", ".h") or f.stat().st_size > 400000 or "table" in f.name: continue
        for i, l in enumerate(f.read_text(errors="replace").splitlines()):
            if rx.search(l): print("N3GREP %s:%d: %s" % (f.name, i + 1, l.strip()[:220]))
if os.environ.get("N3_DUMP"):
    want = os.environ["N3_DUMP"].split(",")
    for f in sorted((tree / "src").glob("*")):
        if f.suffix not in (".c", ".inc", ".h") or f.stat().st_size > 400000 or "table" in f.name: continue
        lines = f.read_text(errors="replace").splitlines()
        for i, l in enumerate(lines):
            if any(re.match(r"^[A-Za-z].*\b" + w + r"\s*\(", l) and not l.rstrip().endswith(";") for w in want):
                print("N3DUMP %s:%d" % (f.name, i + 1)); print("\n".join("N3DUMP| " + x for x in lines[i:i + 60]))
for spec in filter(None, os.environ.get("N3_SHOW", "").split(";")):
    name, rng = spec.split(":"); lo, hi = map(int, rng.split("-"))
    ls = (tree / "src" / name).read_text(errors="replace").splitlines()
    for i in range(lo - 1, min(hi, len(ls))): print("N3SHOW %s:%d: %s" % (name, i + 1, ls[i]))
def sub_patch(path, old, new, count=1):
    t = path.read_text(errors="replace")
    assert t.count(old) >= 1, (path.name, old[:60])
    path.write_text(t.replace(old, new, count))

# 1. Sub source copy: cartridge SRAM -> PRG-RAM array (odd-lane layout kept), no mapper writes.
src = out / "src-sub"
if src.exists(): shutil.rmtree(src)
shutil.copytree(tree / "src", src)
for f in src.rglob("*"):
    if f.suffix not in (".c", ".h", ".inc"): continue
    t = f.read_text(errors="replace"); o = t
    # SRAM addresses stay virtual (0x200000..): every byte goes through R22_SRAM_BYTE -> compact array
    t = t.replace("#define R22_SRAM_BYTE(address) (*(volatile uint8_t*)(uintptr_t)(address))",
                  "#define R22_SRAM_BYTE(address) (scd_sram[((uint32_t)(uintptr_t)(address) - 0x00200000UL) >> 1])")
    t = t.replace("#define DOOM_SRAM_FIRST 0x0020F001UL", "#define DOOM_SRAM_FIRST ((unsigned long)scd_colcache+1UL)")
    t = t.replace("#define DOOM_SRAM_FIRST 0x00200001UL", "#define DOOM_SRAM_FIRST ((unsigned long)scd_colcache+1UL)")
    t = t.replace("#define DOOM_SRAM_CONTROL 0x00A130F1UL", "#define DOOM_SRAM_CONTROL ((unsigned long)scd_colcache+0x10FEUL)")
    t = t.replace("(*(volatile uint8_t*)0x00A130F1UL=1)", "((void)0)").replace("(*(volatile uint8_t*)0x00A130F1UL=0)", "((void)0)")
    if t != o: f.write_text("extern unsigned char scd_sram[], scd_colcache[];\n" + t)
(src / "r39c_movep.h").write_text("""/* N3 sub: MOVEP helpers over the compact SRAM emulation (virtual 0x200000..0x23FFFF -> scd_sram,
 * 4 logical bytes are consecutive there) or real stride-2 memory (column cache). */
#ifndef R39C_MOVEP_H
#define R39C_MOVEP_H
#include <stdint.h>
extern unsigned char scd_sram[];
#define N3_VSRAM(a) ((a) >= 0x00200000UL && (a) < 0x00240000UL)
static inline uint32_t R39C_MovepRead32(uint32_t a)
{
    if (N3_VSRAM(a)) { const uint8_t *q = scd_sram + ((a - 0x00200000UL) >> 1);
        return ((uint32_t)q[0] << 24) | ((uint32_t)q[1] << 16) | ((uint32_t)q[2] << 8) | q[3]; }
    const volatile uint8_t *p = (const volatile uint8_t *)(uintptr_t)a;
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[2] << 16) | ((uint32_t)p[4] << 8) | p[6];
}
static inline uint16_t R39C_MovepRead16(uint32_t a)
{
    if (N3_VSRAM(a)) { const uint8_t *q = scd_sram + ((a - 0x00200000UL) >> 1); return (uint16_t)((q[0] << 8) | q[1]); }
    const volatile uint8_t *p = (const volatile uint8_t *)(uintptr_t)a;
    return (uint16_t)((p[0] << 8) | p[2]);
}
static inline void R39C_MovepWrite32(uint32_t a, uint32_t v)
{
    if (N3_VSRAM(a)) { uint8_t *q = scd_sram + ((a - 0x00200000UL) >> 1); q[0] = v >> 24; q[1] = v >> 16; q[2] = v >> 8; q[3] = v; return; }
    volatile uint8_t *p = (volatile uint8_t *)(uintptr_t)a; p[0] = v >> 24; p[2] = v >> 16; p[4] = v >> 8; p[6] = v;
}
static inline void R39C_MovepWrite16(uint32_t a, uint16_t v)
{
    if (N3_VSRAM(a)) { uint8_t *q = scd_sram + ((a - 0x00200000UL) >> 1); q[0] = v >> 8; q[1] = v; return; }
    volatile uint8_t *p = (volatile uint8_t *)(uintptr_t)a; p[0] = v >> 8; p[2] = v;
}
#endif
""")
(src / "g_game.c").write_text((src / "g_game.c").read_text() +
    "\nvoid N3_SetCmd(const void *c){memcpy(&netcmd,c,sizeof netcmd);}\n"
    "void N3_LoadLevel(void){G_DoLoadLevel();}\n")
# game-logic uses of demoplayback follow the MD (demo sync), demo reading stays off on the sub
for fn, old in (("p_mobj.c", "  if (!_g_demoplayback)\n"), ("p_tick.c", "if (_g_menuactive && !_g_demoplayback"), ("g_game.c", "if (!_g_demoplayback && _g_menuactive)")):
    f = src / fn; t = f.read_text(errors="replace")
    assert old in t, (fn, old)
    f.write_text("extern unsigned char n3_demoplayback;\n" + t.replace(old, old.replace("_g_demoplayback", "n3_demoplayback")))
RND = "\nuint8_t N3_GetPRnd(void){return prndindex;}\nvoid N3_SetPRnd(uint8_t v){prndindex=v;}\n"
(src / "m_random.c").write_text((src / "m_random.c").read_text() + RND)
rv = src / "r22_video.inc"
sub_patch(rv, "#define R59_CURRENT (r59_color_tables[r59_color_mode])", "#define R59_CURRENT (r59_color_tables[N3_R59_MODE])")
sub_patch(rv, "static uint8_t *r115_fb2;", "static uint8_t *r115_fb2;\nuint8_t *N2_DrawBuffer(void){return r115_draw;}")
for fn in ("uint8_t *R96_WallSetup(const uint8_t *colormap,const uint8_t **lut)\n{", "uint8_t *R95_FlatSetup(const uint8_t **lut)\n{"):
    sub_patch(rv, fn, fn + "\n    { extern void SCD_ClockPoll(void); SCD_ClockPoll(); }")

# Split-screen windows (both CPUs): columns outside [N3_X0, N3_X1) are solid (no BSP/wall work)
# and sprites are clamped to the window.
def split_patch(rd):
    t = rd.read_text(errors="replace")
    old = "    solidcol[0] = 1;\n#endif\n}"
    assert t.count(old) == 1, "R_ClearClipSegs anchor"
    t = t.replace(old, "    solidcol[0] = 1;\n#endif\n    { extern int16_t N3_X0(void), N3_X1(void); const int16_t a = N3_X0(), b = N3_X1();\n"
                  "      if (a > 0) memset(solidcol, 1, a); if (b < VIEWWINDOWWIDTH) memset(solidcol + b, 1, VIEWWINDOWWIDTH - b); }\n}")
    for old in ("    vis->x2 = x2 >= VIEWWINDOWWIDTH ? VIEWWINDOWWIDTH - 1 : x2;\n",
                "    vis->x2              = x2 >= VIEWWINDOWWIDTH ? VIEWWINDOWWIDTH - 1 : x2;\n"):
        assert t.count(old) == 1, "vis->x2 anchor"
        t = t.replace(old, old + "    { extern int16_t N3_X0(void), N3_X1(void); const int16_t a = N3_X0(), b = N3_X1();\n"
                      "      if (vis->x1 < a) vis->x1 = a; if (vis->x2 > b - 1) vis->x2 = b - 1; }\n")
    old = "    while (dcvars.x < sprite_end)"
    assert t.count(old) == 1, "sprite loop anchor"
    t = t.replace(old, "    while (dcvars.x < sprite_end && dcvars.x <= vis->x2)")
    rd.write_text(t)
split_patch(src / "r_draw.c")

# 2. R84 composite pool: E1M1 subset (sub PRG-RAM cannot hold the whole pool).
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
print("N3 WAD lumps", n, [(i, lumps[i][0], lumps[i][2]) for i in range(0, 80)])
# Union of the wall textures of every map in the WAD (the sub keeps one resident subset).
used = set(); map_names = []
for mi, mn in enumerate(names):
    if not re.fullmatch(r"E\dM\d|MAP\d\d", mn): continue
    if os.environ.get("N3_SUBSET") and mn not in os.environ["N3_SUBSET"].split(","): continue
    sd = next((i for i in range(mi + 1, min(mi + 12, len(names))) if names[i] == "SIDEDEFS"), None)
    if sd is None: continue
    map_names.append(mn)
    _, p, z = lumps[sd]
    print("N3 map %s SIDEDEFS at %d, %d bytes" % (mn, p, z))
    for o in range(p, p + z - z % 7, 7):
        x, y, top, bottom, mid, sec = struct.unpack_from(">hBbbbB", wad, o)
        for t in (top, bottom, mid):
            if t > 0: used.add(t)
# texture names in index order (TEXTURE1 then TEXTURE2): add switch partners and whole animations
tex_names = []
def _parse_textures(endian):
    out = []
    for tl in ("TEXTURE1", "TEXTURE2"):
        if tl not in names: continue
        _, tp, tz = lumps[names.index(tl)]
        cnt = struct.unpack_from(endian + "i", wad, tp)[0]
        if not 0 < cnt < 2000 or 4 + 4 * cnt > tz: raise ValueError("count")
        for k in range(cnt):
            o2 = struct.unpack_from(endian + "i", wad, tp + 4 + 4 * k)[0]
            if not 0 < o2 < tz - 8: raise ValueError("offset")
            out.append(wad[tp + o2:tp + o2 + 8].rstrip(b"\0").decode("latin1").upper())
    return out
for _e in ("<", ">"):
    try: tex_names = _parse_textures(_e); break
    except Exception as ex: print("N3 texture names", _e, "failed:", ex)
ANIMS = [("BLODGR1", "BLODGR4"), ("BLODRIP1", "BLODRIP4"), ("FIREBLU1", "FIREBLU2"), ("FIRELAV3", "FIRELAVA"),
         ("FIREMAG1", "FIREMAG3"), ("FIREWALA", "FIREWALL"), ("GSTFONT1", "GSTFONT3"), ("ROCKRED1", "ROCKRED3"),
         ("SLADRIP1", "SLADRIP3"), ("BFALL1", "BFALL4"), ("SFALL1", "SFALL4"), ("WFALL1", "WFALL4"), ("DBRAIN1", "DBRAIN4")]
if tex_names:
    idx = {nm_: i for i, nm_ in enumerate(tex_names)}
    extra = set()
    for t in list(used):
        if t < len(tex_names):
            nm_ = tex_names[t]
            if nm_.startswith("SW1") and "SW2" + nm_[3:] in idx: extra.add(idx["SW2" + nm_[3:]])
            if nm_.startswith("SW2") and "SW1" + nm_[3:] in idx: extra.add(idx["SW1" + nm_[3:]])
    for a, z_ in ANIMS:
        if a in idx and z_ in idx and any(idx[a] <= t <= idx[z_] for t in used):
            extra.update(range(idx[a], idx[z_] + 1))
    for sky in ("SKY1", "SKY2", "SKY3", "SKY4"):   # sky is not on any sidedef
        if sky in idx: extra.add(idx[sky])
    print("N3 R84 extra textures (switch/anim/sky):", sorted(tex_names[t] for t in extra - used))
    used |= extra
newpool = bytearray(bytes([0xB0]) * 128); remap = {}
for t in sorted(used):
    if t >= len(starts): continue
    end = starts[t + 1] if t + 1 < len(starts) else len(offs)
    for e in range(starts[t], end):
        o = offs[e]
        if o == 0xFFFFFFFF: continue
        if o not in remap: remap[o] = len(newpool); newpool.extend(pool[o:o + 128])
newoffs = [remap.get(o, 0) if o != 0xFFFFFFFF else o for o in offs]
# The pool lives in Word RAM (same copy in both 1M banks), loaded from the MD at sub boot.
hdr = re.sub(r"static const uint8_t r84_pixels\[\]=\{[^}]*\};", "#define r84_pixels ((const uint8_t *)(0x0C0000UL + 0x10200UL))\n#define N3_POOL_BYTES %du" % len(newpool), hdr)
assert 0x10200 + len(newpool) < 0x1F000, "R84 pool does not fit the Word RAM bank"
# MD side: no second copy of the pool in ROM, just the list of source blocks (offsets/128) in the
# MD's own r84_pixels, in subset order; block 0 of the subset is the 0xB0 "missing" marker.
order = sorted(remap.items(), key=lambda kv: kv[1])
pool_c = "/* N3: R84 wall-texture subset for the Sega CD sub = these blocks of the MD's r84_pixels. */\n#include <stdint.h>\n" \
         "const uint16_t n3_r84_blocks[%d] = {%s};\nconst uint16_t n3_r84_nblocks = %d;\n" % (
             len(order), ",".join(str(o // 128) for o, _ in order), len(order))
hdr = re.sub(r"static const uint32_t r84_offsets\[\]=\{[^}]*\};", "static const uint32_t r84_offsets[]={" + ",".join(str(v) + "u" for v in newoffs) + "};", hdr)
(src / "r84_columns.h").write_text(hdr)
print("N3 R84 subset: textures %d, columns %d, bytes %d" % (len(used), len(remap), len(newpool)))
if os.environ.get("N3_R84INFO"):
    print("N3 R84 table sizes: pool %d, offsets %d, starts %d, max offset %d" % (len(pool), len(offs), len(starts), max(o for o in offs if o != 0xFFFFFFFF)))
    for mi, mn in enumerate(names):
        if re.fullmatch(r"E\dM\d|MAP\d\d", mn):
            sd = next((i for i in range(mi + 1, min(mi + 12, len(names))) if names[i] == "SIDEDEFS"), None)
            if sd is None: continue
            _, p2, z2 = lumps[sd]; u2 = set()
            for o2 in range(p2, p2 + z2 - z2 % 7, 7):
                _x, _y, a1, a2, a3, _s = struct.unpack_from(">hBbbbB", wad, o2)
                u2.update(t for t in (a1, a2, a3) if t > 0)
            blocks = set()
            for t in u2:
                if t >= len(starts): continue
                end = starts[t + 1] if t + 1 < len(starts) else len(offs)
                blocks.update(offs[e] for e in range(starts[t], end) if offs[e] != 0xFFFFFFFF)
            print("N3 map %s: textures %d, blocks %d, bytes %d" % (mn, len(u2), len(blocks), 128 * len(blocks)))

# 3. Sub transport (exported exchange, patient spins) and WAD client.
w = out / "sub"; w.mkdir(exist_ok=True)
tr = (common / "scd_sub_transport.c").read_text()
tr = tr.replace("#define SCD_SUB_MAX_SPINS 4000000UL", "#define SCD_SUB_MAX_SPINS 400000000UL")
tr += ("\nconst volatile uint8_t *SCD_SubExchange(uint16_t c, uint16_t a, uint16_t *len)"
       "{ return scd_exchange(c, a, len); }\nvoid SCD_SubSetTime(uint32_t t){ (void)t; }\n")
(w / "transport.c").write_text(tr)
ww = (common / "scd_sub_w_wad.c").read_text().replace("#define SCD_WAD_CACHE_BYTES (128UL * 1024UL)", "#define SCD_WAD_CACHE_BYTES (" + os.environ.get("N3_CACHE_KIB", "176") + "UL * 1024UL)")
ww = ww.replace("""    const uint16_t size = W_LumpLength(n);
    if (size) memcpy(ptr, W_GetLumpByNum(n), size);""", """    const uint16_t size = W_LumpLength(n);
    if (!size) return;
    if (scd_slots[n]) { memcpy(ptr, scd_slots[n], size); return; }
    if (!scd_fetch_lump((uint16_t)n, ptr, size)) I_Error("SCD LUMP READ FAILED %d", n);""")
ww = ww.replace('I_Error("SCD LUMP %.8s NOT FOUND", name);',
    '{ static char nf[26] = "LUMP NOT FOUND: "; for (uint16_t j = 0; j < 8u; j++) nf[16 + j] = name[j] ? name[j] : 32; nf[24] = 0; I_Error(nf); }')
# Sprite patches (between S_START and S_END) are only used while one sprite is projected/drawn:
# they live in a ring that recycles the oldest ones instead of filling the resident cache.
ww = ww.replace("const void __far* W_GetLumpByNum(int16_t n)\n{\n    scd_check_num(n);\n    if (scd_slots[n]) return scd_slots[n];",
"""#define SCD_RING_BYTES (N3RINGKIBUL * 1024UL)
#define SCD_RING_ENTRIES 96u
static uint8_t scd_ring[SCD_RING_BYTES];
static struct { int16_t lump; uint16_t start, end; } scd_ring_e[SCD_RING_ENTRIES];
static uint16_t scd_ring_n, scd_ring_pos;
static int16_t scd_s_start = -1, scd_s_end = -1, scd_p_start = 0x7FFF, scd_p_end = 0;
/* After a level is set up, every new lump is per-frame data (sprites, patches): ring only. */
static uint8_t scd_level_done;
void SCD_WadLevelDone(void) { scd_level_done = 1; }
static void scd_find_sprites(void)
{
    scd_s_start = scd_s_end = -1;
    for (uint16_t i = 0; i < scd_lump_count; i++)
    {
        const char *m = scd_directory[i].name;
        if (m[0] == 'S' && m[1] == '_' && m[2] == 'S' && m[3] == 'T' && m[4] == 'A' && m[5] == 'R' && m[6] == 'T') scd_s_start = (int16_t)i;
        if (m[0] == 'S' && m[1] == '_' && m[2] == 'E' && m[3] == 'N' && m[4] == 'D') scd_s_end = (int16_t)i;
        if (m[0] == 'P' && m[1] == '_' && m[2] == 'S' && m[3] == 'T' && m[4] == 'A' && m[5] == 'R' && m[6] == 'T') scd_p_start = (int16_t)i;
        if (m[0] == 'P' && m[1] == '_' && m[2] == 'E' && m[3] == 'N' && m[4] == 'D') scd_p_end = (int16_t)i;
    }
    if (scd_s_start < 0 || scd_s_end < 0) { scd_s_start = 0x7FFF; scd_s_end = 0; }
}
static const void *scd_ring_get(int16_t n, uint16_t size)
{
    if (size > SCD_RING_BYTES) I_Error("SCD SPRITE TOO BIG %d", n);
    if ((uint32_t)scd_ring_pos + size > SCD_RING_BYTES) scd_ring_pos = 0;
    const uint16_t a = scd_ring_pos, z = (uint16_t)(a + size);
    for (uint16_t i = 0; i < scd_ring_n; )
        if (scd_ring_e[i].start < z && a < scd_ring_e[i].end)
        { scd_slots[scd_ring_e[i].lump] = 0; scd_ring_e[i] = scd_ring_e[--scd_ring_n]; }
        else i++;
    if (scd_ring_n >= SCD_RING_ENTRIES) { scd_slots[scd_ring_e[0].lump] = 0; scd_ring_e[0] = scd_ring_e[--scd_ring_n]; }
    if (!scd_fetch_lump((uint16_t)n, scd_ring + a, size)) I_Error("SCD SPRITE TRANSFER FAILED %d", n);
    scd_ring_e[scd_ring_n].lump = n; scd_ring_e[scd_ring_n].start = a; scd_ring_e[scd_ring_n].end = z; scd_ring_n++;
    scd_ring_pos = (uint16_t)((z + 3u) & ~3u);
    scd_slots[n] = scd_ring + a;
    return scd_ring + a;
}
const void __far* W_GetLumpByNum(int16_t n)
{
    scd_check_num(n);
    if (scd_slots[n]) return scd_slots[n];
    if (scd_s_start < 0 && scd_s_end < 0) scd_find_sprites();
    /* the sky patch pointer is held for a whole frame (R_LoadSkyPatch): keep it resident */
    const char *nm3 = scd_directory[n].name;
    if ((scd_level_done || (n > scd_s_start && n < scd_s_end) || (n > scd_p_start && n < scd_p_end)) && scd_directory[n].size &&
        !(nm3[0] == 'S' && nm3[1] == 'K' && nm3[2] == 'Y'))
        return scd_ring_get(n, scd_directory[n].size);""")
assert "scd_ring_get" in ww
ww = ww.replace("N3RINGKIB", os.environ.get("N3_RING_KIB", "24"))
ww = ww.replace('I_Error("SCD LUMP CACHE FULL %d", n);', 'I_Error("FULL %d %.8s u%lu s%u S%d-%d P%d-%d", n, scd_directory[n].name, (unsigned long)scd_cache_used, (unsigned)size, scd_s_start, scd_s_end, scd_p_start, scd_p_end);')
ww = ww.replace("static uint32_t scd_cache_used, scd_cache_peak;", "static uint32_t scd_cache_used, scd_cache_peak, scd_cache_mark;")
ww += """
/* Level-scoped cache: everything fetched after the mark (level data, sprites) is dropped at the
 * next level load; init-time lumps (colormaps, texture metadata) stay. */
void SCD_WadMark(void) { scd_cache_mark = scd_cache_used; }
void SCD_WadFlushToMark(void)
{
    for (uint16_t i = 0; i < scd_lump_count; i++)
        if (scd_slots[i] && (uint32_t)(scd_slots[i] - scd_cache) >= scd_cache_mark) scd_slots[i] = 0;
    scd_cache_used = scd_cache_mark; scd_level_done = 0;
    for (uint16_t i = 0; i < scd_ring_n; i++) scd_slots[scd_ring_e[i].lump] = 0;
    scd_ring_n = 0; scd_ring_pos = 0;
}
"""
(w / "w_wad_client.c").write_text(ww)

# 4. Compile + link the sub program.
cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"), "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
          "-m68000", "-O2", "-fno-builtin", "-ffreestanding", "-fomit-frame-pointer", "-fms-extensions",
          "-ffunction-sections", "-fdata-sections", "-std=gnu11", "-w",
          "-I" + str(src), "-I" + str(common), "-I" + str(here),
          "-I" + str(tree / "compat")] + defs
skip = ("w_wad.c", "i_genesis.c", "r25_music.c", "s_sound.c", "i_audio.c")
sources = [n2 / "n2_video_stubs.c", common / "m2/scd_n1_platform.c"]
sources += sorted(p for p in src.glob("*.c") if p.name not in skip) + sorted(src.glob("*.s"))
sources += [common / "s1e/engine_libc.c", common / "s1d/scd_sub_system.c", common / "s1a/sub_libc.c",
            w / "transport.c", w / "w_wad_client.c", here / "n3_sub_main.c", n2 / "sub_sound_stubs.c", n2 / "sub_sound_stubs2.c"]
objs = []
for s in sources:
    obj = w / (s.name + ".o")
    extra = ["-x", "assembler-with-cpp", "-Wa,--register-prefix-optional,--bitwise-or"] if s.suffix == ".s" else []
    zone = ["-DSCD_SUB_ZONE_BYTES=" + os.environ.get("N3_ZONE", "40960")] if s.name == "scd_sub_system.c" else []
    hot = s.name.startswith("r") or s.name == "tables.c"
    r = subprocess.run([b("gcc")] + cflags + (["-O3", "-fno-web", "-fno-gcse"] if hot else ["-Os"]) + zone + extra +
                       ["-c", str(s), "-o", str(obj)], cwd=str(tree), capture_output=True, text=True)
    if r.returncode:
        print("N3 compile FAIL", s.name, r.stderr[-2500:]); raise SystemExit(1)
    objs.append(str(obj))
subprocess.run([b("as"), "-m68000", str(n2 / "sub_boot_n2.s"), "-o", str(w / "boot.o")], check=True)
libgcc = subprocess.check_output([b("gcc"), "-m68000", "-print-libgcc-file-name"], text=True).strip()
ld_script = w / "sub_engine_n3.ld"
ld_script.write_text((common / "s1e/sub_engine.ld").read_text().replace("_end < 0x7C000", "_end < 0x7F000"))
elf = w / "n3-sub.elf"
r = subprocess.run([b("gcc"), "-m68000", "-nostdlib", "-Wl,--gc-sections", "-Wl,-e,subcpu_vectors",
                    "-Wl,-T," + str(ld_script), "-Wl,--allow-multiple-definition", "-Wl,-Map," + str(w / "n3-sub.map"),
                    "-o", str(elf), str(w / "boot.o")] + objs + [str(gdk / "lib" / "libmd.a"), libgcc],
                   capture_output=True, text=True, env=dict(os.environ, LANG="C", LC_ALL="C"))
if r.returncode:
    undef = sorted(set(re.findall(r"undefined reference to [`'\"]([^'`\"]+)", r.stderr)))
    print("N3 sub link FAIL; undefined:", " ".join(undef)); print(r.stderr[-3000:])
    mt = (w / "n3-sub.map").read_text(errors="replace")
    e = re.search(r"0x([0-9a-f]+)\s+_end = \.", mt[mt.find("Linker script and memory map"):]); print("N3 _end would be", e.group(1) if e else "?")
    raise SystemExit(1)
sym = {}
for l in subprocess.check_output([b("nm"), str(elf)], text=True).splitlines():
    f = l.split()
    if len(f) >= 3: sym[f[-1]] = int(f[0], 16)
subprocess.run([b("objcopy"), "-O", "binary", "-R", ".bss", str(elf), str(w / "n3-sub.bin")], check=True)
size = (w / "n3-sub.bin").stat().st_size
print("N3 sub image %d bytes, bss end 0x%X" % (size, sym["_end"]))
assert size <= 4 * 128 * 1024 and sym["_end"] < 0x7F000

# 5. MD side, patched into the R128 tree.
def md_patch(name, old, new, count=1, regex=False):
    f = tree / "src" / name; t = f.read_text(errors="replace")
    if regex:
        t2, k = re.subn(old, new, t)
        assert k >= 1, (name, old)
    else:
        assert t.count(old) >= 1, (name, old[:70]); t2 = t.replace(old, new, count)
    f.write_text(t2)
off = bool(os.environ.get("N3_OFF"))
subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
                str(w / "n3-sub.bin"), str(tree / "src/n3_sub.h")], check=True)
shutil.copyfile(here / "n3_md.c", tree / "src/n3_md.c")
(tree / "src/n3_r84_pool.c").write_text(pool_c)
shutil.copyfile(here / "n3_proto.h", tree / "src/n3_proto.h")
shutil.copyfile(common / "scd_proto.h", tree / "src/scd_proto.h")
sv = (common / "scd_md_server.c").read_text()
a = "    else if (cmd == SCD_CMD_LUMP)\n        status = prepare_lump(arg, &size);\n"
assert sv.count(a) == 1
sv = sv.replace(a, a + "    else if (cmd == 9u)\n    {\n        extern uint16_t N3_MdPoolPayload(volatile uint8_t *);\n"
                "        size = N3_MdPoolPayload((volatile uint8_t *)(SCD_MD_BANK_BASE + SCD_PAYLOAD_OFFSET)); status = size != 0;\n    }\n"
                "    else if (cmd == SCD_CMD_FRAME)\n    {\n        extern uint16_t N3_MdFramePayload(volatile uint8_t *);\n"
                "        size = N3_MdFramePayload((volatile uint8_t *)(SCD_MD_BANK_BASE + SCD_PAYLOAD_OFFSET)); status = size != 0;\n    }\n")
a = "            transactions++;\n"
assert sv.count(a) == 1
sv = sv.replace(a, "            transactions++;\n            if (cmd == SCD_CMD_FRAME) { extern void N3_MdFrameArrived(uint16_t); N3_MdFrameArrived(arg); }\n")
# The sub may finish (ACK/DONE) and publish its next request before we sample ACK/DONE: a newer
# request seq also proves completion.
old = "        if (SCD_MD_REG16(SCD_MD_ACK_REG) == seq &&\n            SCD_MD_REG16(SCD_MD_DONE_REG) == seq &&\n            (SCD_MD_REG16(SCD_MD_MEMCTRL_REG) & 5u) != previous)"
assert sv.count(old) == 1
sv = sv.replace(old, "        if ((SCD_MD_REG16(SCD_MD_ACK_REG) == seq &&\n            SCD_MD_REG16(SCD_MD_DONE_REG) == seq &&\n            (SCD_MD_REG16(SCD_MD_MEMCTRL_REG) & 5u) != previous) ||\n            (SCD_MD_REG16(SCD_MD_REQUEST_REG) != seq && SCD_MD_REG16(SCD_MD_REQUEST_REG) != 0))")
sv += ("\n/* New request pending? Its command, else 0 (does not consume it). */\n"
       "uint16_t SCD_MdPendingCmd(void){ const uint16_t seq=SCD_MD_REG16(SCD_MD_REQUEST_REG);"
       " return (!seq || seq==last_request) ? 0 : SCD_MD_REG16(SCD_MD_CMD_REG); }\n")
(tree / "src/scd_md_server.c").write_text(sv)
ws = (tree / "src/w_wad.c").read_text()
needle = "const char __far* PUREFUNC W_GetNameForNum(int16_t num)"
if "SCD_MdLumpCount" not in ws:
    assert ws.count(needle) == 1
    (tree / "src/w_wad.c").write_text(ws.replace(needle, "uint16_t SCD_MdLumpCount(void) { const wadinfo_t *header=(const wadinfo_t *)&doom_iwad[0]; return (uint16_t)header->numlumps; }\n\n" + needle))
if not off:
    md_patch("i_genesis.c", "\tD_DoomMain(argc, argv);", "\t{ void N3_Boot(void); N3_Boot(); }\n\tD_DoomMain(argc, argv);")
md_patch("g_game.c", "static void G_DoLoadLevel (void)\n{", "static void G_DoLoadLevel (void)\n{\n    { extern void N3_OnLoadLevel(void); N3_OnLoadLevel(); }")
md_patch("g_game.c", "        if (_g_demoplayback)\n            G_ReadDemoTiccmd ();\n    }\n",
         "        if (_g_demoplayback)\n            G_ReadDemoTiccmd ();\n    }\n    { extern void N3_CaptureCmd(void); N3_CaptureCmd(); }\n")
gg = tree / "src/g_game.c"
gg.write_text(gg.read_text() + "\nvoid N3_GetCmd(void *o){memcpy(o,&netcmd,sizeof netcmd);}\n" +
              ("void N3_AutoStart(void){ G_DeferedPlayDemo(\"demo3\"); }\n" if os.environ.get("N3_AUTOSTART") == "demo3" else
               "void N3_AutoStart(void){ G_InitNew(sk_medium, %s); }\n" % os.environ["N3_AUTOSTART"][3:] if os.environ.get("N3_AUTOSTART", "").startswith("map") else
               "void N3_AutoStart(void){ d_skill = sk_medium; _g_gameaction = ga_newgame; }\n"))
(tree / "src/m_random.c").write_text((tree / "src/m_random.c").read_text() + RND)
md_patch("d_main.c", r"G_Ticker \(\);", "G_Ticker (); { extern void N3_OnTicEnd(void); N3_OnTicEnd(); }", regex=True)
md_patch("d_main.c", "    int32_t entertime = I_GetTime();\n", "    int32_t entertime = I_GetTime();\n"
         "    { extern int N3_SkipWait(void); if (N3_SkipWait()) { D_BuildNewTiccmds(); runtics = maketic - _g_gametic; if (runtics <= 0) return; goto n3_run; } }\n")
md_patch("d_main.c", "    while (runtics-- > 0)\n    {\n\n        if (advancedemo)", "n3_run:\n    while (runtics-- > 0)\n    {\n\n        if (advancedemo)")
dm = tree / "src/d_main.c"
dm.write_text(dm.read_text() + "\n/* N3: run the tics that are due now, without waiting (overlaps the sub's render). */\n"
              "void N3_EarlyTics(void){ D_BuildNewTiccmds(); int16_t r = maketic - _g_gametic;\n"
              "  while (r-- > 0) { if (advancedemo) D_DoAdvanceDemo(); M_Ticker(); G_Ticker(); { extern void N3_OnTicEnd(void); N3_OnTicEnd(); } _g_gametic++; } }\n")
md_patch("d_main.c", "    R22_BeginFrame();\n#endif", "    R22_BeginFrame();\n#endif\n    { extern void N3_Pump(void); N3_Pump(); }")
md_patch("d_main.c", r"R_RenderPlayerView \(&_g_player\);", "{ extern int N3_Display(void); if (!N3_Display()) R_RenderPlayerView (&_g_player); }", regex=True)
if os.environ.get("N3_AUTOSTART"):
    md_patch("d_main.c", "    demosequence = -1;\n    D_AdvanceDemo();", "    { extern void N3_AutoStart(void); N3_AutoStart(); }")
split_patch(tree / "src" / "r_draw.c")
rdm = tree / "src" / "r_draw.c"
rdm.write_text(rdm.read_text() + "\nconst uint8_t *N3_R84Pixels(void){return r84_pixels;}\n")
for fn in ("uint8_t *R96_WallSetup(const uint8_t *colormap,const uint8_t **lut)\n{", "uint8_t *R95_FlatSetup(const uint8_t **lut)\n{"):
    md_patch("r22_video.inc", fn, fn + "\n    { extern void N3_Poll(void); N3_Poll(); }")
md_patch("r22_video.inc", "static uint8_t *r115_fb2;", "static uint8_t *r115_fb2;\nuint8_t *N2_DrawBuffer(void){return r115_draw;}")
rvm = tree / "src/r22_video.inc"
rvm.write_text(rvm.read_text() + "\nuint8_t N3_ColorMode(void){return (uint8_t)(&R59_CURRENT == &r59_color_tables[" + os.environ.get("N3_R59_MODE", "1") + "] ? " + os.environ.get("N3_R59_MODE", "1") + " : 255);}\n")
env = dict(os.environ, PATH=str(gdk / "bin") + ":" + os.environ["PATH"])
md_patch("d_main.c", "static void TryRunTics (void)", "static void TryRunTics (void)")
render = " ".join(o for o in opt if o.startswith("-")) + (" -DN3_VERIFY" if os.environ.get("N3_VERIFY") else "") + \
         (" -DN3_SPLIT -DN3_R59_MODE=" + os.environ.get("N3_R59_MODE", "1") if os.environ.get("N3_SPLIT") else "") + (" -DN3_DEMO_TEST" if os.environ.get("N3_DEMO_TEST") else "")
subprocess.run(["make", "GDK=" + str(gdk), "PREFIX=m68k-elf-", "JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 " + render, "LIBGCC=" + libgcc + " -lgcc"], check=True, cwd=str(tree), env=env)
rom = out / "doom-md-scd-n3.bin"
subprocess.run(["python3", "scripts/lab/finish_r35_rom.py", "out/rom.bin", str(out / "linear.bin")], check=True, cwd=str(tree))
tools = common.parent
subprocess.run(["python3", str(tools / "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"), str(out / "linear.bin"), str(rom)], check=True)
subprocess.run(["python3", str(tools / "DOOM_SCD_03E/rom_identity.py"), str(rom)], check=True)
(out / "linear.bin").unlink()
shutil.copyfile(tree / "out/release/rom.out", out / "doom-md-scd-n3.elf")
print("N3 ROM:", rom)
