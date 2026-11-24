"""Tile Palette Studio — native per-tile Mega Drive palette optimizer.

Clean-room NumPy implementation inspired by tiledpalettequant's *task*, not a
Python translation of its algorithm. The original project is MIT licensed.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Settings:
    palettes: int = 4
    colors: int = 16
    tile_size: int = 8
    iterations: int = 10
    dither: str = "off"  # off or six Rilden patterns
    dither_strength: float = 0.35
    transparent: bool = False
    alpha_threshold: int = 128
    background: str = "#000000"
    base_tile: int = 0
    seed: int = 42
    vram_budget_tiles: int = 1024  # User-configurable estimate; actual VRAM usage is game-specific
    allow_lossy_tiles: bool = False


@dataclass
class Result:
    preview: Image.Image
    palettes_rgb: np.ndarray       # (P,C,3) RGB in 0,34,...,238
    tile_palettes: np.ndarray      # (tile_rows,tile_cols)
    indices: np.ndarray            # padded H,W of palette-local 4bpp indices
    settings: Settings
    source_size: tuple[int, int]
    padded_size: tuple[int, int]
    history: list[float]
    mean_squared_error: float
    transparent_pixels: int


_RGB_CODES = np.arange(512, dtype=np.uint16)
_RGB3 = np.stack(((_RGB_CODES >> 6) & 7, (_RGB_CODES >> 3) & 7, _RGB_CODES & 7), axis=-1).astype(np.float32)
_WEIGHT = np.array([1.0, 1.28, 0.72], dtype=np.float32)
_BAYER2 = np.array([[0, 2], [3, 1]], dtype=np.float32)
_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32)
_BAYER8 = np.kron(_BAYER4, np.ones((2, 2), np.float32)) * 4 + np.tile(_BAYER2, (4, 4))
# Exact 2x2 ordering matrices from rilden/tiledpalettequant worker.js (MIT).
_RILDEN_PATTERNS = {
    'diagonal4': np.array([[0, 2], [3, 1]], dtype=np.uint8),
    'horizontal4': np.array([[0, 3], [1, 2]], dtype=np.uint8),
    'vertical4': np.array([[0, 1], [3, 2]], dtype=np.uint8),
    'diagonal2': np.array([[0, 1], [1, 0]], dtype=np.uint8),
    'horizontal2': np.array([[0, 1], [0, 1]], dtype=np.uint8),
    'vertical2': np.array([[0, 0], [1, 1]], dtype=np.uint8),
}
# Matrices above are indexed [x,y], as in rilden/tiledpalettequant worker.js (MIT).



def _rgb_from_hex(color: str) -> np.ndarray:
    color = color.lstrip('#')
    if len(color) != 6:
        raise ValueError('A cor deve estar em hexadecimal #RRGGBB')
    return np.array([int(color[k:k+2], 16) for k in (0, 2, 4)], dtype=np.uint8)


def _distance(codes: np.ndarray, colors: np.ndarray) -> np.ndarray:
    """CIE-inspired weighted RGB distances in 3-bit channel space."""
    a = codes.astype(np.float32)
    b = colors.astype(np.float32)
    return np.sum((a[:, None, :] - b[None, :, :]) ** 2 * _WEIGHT, axis=2)


def _seed_groups(features: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    count = len(features)
    if count == 1 or k == 1:
        return np.zeros(count, dtype=np.int16)
    k = min(k, count)
    centers = np.empty((k, features.shape[1]), dtype=np.float32)
    centers[0] = features[int(rng.integers(count))]
    dist = np.sum((features - centers[0]) ** 2, axis=1)
    for j in range(1, k):
        if float(dist.sum()) <= 0:
            centers[j] = features[int(rng.integers(count))]
        else:
            centers[j] = features[int(rng.choice(count, p=dist / dist.sum()))]
        dist = np.minimum(dist, np.sum((features - centers[j]) ** 2, axis=1))
    labels = np.zeros(count, dtype=np.int16)
    for _ in range(22):
        distances = np.sum((features[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels_new = np.argmin(distances, axis=1).astype(np.int16)
        if np.array_equal(labels, labels_new) and _ > 0:
            break
        labels = labels_new
        for p in range(k):
            subset = features[labels == p]
            if len(subset):
                centers[p] = subset.mean(axis=0)
            else:
                centers[p] = features[int(np.argmax(np.min(distances, axis=1)))]
    return labels


def _fit_palette(hist: np.ndarray, num_colors: int, zero: np.ndarray,
                 rng: np.random.Generator, zero_reserved: bool) -> np.ndarray:
    codes = np.flatnonzero(hist)
    out = np.zeros((num_colors, 3), dtype=np.float32)
    out[0] = zero
    if not len(codes):
        return out.astype(np.uint8)
    weights = hist[codes].astype(np.float64)
    colors = _RGB3[codes]
    slots = num_colors - 1 if zero_reserved else num_colors
    if slots <= 0:
        return out.astype(np.uint8)
    # Preserve palette entry 0 as common background/transparent, and fit all
    # remaining slots to actual colors. Weighted k-means++ + Lloyd refinement.
    centers = np.empty((slots, 3), np.float32)
    centers[0] = colors[int(rng.choice(len(codes), p=weights / weights.sum()))]
    best_dist = _distance(colors, centers[:1])[:, 0].astype(np.float64)
    for j in range(1, slots):
        prob = weights * np.maximum(best_dist, 0)
        if float(prob.sum()) < 1e-12:
            centers[j] = colors[int(rng.choice(len(codes), p=weights / weights.sum()))]
        else:
            centers[j] = colors[int(rng.choice(len(codes), p=prob/prob.sum()))]
        best_dist = np.minimum(best_dist, _distance(colors, centers[j:j+1])[:, 0])
    for _ in range(15):
        dist = _distance(colors, centers)
        labels = np.argmin(dist, axis=1)
        changed = False
        for j in range(slots):
            m = labels == j
            if np.any(m):
                center = np.average(colors[m], axis=0, weights=weights[m])
                if np.max(np.abs(center - centers[j])) > 0.04:
                    changed = True
                centers[j] = center
            else:
                err = weights * np.min(dist, axis=1)
                centers[j] = colors[int(np.argmax(err))]
                changed = True
        if not changed:
            break
    picks = np.rint(centers).clip(0, 7).astype(np.uint8)
    # Repair quantization duplicates with the colors carrying the most error.
    used: set[tuple[int, int, int]] = {tuple(map(int, zero))} if zero_reserved else set()
    for j in range(slots):
        key = tuple(map(int, picks[j]))
        if key in used:
            occupied = np.asarray(list(used), dtype=np.float32) if used else np.zeros((1, 3), np.float32)
            residual = _distance(colors, occupied).min(axis=1) * weights
            for c in np.argsort(-residual):
                key = tuple(map(int, colors[int(c)]))
                if key not in used:
                    picks[j] = colors[int(c)].astype(np.uint8)
                    break
        used.add(tuple(map(int, picks[j])))
    out[1:] = picks[:num_colors - 1]
    return out.astype(np.uint8)


def vram_usage(width: int, height: int, base_tile: int = 0,
               budget_tiles: int = 1024) -> dict:
    """Conservative uncompressed estimate; does not account for shared game VRAM."""
    if width < 1 or height < 1:
        raise ValueError('Dimensões devem ser positivas')
    tw, th = (width + 7)//8, (height + 7)//8
    count = tw*th
    return {
        'tiles_x': tw, 'tiles_y': th, 'tiles': count,
        'tile_bytes': count*32, 'vram_bytes': 65536,
        'base_tile': base_tile, 'budget_tiles': budget_tiles,
        'over_budget': count > budget_tiles,
        'over_index': count + base_tile > 2048,
        'vram_percent': 100.0 * count * 32 / 65536,
        'fits_vdp': count + base_tile <= 2048,
    }


def _floyd_steinberg(rgb: np.ndarray, valid: np.ndarray, pix_palette: np.ndarray,
                     palettes: np.ndarray, transparent: bool, strength: float,
                     indices: np.ndarray, preview_arr: np.ndarray) -> None:
    """Serpentine Floyd–Steinberg in RGB, constrained to each tile's palette.

    Error only crosses into an opaque pixel using the same palette. Keeps
    tile/transparent boundaries from contaminating unrelated colors.
    """
    h, w = valid.shape
    pal = (palettes.astype(np.float32) * 34.0).tolist()
    start = 1  # color index 0 is never opaque on the Mega Drive
    curr = np.zeros((w+2, 3), dtype=np.float32)
    nxt = np.zeros_like(curr)
    for y in range(h):
        forward = y % 2 == 0
        xiter = range(w) if forward else range(w-1, -1, -1)
        for x in xiter:
            if not valid[y, x]:
                continue
            pid = int(pix_palette[y, x]); colors = pal[pid]
            old = rgb[y, x]
            rr = min(255.0, max(0.0, float(old[0]) + float(curr[x+1, 0])))
            gg = min(255.0, max(0.0, float(old[1]) + float(curr[x+1, 1])))
            bb = min(255.0, max(0.0, float(old[2]) + float(curr[x+1, 2])))
            best = start; mind = float('inf')
            for j in range(start, len(colors)):
                c = colors[j]
                dr, dg, db = rr-c[0], gg-c[1], bb-c[2]
                d = dr*dr + 1.28*dg*dg + .72*db*db
                if d < mind:
                    mind = d; best = j
            indices[y, x] = best
            col = colors[best]
            preview_arr[y, x, :3] = col
            if strength <= 0:
                continue
            er = (rr-col[0])*strength
            eg = (gg-col[1])*strength
            eb = (bb-col[2])*strength
            direction = 1 if forward else -1
            nx = x + direction
            if 0 <= nx < w and valid[y, nx] and pix_palette[y, nx] == pid:
                curr[nx+1, 0] += er*7/16
                curr[nx+1, 1] += eg*7/16
                curr[nx+1, 2] += eb*7/16
            if y+1 < h:
                for dx, weight in ((-direction, 3/16), (0, 5/16), (direction, 1/16)):
                    xx = x + dx
                    if 0 <= xx < w and valid[y+1, xx] and pix_palette[y+1, xx] == pid:
                        nxt[xx+1, 0] += er*weight
                        nxt[xx+1, 1] += eg*weight
                        nxt[xx+1, 2] += eb*weight
        curr, nxt = nxt, curr
        nxt.fill(0)


def quantize(image: Image.Image, config: Settings,
             on_progress: Callable[[int, str], None] | None = None) -> Result:
    if not 0 <= config.base_tile <= 2047:
        raise ValueError('Índice inicial VDP deve estar entre 0 e 2047')
    if not 1 <= config.vram_budget_tiles <= 2048:
        raise ValueError('Orçamento VRAM deve ser de 1 a 2048 tiles')
    if not 1 <= config.palettes <= 4:
        raise ValueError('Mega Drive oferece até 4 paletas simultâneas')
    if not 2 <= config.colors <= 16:
        raise ValueError('Até 16 cores por paleta no Mega Drive')
    if config.tile_size != 8:
        raise ValueError('Os tiles do Mega Drive têm 8x8 pixels')
    if not 1 <= config.iterations <= 40:
        raise ValueError('Iterações: 1 a 40')
    if not 0 <= config.dither_strength <= 1:
        raise ValueError('Dithering: intensidade de 0 a 1')
    if config.dither not in ('off', 'diagonal4', 'horizontal4', 'vertical4', 'diagonal2', 'horizontal2', 'vertical2', 'floyd'):
        raise ValueError('Padrão de dithering inválido')

    def update(percent: int, msg: str):
        if on_progress:
            on_progress(percent, msg)

    original = image.convert('RGBA')
    width, height = original.size
    if width <= 0 or height <= 0:
        raise ValueError('Imagem inválida')
    if width * height > 16_000_000:
        raise ValueError('Limite de 16 megapixels nesta versão')
    pw = (width + 7) & ~7
    ph = (height + 7) & ~7
    raw = np.asarray(original, dtype=np.uint8)
    rgb = np.zeros((ph, pw, 3), np.uint8)
    alpha = np.zeros((ph, pw), np.uint8)
    rgb[:height, :width] = raw[..., :3]
    alpha[:height, :width] = raw[..., 3]
    valid = np.zeros((ph, pw), np.bool_)
    valid[:height, :width] = True
    if config.transparent:
        valid[:height, :width] &= alpha[:height, :width] >= config.alpha_threshold
    zero_rgb = _rgb_from_hex(config.background)
    zero = np.clip(np.rint(zero_rgb.astype(np.float32) / 34), 0, 7).astype(np.uint8)

    update(5, 'Preparando histograma por tile…')
    q3 = np.clip(np.rint(rgb.astype(np.float32) / 34), 0, 7).astype(np.uint16)
    codes = (q3[:, :, 0] << 6) | (q3[:, :, 1] << 3) | q3[:, :, 2]
    tw, th = pw // 8, ph // 8
    tile_ids = np.repeat(np.arange(th) * tw, 8)[:, None] + np.repeat(np.arange(tw), 8)[None, :]
    tile_ids = np.broadcast_to(tile_ids, (ph, pw))
    hist = np.zeros((tw * th, 512), np.float32)
    np.add.at(hist, (tile_ids[valid], codes[valid]), 1)
    active = hist.sum(axis=1)
    # Compact 4x4x4 RGB bins (histogram shape of each tile) initializes tile grouping.
    coarse = np.zeros((tw * th, 64), np.float32)
    coarse_id = (((_RGB_CODES >> 7) & 3) * 16 + ((_RGB_CODES >> 4) & 3) * 4 + ((_RGB_CODES >> 1) & 3)).astype(np.intp)
    for c in range(512):
        coarse[:, coarse_id[c]] += hist[:, c]
    coarse /= np.maximum(active[:, None], 1)
    coarse = np.sqrt(coarse, out=coarse)
    seed = np.random.default_rng(config.seed)
    assignments = _seed_groups(coarse, config.palettes, seed)
    zero_reserved = True  # Mega Drive: palette index 0 is always transparent on planes
    history: list[float] = []
    palettes = np.zeros((config.palettes, config.colors, 3), dtype=np.uint8)
    update(14, 'Otimizando paletas compartilhadas entre tiles…')
    all_colors = _RGB3
    for iteration in range(config.iterations):
        for p in range(config.palettes):
            h = hist[assignments == p].sum(axis=0)
            if not h.any():
                h = hist.sum(axis=0)
            palettes[p] = _fit_palette(h, config.colors, zero, seed, zero_reserved)
        costs = np.empty((512, config.palettes), np.float32)
        for p in range(config.palettes):
            costs[:, p] = _distance(all_colors, palettes[p, 1:]).min(axis=1)
        tile_err = hist @ costs
        # Avoid arbitrary thrash of identical tiles by stable argmin.
        new_assignments = np.argmin(tile_err, axis=1).astype(np.int16)
        total_error = float(np.sum(np.min(tile_err, axis=1)) / max(1, active.sum()))
        history.append(total_error)
        update(15 + int(65 * (iteration+1) / config.iterations),
               f'Iteração {iteration+1}/{config.iterations} · erro {total_error:.3f}')
        if np.array_equal(new_assignments, assignments):
            break
        assignments = new_assignments
    # Refit once after last assignment, otherwise palette colors may correspond
    # to the penultimate assignment rather than the final one.
    for p in range(config.palettes):
        h = hist[assignments == p].sum(axis=0)
        if not h.any():
            h = hist.sum(axis=0)
        palettes[p] = _fit_palette(h, config.colors, zero, seed, zero_reserved)
    update(85, 'Aplicando cores finais e dithering…')
    pix_palette = assignments[tile_ids]
    rgbfloat = rgb.astype(np.float32)
    pattern = _RILDEN_PATTERNS.get(config.dither)
    indices = np.zeros((ph, pw), np.uint8)
    preview_arr = np.zeros((ph, pw, 4), np.uint8)
    preview_arr[..., 3] = 255
    if config.transparent:
        preview_arr[~valid, 3] = 0
    if config.dither == 'floyd':
        _floyd_steinberg(rgbfloat, valid, pix_palette, palettes,
                         config.transparent, config.dither_strength,
                         indices, preview_arr)
    else:
        for p in range(config.palettes):
            mask = valid & (pix_palette == p)
            coords = np.flatnonzero(mask)
            if not len(coords):
                continue
            colors = np.rint(palettes[p].astype(np.float32) * 34).astype(np.uint8)
            src_flat = rgbfloat.reshape(-1, 3)
            ind_flat = indices.reshape(-1)
            dst_flat = preview_arr.reshape(-1, 4)
            for ch in np.array_split(coords, max(1, (len(coords)+4095)//4096)):
                original = src_flat[ch]
                if pattern is None or config.dither_strength <= 0:
                    dif = original[:, None, :] - colors[None, :, :].astype(np.float32)
                    dist = np.sum(dif*dif*np.array([2,4,1],np.float32),axis=2)
                    dist[:,0] = np.inf
                    chosen = np.argmin(dist,axis=1).astype(np.uint8)
                else:
                    # Rilden's iterative candidate generation in linear (squared RGB)
                    # space; sorted by brightness and selected via pattern[x][y].
                    n = 2 if config.dither.endswith('2') else 4
                    linear = original*original
                    error = np.zeros_like(linear)
                    choices = []
                    brightnesses = []
                    bright_weights = np.array([.299,.587,.114],np.float32)
                    palette_linear = colors.astype(np.float32)**2
                    for k in range(n):
                        sample = np.sqrt(np.clip(linear+error*config.dither_strength,0,65025))
                        diff = sample[:,None,:]-colors[None,:,:].astype(np.float32)
                        distance = np.sum(diff*diff*np.array([2,4,1],np.float32),axis=2)
                        distance[:,0] = np.inf
                        candidate = np.argmin(distance,axis=1).astype(np.uint8)
                        choices.append(candidate)
                        brightnesses.append(np.sum(palette_linear[candidate]*bright_weights,axis=1))
                        error += linear-palette_linear[candidate]
                    order = np.argsort(np.stack(brightnesses,axis=1),axis=1,kind='stable')
                    ordered = np.take_along_axis(np.stack(choices,axis=1),order,axis=1)
                    x = ch % pw
                    y = ch // pw
                    rank = pattern[x%2,y%2]
                    chosen = ordered[np.arange(len(ch)),rank]
                ind_flat[ch] = chosen
                dst_flat[ch,:3] = colors[chosen]
    # Outside the source rectangle, map to color zero for clean tile padding.
    preview = Image.fromarray(preview_arr[:height, :width], 'RGBA')
    # RGB error on visible, opaque pixels (reconstruction compared with original)
    vis = valid[:height, :width]
    if np.any(vis):
        delta = preview_arr[:height, :width, :3][vis].astype(np.float32) - rgb[:height, :width][vis].astype(np.float32)
        mse = float(np.mean(delta**2))
    else:
        mse = 0.0
    update(100, 'Concluído')
    return Result(preview, palettes.astype(np.uint8)*34,
                  assignments.reshape(th, tw), indices, config, (width, height),
                  (pw, ph), history, mse, int(np.count_nonzero(~vis)))


def _genesis_cram_word(rgb: np.ndarray) -> int:
    r, g, b = np.rint(np.asarray(rgb, dtype=np.float32) / 34).clip(0, 7).astype(int)
    return int((b << 9) | (g << 5) | (r << 1))


def palette_image(result: Result) -> Image.Image:
    n = result.settings.colors
    p = result.settings.palettes
    size = 24
    out = Image.new('RGB', (n * size, p * size), '#242833')
    draw = ImageDraw.Draw(out)
    for j in range(p):
        for i in range(n):
            c = tuple(map(int, result.palettes_rgb[j, i]))
            draw.rectangle((i*size, j*size, (i+1)*size-1, (j+1)*size-1), fill=c)
    return out


def export(result: Result, destination: str | Path, prefix: str = 'art') -> list[Path]:
    """Export Genesis 4bpp tiles, plane map attrs, CRAM, PNG, CSV, JSON, GPL."""
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    prefix = ''.join(c for c in prefix if c.isalnum() or c in ('-', '_')) or 'art'
    settings = result.settings
    height, width = result.indices.shape
    ty, tx = result.tile_palettes.shape
    ntiles = ty * tx
    from tile_optimizer import optimize
    available = min(settings.vram_budget_tiles, 2048-settings.base_tile)
    optimized = optimize(result.indices, result.tile_palettes, budget=available, allow_lossy=getattr(settings, 'allow_lossy_tiles', False), palettes_rgb=result.palettes_rgb)
    unique_count = optimized['unique_count']
    limits = vram_usage(result.source_size[0], result.source_size[1],
                        settings.base_tile, settings.vram_budget_tiles)
    fits = unique_count <= available and settings.base_tile + unique_count <= 2048
    result_files: list[Path] = []

    def save_bytes(suffix: str, data: bytes):
        path = output / f'{prefix}.{suffix}'
        path.write_bytes(data)
        result_files.append(path)

    preview_path = output / f'{prefix}.png'
    result.preview.save(preview_path)
    result_files.append(preview_path)
    palette_path = output / f'{prefix}_palettes.png'
    palette_image(result).save(palette_path)
    result_files.append(palette_path)

    # 4bpp packed: each row of 8 pixels -> 4 bytes (high nibble = left pixel),
    # 32 bytes per 8x8 tile, raster order. This is the Mega Drive VRAM format.
    tiled = result.indices.reshape(ty, 8, tx, 8).transpose(0, 2, 1, 3).reshape(ntiles, 8, 8)
    tiled = optimized['tiles']
    packed = ((tiled[:, :, ::2] << 4) | tiled[:, :, 1::2]).astype(np.uint8)
    save_bytes('tiles.4bpp.bin', packed.tobytes())
    palette_ids = result.tile_palettes.ravel()
    vals = optimized['mapping'].astype(np.uint16) + settings.base_tile
    attrs = ((palette_ids.astype(np.uint16) << 13) | optimized['flips'] | vals).astype('>u2') if fits else None
    if fits:
        save_bytes('map.attr.be.bin', attrs.tobytes())
    # Pack four 16-color palettes (32 bytes each), regardless of visible count.
    cram = np.zeros((4, 16), dtype='>u2')
    for p in range(settings.palettes):
        for c in range(settings.colors):
            cram[p, c] = _genesis_cram_word(result.palettes_rgb[p, c])
    save_bytes('palettes.cram.be.bin', cram.tobytes())

    csv_path = output / f'{prefix}_tile_palettes.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as fp:
        w = csv.writer(fp)
        w.writerow(['tile_x', 'tile_y', 'tile_index', 'palette_0_to_3', 'attribute_hex'])
        for iy in range(ty):
            for ix in range(tx):
                i = iy * tx + ix
                w.writerow([ix, iy, int(vals[i]) if fits else 'INCOMPATIVEL', int(palette_ids[i]),
                            f'0x{int(attrs[i]):04X}' if fits else 'N/A'])
    result_files.append(csv_path)

    gpl = ['GIMP Palette', 'Name: Tile Palette Studio — Mega Drive', 'Columns: 16', '# RGB 8-bit approximations of 9-bit Genesis CRAM']
    for p in range(settings.palettes):
        for j in range(settings.colors):
            r, g, b = map(int, result.palettes_rgb[p, j])
            gpl.append(f'{r:3} {g:3} {b:3}   P{p}:{j:02}')
    gpl_path = output / f'{prefix}_palettes.gpl'
    gpl_path.write_text('\n'.join(gpl)+'\n', encoding='utf-8')
    result_files.append(gpl_path)

    manifest = {
        'format': 'Mega Drive / Genesis, H32/H40 independent tile data',
        'source_width': result.source_size[0], 'source_height': result.source_size[1],
        'padded_width': result.padded_size[0], 'padded_height': result.padded_size[1],
        'tile_width': 8, 'tile_height': 8, 'tiles_x': tx, 'tiles_y': ty,
        'tile_count': ntiles, 'unique_tile_count': unique_count, 'lossless_unique': optimized['lossless_unique'], 'lossy_merges': optimized['lossy_merges'], 'tile_index_base': settings.base_tile,
        'vram': limits, 'tilemap_exported': fits,
        'palette_count': settings.palettes, 'colors_per_palette': settings.colors,
        'palette_zero_shared_rgb': settings.background,
        'alpha_reserved': settings.transparent, 'alpha_threshold': settings.alpha_threshold,
        'dither': settings.dither, 'dither_strength': settings.dither_strength,
        'iterations': settings.iterations, 'weighted_error_history': result.history,
        'rgb_mse': result.mean_squared_error,
        'tiles': '8x8, 4bpp packed, high nibble first, 32 bytes/tile, row-major',
        'map': '16-bit big-endian: palette bits 14-13, H/V flip bits 11-12, tile index bits 10-0, priority=0',
        'cram': '4 x 16 16-bit big-endian entries, 0x0BGR (R bits 1-3, G bits 5-7, B bits 9-11)',
        'note': 'Not a complete ROM. VRAM available depends on the game. Oversize exports omit map.attr.be.bin to prevent 11-bit tile index overflow. Index zero is common across palettes.'
    }
    manifest_path = output / f'{prefix}.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    result_files.append(manifest_path)
    # Ready-to-add SGDK rescomp declarations, only for valid tile indices.
    if fits:
        res_lines = [f'BIN {prefix}_tiles "{prefix}.tiles.4bpp.bin" NONE',
                     f'BIN {prefix}_map "{prefix}.map.attr.be.bin" NONE',
                     f'BIN {prefix}_cram "{prefix}.palettes.cram.be.bin" NONE']
        res_path = output / f'{prefix}.res'
        res_path.write_text('\n'.join(res_lines)+'\n', encoding='utf-8')
        result_files.append(res_path)
    guide = output / f'{prefix}_COMO_USAR.txt'
    guide.write_text(f"""TILE PALETTE STUDIO — COMO USAR O EXPORT (MEGA DRIVE)

