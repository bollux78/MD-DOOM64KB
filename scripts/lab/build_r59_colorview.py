#!/usr/bin/env python3
"""Build R59 COLOR VIEW: R58 CM6 + three exact historical R57 A6 modes.

One full-featured PLAY ROM (Options H40/H32 + H/V crop 0..32, built-in benchmark)
and one PERF companion. COLOR VIEW switches CRAM, LUTs and VDP pair patterns.
Preserves the exact ColorMatch v2 LUT-generator source from exp-r57-colormatch.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='dist/r59-colorview')
    args=ap.parse_args();root=Path(__file__).resolve().parents[2];os.chdir(root)
    dest=Path(args.out).resolve();dest.mkdir(parents=True,exist_ok=True)
    profiles=['cm6']
    records=[]
    size_exe=Path.home()/'mars/m68k-elf/bin/m68k-elf-size'
    assert size_exe.is_file(),'MarsDev size tool unavailable'
    vgm=os.environ.get('DOOM_R20_BGM_VGM',str((root/'res/e1m1.vgm').resolve()))
    assert Path(vgm).is_file(),'Run the existing pinned VGM preflight first'
    for profile in profiles:
        for variant,mode,video,hcrop,vcrop in (('colorview-v2','play',0,16,16),('colorview-v2','perf',0,16,16)):
            bench='1' if mode=='play' else '0';name=variant+'-'+mode
            env=os.environ.copy()
            for key in ('DOOM_R53_MICRO_RATIO','DOOM_R55_WERK_VARIANT','DOOM_R56_CLAUDIO_PROFILE',
                        'DOOM_R56_BUILD','DOOM_R55_BUILD','DOOM_R52_BUILD','DOOM_R57_PROFILE','DOOM_R57_TABLES_DIR','DOOM_R58_BUILD','DOOM_R58_CM_VIEW','DOOM_R57_BUILD','DOOM_R59_BUILD','DOOM_R59_COLOR_VIEW'):
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
                'DOOM_R57_SIZE_MENU':'0',
                'DOOM_R57_VIEW_MENU':'1',
                'DOOM_R57_VIEW_MODE':str(video),
                'DOOM_R57_VIEW_HCROP':str(hcrop),
                'DOOM_R57_VIEW_VCROP':str(vcrop),
                'DOOM_R57_NARROW256':'1',
                'DOOM_R57_H32':'1',
                'DOOM_R59_BUILD':name,'DOOM_R59_COLOR_VIEW':'1','DOOM_R58_CM_VIEW':'1','DOOM_R50_PLAY_BENCH':bench,'DOOM_R50_MENU_FREEZE':bench,
                'DOOM_R50_STATIC_MENU':bench,'DOOM_R50_HARD_REINIT':bench,'DOOM_R50_RESET_SRAM':'0',
                'DOOM_R51_HW_WEAPON':'0','DOOM_R51_NO_PSPRITE':'0','DOOM_R20_BGM_VGM':vgm,
            })
            # The approved CM6 palettes are generated inside the fish build
            # from the exact R56 A6 snapshot, before code compilation.
            backend='pixel4'
            print('BUILD R59',name,flush=True)
            subprocess.run(['fish','scripts/lab/build_r35_linear.fish',backend+'-'+mode],env=env,check=True)
            stem='doom-md-r59-'+name;source=root/'dist/r35'/stem
            for suffix in ('.bin','.elf'):
                shutil.copy2(source.with_suffix(suffix),dest/(stem+suffix))
            shutil.copy2(root/'dist/r35'/('flags-'+stem+'.txt'),dest/('flags-'+stem+'.txt'))
            size=subprocess.run([str(size_exe),'-A',str(source.with_suffix('.elf'))],text=True,capture_output=True,check=True).stdout
            (dest/('size-'+name+'.txt')).write_text(size)
            bss=sum(int(parts[1]) for line in size.splitlines() if len(parts:=line.split())>=2 and parts[0] in ('.bss','.sbss'))
            assert 0<bss<=57920,(name,bss)
            binary=(dest/(stem+'.bin')).read_bytes()
            assert 0<len(binary)<=4*1024*1024,(name,len(binary))
            if profile=='cm6':
                runtime=root/'src/r56_tables.h'
                report_src=root/'src/r58_colormatch_report.json'
                assert runtime.is_file() and report_src.is_file(),'ColorMatch generator not run'
                report=json.loads(report_src.read_text())
                assert report['preserved_flat_anchors']==6
                assert report['unique_cram_words_union_normal']==24,report
                assert report['shared_free_color_source_slots']==0
                assert report['mixed_code_count_per_plane']==[2,3],report
                assert report['palette_slots_from_8x8']==[
                    [41,11,43,7,2,1,32,52,10],
                    [8,22,39,16,15,35,19,40,36]],'not approved ColorMatch CM6 palette'
                shutil.copy2(runtime,dest/('PALETTES-'+name+'.h'))
                shutil.copy2(report_src,dest/('METRICS-'+name+'.json'))
            color_src=root/'src/r59_color_tables.h'
            color_report=root/'src/r59_color_report.json'
            assert color_src.is_file() and color_report.is_file(),'R59 tables missing'
            shutil.copy2(color_src,dest/('COLOR-TABLES-'+name+'.h'))
            shutil.copy2(color_report,dest/('COLOR-REPORT-'+name+'.json'))
            records.append({'rom':stem+'.bin','profile':profile,'viewport':variant,'mode':mode,'backend':backend,'video_mode':'H32' if video else 'H40','h_crop':hcrop,'v_crop':vcrop,
                            'bytes':len(binary),'bss_bytes':bss,'sha256':hashlib.sha256(binary).hexdigest()})
            (dest/'MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n')
    assert len(records)==2
    play_header=(dest/'PALETTES-colorview-v2-play.h').read_bytes()
    perf_header=(dest/'PALETTES-colorview-v2-perf.h').read_bytes()
    assert play_header==perf_header,'ColorMatch table changed between PLAY/PERF'
    assert (dest/'COLOR-TABLES-colorview-v2-play.h').read_bytes()==(dest/'COLOR-TABLES-colorview-v2-perf.h').read_bytes(),'R59 profiles changed between builds'
    assert (dest/'COLOR-REPORT-colorview-v2-play.json').read_bytes()==(dest/'COLOR-REPORT-colorview-v2-perf.json').read_bytes(),'R59 profile report changed'
    print('R59: CM6/Balanced/Tolerant/Accents in same ROM, runtime H32/H40 and crop; 2 ROMs built.',flush=True)
    print('ColorMatch tables SHA256:',hashlib.sha256(play_header).hexdigest(),flush=True)
    print('Real-hardware mode switching and complete timedemo validation still pending.',flush=True)


if __name__=='__main__':main()
