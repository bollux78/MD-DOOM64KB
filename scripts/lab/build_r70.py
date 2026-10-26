#!/usr/bin/env python3
"""R70-A A/B build: R66 PERF control and three R70-A variants, all uninstrumented (no R68), H40 crop 16/16.

  r66-perf    : control (label r66-control), no R70-A flag
  r70a1       : DOOM_R70A_LOCALS=1      -> -DDOOM_R21_SEGLOOP_LOCALS
  r70a2       : DOOM_R70A_INVARIANTS=1  -> -DDOOM_R70A_INVARIANTS
  r70a12      : both

Everything else is the exact R66 environment of build_r68.py (same keys, same values). Asserts: the control
carries no R70-A flag, every variant's flag list equals control + exactly its own flags, identical colour
tables, BSS <= 57,920 B and ROM <= 4 MiB. Each variant builds in its own copy of the checkout (R70_WORK, default dist/r70-work/<variant>). Writes dist/r70/{ROMs,ELFs,flags,SIZE-*,MANIFEST.json}.
"""
from pathlib import Path
import os, subprocess, shutil, hashlib, json

# The build name becomes DOOM_BUILD_ID inside the ROM, so the control MUST be built under the name 'r66-perf' to be
# byte-identical to the approved original (doom-md-r60-r66-perf.bin). Variant names only change the fixed-size header ID.
VARIANTS = (
    ('r66-perf', {}, []),
    ('r70a1', {'DOOM_R70A_LOCALS': '1'}, ['-DDOOM_R21_SEGLOOP_LOCALS']),
    ('r70a2', {'DOOM_R70A_INVARIANTS': '1'}, ['-DDOOM_R70A_INVARIANTS']),
    ('r70a12', {'DOOM_R70A_LOCALS': '1', 'DOOM_R70A_INVARIANTS': '1'},
     ['-DDOOM_R21_SEGLOOP_LOCALS', '-DDOOM_R70A_INVARIANTS']),
)
LABEL = {'r66-perf': 'r66-control'}
CLEAN = ('DOOM_R53_MICRO_RATIO', 'DOOM_R55_WERK_VARIANT', 'DOOM_R56_CLAUDIO_PROFILE',
         'DOOM_R56_BUILD', 'DOOM_R55_BUILD', 'DOOM_R52_BUILD', 'DOOM_R57_PROFILE',
         'DOOM_R57_TABLES_DIR', 'DOOM_R58_BUILD', 'DOOM_R58_CM_VIEW', 'DOOM_R57_BUILD',
         'DOOM_R59_BUILD', 'DOOM_R59_COLOR_VIEW', 'DOOM_R60_BUILD', 'DOOM_R60_PAIR_ASM',
         'DOOM_R64_DIAG', 'DOOM_R64A_PROLOGUE', 'DOOM_R66_COLPAIR', 'DOOM_R68_PROF', 'DOOM_R68_SPLIT',
         'DOOM_R70A_LOCALS', 'DOOM_R70A_INVARIANTS')


def main():
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    dest = (root / 'dist/r70').resolve()
    dest.mkdir(parents=True, exist_ok=True)
    size_exe = Path.home() / 'mars/m68k-elf/bin/m68k-elf-size'
    nm_exe = Path.home() / 'mars/m68k-elf/bin/m68k-elf-nm'
    assert size_exe.is_file() and nm_exe.is_file(), 'MarsDev missing'
    vgm = os.environ.get('DOOM_R20_BGM_VGM', str(root / 'res/e1m1.vgm'))
    assert Path(vgm).is_file()
    flags, records = {}, []
    for name, extra_env, _extra_flags in VARIANTS:
        video = 0; hcrop = 16; vcrop = 16
        mode = 'perf'
        bench = '0'
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
        env.update(extra_env)
        # Isolation: every variant is built from its own copy of the checkout (the fish script derives its root from its own
        # location), so no intermediate file, generated table or dist/r35 output is shared between variants.
        work = Path(os.environ.get('R70_WORK', str(root / 'dist/r70-work'))).resolve() / name
        assert not work.exists(), ('work directory already exists, refusing to reuse it', work)
        shutil.copytree(root, work, ignore=shutil.ignore_patterns('dist', '.git', '__pycache__'))
        print('BUILD R70', name, extra_env, 'in', work, flush=True)
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
        # R_RenderSegLoop may be inlined into R_StoreWallRange by LTO, so it is not required as a symbol.
        for sym in ('I_FinishUpdate', 'r22_fb', '_g_gametic', '_g_vblankCount', 'R_StoreWallRange'):
            assert any(l.split()[-1] == sym or l.split()[-1].startswith(sym + '.') for l in nm.splitlines() if l.split()), ('symbol missing', name, sym)
        sizes = subprocess.run([str(size_exe), '-A', str(src.with_suffix('.elf'))], check=True, capture_output=True, text=True).stdout
        (dest / ('SIZE-' + name + '.txt')).write_text(sizes)
        bss = sum(int(a[1]) for line in sizes.splitlines() if len(a := line.split()) >= 2 and a[0] in ('.bss', '.sbss'))
        assert 0 < bss <= 57920, (name, bss)
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
    control = normalize(flags['r66-perf'], 'r66-perf')
    for name, _env, extra in VARIANTS:
        cand = normalize(flags[name], name)
        assert sorted(cand) == sorted(control + extra), ('Unexpected flag drift', name, set(cand) ^ set(control))
    for table in ('r56_tables.h', 'r59_color_tables.h'):
        assert len({(dest / (n + '-' + table)).read_bytes() for n, _e, _f in VARIANTS}) == 1, table
    print('PASS R70: control has no R70-A flag; each variant = control + only its own flags; identical palettes; BSS <= 57920', flush=True)


if __name__ == '__main__':
    main()