Imagem: {result.source_size[0]}x{result.source_size[1]} px; grade {tx}x{ty}; {ntiles} tiles.
VRAM bruta de tiles: {ntiles*32:,} bytes de 65.536 (total da VDP).
Orçamento configurado: {settings.vram_budget_tiles} tiles ({settings.vram_budget_tiles*32} bytes).
Base de tiles: {settings.base_tile}; teto do campo VDP: 2048 índices.
Compatível com índice VDP: {'SIM' if fits else 'NÃO: excede 2048 índices; divida em bancos ou deduplique.'}
{'AVISO: acima do orçamento de VRAM informado.' if limits['over_budget'] else ''}

QUAL ARQUIVO USAR?
1) {prefix}.png — imagem pronta para ver/editar/compartilhar.
2) {prefix}.tiles.4bpp.bin — dados gráficos (32 bytes por tile, sem compressão).
3) {prefix}.palettes.cram.be.bin — 64 cores CRAM, 128 bytes big-endian.
4) {prefix}.map.attr.be.bin — mapa de atributos 16 bits big-endian; só existe
   quando o índice de tile cabe nos 11 bits (base + contagem <= 2048).
5) {prefix}.res — declarações BIN para o compilador rescomp do SGDK,
   só gerado quando o tilemap é compatível.
