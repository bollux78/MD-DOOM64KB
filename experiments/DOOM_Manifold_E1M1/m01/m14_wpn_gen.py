"""M14 multi-weapon (r045): fist, pistol, shotgun, chaingun, rocket launcher, chainsaw.

Builds, from the user's WAD, per weapon an idle frame and a firing frame (patches placed with their
true Doom left/top offsets, clipped at the status bar line Y=168 and cropped to <=128 tiles), as raw
VDP tile data + hardware-sprite lists, plus a 9-colour palette per weapon.  Everything is appended to
src/weapon_sprites.c (which the linker script already puts in the common block).  A cycles weapons, C fires.
Sounds for the weapons that lack one are cut from the WAD DS* lumps.
"""
import os, struct, math, wave
from pathlib import Path

# name, idle layers, fire layers, cadence (1/60 s ticks between shots), flash hold (1/60 s ticks),
# pellets (0 = melee: no hit on decorations), sfx key
# cadence / flash hold in getTick() units (1/300 s): Doom tics (1/35 s) * 300/35
# Doom refire: fist 22 tics (punch cycle), pistol 14, shotgun 37, chaingun 4, rocket 20, saw 4
WEAPONS = [
    ("FIST",    ["PUNGA0"], ["PUNGC0"],            189, 86, 0, "punch"),
    ("PISTOL",  ["PISGA0"], ["PISGB0", "PISFA0"],  120, 60, 1, "pistol"),
    ("SHOTGUN", ["SHTGA0"], ["SHTGA0", "SHTFB0"],  317, 60, 3, "shotgun"),
    ("CHAINGUN",["CHGGA0"], ["CHGGB0", "CHGFB0"],   34, 17, 1, "pistol"),
    ("ROCKET",  ["MISGA0"], ["MISGB0", "MISFB0"],  171, 60, 1, "rocket"),
    ("SAW",     ["SAWGC0"], ["SAWGD0"],             34, 34, 0, "saw"),
]
SOUNDS = {  # key -> (lump, max seconds @14 kHz)
    "punch": ("DSPUNCH", 0.35), "shotgun": ("DSSHOTGN", 0.45),
    "rocket": ("DSRLAUNC", 0.5), "saw": ("DSSAWFUL", 0.35),
}
SFX_BASE = 72
SFX_IDS = {"punch": 72, "shotgun": 73, "rocket": 74, "saw": 75}   # pistol keeps SFX_SHOTGUN_ID (69)

SCALE = {"SAW": 0.66}      # too wide for 128 tiles: scale it down instead of cropping the sides
BASE_BOTTOM = 168            # Doom status bar line: weapon art below it is hidden anyway
PIS_X0, PIS_Y0 = 122, 104    # origin that the original pistol canvas had (dx,dy = X0-122, Y0-104)
FIRE_MAXTILES = 104          # fire frames live in the reclaimed window area: 104 tiles are known to be safe there


def md_color(c):
    r, g, b = c
    f = lambda v: (v * 7 + 127) // 255
    return (f(b) << 9) | (f(g) << 5) | (f(r) << 1)


