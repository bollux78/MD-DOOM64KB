#!/usr/bin/env python3
"""Recreated Doom status bar (HUD-WAD): R66 control and HUD variants, uninstrumented, H40 crop 16/16.

  r70a12          : A12 PERF (R70-A LOCALS+INVARIANTS), byte-identical to the A12 ROM of run 40362045678 (no HUD flag)
  r70a12-play     : A12 PLAY (menu/play build), flags/BSS reference for the HUD play ROM
  r70a12-hud-perf : A12 + DOOM_HUD_WAD=1 PERF  (timedemo: HUD cost)
  r70a12-hud-play : A12 + DOOM_HUD_WAD=1 PLAY  (the ROM to play)

Needs src/hud_wad_assets.h (scripts/lab/gen_hud_wad.py from the user's IWAD). Each variant builds in its own copy of the checkout.
"""
from pathlib import Path
import os, subprocess, shutil, hashlib, json

# The build name becomes DOOM_BUILD_ID inside the ROM, so the control MUST be built as 'r66-perf' to be byte-identical.
VARIANTS = (
    ('r70a12', 'perf', {}, []),
    ('r70a12-play', 'play', {}, []),
    ('r70a12-hud-perf', 'perf', {'DOOM_HUD_WAD': '1'}, ['-DDOOM_HUD_WAD']),
    ('r70a12-hud-play', 'play', {'DOOM_HUD_WAD': '1'}, ['-DDOOM_HUD_WAD']),
)
LABEL = {'r70a12': 'a12-control', 'r70a12-play': 'a12-play-control'}
A12_ENV = {'DOOM_R70A_LOCALS': '1', 'DOOM_R70A_INVARIANTS': '1'}
A12_FLAGS = ['-DDOOM_R21_SEGLOOP_LOCALS', '-DDOOM_R70A_INVARIANTS']
CLEAN = ('DOOM_R53_MICRO_RATIO', 'DOOM_R55_WERK_VARIANT', 'DOOM_R56_CLAUDIO_PROFILE',
         'DOOM_R56_BUILD', 'DOOM_R55_BUILD', 'DOOM_R52_BUILD', 'DOOM_R57_PROFILE',
         'DOOM_R57_TABLES_DIR', 'DOOM_R58_BUILD', 'DOOM_R58_CM_VIEW', 'DOOM_R57_BUILD',
         'DOOM_R59_BUILD', 'DOOM_R59_COLOR_VIEW', 'DOOM_R60_BUILD', 'DOOM_R60_PAIR_ASM',
         'DOOM_R64_DIAG', 'DOOM_R64A_PROLOGUE', 'DOOM_R66_COLPAIR', 'DOOM_R68_PROF', 'DOOM_R68_SPLIT',
         'DOOM_R70A_LOCALS', 'DOOM_R70A_INVARIANTS', 'DOOM_HUD_WAD')


