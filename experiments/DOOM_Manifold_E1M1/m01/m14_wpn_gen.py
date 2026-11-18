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
if os.environ.get("MANIFOLD_WPN_GAME") == "heretic":
    # Heretic shareware: slots keep the Doom behaviour classes (0 melee, 1 single, 2 spread, 3 rapid, 4 projectile, 5 melee)
    WEAPONS = [
        ("FIST",    ["STFFA0"], ["STFFC0"],            189, 86, 0, "punch"),    # Staff
        ("PISTOL",  ["GWNDA0"], ["GWNDC0"],            120, 60, 1, "pistol"),   # Elven Wand
        ("SHOTGUN", ["CRBWA0"], ["CRBWD0"],            317, 60, 3, "shotgun"),  # Ethereal Crossbow
        ("CHAINGUN",["BLSRA0"], ["BLSRC0"],             34, 17, 1, "pistol"),   # Dragon Claw
        ("ROCKET",  ["GWNDA0"], ["GWNDC0"],            171, 60, 1, "rocket"),   # placeholder (small art) until the Hellstaff (registered only)
        ("SAW",     ["GAUNA0"], ["GAUNB0"],             34, 34, 0, "saw"),      # Gauntlets of the Necromancer
    ]
SOUNDS = {  # key -> (lump, max seconds @14 kHz)
    "punch": ("DSPUNCH", 0.35), "shotgun": ("DSSHOTGN", 0.4),
    "rocket": ("DSRLAUNC", 0.4), "saw": ("DSSAWFUL", 0.35),
    "mpain": ("DSPOPAIN", 0.25), "mdeath": ("DSPODTH1", 0.4),
}
# placeholder WAV resources (were copies of select.wav = noise) replaced with the real Doom sounds
WAV_FIX = {"enemya_wake.wav": ("DSPOSIT1", 0.6), "jump1.wav": ("DSNOWAY", 0.4), "jump2.wav": ("DSOOF", 0.4), "liftgoup.wav": ("DSPSTART", 0.5)}
if os.environ.get("MANIFOLD_WPN_GAME") == "heretic":
    SOUNDS = {"punch": ("STFHIT", 0.35), "shotgun": ("BOWSHT", 0.4), "rocket": ("BOWSHT", 0.25), "saw": ("GNTFUL", 0.35),
              "mpain": ("CHICPAI", 0.25), "mdeath": ("IMPDTH", 0.4)}
    WAV_FIX = {"enemya_wake.wav": ("IMPSIT", 0.6), "jump1.wav": ("PLROOF", 0.4), "jump2.wav": ("PLROOF", 0.4), "liftgoup.wav": ("DORMOV", 0.5)}
SFX_BASE = 72
SFX_IDS = {"punch": 72, "shotgun": 73, "rocket": 74, "saw": 75, "mpain": 76, "mdeath": 77}   # pistol keeps SFX_SHOTGUN_ID (69)

SCALE = {"SAW": 0.5 if os.environ.get("MANIFOLD_WPN_GAME") == "heretic" else 0.66}      # too wide for 128 tiles: scale it down instead of cropping the sides
BASE_BOTTOM = 168            # Doom status bar line: weapon art below it is hidden anyway
PIS_X0, PIS_Y0 = 122, 104    # origin that the original pistol canvas had (dx,dy = X0-122, Y0-104)
A_TILES, B_TILES = 128, 104
POST = {"FIST": ([["PUNGC0"], ["PUNGD0"], ["PUNGC0"], ["PUNGB0"]], 38),
        "SHOTGUN": ([["SHTGB0"], ["SHTGC0"], ["SHTGD0"], ["SHTGC0"], ["SHTGB0"]], 43),
        "PISTOL": ([["PISGC0"], ["PISGD0"], ["PISGC0"]], 30)}
FIRE_MAXTILES = 128          # fire frames live in the reclaimed window area: 104 tiles are known to be safe there


SHEET_ORDER = ("PUNGA0 PUNGB0 PUNGC0 PUNGD0 PISGA0 PISGB0 PISGC0 PISGD0 PISGE0 PISFA0 SHTGA0 SHTGB0 SHTGC0 SHTGD0 SHTFA0 SHTFB0 "
               "SAWGA0 SAWGB0 SAWGC0 SAWGD0 CHGGA0 CHGGB0 CHGFA0 CHGFB0 MISFA0 MISFB0 MISFC0 MISFD0 MISGA0 MISGB0").split()