def build(w, rgb, cut):
    from PIL import Image

    def load(name):
        l = w.lump(name)
        lo, to = struct.unpack("<hh", l[4:8])
        import wad_textures as WT
        pw, ph, img = WT.patch_image(l)
        im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        for y in range(ph):
            for x in range(pw):
                p = img[y][x]
                if p is not None:
                    im.putpixel((x, y), tuple(rgb[p]) + (255,))
        return im, -lo, -to

    bottom = BASE_BOTTOM - cut

    def scaled(name, sc):
        im, X, Y = load(name)
        if sc >= 1.0:
            return im, X, Y
        nw = max(1, round(im.width * sc)); nh = max(1, round(im.height * sc))
        a = im.getchannel("A").resize((nw, nh), Image.BOX).point(lambda v: 255 if v >= 128 else 0)
        rgb_ = im.convert("RGB").resize((nw, nh), Image.BOX)
        r = rgb_.convert("RGBA"); r.putalpha(a)
        return r, round(160 + (X - 160) * sc), round(bottom + (Y - bottom) * sc)

    def frame_canvas(names, maxtiles, sc=1.0):
        layers = [scaled(n, sc) for n in names]
        bx0 = min(X for _, X, _ in layers); bx1 = max(X + im.width for im, X, _ in layers)
        by0 = min(Y for _, _, Y in layers)
        tw = math.ceil((bx1 - bx0) / 8); th = math.ceil((bottom - by0) / 8)
        cx0 = bx0
        cy0 = bottom - th * 8
        while tw * th > maxtiles:
            if tw > 8:           # trim width on the side farther from the screen centre (Doom x=160)
                if abs(cx0 - 160) >= abs(cx0 + tw * 8 - 160):
                    cx0 += 8
                tw -= 1
            else:
                cy0 += 8; th -= 1
        cv = Image.new("RGBA", (tw * 8, th * 8), (0, 0, 0, 0))
        for im, X, Y in layers:
            _paste_clipped(cv, im, X - cx0, Y - cy0)
        return cv, cx0, cy0

    def _paste_clipped(cv, im, ox, oy):
        x0 = max(0, ox); y0 = max(0, oy); x1 = min(cv.width, ox + im.width); y1 = min(cv.height, oy + im.height)
        if x1 <= x0 or y1 <= y0:
            return
        cv.alpha_composite(im.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy)), (x0, y0))

    out = []
    for (name, idle, fire, cad, hold, pel, snd) in WEAPONS:
        sc = SCALE.get(name, 1.0)
        frames = [frame_canvas(idle, 128, sc), frame_canvas(fire, FIRE_MAXTILES, sc)]
        # palette: 9 colours over both frames
        total_h = sum(f[0].height for f in frames); total_w = max(f[0].width for f in frames)
        sheet = Image.new("RGB", (total_w, total_h), (0, 0, 0)); yy = 0
        for cv, _, _ in frames:
            sheet.paste(cv, (0, yy), cv); yy += cv.height
        pal_img = sheet.quantize(colors=9, method=Image.MEDIANCUT)
        pal = pal_img.getpalette()[:27]
        pal = [tuple(pal[i * 3:i * 3 + 3]) for i in range(9)]
        fr = []
        for cv, cx0, cy0 in frames:
            tw, th = cv.width // 8, cv.height // 8
            flat = Image.new("RGB", cv.size, (0, 0, 0)); flat.paste(cv, (0, 0), cv)
            q = flat.quantize(palette=pal_img, dither=Image.NONE)
            idx = [[(q.getpixel((x, y)) + 1) if cv.getpixel((x, y))[3] > 0 else 0 for x in range(cv.width)] for y in range(cv.height)]
            spr = []; data = []
            for by in range(0, th, 4):
                for bx in range(0, tw, 4):
                    bw = min(4, tw - bx); bh = min(4, th - by)
                    if not any(idx[y][x] for y in range(by * 8, (by + bh) * 8) for x in range(bx * 8, (bx + bw) * 8)):
                        continue
                    for c in range(bw):
                        for r in range(bh):
                            for y in range(8):
                                v = 0
                                for x in range(8):
                                    v = (v << 4) | idx[(by + r) * 8 + y][(bx + c) * 8 + x]
                                data.append(v)
                    spr.append((bx * 8, by * 8, ((bw - 1) << 2) | (bh - 1), bw * bh))
            fr.append(dict(dx=cx0 - PIS_X0, dy=cy0 - PIS_Y0, spr=spr, data=data))
        out.append(dict(name=name, frames=fr, pal=[md_color(c) for c in pal], cad=cad, hold=hold, pel=pel, snd=snd))
    return out