def main():
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    dest = (root / 'dist/hud').resolve()
    dest.mkdir(parents=True, exist_ok=True)
    size_exe = Path.home() / 'mars/m68k-elf/bin/m68k-elf-size'
    nm_exe = Path.home() / 'mars/m68k-elf/bin/m68k-elf-nm'
    assert size_exe.is_file() and nm_exe.is_file(), 'MarsDev missing'
    vgm = os.environ.get('DOOM_R20_BGM_VGM', str(root / 'res/e1m1.vgm'))
    assert Path(vgm).is_file()
    flags, records = {}, []
    for name, mode, extra_env, _extra_flags in VARIANTS:
        video = 0; hcrop = 16; vcrop = 16
        bench = '1' if mode == 'play' else '0'
        env = os.environ.copy()
        for key in CLEAN:
            env.pop(key, None)
        env.update({
            'DOOM_R35D_CHECKER': '1', 'DOOM_R39C_VARIANT': 'mall', 'DOOM_R39D_DITHER_TOGGLE': '0',
            'DOOM_R39E_AUDIO_TOGGLES': '1', 'DOOM_R40_STAGE1': 'fast', 'DOOM_R42_WALL_ASM': '1',
            'DOOM_R45_VARIANT': 'asm', 'DOOM_R47_PLANE_PAIR': '1', 'DOOM_R47_FLAT_HOIST': '1',
            'DOOM_R47_SPRITE_HOIST': '1', 'DOOM_R48_PAIR_V': '1', 'DOOM_R48_V_FAST': '1',
            'DOOM_R49_COLORMIX': '0', 'DOOM_R49_COMPLUT': '0', 'DOOM_R49_RATIO': 'none',
            'DOOM_R52_AB': '1', 'DOOM_R52_CLAUDIO': '1', 'DOOM_R52_AB_PROFILE': 'luma32',
            'DOOM_R52_ZERO_POLICY': 'forbid', 'DOOM_R52_CPLUT': '1', 'DOOM_R56_DUAL_COLOR': '1',
            'DOOM_R57_CROP16': '1',
            'DOOM_R57_SIZE_MENU': '0',
            'DOOM_R57_VIEW_MENU': '1',
            'DOOM_R57_VIEW_MODE': str(video),
            'DOOM_R57_VIEW_HCROP': str(hcrop),
            'DOOM_R57_VIEW_VCROP': str(vcrop),
            'DOOM_R57_NARROW256': '1',
            'DOOM_R57_H32': '1',
            'DOOM_R59_BUILD': name, 'DOOM_R59_COLOR_VIEW': '1', 'DOOM_R58_CM_VIEW': '1', 'DOOM_R50_PLAY_BENCH': bench,
            'DOOM_R50_MENU_FREEZE': bench, 'DOOM_R50_STATIC_MENU': bench, 'DOOM_R50_HARD_REINIT': bench,
            'DOOM_R50_RESET_SRAM': '0', 'DOOM_R51_HW_WEAPON': '0', 'DOOM_R51_NO_PSPRITE': '0',
            'DOOM_R20_BGM_VGM': vgm,
        })
        env.update(DOOM_R60_BUILD=name, DOOM_R60_PAIR_ASM='1', DOOM_R64A_PROLOGUE='1', DOOM_R66_COLPAIR='1',
                   DOOM_R68_PROF='0', DOOM_R68_SPLIT='0')
        env.update(A12_ENV)
        env.update(extra_env)
        # Isolation: every variant is built from its own copy of the checkout (the fish script derives its root from its own
        # location), so no intermediate file, generated table or dist/r35 output is shared between variants.
        work = Path(os.environ.get('HUD_WORK', str(root / 'dist/hud-work'))).resolve() / name
        assert not work.exists(), ('work directory already exists, refusing to reuse it', work)
        shutil.copytree(root, work, ignore=shutil.ignore_patterns('dist', '.git', '__pycache__'))
        print('BUILD HUD', name, extra_env, 'in', work, flush=True)
        subprocess.run(['fish', str(work / 'scripts/lab/build_r35_linear.fish'), 'pixel4-' + mode], env=env, check=True, cwd=work)
        stem = 'doom-md-r60-' + name
        src = work / 'dist/r35' / stem
        for ext in ('.bin', '.elf'):
            shutil.copy2(src.with_suffix(ext), dest / (stem + ext))
        flagpath = work / 'dist/r35' / ('flags-' + stem + '.txt')
        flags[name] = flagpath.read_text()
        (dest / ('flags-' + stem + '.txt')).write_text(flags[name])
        nm = subprocess.run([str(nm_exe), str(src.with_suffix('.elf'))], check=True, capture_output=True, text=True).stdout
        assert 'R60_WallColumn' in nm, ('R60 linked kernel mismatch', name)
        # R_RenderSegLoop and R_StoreWallRange are inlined by LTO in the normal build, so they are not required symbols.
        for sym in ('I_FinishUpdate', 'r22_fb', '_g_gametic', '_g_vblankCount'):
            assert any(l.split()[-1] == sym or l.split()[-1].startswith(sym + '.') for l in nm.splitlines() if l.split()), ('symbol missing', name, sym)
        sizes = subprocess.run([str(size_exe), '-A', str(src.with_suffix('.elf'))], check=True, capture_output=True, text=True).stdout
        (dest / ('SIZE-' + name + '.txt')).write_text(sizes)
        bss = sum(int(a[1]) for line in sizes.splitlines() if len(a := line.split()) >= 2 and a[0] in ('.bss', '.sbss'))
        print('BSS', name, bss, 'margin', 57920 - bss, flush=True)
        small = subprocess.run([str(nm_exe), '-S', '-t', 'd', '--size-sort', str(src.with_suffix('.elf'))], check=True, capture_output=True, text=True).stdout
        print('SMALL-BSS', name, ' '.join(f"{l.split()[3]}:{int(l.split()[1])}" for l in small.splitlines() if len(l.split()) == 4 and l.split()[2] in 'bB' and int(l.split()[1]) <= 12 and 'hudw' in l or len(l.split()) == 4 and l.split()[2] in 'bB' and int(l.split()[1]) <= 2), flush=True)
        assert 0 < bss <= 57920 + int(os.environ.get('HUD_BSS_SLACK', '0')), (name, bss)
        blob = (dest / (stem + '.bin')).read_bytes()
        assert 0 < len(blob) <= 4 * 1024 * 1024
        for table in ('r56_tables.h', 'r59_color_tables.h'):
            shutil.copy2(work / 'src' / table, dest / (name + '-' + table))
        report = json.loads((work / 'src/r58_colormatch_report.json').read_text())
        assert report['preserved_flat_anchors'] == 6
        assert report['palette_slots_from_8x8'] == [[41, 11, 43, 7, 2, 1, 32, 52, 10], [8, 22, 39, 16, 15, 35, 19, 40, 36]]
        records.append(dict(variant=LABEL.get(name, name), rom=stem + '.bin', elf=stem + '.elf', bytes=len(blob), bss_bytes=bss,
                            sha256=hashlib.sha256(blob).hexdigest()))
        (dest / 'MANIFEST.json').write_text(json.dumps(records, indent=2) + '\n')
    assert len(records) == len(VARIANTS)

    def normalize(text, name):
        return text.replace('doom-md-r60-' + name, 'ID').split()
    for name, mode, _env, extra in VARIANTS:
        ctl = 'r70a12' if mode == 'perf' else 'r70a12-play'
        cand, base = normalize(flags[name], name), normalize(flags[ctl], ctl)
        assert all(f in base for f in A12_FLAGS), ('control lacks A12 flags', ctl)
        assert sorted(cand) == sorted(base + extra), ('Unexpected flag drift', name, set(cand) ^ set(base))
    for table in ('r56_tables.h', 'r59_color_tables.h'):
        assert len({(dest / (n + '-' + table)).read_bytes() for n, _m, _e, _f in VARIANTS}) == 1, table
    print('PASS HUD build: control has no HUD flag; HUD variants = control + -DDOOM_HUD_WAD only; identical palettes; BSS <= 57920', flush=True)


if __name__ == '__main__':
    main()
