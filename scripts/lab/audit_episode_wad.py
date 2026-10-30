#!/usr/bin/env python3
"""Episode audit: will each episode of a user's own Doom IWAD fit one Mega Drive ROM?

Read-only. Runs on the owner's WAD locally; prints a report and never copies WAD data anywhere.
  python3 scripts/lab/audit_episode_wad.py --wad /path/to/doom.wad [--src src] [--json out.json]

Per map (hard limits of the current converter + SRAM layout):
  lines < 2048, sectors < 255, specials < 128, flags < 512, |dx|,|dy| < 32768,
  converted lumps <= 65535 B (SEGS 22 B, NODES 28 B, LINEDEFS 31 B, SIDEDEFS 8 B, BLOCKMAP 2 B/word),
  blockmap cells <= 4096 (SRAM heads), SRAM map state cells*4 + lines*6 + sides*8 <= R81_SAVE_BASE.
Per episode:
  thing types the engine does not implement yet (src/info.c holds the shareware E1 set),
  distinct wall textures (side texture index is a signed byte: <= 127 per ROM),
  raw sprite / patch bytes against the E1 set, and ROM budget with Shadow full / R79 only / off.
"""
import argparse, json, re, struct, sys, hashlib
from pathlib import Path

KNOWN = {
    '1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771': 'Doom shareware 1.9 (doom1.wad)',
}
# doomednum -> (label, sprite prefixes it brings, including projectiles/effects of monsters and weapons)
THINGS = {
    3004: ('Zombieman', 'POSS'), 9: ('Shotgun guy', 'SPOS'), 3001: ('Imp', 'TROO BAL1'), 3002: ('Demon', 'SARG'),
    58: ('Spectre', 'SARG'), 3006: ('Lost soul', 'SKUL'), 3005: ('Cacodemon', 'HEAD BAL2'), 3003: ('Baron', 'BOSS BAL7'),
    16: ('Cyberdemon', 'CYBR MISL'), 7: ('Spider Mastermind', 'SPID'),
    2001: ('Shotgun', 'SHOT SHTG SHTF'), 2002: ('Chaingun', 'MGUN CHGG CHGF'), 2003: ('Rocket launcher', 'LAUN MISG MISF MISL'),
    2004: ('Plasma rifle', 'PLAS PLSG PLSF PLSS PLSE'), 2005: ('Chainsaw', 'CSAW SAWG'), 2006: ('BFG9000', 'BFUG BFGG BFGF BFS1 BFE1 BFE2'),
    2007: ('Clip', 'CLIP'), 2048: ('Ammo box', 'AMMO'), 2008: ('Shells', 'SHEL'), 2049: ('Shell box', 'SBOX'), 2010: ('Rocket', 'ROCK'),
    2046: ('Rocket box', 'BROK'), 2047: ('Cell', 'CELL'), 17: ('Cell pack', 'CELP'), 8: ('Backpack', 'BPAK'),
    2011: ('Stimpack', 'STIM'), 2012: ('Medikit', 'MEDI'), 2014: ('Health bonus', 'BON1'), 2015: ('Armor bonus', 'BON2'),
    2018: ('Green armor', 'ARM1'), 2019: ('Blue armor', 'ARM2'), 2013: ('Soulsphere', 'SOUL'), 2022: ('Invulnerability', 'PINV'),
    2023: ('Berserk', 'PSTR'), 2024: ('Invisibility', 'PINS'), 2025: ('Radiation suit', 'SUIT'), 2026: ('Computer map', 'PMAP'),
    2045: ('Light amp', 'PVIS'), 5: ('Blue keycard', 'BKEY'), 40: ('Blue skull', 'BSKU'), 13: ('Red keycard', 'RKEY'),
    38: ('Red skull', 'RSKU'), 6: ('Yellow keycard', 'YKEY'), 39: ('Yellow skull', 'YSKU'), 2035: ('Barrel', 'BAR1 BEXP'),
    48: ('Tech column', 'ELEC'), 30: ('Tall green pillar', 'COL1'), 31: ('Short green pillar', 'COL2'), 32: ('Tall red pillar', 'COL3'),
    33: ('Short red pillar', 'COL4'), 36: ('Pillar w/ heart', 'COL5'), 37: ('Red pillar w/ skull', 'COL6'), 47: ('Stalagmite', 'SMIT'),
    43: ('Burnt tree', 'TRE1'), 54: ('Large tree', 'TRE2'), 2028: ('Floor lamp', 'COLU'), 34: ('Candle', 'CAND'),
    35: ('Candelabra', 'CBRA'), 44: ('Blue torch', 'TBLU'), 45: ('Green torch', 'TGRN'), 46: ('Red torch', 'TRED'),
    55: ('Short blue torch', 'SMBT'), 56: ('Short green torch', 'SMGT'), 57: ('Short red torch', 'SMRT'), 41: ('Evil eye', 'CEYE'),
    42: ('Floating skull', 'FSKU'), 49: ('Hanging body', 'GOR1'), 63: ('Hanging body (nb)', 'GOR1'), 50: ('Hanging arms out', 'GOR2'),
    59: ('Hanging arms out (nb)', 'GOR2'), 52: ('Hanging pair of legs', 'GOR4'), 60: ('Hanging legs (nb)', 'GOR4'),
    51: ('Hanging one-legged', 'GOR3'), 61: ('Hanging one-legged (nb)', 'GOR3'), 53: ('Hanging leg', 'GOR5'), 62: ('Hanging leg (nb)', 'GOR5'),
    15: ('Dead player', 'PLAY'), 18: ('Dead zombieman', 'POSS'), 19: ('Dead shotgun guy', 'SPOS'), 20: ('Dead imp', 'TROO'),
    21: ('Dead demon', 'SARG'), 22: ('Dead cacodemon', 'HEAD'), 23: ('Dead lost soul', 'SKUL'), 24: ('Pool of blood', 'POL5'),
    10: ('Bloody mess', 'PLAY'), 12: ('Bloody mess 2', 'PLAY'), 25: ('Impaled body', 'POL1'), 26: ('Twitching impaled', 'POL6'),
    27: ('Skull on pole', 'POL4'), 28: ('Skulls on pole', 'POL2'), 29: ('Pile of skulls', 'POL3'),
    1: ('Player 1 start', ''), 2: ('Player 2 start', ''), 3: ('Player 3 start', ''), 4: ('Player 4 start', ''),
    11: ('Deathmatch start', ''), 14: ('Teleport destination', ''),
}
ALWAYS = 'PLAY PUFF BLUD TFOG IFOG PUNG PISG PISF'.split()
LIMIT_ROM = 4 * 1024 * 1024
SHADOW = {'full': 0, 'r79': 0x80000, 'off': 0x80000 + 0x1C000}   # bytes freed vs the current Shadow build