C_LOGIC = r'''
/* ===== M14 multi-weapon (generated by m14_wpn_gen.py) ===== */
typedef struct { u8 ox, oy, size, nt; } m14w_spr;
typedef struct { s16 dx, dy; u8 ns; u8 pad; u16 ntiles; const m14w_spr *spr; const u32 *tiles; } m14w_frame;
typedef struct { const m14w_frame *idle, *fire; u16 pal[9]; u16 cad, hold; u8 pel, sfx; } m14w_def;
@DATA@
u8 m14w_cur = 1;
static const m14w_frame *m14w_shown; static u8 m14w_isfire; static u16 m14w_hold;
static s16 m14w_bx, m14w_by;
u16 m14w_cad(void) { return m14w_defs[m14w_cur].cad; }
u8 m14w_pellets(void) { return m14w_defs[m14w_cur].pel; }
u8 m14w_sfx(void) { return m14w_defs[m14w_cur].sfx; }
static void m14w_place(void) {
    const m14w_frame *f = m14w_shown; if (!f) return;
    u16 tile = m14w_isfire ? manifold_weapon_buf1 : (u16)start_tile_loc;
    VDP_clearSprites();
    for (u8 i = 0; i < f->ns; i++) {
        const m14w_spr *s = &f->spr[i];
        VDP_setSprite(sprite_idx_start + i, BASE_WEAPON_X + f->dx + s->ox + m14w_bx, BASE_WEAPON_Y + f->dy + s->oy + m14w_by,
                      s->size, TILE_ATTR_FULL(PAL0, 0, 0, 0, tile));
        tile += s->nt;
    }
    VDP_linkSprites(sprite_idx_start, f->ns);
    VDP_setSpriteLink(sprite_idx_start + f->ns, 0);
    VDP_setSpritePosition(sprite_idx_start + f->ns, 0, 0);
    cur_num_sprites = f->ns;
    m14_sat_update(f->ns);
}
void set_weapon_sprite_position_offset(s16 offX, s16 offY) {
    const m14w_frame *f = m14w_shown; m14w_bx = offX; m14w_by = offY; if (!f) return;
    for (u8 i = 0; i < f->ns; i++) {
        const m14w_spr *s = &f->spr[i];
        VDP_setSpritePosition(sprite_idx_start + i, BASE_WEAPON_X + f->dx + s->ox + offX, BASE_WEAPON_Y + f->dy + s->oy + offY);
    }
    m14_sat_update(f->ns);
}
void m14w_select(u8 id) {
    const m14w_def *d = &m14w_defs[id]; m14w_cur = id;
    /* the V-int handler also talks to the VDP: no interrupt may split our tile writes (that scrambled the tiles) */
    for (;;) { SYS_disableInts(); if (*(volatile u16*)0xC00004 & 8) break; SYS_enableInts(); __asm__ volatile("nop\n nop\n nop\n nop"); }
    PAL_setColors(1, d->pal, 9, CPU);
    VDP_loadTileData(d->idle->tiles, start_tile_loc, d->idle->ntiles, CPU);
    VDP_loadTileData(d->fire->tiles, manifold_weapon_buf1, d->fire->ntiles, CPU);
    SYS_enableInts();
    m14w_shown = d->idle; m14w_isfire = 0; m14w_hold = 0; m14w_place();
}
void m14w_next(void) { m14w_select((u8)((m14w_cur + 1) % @NW@)); }
void m14_fire_anim(void) {
    const m14w_def *d = &m14w_defs[m14w_cur];
    u16 h = d->hold / (last_frame_ticks ? last_frame_ticks : 1); if (h < 1) h = 1;
    if (d->sfx == 75) {                     /* chainsaw: alternate the two frames on every shot while C is held */
        m14w_isfire ^= 1; m14w_shown = m14w_isfire ? d->fire : d->idle; m14w_hold = 0; m14w_place(); return;
    }
    m14w_hold = h; m14w_shown = d->fire; m14w_isfire = 1; m14w_place();
}
void m14w_idle(void) { if (m14w_isfire) { m14w_shown = m14w_defs[m14w_cur].idle; m14w_isfire = 0; m14w_hold = 0; m14w_place(); } }
void m14w_step(void) {
    if (m14w_hold && --m14w_hold == 0) { m14w_shown = m14w_defs[m14w_cur].idle; m14w_isfire = 0; m14w_place(); }
}
'''