6) {prefix}.json — dimensões, índice base, limites e opções.
7) {prefix}_tile_palettes.csv — inspecionar qual paleta cada tile utiliza.

PARA USAR NO SGDK:
- Copie os .bin e o .res para a pasta res/ do projeto.
- Adicione as três linhas do .res gerado ao res/resources.res do projeto
  (ou use o .res como recurso principal na configuração do seu makefile).
- No C, inclua o cabeçalho gerado pelo rescomp (resources.h ou equivalente).
- Carregue os tiles na VRAM a partir do índice {settings.base_tile}.
- Carregue as quatro paletas na CRAM (respeitando as paletas já usadas no jogo).
- Escreva o tilemap com {tx} colunas por {ty} linhas no plano escolhido,
  respeitando as dimensões do plano e os índices reservados pelo jogo.
- Os .bin são dados brutos, NÃO uma ROM nem uma imagem SGDK IMAGE.
- CUIDADO: se o jogo usa HUD, sprites, planos ou framebuffer, eles também
  ocupam VRAM. O teto de 2048 é teórico, NÃO espaço livre garantido.
- Para uma ROM existente, o formato do conversor/engine pode ser diferente:
  integrar exige adaptar o loader ao formato do jogo.

OBS: PNG com tamanho arbitrário é válido para edição, mas uma imagem maior
que o plano de vídeo precisa ser dividida/rolada; a VDP não exibe automaticamente
uma imagem gigante de uma vez. Tiles idênticos e espelhados são deduplicados; substituições aproximadas são opcionais.
""", encoding='utf-8')
    result_files.append(guide)
    return result_files