def read_wad(path):
    b = Path(path).read_bytes()
    assert b[:4] in (b'IWAD', b'PWAD'), 'not a WAD'
    n, ofs = struct.unpack_from('<ii', b, 4)
    lumps = []
    for i in range(n):
        p, s, name = struct.unpack_from('<ii8s', b, ofs + 16 * i)
        lumps.append((name.split(b'\0')[0].decode('ascii', 'replace').upper(), b[p:p + s]))
    return b, lumps


def recs(b, fmt):
    s = struct.calcsize(fmt)
    return list(struct.iter_unpack(fmt, b[:len(b) - len(b) % s]))


def maps_of(lumps):
    out = {}
    for i, (name, _) in enumerate(lumps):
        if re.fullmatch(r'E\dM\d', name):
            out[name] = dict(lumps[i + 1:i + 11])
    return out


def textures(lumps):
    d = dict(lumps); pn = d.get('PNAMES')
    pnames = [pn[4 + 8 * i:12 + 8 * i].split(b'\0')[0].decode().upper() for i in range(struct.unpack_from('<i', pn)[0])] if pn else []
    tex = {}
    for t in ('TEXTURE1', 'TEXTURE2'):
        b = d.get(t)
        if not b: continue
        n = struct.unpack_from('<i', b)[0]
        for o in struct.unpack_from('<%di' % n, b, 4):
            name = b[o:o + 8].split(b'\0')[0].decode().upper(); pc = struct.unpack_from('<h', b, o + 20)[0]
            tex[name] = (t, [pnames[struct.unpack_from('<h', b, o + 22 + 10 * k + 4)[0]] for k in range(pc)])
    return tex