SHEET_OFFS = {}      # name -> (dx, dy): where an edited (smaller) frame sits relative to its Doom lump


def load_sheet(path, w):
    """User-edited weapon art: one RGBA sheet (transparent background), 16 colours = 15 opaque + transparent.
    Frames are laid out left to right in SHEET_ORDER; each keeps the size (and therefore the Doom offsets) of its WAD lump."""
    import wad_textures as WT
    from PIL import Image
    im = Image.open(path).convert("RGBA"); W, H = im.size; a = im.getchannel("A")
    cols = [x for x in range(W) if a.crop((x, 0, x + 1, H)).getbbox()]
    npx = lambda s: int((__import__("numpy").array(a.crop((s[0], 0, s[1] + 1, H))) > 0).sum())
    def split(gapmin):                                # frames are separated by >= gapmin empty columns
        sg = []; s0 = p0 = cols[0]
        for x in cols[1:]:
            if x - p0 - 1 >= gapmin: sg.append((s0, p0)); s0 = x
            p0 = x
        sg.append((s0, p0))
        return [s for s in sg if npx(s) >= 60]        # stray specks are not frames
    NEED = len(SHEET_ORDER) + 4
    seg = split(3)
    if len(seg) != NEED:                              # tightly packed sheet: try narrower gaps; extra trailing pieces (explosion debris) are ignored
        for gm in (2, 1):
            s2 = split(gm)
            if len(s2) >= NEED: seg = s2[:NEED] if len(s2) > NEED else s2; break
    order = list(SHEET_ORDER)
    alias = {}
    if len(seg) == len(order) + 3:                    # the two shotgun flashes (SHTFA0/SHTFB0) touch: split that block at its widest inner gap
        i = order.index("SHTFA0"); x0, x1 = seg[i]
        colsb = [x for x in range(x0, x1 + 1) if a.crop((x, 0, x + 1, H)).getbbox()]
        gaps = sorted(((colsb[k + 1] - colsb[k], k) for k in range(len(colsb) - 1)), reverse=True)
        if gaps and gaps[0][0] > 1:
            k = gaps[0][1]; seg[i:i + 1] = [(x0, colsb[k]), (colsb[k + 1], x1)]
    if len(seg) != len(order) + 4:
        raise ValueError("sheet has %d frames, expected %d (30 weapon frames + 4 rocket projectile/explosion frames); frames need >= 4 empty columns between them, and no stray pixels. Frame widths: %s" % (len(seg), len(order) + 4, [s[1] - s[0] + 1 for s in seg]))
    frames = {}
    for name, (x0, x1) in zip(order, seg):
        pw, ph, pimg = WT.patch_image(w.lump(name))
        ss = float(os.environ.get("MANIFOLD_WPN_SHEET_SCALE", "1"))     # legacy: whole sheet drawn at this fraction of the Doom size
        if ss != 1.0: pw, ph = round(pw * ss), round(ph * ss)
        crop = a.crop((x0, 0, x1 + 1, H)).getbbox()
        fw, fh = x1 - x0 + 1, crop[3] - crop[1]
        top = crop[1]
        if top + max(fh, ph if (fw, fh) == (pw, ph) else fh) > H: top = max(0, H - fh)
        frames[name] = im.crop((x0, top, x0 + fw, top + fh))
        SHEET_OFFS[name] = (0, 0)
        if os.environ.get("MANIFOLD_WPN_SHEET_ANCHOR") == "1":
            SHEET_OFFS[name] = ("anchor", pw, ph, fw, fh)
        elif ss == 1.0 and (fw, fh) != (pw, ph):
            # an edited frame smaller than the Doom lump (cropped / redrawn): find where it sits inside the original silhouette
            import numpy as np
            m = np.array(frames[name].getchannel("A")) > 0
            o = np.array([[p is not None for p in r] for r in pimg])
            best = (-1, 0, 0)
            for dy in range(-2, ph - fh + 3):
                for dx in range(-2, pw - fw + 3):
                    y0, y1, xa, xb = max(0, dy), min(ph, dy + fh), max(0, dx), min(pw, dx + fw)
                    if y1 <= y0 or xb <= xa: continue
                    inter = int((m[y0 - dy:y1 - dy, xa - dx:xb - dx] & o[y0:y1, xa:xb]).sum())
                    if inter > best[0]: best = (inter, dx, dy)
            SHEET_OFFS[name] = (best[1], best[2])
    for k, v in alias.items(): frames[k] = frames[v]; SHEET_OFFS[k] = SHEET_OFFS[v]
    colors = sorted({px[:3] for px in im.getdata() if px[3] > 0})
    if len(colors) > 15: raise ValueError("sheet has %d opaque colours (max 15)" % len(colors))
    return frames, colors


