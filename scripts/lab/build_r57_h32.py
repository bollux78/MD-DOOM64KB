#!/usr/bin/env python3
"""Build R57 fixed-palette crop16 and full viewport PLAY/PERF comparison.

Uses the existing R56 renderer, SGDK/MarsDev, audio and fast-menu flags.
No promises of visual quality or benchmark speed from a successful build.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/r57-diversity')
    args=ap.parse_args();root=Path(__file__).resolve().parents[2];os.chdir(root)
    dest=Path(args.out).resolve();tables=dest/'tables';dest.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'scripts/lab/gen_r57_diversity.py','--repo','.','--out',str(tables)],check=True)
    subprocess.run([sys.executable,'scripts/lab/test_r57_diversity.py','--repo','.','--tables',str(tables),'--host-c'],check=True)
    profiles=['c55-a6']
    records=[]
    size_exe=Path.home()/'mars/m68k-elf/bin/m68k-elf-size'
    assert size_exe.is_file(),'MarsDev size tool unavailable'
    vgm=os.environ.get('DOOM_R20_BGM_VGM',str((root/'res/e1m1.vgm').resolve()))
    assert Path(vgm).is_file(),'Run the existing pinned VGM preflight first'
    for profile in profiles:
        for variant,mode in (('size','play'),('crop16','perf'),('h40n','play'),('h40n','perf'),('h32','play'),('h32','perf')):
            bench='1' if mode=='play' else '0';name=variant+'-'+mode
            env=os.environ.copy()
            for key in ('DOOM_R53_MICRO_RATIO','DOOM_R55_WERK_VARIANT','DOOM_R56_CLAUDIO_PROFILE',
                        'DOOM_R56_BUILD','DOOM_R55_BUILD','DOOM_R52_BUILD','DOOM_R57_PROFILE','DOOM_R57_TABLES_DIR'):
                env.pop(key,None)
            env.update({
                'DOOM_R35D_CHECKER':'1','DOOM_R39C_VARIANT':'mall','DOOM_R39D_DITHER_TOGGLE':'0',
                'DOOM_R39E_AUDIO_TOGGLES':'1','DOOM_R40_STAGE1':'fast','DOOM_R42_WALL_ASM':'1',
                'DOOM_R45_VARIANT':'asm','DOOM_R47_PLANE_PAIR':'1','DOOM_R47_FLAT_HOIST':'1',
                'DOOM_R47_SPRITE_HOIST':'1','DOOM_R48_PAIR_V':'1','DOOM_R48_V_FAST':'1',
                'DOOM_R49_COLORMIX':'0','DOOM_R49_COMPLUT':'0','DOOM_R49_RATIO':'none',
                'DOOM_R52_AB':'1','DOOM_R52_CLAUDIO':'1','DOOM_R52_AB_PROFILE':'luma32',
                'DOOM_R52_ZERO_POLICY':'forbid','DOOM_R52_CPLUT':'1','DOOM_R56_DUAL_COLOR':'1',
                'DOOM_R57_CROP16':'1',
                'DOOM_R57_SIZE_MENU':'1' if variant=='size' else '0',
                'DOOM_R57_NARROW256':'1' if variant in ('h40n','h32') else '0',
                'DOOM_R57_H32':'1' if variant=='h32' else '0',
                'DOOM_R57_BUILD':name,'DOOM_R50_PLAY_BENCH':bench,'DOOM_R50_MENU_FREEZE':bench,
                'DOOM_R50_STATIC_MENU':bench,'DOOM_R50_HARD_REINIT':bench,'DOOM_R50_RESET_SRAM':'0',
                'DOOM_R51_HW_WEAPON':'0','DOOM_R51_NO_PSPRITE':'0','DOOM_R20_BGM_VGM':vgm,
            })
            backend='pixel4'
            if profile=='legacy8':
                backend='cell'
                for key in ('DOOM_R52_AB','DOOM_R52_CLAUDIO','DOOM_R52_CPLUT','DOOM_R56_DUAL_COLOR',
                            'DOOM_R47_PLANE_PAIR','DOOM_R48_PAIR_V','DOOM_R48_V_FAST',
                            'DOOM_R42_WALL_ASM','DOOM_R47_FLAT_HOIST','DOOM_R47_SPRITE_HOIST',
                            'DOOM_R50_PLAY_BENCH','DOOM_R50_MENU_FREEZE','DOOM_R50_STATIC_MENU',
                            'DOOM_R50_HARD_REINIT'):
                    env[key]='0'
                env.pop('DOOM_R45_VARIANT',None)
                env.pop('DOOM_R40_STAGE1',None)
            else:
                env['DOOM_R57_PROFILE']=profile;env['DOOM_R57_TABLES_DIR']=str(tables)
            print('BUILD R57',name,flush=True)
            subprocess.run(['fish','scripts/lab/build_r35_linear.fish',backend+'-'+mode],env=env,check=True)
            stem='doom-md-r57-'+name;source=root/'dist/r35'/stem
            for suffix in ('.bin','.elf'):
                shutil.copy2(source.with_suffix(suffix),dest/(stem+suffix))
            shutil.copy2(root/'dist/r35'/('flags-'+stem+'.txt'),dest/('flags-'+stem+'.txt'))
            size=subprocess.run([str(size_exe),'-A',str(source.with_suffix('.elf'))],text=True,capture_output=True,check=True).stdout
            (dest/('size-'+name+'.txt')).write_text(size)
            bss=sum(int(parts[1]) for line in size.splitlines() if len(parts:=line.split())>=2 and parts[0] in ('.bss','.sbss'))
            assert 0<bss<=57920,(name,bss)
            binary=(dest/(stem+'.bin')).read_bytes()
            assert 0<len(binary)<=4*1024*1024,(name,len(binary))
            if profile!='legacy8':
                runtime=(root/'src/r56_tables.h').read_bytes()
                assert runtime==(tables/(profile+'.h')).read_bytes(),'wrong palette header entered build'
                shutil.copy2(root/'src/r56_tables.h',dest/('PALETTES-'+name+'.h'))
            records.append({'rom':stem+'.bin','profile':profile,'viewport':variant,'mode':mode,'backend':backend,
                            'bytes':len(binary),'bss_bytes':bss,'sha256':hashlib.sha256(binary).hexdigest()})
            (dest/'MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n')
    assert len(records)==6
    print('R57: 6 screen-size / H32 ROMs built; hardware and complete timedemo validation pending.',flush=True)


if __name__=='__main__':main()