def sprites_bytes(lumps, prefixes):
    inside = False; total = 0; per = {}
    for name, data in lumps:
        if name in ('S_START', 'SS_START'): inside = True; continue
        if name in ('S_END', 'SS_END'): inside = False; continue
        if inside and name[:4] in prefixes:
            total += len(data); per[name[:4]] = per.get(name[:4], 0) + len(data)
    return total, per


def map_audit(name, m, save_base):
    lines = recs(m['LINEDEFS'], '<7H'); sides = recs(m['SIDEDEFS'], '<hh8s8s8sH'); sectors = recs(m['SECTORS'], '<hh8s8s3h')
    verts = recs(m['VERTEXES'], '<hh'); segs = len(m['SEGS']) // 12; nodes = len(m['NODES']) // 28
    bw, bh = struct.unpack_from('<4h', m['BLOCKMAP'])[2:]
    mutable = {s for ln in lines if ln[3] for s in ln[5:7] if s != 65535}
    dedup = len({(i if i in mutable else None, s) for i, s in enumerate(sides)})
    cells = bw * bh; sram = cells * 4 + len(lines) * 6 + dedup * 8
    maxd = max([abs(verts[l[1]][0] - verts[l[0]][0]) for l in lines] + [abs(verts[l[1]][1] - verts[l[0]][1]) for l in lines])
    conv = {'LINEDEFS': len(lines) * 31, 'SIDEDEFS': dedup * 8, 'SEGS': segs * 22, 'NODES': nodes * 28,
            'BLOCKMAP': len(m['BLOCKMAP']), 'REJECT': len(m['REJECT']), 'SECTORS': len(sectors) * 12}
    fails = []
    if len(lines) >= 2048: fails.append('lines %d >= 2048' % len(lines))
    if len(sectors) >= 255: fails.append('sectors %d >= 255' % len(sectors))
    if any(l[3] >= 128 for l in lines): fails.append('special >= 128')
    if any(l[2] >= 512 for l in lines): fails.append('line flags >= 512')
    if maxd >= 32768: fails.append('line delta >= 32768')
    fails += ['%s %d B > 65535' % (k, v) for k, v in conv.items() if v > 65535]
    if cells > 4096: fails.append('blockmap %dx%d = %d cells > 4096' % (bw, bh, cells))
    if sram > save_base: fails.append('SRAM map state %d B > %d' % (sram, save_base))
    used_tex = {n.split(b'\0')[0].decode().upper() for s in sides for n in s[2:5]} - {'-', ''}
    things = recs(m['THINGS'], '<5h')
    return dict(map=name, lines=len(lines), sides=len(sides), sides_dedup=dedup, sectors=len(sectors), segs=segs, nodes=nodes,
                things=len(things), blockmap=[bw, bh], cells=cells, sram_bytes=sram, sram_limit=save_base,
                contact_nodes_left=max(0, (save_base - sram) // 12), converted=conv, fails=fails,
                textures=sorted(used_tex), thing_types=sorted({t[3] for t in things}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wad', required=True); ap.add_argument('--src', default='src'); ap.add_argument('--json')
    ap.add_argument('--rom-used', type=int, default=0x36E8E5, help='bytes used by the current E1 ROM (R105 twoface)')
    ap.add_argument('--e1-iwad', type=int, default=0x16B9C4, help='bytes of the embedded E1 WAD in that ROM')
    a = ap.parse_args()
    raw, lumps = read_wad(a.wad); sha = hashlib.sha256(raw).hexdigest()
    src = Path(a.src)
    save_base = int(re.search(r'#define R81_SAVE_BASE (\d+)', (src / 'r81_save.h').read_text()).group(1))
    have = set(re.findall(r'"([A-Z0-9]{4})"', (src / 'info.c').read_text()))
    tex = textures(lumps); maps = maps_of(lumps)
    rep = dict(wad=Path(a.wad).name, sha256=sha, identified=KNOWN.get(sha, 'unknown (audit still runs)'),
               engine_sprites=sorted(have), episodes={})
    e1_sprites = None
    for ep in sorted({k[1] for k in maps}):
        ms = [map_audit(k, maps[k], save_base) for k in sorted(maps) if k[1] == ep]
        types = sorted({t for m in ms for t in m['thing_types']})
        pref = set(ALWAYS)
        for t in types: pref |= set(THINGS.get(t, ('?', ''))[1].split())
        unknown = [t for t in types if t not in THINGS]
        missing = sorted(p for p in pref if p not in have)
        sbytes, sper = sprites_bytes(lumps, pref)
        used = sorted({t for m in ms for t in m['textures']})
        patches = sorted({p for t in used if t in tex for p in tex[t][1]})
        pbytes = sum(len(d) for n, d in lumps if n in set(patches))
        e = dict(maps=ms, thing_types=[[t, THINGS.get(t, ('UNKNOWN', ''))[0]] for t in types], unknown_types=unknown,
                 sprite_prefixes=sorted(pref), sprites_missing_in_engine=missing,
                 monsters_missing=[THINGS[t][0] for t in types if t in THINGS and any(p in missing for p in THINGS[t][1].split()[:1])],
                 sprite_raw_bytes=sbytes, wall_textures=len(used), textures_missing=[t for t in used if t not in tex],
                 texture_index_ok=len(used) <= 127, patch_raw_bytes=pbytes,
                 map_fails=sum(1 for m in ms if m['fails']))
        if ep == '1': e1_sprites = (sbytes, pbytes)
        rep['episodes']['E' + ep] = e
    base = e1_sprites or (None, None)
    for k, e in rep['episodes'].items():
        if base[0]:
            delta = (e['sprite_raw_bytes'] - base[0]) + (e['patch_raw_bytes'] - base[1])
            e['raw_delta_vs_E1'] = delta
            e['rom_estimate'] = {s: a.rom_used + delta - freed for s, freed in SHADOW.items()}
            e['rom_fits'] = {s: v <= LIMIT_ROM for s, v in e['rom_estimate'].items()}
    if a.json: Path(a.json).write_text(json.dumps(rep, indent=1) + '\n')
    print('# Episode audit: %s\n\nsha256 `%s` - %s\n' % (rep['wad'], sha, rep['identified']))
    for k, e in rep['episodes'].items():
        print('## %s\n' % k)
        print('| map | lines | sides (dedup) | sectors | segs | nodes | things | blockmap | SRAM state | status |')
        print('|---|---:|---:|---:|---:|---:|---:|---|---:|---|')
        for m in e['maps']:
            print('| %s | %d | %d | %d | %d | %d | %d | %dx%d=%d | %d/%d | %s |' % (m['map'], m['lines'], m['sides_dedup'], m['sectors'], m['segs'],
                  m['nodes'], m['things'], m['blockmap'][0], m['blockmap'][1], m['cells'], m['sram_bytes'], m['sram_limit'],
                  'OK' if not m['fails'] else '**' + '; '.join(m['fails']) + '**'))
        print('\n- wall textures used: %d (limit 127)%s' % (e['wall_textures'], '' if e['texture_index_ok'] else ' **OVER**'))
        print('- sprite prefixes needed: %d; not in engine yet: %s' % (len(e['sprite_prefixes']), ' '.join(e['sprites_missing_in_engine']) or 'none'))
        print('- monsters/items the engine lacks: %s' % (', '.join(sorted(set(e['monsters_missing']))) or 'none'))
        if e['unknown_types']: print('- unknown thing types: %s' % e['unknown_types'])
        print('- raw sprites %d B, raw wall patches %d B' % (e['sprite_raw_bytes'], e['patch_raw_bytes']))
        if 'rom_estimate' in e:
            print('- ROM estimate (raw delta vs E1 %+d B): ' % e['raw_delta_vs_E1'] + ', '.join(
                'Shadow %s %.2f MiB %s' % (s, v / 1048576, 'fits' if e['rom_fits'][s] else '**over**') for s, v in e['rom_estimate'].items()))
        print()
    print('Estimates use raw WAD bytes as a proxy for the converted ROM data; the E1 row is the calibration point (current ROM).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