def md_color(c):
    r, g, b = c
    f = lambda v: (v * 7 + 127) // 255
    return (f(b) << 9) | (f(g) << 5) | (f(r) << 1)


def build(w, rgb, cut, sheet=None):
    from PIL import Image
    sheet_frames, sheet_pal = sheet if sheet else (None, None)

    def load(name):
        l = w.lump(name)
        lo, to = struct.unpack("<hh", l[4:8])
        if sheet_frames and name in sheet_frames:
            ss = float(os.environ.get("MANIFOLD_WPN_SHEET_SCALE", "1"))
            so = SHEET_OFFS.get(name, (0, 0))
            if so[0] == "anchor":      # drawn as the visible part only: bottom on the viewport line, centred where the Doom frame was
                X, Y = 160 - so[3] // 2, (BASE_BOTTOM - cut) - so[4]          # centred on the screen, standing on the viewport line
            else: X, Y = -lo + so[0], -to + so[1]
            if ss != 1.0: X, Y = round(160 + (X - 160) * ss), round(BASE_BOTTOM - cut + (Y - (BASE_BOTTOM - cut)) * ss)   # same anchor as SCALE
            return sheet_frames[name].copy(), X, Y
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
        if sheet_frames and os.environ.get("MANIFOLD_WPN_SHEET_ANCHOR") == "1" and len(layers) > 1:
            g0, f1 = layers[0], layers[1]      # muzzle flash: centred on the gun, 55% of its height overlapping the gun
            layers[1] = (f1[0], g0[1] + g0[0].width // 2 - f1[0].width // 2, g0[2] - f1[0].height + round(f1[0].height * 0.55))
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
        sc = 1.0 if (sheet_frames and os.environ.get("MANIFOLD_WPN_SHEET_SCALE")) else SCALE.get(name, 1.0)
        if sheet_pal and name == "FIST": fire, hold = ["PUNGB0"], 34
        if sheet_pal and name == "SHOTGUN": hold = 26
        frames = [frame_canvas(idle, 128, sc), frame_canvas(fire, FIRE_MAXTILES, sc)]
        # palette: 9 colours over both frames
        total_h = sum(f[0].height for f in frames); total_w = max(f[0].width for f in frames)
        sheet = Image.new("RGB", (total_w, total_h), (0, 0, 0)); yy = 0
        for cv, _, _ in frames:
            sheet.paste(cv, (0, yy), cv); yy += cv.height
        if sheet_pal:
            pal = list(sheet_pal) + [(0, 0, 0)] * (15 - len(sheet_pal)); pal_img = None
        else:
            NC = 15 if os.environ.get("MANIFOLD_WPN_GAME") else 9
            pal_img = sheet.quantize(colors=NC, method=Image.MEDIANCUT)
            pal = (pal_img.getpalette() + [0] * (NC * 3))[:NC * 3]
            pal = [tuple(pal[i * 3:i * 3 + 3]) for i in range(NC)]
        def conv(cv, cx0, cy0):
            tw, th = cv.width // 8, cv.height // 8
            flat = Image.new("RGB", cv.size, (0, 0, 0)); flat.paste(cv, (0, 0), cv)
            if sheet_pal:
                near = {}
                def nidx(c):
                    if c not in near: near[c] = min(range(len(sheet_pal)), key=lambda i: sum((c[k] - sheet_pal[i][k]) ** 2 for k in range(3)))
                    return near[c]
                idx = [[(nidx(flat.getpixel((x, y))) + 1) if cv.getpixel((x, y))[3] > 0 else 0 for x in range(cv.width)] for y in range(cv.height)]
            else:
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
            return dict(dx=cx0 - PIS_X0, dy=cy0 - PIS_Y0, spr=spr, data=data, nsA=0)
        fr = []
        for k, (cv, cx0, cy0) in enumerate(frames):
            f = conv(cv, cx0, cy0); f["nsA"] = len(f["spr"]) if k == 0 else 0     # idle frame lives in buffer A, fire frame in buffer B
            fr.append(f)
        post = []
        if sheet_pal and name in POST:
            for names in POST[name][0]:
                mt = A_TILES + B_TILES
                while True:
                    cvp, cxp, cyp = frame_canvas(names, mt, sc); f = conv(cvp, cxp, cyp)
                    acc = 0; nsa = 0
                    for (_, _, _, nt) in f["spr"]:
                        if acc + nt > A_TILES: break
                        acc += nt; nsa += 1
                    if sum(x[3] for x in f["spr"]) - acc <= B_TILES: break
                    mt -= 4
                f["nsA"] = nsa; post.append(f)
        out.append(dict(name=name, frames=fr, post=post, ptime=(POST[name][1] if (sheet_pal and name in POST) else 0), pal=[md_color(c) for c in pal], cad=cad, hold=hold, pel=pel, snd=snd))
    return out


C_LOGIC = r'''
/* ===== M14 multi-weapon (generated by m14_wpn_gen.py) ===== */
typedef struct { u8 ox, oy, size, nt; } m14w_spr;
typedef struct { s16 dx, dy; u8 ns; u8 nsA; u16 ntiles; const m14w_spr *spr; const u32 *tiles; } m14w_frame;
typedef struct { const m14w_frame *idle, *fire; u16 pal[15]; u16 cad, hold; u8 pel, sfx; const m14w_frame *post[6]; u8 npost; u16 ptime; } m14w_def;
@DATA@
u8 m14w_cur = 1;
static const m14w_frame *m14w_shown; static u8 m14w_isfire; static u16 m14w_hold;
static s16 m14w_bx, m14w_by; static u8 m14w_pi = 0xFF, m14w_pt;
u16 m14w_cad(void) { return m14w_defs[m14w_cur].cad; }
u8 m14w_pellets(void) { return m14w_defs[m14w_cur].pel; }
u8 m14w_sfx(void) { return m14w_defs[m14w_cur].sfx; }
/* Where the shown frame sits in VRAM: 0 = all tiles in buffer A, 1 = all in buffer B, 2 = split (first nsA sprites in A, rest in B).
   Frames are never loaded over tiles that are on screen (that tears: square corrupt tiles on real hardware): the next frame is loaded
   into the buffer that is not displayed, then the sprite list is switched. Frames that need both buffers hide the weapon while loading. */
static u8 m14w_mode, m14w_ib;      /* m14w_ib: buffer of the idle frame (0 = A, 1 = B); the fire frame lives in the other one */
static void m14w_place(void) {
    const m14w_frame *f = m14w_shown; if (!f) return;
    u16 ta = (u16)start_tile_loc, tb = manifold_weapon_buf1, m = m14w_mode;
    VDP_clearSprites();
    for (u8 i = 0; i < f->ns; i++) {
        const m14w_spr *s = &f->spr[i];
        u8 inA = (m == 0) || (m == 2 && i < f->nsA);
        VDP_setSprite(sprite_idx_start + i, BASE_WEAPON_X + f->dx + s->ox + m14w_bx, BASE_WEAPON_Y + 8 + f->dy + s->oy + m14w_by,
                      s->size, TILE_ATTR_FULL(PAL0, 0, 0, 0, inA ? ta : tb));
        if (inA) ta += s->nt; else tb += s->nt;
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
        VDP_setSpritePosition(sprite_idx_start + i, BASE_WEAPON_X + f->dx + s->ox + offX, BASE_WEAPON_Y + 8 + f->dy + s->oy + offY);
    }
    m14_sat_update(f->ns);
}
/* tile copy in chunks of <= 64 tiles, one per vblank (a 7 KB copy with interrupts off starves the 3D view's own transfer: black band) */
static void m14w_tiles(const u32 *src, u16 idx, u16 n) {
    while (n) {
        u16 c = n > 64 ? 64 : n;
        for (;;) { SYS_disableInts(); if (*(volatile u16*)0xC00004 & 8) break; SYS_enableInts(); __asm__ volatile("nop\n nop\n nop\n nop"); }
        VDP_loadTileData(src, idx, c, CPU);
        SYS_enableInts();
        src += c * 8; idx += c; n -= c;
        if (n) while (*(volatile u16*)0xC00004 & 8) { }
    }
}
static void m14w_load(const m14w_frame *f, u8 mode) {
    if (mode == 0) m14w_tiles(f->tiles, start_tile_loc, f->ntiles);
    else if (mode == 1) m14w_tiles(f->tiles, manifold_weapon_buf1, f->ntiles);
    else {
        u16 ta = 0; for (u8 i = 0; i < f->nsA; i++) ta += f->spr[i].nt;
        if (ta) m14w_tiles(f->tiles, start_tile_loc, ta);
        if (f->ntiles > ta) m14w_tiles(f->tiles + ta * 8, manifold_weapon_buf1, f->ntiles - ta);
    }
}
static void m14w_hide(void) { VDP_clearSprites(); m14_sat_update(0); }
static void m14w_show(const m14w_frame *f, u8 mode) { m14w_shown = f; m14w_mode = mode; m14w_place(); }
static u8 m14w_fits(const m14w_frame *f, u8 buf) { return f->ntiles <= (buf ? 104 : 128); }
static void m14w_home(const m14w_def *d) {      /* idle in A, fire in B (a fire frame bigger than 104 tiles: swapped), shown with the weapon hidden meanwhile */
    u8 sw = (d->fire->ntiles > 104 && d->idle->ntiles <= 104) ? 1 : 0;
    m14w_hide(); m14w_ib = sw; m14w_load(d->idle, sw); m14w_load(d->fire, 1 - sw); m14w_show(d->idle, sw);
}
static void m14w_post_end(void) {
    const m14w_def *d = &m14w_defs[m14w_cur]; u8 m = m14w_mode; m14w_pi = 0xFF; m14w_isfire = 0; m14w_hold = 0;
    if (m == 2 || !m14w_fits(d->idle, 1 - m)) { m14w_home(d); return; }
    u8 nb = 1 - m;                                  /* the buffer that is not on screen */
    m14w_load(d->idle, nb); m14w_show(d->idle, nb); m14w_ib = nb;
    m14w_load(d->fire, m);                          /* the fire frame goes to the buffer that just became free */
}
static void m14w_post_show(const m14w_frame *f) {
    u8 m = m14w_mode;
    if (m != 2 && m14w_fits(f, 1 - m)) { m14w_load(f, 1 - m); m14w_show(f, 1 - m); return; }
    u8 m2 = f->ntiles <= 104 ? 1 : (f->ntiles <= 128 ? 0 : 2);
    m14w_hide(); m14w_load(f, m2); m14w_show(f, m2);
}
void m14w_select(u8 id) {
    const m14w_def *d = &m14w_defs[id]; m14w_cur = id; m14w_pi = 0xFF;
    PAL_setColors(1, d->pal, 15, CPU);
    m14w_home(d); m14w_isfire = 0; m14w_hold = 0;
}
void m14w_next(void) { m14w_select((u8)((m14w_cur + 1) % @NW@)); }
void m14_fire_anim(void) {
    const m14w_def *d = &m14w_defs[m14w_cur];
    if (m14w_pi != 0xFF) m14w_post_end();
    u16 h = d->hold / (last_frame_ticks ? last_frame_ticks : 1); if (h < 1) h = 1;
    if (d->sfx == 75) return;               /* chainsaw: its two frames alternate by themselves (m14w_step) */
    m14w_hold = h; m14w_isfire = 1; m14w_show(d->fire, 1 - m14w_ib);
}
void m14w_idle(void) { if (m14w_isfire) { m14w_show(m14w_defs[m14w_cur].idle, m14w_ib); m14w_isfire = 0; m14w_hold = 0; } }
void m14w_step(void) {
    const m14w_def *d = &m14w_defs[m14w_cur];
    if (d->sfx == 75) {                     /* Doom's chainsaw ready state: the two frames alternate every 4 tics, both stay resident */
        static s16 st; st -= (s16)last_frame_ticks;
        if (st <= 0) { st = 34; m14w_isfire ^= 1; m14w_show(m14w_isfire ? d->fire : d->idle, m14w_isfire ? 1 - m14w_ib : m14w_ib); }
        return;
    }
    if (m14w_pi != 0xFF) {
        s16 q = (s16)m14w_pt - (s16)(last_frame_ticks > 90 ? 90 : last_frame_ticks);
        if (q > 0) m14w_pt = (u8)q;
        else {
            m14w_pi++;
            if (m14w_pi >= d->npost) m14w_post_end();
            else { m14w_post_show(d->post[m14w_pi]); m14w_isfire = 0; m14w_pt = d->ptime; }
        }
        return;
    }
    if (m14w_hold && --m14w_hold == 0) {
        if (d->npost) { m14w_pi = 0; m14w_post_show(d->post[0]); m14w_isfire = 0; m14w_pt = d->ptime; }
        else { m14w_show(d->idle, m14w_ib); m14w_isfire = 0; }
    }
}
'''


def gen_c(ws):
    s = []
    for i, wp in enumerate(ws):
        for j, f in enumerate(wp["frames"]):
            n = "w%df%d" % (i, j)
            s.append("static const m14w_spr %s_s[] = {%s};" % (n, ",".join("{%d,%d,0x%02X,%d}" % x for x in f["spr"])))
            d = f["data"]
            s.append("static const u32 %s_t[] __attribute__((section(\"%s\"))) = {%s};" % (n, ".wpndata2" if j == 1 else ".wpndata", ",".join("0x%08X" % v for v in d)))   # fire frames live in the big window
            s.append("static const m14w_frame %s = {%d,%d,%d,%d,%d,%s_s,%s_t};" % (n, f["dx"], f["dy"], len(f["spr"]), f["nsA"], len(d) // 8, n, n))
        for j, f in enumerate(wp["post"]):
            n = "w%dp%d" % (i, j)
            s.append("static const m14w_spr %s_s[] = {%s};" % (n, ",".join("{%d,%d,0x%02X,%d}" % x for x in f["spr"])))
            d = f["data"]
            s.append("static const u32 %s_t[] __attribute__((section(\".wpndata2\"))) = {%s};" % (n, ",".join("0x%08X" % v for v in d)))
            s.append("static const m14w_frame %s = {%d,%d,%d,%d,%d,%s_s,%s_t};" % (n, f["dx"], f["dy"], len(f["spr"]), f["nsA"], len(d) // 8, n, n))
    s.append("static const m14w_def m14w_defs[%d] = {" % len(ws))
    for i, wp in enumerate(ws):
        sfx = SFX_IDS.get(wp["snd"], 69)
        np_ = len(wp["post"])
        s.append("  {&w%df0,&w%df1,{%s},%d,%d,%d,%d,{%s},%d,%d}," % (i, i, ",".join("0x%04X" % c for c in wp["pal"]), wp["cad"], wp["hold"], wp["pel"], sfx, ",".join("&w%dp%d" % (i, j) for j in range(np_)) or "0", np_, wp["ptime"]))
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
    w = WT.Wad(wad)
    if os.environ.get("MANIFOLD_SAFE_WAD") == "1":
        import m12_objects as _M; w = _M._SafeWad(w)
    rgb = WT.playpal(w)
    cut = int(os.environ.get("MANIFOLD_WPN_CUT", "16"))
    _sp = os.environ.get("MANIFOLD_WPN_SHEET")
    ws = build(w, rgb, cut, load_sheet(_sp, w) if _sp else None)
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
    # r059: A = switch weapon, B = fire, C = use / open doors
    t = t.replace("BUTTON_B", "@@B@@").replace("BUTTON_C", "BUTTON_B").replace("@@B@@", "BUTTON_C")
    k = "s16 bobOffY = gun_bobs[idx].y<<1;"
    assert t.count(k) == 1
    t = t.replace(k, k + " if (bobOffY < 0) bobOffY = 0;")      # bob only downward (under the HUD)
    if os.environ.get("MANIFOLD_WPN_SHEET") or os.environ.get("MANIFOLD_WPN_GAME"):       # the 15-colour weapon palette now occupies PAL0 entry 10, which was the backdrop: backdrop -> entry 0 (black)
        for x, y in (("VDP_setBackgroundColor(10);", "VDP_setBackgroundColor(0);"), ("PAL_setPalette(PAL0, shotgun.palette->data, DMA);", "PAL_setPalette(PAL0, shotgun.palette->data, DMA); PAL_setColor(0, 0);")):
            assert t.count(x) == 1, x
            t = t.replace(x, y)
    g.write_text(t)
    # sounds
    szs = {}; ctext = ""
    for k, (lump, sec) in SOUNDS.items():
        b = make_pcm(w.lump(lump), sec); szs[k] = len(b)
        ctext += "const u8 sfx_w_%s[%d] __attribute__((aligned(256), section(\".wpndata\"))) = {%s};\nconst u16 sfx_w_%s_len = %d;\n" % (k, len(b), ",".join(str(x) for x in b), k, len(b))
    p.write_text(p.read_text() + ctext)
    for fn, (lump, sec) in WAV_FIX.items():
        b = make_pcm(w.lump(lump), sec)
        with wave.open(str(out / "res/sfx" / fn), "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(1); wf.setframerate(14000)
            wf.writeframes(bytes(((x + 128) & 0xFF) for x in b))       # WAV 8-bit is unsigned
    print("M14 weapons: %d weapons, %d bytes of tiles, sounds %s, cut=%d" % (len(ws), tot, szs, cut))
