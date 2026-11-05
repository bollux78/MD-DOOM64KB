#!/usr/bin/env python3
"""Convert pinned Freedoom E1M1 and place it in a mirrored SSF page."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

from convert_r24_episode import convert_map, definitions, metadata, read_wad, recs, write_wad
from r133_pack import sig
from r134_freedoom_pack import BANK, FREEDOOM_COMMIT, MAPS, ROM_SIZE, git_hash

SLOT = 7 * BANK
EXTRA = 8 * BANK
MAP_OFFSET = 0x50000
SIGNATURE = 0x7FFF0

# Use the existing episode's artwork and switch pairs. Exact names take priority.
WALLS = {
    'A-CONCTE': 'GRAY5', 'A-MUD': 'BROWN1', 'AQCOMP01': 'COMPUTE2',
    'AQDOOR01': 'DOOR1', 'AQDOOR02': 'DOOR3', 'AQSECT11': 'COMPSTA1',
    'AQTILE01': 'COMPTILE', 'AQTILE02': 'COMPTILE', 'AQTRIM05': 'DOORSTOP',
    'ASHWALL': 'STONE2', 'ASHWALL2': 'STONE3', 'BASE': 'STARTAN2',
    'BASE2': 'STARTAN3', 'BIGDOOR3': 'BIGDOOR2', 'CEILVINE': 'BROWNGRN',
    'COMPLIT3': 'COMPTALL', 'COMPUTE4': 'COMPUTE3', 'COMPVENT': 'COMPSTA1',
    'COMPWERF': 'COMPSTA2', 'CRATE1': 'BROWN1', 'CRATE2': 'BROWN96',
    'CRATE3': 'GRAY5', 'CRATELIT': 'LITE3', 'CRATINY': 'BROWN1',
    'CRATWIDE': 'BROWN144', 'CRAWHBP': 'BROWNPIP', 'METAL': 'METAL1',
    'METAL2': 'METAL1', 'METAL5': 'METAL1', 'SFALL1': 'SLADRIP1',
    'SHAWN02': 'SHAWN2', 'SHAWN1': 'SHAWN2', 'SP_ROCK1': 'STONE2',
    'STARGR2': 'STARGR1', 'STEPTOP': 'STEP4', 'STONE4': 'STONE3',
    'WFALL1': 'SLADRIP1', 'ZIMMER3': 'STONE2',
}
WALL_FAMILIES = {
    'AQCONC': 'GRAY5', 'AQLITE': 'LITE3', 'AQMETL': 'METAL1',
    'AQPANL': 'STARTAN2', 'AQPIPE': 'PIPE2', 'AQRUST': 'BROWN1',
    'AQSUPP': 'SUPPORT2', 'MCSTAT': 'COMPSTA1',
}
FLATS = {
    'FWATER1': 'NUKAGE1', 'SLIME14': 'NUKAGE1', 'GRASS1': 'FLOOR7_1',
    'RROCK17': 'MFLR8_1', 'RROCK18': 'FLOOR7_2',
    'CRATOP1': 'FLAT5_4', 'CRATOP2': 'FLAT5_4', 'FLAT1': 'FLOOR0_1',
    'MFLR8_3': 'MFLR8_1', 'MFLR8_4': 'MFLR8_1', 'CEIL4_1': 'CEIL4_2',
    'FLOOR0_5': 'FLOOR0_6', 'FLAT20': 'FLOOR4_8', 'FLAT4': 'FLOOR4_8',
}
# Substitutes for gameplay items whose sprites/logic are absent from this port.
THINGS = {2004: 2002, 2047: 2048, 2023: 2012}
DECORATIONS = {17, 18, 19, 20, 21, 26, 43, 47, 54, 60}
LUMPS = ('THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS',
         'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP')


def read_map(raw):
    name, _, _, size, sha = MAPS[0]
    assert len(raw) == size and git_hash(raw) == sha and raw[:4] == b'PWAD'
    count, directory = struct.unpack_from('<II', raw, 4)
    result = {}
    for offset, length, key in struct.iter_unpack('<II8s', raw[directory:directory + count * 16]):
        assert offset + length <= len(raw)
        result[key.rstrip(b'\0').decode('ascii')] = raw[offset:offset + length]
    assert tuple(result) == (name, *LUMPS)
    return result


def convert(raw, base, iwad):
    from convert_r24_episode import SOURCE_SHA, TARGET_ORDER, texnames

    assert hashlib.sha256(iwad).hexdigest() == SOURCE_SHA
    m = read_map(raw)
    textures = set(texnames(dict(base)['TEXTURE1']))
    stock = dict(read_wad(iwad))
    palette = [stock['PLAYPAL'][i:i + 3] for i in range(0, 768, 3)]
    substitutions = {}
    flat_substitutions = {}

    def wall(value):
        name = value.rstrip(b'\0').decode('ascii')
        if name == '-' or name in textures:
            return value
        family = next((replacement for prefix, replacement in WALL_FAMILIES.items()
                       if name.startswith(prefix)), None)
        target = WALLS.get(name, family)
        assert target in textures, name
        substitutions[name] = target
        return target.encode('ascii')

    def flat(value, light):
        name = value.rstrip(b'\0').decode('ascii')
        if name == 'F_SKY1':
            return -2
        target = name if name in stock else FLATS.get(name)
        if target is None and name.startswith('AQF'):
            # Alternating metal/concrete anchors for the Aquatex floor family.
            target = ('FLOOR4_8', 'FLOOR0_1', 'CEIL5_1')[int(name[3:]) % 3]
        assert target in stock, (name, target)
        if target != name:
            flat_substitutions[name] = target
        if target.startswith('NUKAGE'):
            return -3
        pixels = stock[target]
        assert len(pixels) == 4096
        counts = Counter(pixels)
        rgb = [sum(palette[p][c] * n for p, n in counts.items()) * light / (4096 * 255)
               for c in range(3)]
        return min(range(256), key=lambda i: sum((palette[i][c] - rgb[c]) ** 2 for c in range(3)))

    m['SIDEDEFS'] = b''.join(struct.pack('<hh8s8s8sH', x, y, wall(t), wall(b), wall(mid), sector)
                             for x, y, t, b, mid, sector in recs(m['SIDEDEFS'], '<hh8s8s8sH'))
    lines = recs(m['LINEDEFS'], '<7H')
    assert {line[3] for line in lines} <= {0, 1, 2, 11, 23, 26, 62, 88, 117}
    # The port handles the normal-speed variant of this repeatable manual door.
    m['LINEDEFS'] = b''.join(struct.pack('<7H', v1, v2, flags, 1 if special == 117 else special, tag, s0, s1)
                             for v1, v2, flags, special, tag, s0, s1 in lines)
    defs = definitions()
    supported = {d['doomednum'] for d in defs}
    things = recs(m['THINGS'], '<5h')
    assert sum(t[3] == 1 for t in things) == 1
    assert {t[3] for t in things} <= supported | DECORATIONS | THINGS.keys() | {1, 2, 3, 4, 11}
    m['THINGS'] = b''.join(struct.pack('<5h', x, y, angle, THINGS.get(kind, kind), options)
                          for x, y, angle, kind, options in things if kind not in DECORATIONS)
    colors = [(flat(floor, light), flat(ceil, light))
              for _, _, floor, ceil, light, _, _ in recs(m['SECTORS'], '<hh8s8s3h')]
    converted, report = convert_map(m, base, colors, 'E1M1')
    meta, statics = metadata(converted, 0, defs)  # S0 prefix keeps every name <= 8 bytes.
    assert report['blockmap'][2] * report['blockmap'][3] * 4 + report['linedefs'] * 8 + report['sidedefs'] * 10 < 30720
    assert len(converted['REJECT']) * 8 >= report['sectors'] ** 2
    converted['LINEDEFS'] = b''.join(converted['LINEDEFS'][i:i + 31] + b'\0'
                                     for i in range(0, len(converted['LINEDEFS']), 31))
    wad = write_wad([('E1M10', b'')] + [(name, converted[name]) for name in TARGET_ORDER] + meta)
    assert dict(read_wad(wad, True)) == {'E1M10': b'', **converted, **dict(meta)}
    report.update(rom_static_candidates=statics, source_git_blob_sha1=git_hash(raw),
                  wall_substitutions=substitutions, flat_substitutions=flat_substitutions,
                  thing_substitutions=THINGS, omitted_decorations=dict(Counter(t[3] for t in things if t[3] in DECORATIONS)),
                  line_special_substitutions={117: 1}, start=[t[:3] for t in things if t[3] == 1][0])
    report.pop('lumps')
    return wad, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'output', 'report', 'iwad', 'base'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--freedoom', type=Path)
    p.add_argument('--linked-size', type=int, required=True)
    args = p.parse_args()
    initial = args.input.read_bytes()
    assert 0 < args.linked_size <= min(len(initial), SLOT + MAP_OFFSET), (
        'linked ROM overlaps banked map', hex(args.linked_size))
    assert set(initial[args.linked_size:]) <= {0, 255}, 'unexpected content after linked ROM'
    if args.freedoom:
        raw = args.freedoom.read_bytes()
    else:
        url = f'https://raw.githubusercontent.com/freedoom/freedoom/{FREEDOOM_COMMIT}/levels/e1m1.wad'
        with urllib.request.urlopen(url, timeout=40) as response:
            raw = response.read()
    wad, report = convert(raw, read_wad(args.base.read_bytes(), True), args.iwad.read_bytes())
    assert MAP_OFFSET + len(wad) <= SIGNATURE
    with tempfile.TemporaryDirectory(prefix='r136-base-') as work:
        base_rom = Path(work) / 'base.bin'
        subprocess.run([sys.executable, str(Path(__file__).with_name('r133_pack.py')),
                        '--input', str(args.input), '--output', str(base_rom),
                        '--report', str(Path(work) / 'base.json')], check=True, stdout=subprocess.DEVNULL)
        rom = bytearray(base_rom.read_bytes())
    # Keep every base byte visible, including live data in the lower half of slot 7.
    rom[EXTRA:EXTRA + MAP_OFFSET] = rom[SLOT:SLOT + MAP_OFFSET]
    start = EXTRA + MAP_OFFSET
    rom[start:start + len(wad)] = wad
    for page in (8, 9):
        struct.pack_into('>I', rom, page * BANK + SIGNATURE, sig(page))
    struct.pack_into('>H', rom, 0x18E, sum(w[0] for w in struct.iter_unpack('>H', rom[0x200:])) & 0xFFFF)
    assert len(rom) == ROM_SIZE and rom[0x100:0x110] == b'SEGA SSF        '
    assert struct.unpack_from('>I', rom, 0x1A4)[0] == ROM_SIZE - 1
    assert rom[EXTRA:EXTRA + MAP_OFFSET] == rom[SLOT:SLOT + MAP_OFFSET]
    assert rom[start:start + len(wad)] == wad
    args.output.write_bytes(rom)
    result = dict(file=str(args.output), bytes=len(rom), sha256=hashlib.sha256(rom).hexdigest(),
                  base_bytes=len(initial), map_rom_offset=hex(start), map_bytes=len(wad),
                  map_sha256=hashlib.sha256(wad).hexdigest(), map_source=FREEDOOM_COMMIT,
                  license='BSD-3-Clause', conversion=report)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
