#!/usr/bin/env python3
"""Drive the shipping ROM through its ordinary SGDK joypad and Doom menus."""
import argparse
import hashlib
import json
import math
import os
import re
import struct
import subprocess
from pathlib import Path

from r64a_rsp_capture import RSP, symbols

UP, DOWN, LEFT, RIGHT, FIRE, USE, START = 1, 2, 4, 8, 16, 64, 128


class Play:
    def __init__(self, blastem, rom, elf):
        self.syms = symbols(elf)
        self.pcm = 0
        self.joy = self.sym('joyState')
        asm = subprocess.check_output([os.environ['M68K_OBJDUMP'], '-d', '--disassemble=I_StartTic', elf], text=True)
        reads = re.findall(r'^\s*([0-9a-f]+):.*\bmovew\s+[0-9a-f]+ <joyState[^>]*>,%d[0-7]$', asm, re.MULTILINE)
        assert len(reads) == 1, ('JOY_1 cached read in I_StartTic', reads)
        self.poll = int(reads[0], 16)
        self.error = self.sym('I_Error')
        self.frame = self.sym('I_FinishUpdate')
        self.sound = self.sym('XGM2_playPCMEx')
        self.g = RSP(blastem, rom, 4200, 60)

    def sym(self, name):
        if name in self.syms:
            return self.syms[name] & 0xFFFFFF
        matches = [a for s, a in self.syms.items() if s.startswith(name + '.')]
        assert len(matches) == 1, (name, matches)
        return matches[0] & 0xFFFFFF

    def read(self, addr, length):
        return self.g.readmem(addr & 0xFFFFFF, length)

    def number(self, name, length=2):
        return int.from_bytes(self.read(self.sym(name), length), 'big')

    def breakpoint(self, addr, enable=True):
        assert self.g.req(f"{'Z' if enable else 'z'}0,{addr:x},2") == 'OK'

    def next(self, target):
        for _ in range(1000):
            self.g.cont()
            regs = self.g.req('g')
            pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF
            if pc == self.error:
                sp = int(regs[15 * 8:16 * 8], 16)
                pointer = int.from_bytes(self.read(sp + 4, 4), 'big')
                msg = self.read(pointer, 100).split(b'\0', 1)[0].decode(errors='replace')
                if msg.startswith('Z_Malloc'):
                    msg %= struct.unpack('>III', self.read(sp + 8, 12))
                raise AssertionError('I_Error: ' + msg)
            if pc == self.sound:
                self.pcm += 1
            elif pc == target:
                return
            else:
                raise AssertionError(f'unexpected BlastEm stop at {pc:06x}, wanted {target:06x}')
        raise AssertionError('excessive breakpoint stops')

    def boot(self):
        self.g.req('qSupported')
        for address in (self.error, self.sound, self.poll):
            self.breakpoint(address)
        self.next(self.poll)

    def step(self, mask, count=1):
        for _ in range(count):
            # Set the cached JOY_1 word after JOY_update and before JOY_readJoypad.
            # Doom's edge detection and responder still consume the input normally.
            assert self.g.req(f'M{self.joy:x},2:{mask:04x}') == 'OK'
            self.next(self.poll)

    def tap(self, button):
        self.step(button, 2)
        self.step(0, 2)

    def menu(self, row):
        self.tap(START)
        if self.number('currentMenu', 4) & 0xFFFFFF == self.sym('LevelDef'):
            self.tap(FIRE)
        assert self.number('_g_menuactive', 4), 'Start did not open a menu'
        assert self.number('currentMenu', 4) & 0xFFFFFF == self.sym('MainDef')
        assert self.number('r76_menu_cursor') == 0, 'main menu cursor was not reset'
        for _ in range(row):
            self.tap(DOWN)
        self.tap(USE)

    def position(self):
        player = self.number('_g_player', 4)
        return struct.unpack('>iii', self.read(player + 12, 12))

    def aim(self, x, y):
        px, py, _ = self.position()
        angle = math.atan2((y << 16) - py, (x << 16) - px)
        target = int(angle * (1 << 32) / (2 * math.pi))
        for _ in range(80):
            player = self.number('_g_player', 4)
            current = int.from_bytes(self.read(player + 32, 4), 'big')
            delta = ((target - current + (1 << 31)) % (1 << 32)) - (1 << 31)
            if abs(delta) < (1 << 32) * 4 / 360:
                self.step(0, 1)
                return
            self.step(LEFT if delta > 0 else RIGHT)
        raise AssertionError('joypad turning did not converge')

    def kills(self):
        # The save codec's field descriptors contain the target ABI offsets.
        off = int.from_bytes(self.read(self.sym('r81_player_fields') + 22 * 4, 2), 'big')
        return int.from_bytes(self.read(self.sym('_g_player') + off, 2), 'big')

    def check_map(self, index, sectors):
        assert self.number('_g_gamemap') == index, ('map', index, self.number('_g_gamemap'))
        assert self.number('_g_numsectors') == sectors, ('sectors', sectors, self.number('_g_numsectors'))
        assert self.number('_g_usergame', 4)
        ptr = self.number('_g_maplines', 4) & 0xFFFFFF
        assert (0x3D0000 <= ptr < 0x3FFFF0) == (index == 10), hex(ptr)
        assert self.number('r39e_song_active') == 1
        return hex(ptr)

    def picture(self, path):
        self.breakpoint(self.poll, False)
        self.breakpoint(self.frame)
        self.next(self.frame)
        fb = self.number('r115_draw', 4)
        data = self.read(fb, 3344)
        path.write_bytes(data)
        self.breakpoint(self.frame, False)
        self.breakpoint(self.poll)
        self.next(self.poll)
        return hashlib.sha256(data).hexdigest()


