#!/usr/bin/env python3
"""Quantize WAD colors directly into solids and intermediate Pair-V tones."""
from pathlib import Path
import os
import re
import runpy

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
MATH = runpy.run_path(str(ROOT / 'scripts/lab/gen_r52_claudio.py'))
AVG, LAB = MATH['avg_rgb'], MATH['to_lab']


def replace_array(text, name, transform):
    pattern = rf'(\b{name}\s*)((?:\[\d+\])+)\s*=\s*\{{(.*?)\}};'
    match = re.search(pattern, text, re.S)
    assert match, name
    shape = tuple(map(int, re.findall(r'\d+', match[2])))
    values = np.array([int(v, 0) for v in re.findall(r'0x[\da-fA-F]+|\d+', match[3])])
    updated = transform(values.reshape(shape))
    assert updated.shape == shape

    def emit(array):
        if array.ndim == 1:
            return '{' + ','.join(map(str, array)) + '}'
        return '{\n' + ',\n'.join(map(emit, array)) + '\n}'

    return text[:match.start()] + match[1] + match[2] + '=' + emit(updated) + ';' + text[match.end():]


def quantize(words, colors, weights, armor_colors=None):
    green = []
    if armor_colors is not None:
        # Anchor both banks to the same dark and light greens from ARM1.
        # The intervening striped code provides an additional effective shade.
        words = words.copy()
        _, baseline_pairs, _, _ = quantize(words, colors, weights)
        green = sorted(set(range(1, 16)) - set(baseline_pairs.ravel()))[:2]
        assert len(green) == 2
        words[:, green] = armor_colors
    rgb = np.stack([(words >> shift) & 7 for shift in (1, 5, 9)], axis=-1) * (255 / 7)
    normal = rgb[0]
    gray = [int(i) for i in np.argsort(normal[:, 0])
            if i and normal[i, 0] == normal[i, 1] == normal[i, 2]]
    assert len(gray) == 4 and len(set(words[0, gray])) == 4
    ramp = [(i, i) for i in gray] + list(zip(gray, gray[1:]))
    green_ramp = [(i, i) for i in green] + ([tuple(green)] if green else [])
    solids = [(i, i) for i in range(1, 16) if i not in gray + green]
    candidates = np.array(ramp + green_ramp + solids)
    means = LAB(AVG(normal[candidates[:, 0]], normal[candidates[:, 1]]))
    error = ((LAB(colors)[:, None, :] - means[None, :, :]) ** 2).sum(axis=-1)
    # Discourage neutral pixels from taking on a tint when gray is available.
    neutral = np.ptp(colors, axis=1) <= 7
    error[neutral, len(ramp):] += 36
    selected = list(range(len(ramp) + len(green_ramp)))
    best = error[:, selected].min(axis=1)
    while len(selected) < 15:
        remaining = [i for i in range(len(candidates)) if i not in selected]
        gains = (weights[:, None] * np.maximum(best[:, None] - error[:, remaining], 0)).sum(axis=0)
        chosen = remaining[int(np.argmax(gains))]
        selected.append(chosen)
        best = np.minimum(best, error[:, chosen])
    pairs = np.vstack(([0, 0], candidates[selected]))
    codes = error[:, selected].argmin(axis=1) + 1
    assert len(set(codes[neutral]) & set(range(1, 8))) >= 6
    print('Pair-V gray ramp codes from WAD:', sorted(set(codes[neutral]) & set(range(1, 8))))
    if green:
        assert {8, 9, 10} <= set(codes[113:126]), codes[113:126]
        print('ARM1 green codes:', codes[113:126].tolist())
    solid_codes = np.flatnonzero(pairs[1:, 0] == pairs[1:, 1])
    flat_codes = solid_codes[error[:, np.asarray(selected)[solid_codes]].argmin(axis=1)] + 1
    return words, pairs, codes, flat_codes


def resample(text):
    wad = (ROOT / 'scripts/doom64.wad').read_bytes()
    lumps = MATH['wad_lumps'](wad)
    data = dict(lumps)
    palette = runpy.run_path(str(ROOT / 'scripts/genpal.py'))
    colors = np.asarray(palette['decode_subpal'](data['PLAYPAL'], 0), float)
    armor_colors = None
    if os.environ.get('R128_ARMOR_TONES') == '1':
        armor_colors = np.array([
            [palette['gen_color'](palette['decode_subpal'](data['PLAYPAL'], effect)[index])
             for index in (123, 117)]
            for effect in range(14)
        ])
    cm = np.frombuffer(data['COLORMAP'], dtype=np.uint8).reshape(-1, 256)
    weights = MATH['proxy_histogram'](lumps, 0.85, range(32), 0.20, cm.ravel())
    for prefix in ('r76_a', 'r76_l'):
        for bank, side in enumerate(('even', 'odd')):
            words = MATH['parse_c_array'](text, f'{prefix}_pal{bank}')
            words, pairs, codes, flat_codes = quantize(
                np.asarray(words).reshape(14, 16), colors, weights, armor_colors)
            if armor_colors is not None:
                text = replace_array(text, f'{prefix}_pal{bank}', lambda _: words)
            text = replace_array(text, f'{prefix}_pairs_{side}', lambda _: pairs)
            text = replace_array(text, f'{prefix}_wall_{side}', lambda _: codes)
            text = replace_array(text, f'{prefix}_comp_{side}', lambda old: codes[cm].reshape(old.shape))
            # Broad uniform floors and ceilings make continuous stripes conspicuous.
            flats = [prefix] if prefix != 'r76_l' else ['r76_l', 'r76_b', 'r76_n']
            for flat in flats:
                text = replace_array(text, f'{flat}_flat_{side}', lambda _: flat_codes)
    return text
