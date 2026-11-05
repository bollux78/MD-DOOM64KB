#!/usr/bin/env python3
"""Measure actual renderer pressure and unpainted samples in pinned R136."""
import argparse
import os
import re
import struct
import subprocess
from pathlib import Path

from convert_r24_episode import read_wad, recs
from test_r136_play import Play, USE


def floor_at(x, y, nodes, sectors, subsectors, segs):
    index = len(nodes) - 1
    while index < 0x8000:
        nx, ny, dx, dy, *_, front, back = nodes[index]
        if dx == 0:
            side = dy > 0 if x <= nx else dy < 0
        elif dy == 0:
            side = dx < 0 if y <= ny else dx > 0
        else:
            side = (y - ny) * dx >= (x - nx) * dy
        index = back if side else front
    return sectors[segs[subsectors[index & 0x7fff][1]][8]][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blastem', required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--require-painted', action='store_true')
    args = parser.parse_args()
    lumps = dict(read_wad(args.rom.read_bytes()[0x450000:0x47fff0], True))
    nodes = recs(lumps['NODES'], '>hhhh8hHH')
    sectors = recs(lumps['SECTORS'], '>hhhhBbh')
    subsectors = recs(lumps['SSECTORS'], '>HH')
    segs = recs(lumps['SEGS'], '>hhhhHHHHBB')
    things = recs(lumps['THINGS'], '>hhhbb')
    # Sample occupied areas spread throughout the map, even past closed doors.
    points = {}
    for x, y, kind, _, _ in things:
        if kind == 1:
            points['start'] = (x, y)
        points.setdefault((x // 320, y // 320), (x, y))
    nm = subprocess.check_output([os.environ['M68K_NM'], '-S', args.elf], text=True)
    size, = [int(line.split()[1], 16) for line in nm.splitlines()
             if len(line.split()) == 4 and line.split()[3].split('.')[0] == '_s_drawsegs']
    game = Play(args.blastem, args.rom, args.elf)
    try:
        game.boot()
        game.step(0, 24)
        game.menu(7)
        game.tap(USE)
        game.tap(USE)
        game.step(0, 24)
        game.check_map(10, 182)
        player = game.sym('_g_player')
        viewz = player + int.from_bytes(game.read(game.sym('r81_player_fields') + 4, 2), 'big')
        loop, = [s for s in game.syms if s.split('.')[0] == 'D_DoomLoop']
        assembly = subprocess.check_output(
            [os.environ['M68K_OBJDUMP'], '-d', f'--disassemble={loop}', args.elf], text=True
        ).splitlines()
        store, = [line for line in assembly
                  if re.search(r'\bmovel\s+%a[0-7]@\(12\),[0-9a-f]+ <viewx[.>]', line)]
        camera = int(store.split(':')[0], 16)
        ds_base = game.sym('_s_drawsegs')

        def write(address, data):
            for offset in range(0, len(data), 128):
                part = data[offset:offset + 128]
                assert game.g.req(f'M{address + offset:x},{len(part):x}:{part.hex()}') == 'OK'

        def draw(x, y, z, yaw, fill=None):
            game.next(camera)
            game.breakpoint(camera, False)
            mobj = game.number('_g_player', 4) & 0xffffff
            old_xy = game.read(mobj + 12, 8)
            old_angle = game.read(mobj + 32, 4)
            old_z = game.read(viewz, 4)
            write(mobj + 12, struct.pack('>ii', x << 16, y << 16))
            write(mobj + 32, struct.pack('>I', yaw))
            write(viewz, struct.pack('>i', z << 16))
            fb = game.number('r115_draw', 4) & 0xffffff
            if fill is not None:
                initial = bytearray(game.read(fb, 3344))
                initial[1::2] = bytes([fill]) * 1672
                write(fb, initial)
            game.breakpoint(game.frame)
            game.next(game.frame)
            game.breakpoint(game.frame, False)
            game.breakpoint(camera)
            assert game.number('viewx', 4) == (x << 16) & 0xffffffff
            assert game.number('viewy', 4) == (y << 16) & 0xffffffff
            write(mobj + 12, old_xy)
            write(mobj + 32, old_angle)
            write(viewz, old_z)
            used = (game.number('ds_p', 4) & 0xffffff) - ds_base
            openings = ((game.number('lastopening', 4) - game.number('openings', 4)) & 0xffffff) // 2
            result = game.read(fb, 3344) if fill is not None else None
            return used * 64 // size, openings, result

        game.breakpoint(camera)
        game.breakpoint(game.poll, False)
        rows = []
        for x, y in points.values():
            z = floor_at(x, y, nodes, sectors, subsectors, segs) + 41
            for i in range(8):
                yaw = i << 29
                ds, op, _ = draw(x, y, z, yaw)
                rows.append((ds, op, x, y, z, yaw))
        rows.sort(reverse=True)
        print('views', len(rows), 'drawseg usage / 64, openings words / 1216:', rows[:16], flush=True)
        print('views at drawseg capacity:', sum(row[0] == 64 for row in rows), flush=True)
        xmin, xend, ymin, yend = game.read(game.sym('r57_view') + 3, 4)
        assert 0 <= xmin < xend <= 76 and 0 <= ymin < yend <= 44
        print('visible viewport:', xmin, xend, ymin, yend, flush=True)
        # Fixed problem views from the baseline sweep, plus an ordinary start-room view.
        cases = [(848, 1056, -87, 0), (2192, 576, 177, 1 << 29),
                 (2192, 576, 177, 3 << 29), (2192, 576, 177, 2 << 29),
                 (848, 1056, -87, 7 << 29), (928, -896, 41, 1 << 29),
                 (2680, 980, 193, 4 << 29), (928, -896, 41, 2 << 29),
                 (-416, 256, 41 + floor_at(-416, 256, nodes, sectors, subsectors, segs), 0)]
        counts = []
        for x, y, z, yaw in cases:
            *_, frame_a = draw(x, y, z, yaw, 0x11)
            *_, frame_b = draw(x, y, z, yaw, 0xee)
            holes = []
            for py in range(ymin, yend):
                shift = 0 if py & 1 else 4
                for px in range(xmin, xend):
                    byte = (py // 2) * 152 + (px & 1) * 76 + (px // 2) * 2 + 1
                    if ((frame_a[byte] >> shift) & 15, (frame_b[byte] >> shift) & 15) == (1, 14):
                        holes.append((px, py))
            counts.append(len(holes))
            print('view', x, y, z, yaw, 'unpainted', len(holes), holes[:8], flush=True)
        if args.require_painted:
            assert max(counts) == 0, ('viewport samples retained from old frames', counts)
    finally:
        game.g.close()


if __name__ == '__main__':
    main()