def run(args, rom, elf, candidate, report):
    game = Play(args.blastem, rom, elf)
    try:
        report['stage'] = 'boot'
        game.boot()
        if candidate:
            report['boot_bits'] = game.number('r136_boot_result', 1)
            assert report['boot_bits'] == 31
        assert game.number('r89_ai_low', 1) == 0
        game.step(0, 24)  # Let the title loop process its initial advance.
        report['stage'] = 'original E1M1'
        game.menu(0)
        game.tap(USE)
        game.step(0, 24)
        original = {'maplines': game.check_map(1, 85), 'start': game.position()}
        original['frame'] = game.picture(args.out.parent / ('original.bin' if candidate else 'r128-original.bin'))
        game.step(UP, 35)
        game.step(0, 4)
        original['after_forward'] = game.position()
        report['original'] = original
        if not candidate:
            report['stage'] = 'complete'
            return

        # Extra Maps is the last entry. Use the real menu to start the banked map.
        report['stage'] = 'Freedoom selection'
        game.menu(7)
        assert game.number('currentMenu', 4) & 0xFFFFFF == game.sym('ExtraMapDef')
        game.tap(USE)
        game.tap(USE)
        game.step(0, 24)
        extra = report['extra'] = {'maplines': game.check_map(10, 182), 'start': game.position()}
        assert extra['start'][:2] == (-416 << 16, 256 << 16), extra
        extra['start_frame'] = game.picture(args.out.parent / 'freedoom-start.bin')

        # Head east out of the start room, onto the tag-1 walkover lift, and into the yard.
        report['stage'] = 'Freedoom lift'
        game.step(UP, 85)
        game.step(0, 25)
        game.tap(USE)
        game.step(UP, 85)
        game.step(0, 8)
        extra['after_lift'] = game.position()
        assert extra['after_lift'][0] > 208 << 16, extra
        extra['yard_frame'] = game.picture(args.out.parent / 'freedoom-yard.bin')
        assert extra['yard_frame'] != extra['start_frame']

        report['stage'] = 'Freedoom combat'
        before, kills = game.pcm, game.kills()
        game.aim(752, 336)
        game.step(FIRE | UP, 85)
        game.step(0, 10)
        extra['pcm_during_fire'] = game.pcm - before
        extra['kills'] = game.kills() - kills
        extra['after_fire'] = game.position()
        assert extra['pcm_during_fire'] > 0 and extra['kills'] > 0, extra

        report['stage'] = 'return to original E1M1'
        game.menu(0)
        game.tap(USE)
        game.step(0, 24)
        extra['return_maplines'] = game.check_map(1, 85)
        assert extra['return_maplines'] == original['maplines']
        assert game.position() == tuple(original['start'])
        assert game.picture(args.out.parent / 'original-return.bin') == original['frame']
        report['map_switch'] = 'PASS'

        report['stage'] = 'original E1M1 SRAM save and load'
        game.menu(5)
        game.tap(USE)
        save = game.read(game.sym('_g_savegamestrings'), 8).split(b'\0', 1)[0]
        assert save == b'E1M1', save
        game.step(UP, 35)
        game.step(0, 4)
        assert game.position() != tuple(original['start'])
        game.menu(4)
        game.tap(USE)
        game.step(0, 24)
        assert game.position() == tuple(original['start'])
        report['original_save_load'] = 'PASS'
        report['stage'] = 'complete'
    finally:
        game.g.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blastem', required=True)
    for name in ('rom', 'elf', 'reference-rom', 'reference-elf', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    result = {'build': 'PASS', 'blastem': 'INCONCLUSIVE', 'candidate': {}, 'r128_all': {}}
    try:
        run(args, args.rom, args.elf, True, result['candidate'])
        run(args, args.reference_rom, args.reference_elf, False, result['r128_all'])
        a, b = (result[key]['original'] for key in ('candidate', 'r128_all'))
        assert all(a[key] == b[key] for key in ('start', 'frame', 'after_forward')), (a, b)
        result['r128_original_e1m1'] = 'PASS'
        result['blastem'] = 'PASS'
    except AssertionError as exc:
        result['blastem'] = 'FAIL'
        result['error'] = str(exc)
        raise
    finally:
        args.out.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