def gen_c(ws):
    s = []
    for i, wp in enumerate(ws):
        for j, f in enumerate(wp["frames"]):
            n = "w%df%d" % (i, j)
            s.append("static const m14w_spr %s_s[] = {%s};" % (n, ",".join("{%d,%d,0x%02X,%d}" % x for x in f["spr"])))
            d = f["data"]
            s.append("static const u32 %s_t[] __attribute__((section(\".wpndata\"))) = {%s};" % (n, ",".join("0x%08X" % v for v in d)))
            s.append("static const m14w_frame %s = {%d,%d,%d,0,%d,%s_s,%s_t};" % (n, f["dx"], f["dy"], len(f["spr"]), len(d) // 8, n, n))
    s.append("static const m14w_def m14w_defs[%d] = {" % len(ws))
    for i, wp in enumerate(ws):
        sfx = SFX_IDS.get(wp["snd"], 69)
        s.append("  {&w%df0,&w%df1,{%s},%d,%d,%d,%d}," % (i, i, ",".join("0x%04X" % c for c in wp["pal"]), wp["cad"], wp["hold"], wp["pel"], sfx))
    s.append("};")
    return "\n".join(s)


def make_pcm(lump_data, maxsec):
    rate = struct.unpack("<H", lump_data[2:4])[0]
    n = struct.unpack("<I", lump_data[4:8])[0]
    pcm = list(lump_data[8 + 16:8 + n - 16]) if n > 40 else list(lump_data[8:8 + n])
    m = max(abs(x - 128) for x in pcm) or 1
    nn = min(int(len(pcm) * 14000 / rate), int(maxsec * 14000))
    o = bytearray()
    for i in range(nn):
        v = (pcm[min(len(pcm) - 1, int(i * rate / 14000))] - 128) * min(120 / m, 2.0)
        fade = min(1.0, (nn - i) / 700.0)
        o.append(max(-127, min(127, int(v * fade))) & 0xFF)     # signed 8-bit, as the XGM PCM driver wants
    o += bytes((-len(o)) % 256)                                  # length multiple of 256
    return bytes(o)


def apply(out, wad):
    import wad_textures as WT
    w = WT.Wad(wad); rgb = WT.playpal(w)
    cut = int(os.environ.get("MANIFOLD_WPN_CUT", "8"))
    ws = build(w, rgb, cut)
    tot = sum(len(f["data"]) * 4 for wp in ws for f in wp["frames"])
    p = out / "src/weapon_sprites.c"; t = p.read_text()
    # old entry points keep their code under other names; the new ones live in the appended block
    for a, b in (("void set_weapon_sprite_position_offset(s16 offX, s16 offY) {", "static __attribute__((unused)) void m14_old_bob(s16 offX, s16 offY) {"),
                 ("void m14_fire_anim(void) {", "static __attribute__((unused)) void m14_old_fire(void) {"),
                 ("void step_weapon_animation(TransferMethod transfer_type) {", "static __attribute__((unused)) void m14_old_step(TransferMethod transfer_type) {")):
        assert t.count(a) == 1, a
        t = t.replace(a, b, 1)
    t += C_LOGIC.replace("@DATA@", gen_c(ws)).replace("@NW@", str(len(ws)))
    t += "\nvoid step_weapon_animation(TransferMethod transfer_type) { m14w_step(); }\n"
    p.write_text(t)
    # game.c hooks
    g = out / "src/game.c"; t = g.read_text()
    def rep(a, b):
        nonlocal t
        assert t.count(a) == 1, a
        t = t.replace(a, b, 1)
    rep("""void init_shotgun() {
    set_weapon_anim(SHOTGUN_IDLE_ANIM, DMA);
    { extern void update_weapon_sprites(TransferMethod t); update_weapon_sprites(DMA); }
    { extern void m14_weapon_preload(void); m14_weapon_preload(); }
}""", "void init_shotgun() { extern void m14w_select(u8 id); extern u8 m14w_cur; m14w_select(m14w_cur); }")
    rep("        if(shooting == m14_anim_at) { { extern void m14_fire_anim(void); m14_fire_anim(); } }\n", "")
    rep("{ s32 sl = 135 / (last_frame_ticks ? last_frame_ticks : 1); if (sl < 2) sl = 2; if (sl > 12) sl = 12; shooting = sl; m14_anim_at = (sl > 4) ? 4 : 1; }",
        "{ extern u16 m14w_cad(void); extern void m14_fire_anim(void); s32 sl = m14w_cad() / (last_frame_ticks ? last_frame_ticks : 1); if (sl < 1) sl = 1; if (sl > 120) sl = 120; shooting = sl; m14_anim_at = -1; { extern u8 m14w_sfx(void); if (m14w_sfx() != 75) m14_fire_anim(); } }")
    rep("        play_sfx(SFX_SHOTGUN_ID, 15);\n        run_in_phs", "        { extern u8 m14w_sfx(void); if (m14w_sfx() != 75) play_sfx(m14w_sfx(), 15); }\n        run_in_phs")
    rep("if (drawn_to_center_cols == DECORATION) { extern void m14_shoot_dec(u8 l, u16 s); m14_shoot_dec(sprite_on_center_col, center_object_sector); }",
        "if (drawn_to_center_cols == DECORATION) { extern void m14_shoot_dec(u8 l, u16 s); extern u8 m14w_pellets(void); for (u8 m14_p = 0; m14_p < m14w_pellets(); m14_p++) m14_shoot_dec(sprite_on_center_col, center_object_sector); }")
    rep("    if(joy_button_pressed(BUTTON_A|BUTTON_C) && !shooting) {",
        "    { static u8 m14_sp = 1; u8 m14_now = joy_button_pressed(BUTTON_A) ? 1 : 0; if (m14_now && !m14_sp) { extern void m14w_next(void); m14w_next(); } m14_sp = m14_now; }\n"
        "    { static s16 m14_saw_t = 0; static u8 m14_saw_on = 0; extern u8 m14w_sfx(void); if (m14w_sfx() == 75 && joy_button_pressed(BUTTON_C)) { m14_saw_t -= (s16)last_frame_ticks; { static s16 m14_saw_f = 0; extern void m14_fire_anim(void); m14_saw_f -= (s16)last_frame_ticks; if (m14_saw_f <= 0) { m14_fire_anim(); m14_saw_f = 34; } } if (!m14_saw_on || m14_saw_t <= 0) { XGM_startPlayPCM(75, 15, SOUND_PCM_CH4); m14_saw_t = 96; m14_saw_on = 1; } } else if (m14_saw_on) { extern void m14w_idle(void); XGM_stopPlayPCM(SOUND_PCM_CH4); m14_saw_on = 0; m14w_idle(); } }\n    if(joy_button_pressed(BUTTON_A|BUTTON_C) && !shooting) {")
    # sound registration
    rep("    XGM_setPCM(SFX_SHOTGUN_ID, sfx_shotgun, sizeof(sfx_shotgun));",
        "    XGM_setPCM(SFX_SHOTGUN_ID, sfx_shotgun, sizeof(sfx_shotgun));\n" +
        "".join("    { extern const u8 sfx_w_%s[]; extern const u16 sfx_w_%s_len; XGM_setPCM(%d, sfx_w_%s, sfx_w_%s_len); }\n" % (k, k, i, k, k) for k, i in SFX_IDS.items()))
    assert t.count("joy_button_pressed(BUTTON_A|BUTTON_C)") == 2
    t = t.replace("joy_button_pressed(BUTTON_A|BUTTON_C)", "joy_button_pressed(BUTTON_C)")
    k = "        if(shooting == 0 && joy_button_pressed(BUTTON_C)) { shooting = 1;}\n"
    assert t.count(k) == 1
    t = t.replace(k, "")          # this re-armed shooting forever: held button never fired again (now: auto-fire)
    g.write_text(t)
    # sounds
    szs = {}; ctext = ""
    for k, (lump, sec) in SOUNDS.items():
        b = make_pcm(w.lump(lump), sec); szs[k] = len(b)
        ctext += "const u8 sfx_w_%s[%d] __attribute__((aligned(256), section(\".wpndata\"))) = {%s};\nconst u16 sfx_w_%s_len = %d;\n" % (k, len(b), ",".join(str(x) for x in b), k, len(b))
    p.write_text(p.read_text() + ctext)
    print("M14 weapons: %d weapons, %d bytes of tiles, sounds %s, cut=%d" % (len(ws), tot, szs, cut))
