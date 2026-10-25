#!/usr/bin/env python3
"""R64A: R60 PairASM control PERF versus prologue cache candidate PERF/PLAY."""
from pathlib import Path
import os, subprocess, shutil, hashlib, json

def main():
    root=Path(__file__).resolve().parents[2]
    os.chdir(root)
    dest=(root/'dist/r64a').resolve()
    dest.mkdir(parents=True,exist_ok=True)
    size_exe=Path.home()/'mars/m68k-elf/bin/m68k-elf-size'
    nm_exe=Path.home()/'mars/m68k-elf/bin/m68k-elf-nm'
    assert size_exe.is_file() and nm_exe.is_file(),'MarsDev missing'
    vgm=os.environ.get('DOOM_R20_BGM_VGM',str(root/'res/e1m1.vgm'))
    assert Path(vgm).is_file()
    variants=(('ref-perf','perf',1,0),('r64a-perf','perf',1,1),('r64a-play','play',1,1))
    flags={}
    records=[]
    for name,mode,kernel,r64a in variants:
        video=0;hcrop=16;vcrop=16
        bench='1' if mode=='play' else '0'
        env=os.environ.copy()
        for key in ('DOOM_R53_MICRO_RATIO','DOOM_R55_WERK_VARIANT','DOOM_R56_CLAUDIO_PROFILE',
                    'DOOM_R56_BUILD','DOOM_R55_BUILD','DOOM_R52_BUILD','DOOM_R57_PROFILE',
                    'DOOM_R57_TABLES_DIR','DOOM_R58_BUILD','DOOM_R58_CM_VIEW','DOOM_R57_BUILD',
                    'DOOM_R59_BUILD','DOOM_R59_COLOR_VIEW','DOOM_R60_BUILD','DOOM_R60_PAIR_ASM',
                    'DOOM_R64_DIAG','DOOM_R64A_PROLOGUE'):
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
        env.update(DOOM_R60_BUILD=name,DOOM_R60_PAIR_ASM=str(kernel),DOOM_R64A_PROLOGUE=str(r64a))
        print('BUILD R64A',name,flush=True)
        subprocess.run(['fish','scripts/lab/build_r35_linear.fish','pixel4-'+mode],env=env,check=True)
        stem='doom-md-r60-'+name
        src=root/'dist/r35'/stem
        for ext in ('.bin','.elf'):
            shutil.copy2(src.with_suffix(ext),dest/(stem+ext))
        flagpath=root/'dist/r35'/('flags-'+stem+'.txt')
        flags[name]=flagpath.read_text()
        (dest/('flags-'+stem+'.txt')).write_text(flags[name])
        nm=subprocess.run([str(nm_exe),str(src.with_suffix('.elf'))],check=True,capture_output=True,text=True).stdout
        assert ('R60_WallColumn' in nm)==bool(kernel),('R60 linked kernel mismatch',name)
        sizes=subprocess.run([str(size_exe),'-A',str(src.with_suffix('.elf'))],check=True,capture_output=True,text=True).stdout
        (dest/('SIZE-'+name+'.txt')).write_text(sizes)
        bss=sum(int(a[1]) for line in sizes.splitlines() if len(a:=line.split())>=2 and a[0] in ('.bss','.sbss'))
        assert 0<bss<=57920,(name,bss)
        blob=(dest/(stem+'.bin')).read_bytes()
        assert 0<len(blob)<=4*1024*1024
        for table in ('r56_tables.h','r59_color_tables.h'):
            shutil.copy2(root/'src'/table,dest/(name+'-'+table))
        report=json.loads((root/'src/r58_colormatch_report.json').read_text())
        assert report['preserved_flat_anchors']==6
        assert report['palette_slots_from_8x8']==[[41,11,43,7,2,1,32,52,10],[8,22,39,16,15,35,19,40,36]]
        records.append(dict(rom=stem+'.bin',mode=mode,kernel=kernel,bytes=len(blob),bss_bytes=bss,sha256=hashlib.sha256(blob).hexdigest()))
        (dest/'MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n')
    assert len(records)==3
    def normalize(text,id):
        return text.replace('doom-md-r60-'+id,'ID').split()
    original=normalize(flags['ref-perf'],'ref-perf')
    candidate=normalize(flags['r64a-perf'],'r64a-perf')
    assert sorted(candidate)==sorted(original+['-DDOOM_R64A_PROLOGUE']),('Unexpected flag drift',set(candidate)^set(original))
    for table in ('r56_tables.h','r59_color_tables.h'):
        assert len({(dest/(id+'-'+table)).read_bytes() for id,_,_,_ in variants})==1,table
    print('PASS R64A 3 ROMs, BSS <=57920, ASM intact, R60 flags unchanged except candidate macro, identical palettes',flush=True)

if __name__=='__main__':
    main()
