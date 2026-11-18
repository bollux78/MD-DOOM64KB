#!/usr/bin/env python3
"""Recompile one map layout using an already prepared E1M1 lab checkout."""
import argparse,os,shutil,struct,subprocess,time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('prepared',type=Path)
parser.add_argument('sgdk',type=Path)
parser.add_argument('format',choices=('control','side8','seg32','chunkrom','chunk128'))
parser.add_argument('output',type=Path)
args=parser.parse_args()
work,gdk,out=args.prepared.resolve(),args.sgdk.resolve(),args.output.resolve()
out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env['R128_MAP_FORMAT']=args.format
env['DOOM_R30_NATIVE']='1'
env['DOOM_R29_XGM2']='1'
env['DOOM_R29_MULTI']='1'
env['PATH']=str(gdk/'bin')+os.pathsep+env['PATH']
start=time.monotonic()
def run(command):
    subprocess.run(command,cwd=work,env=env,check=True)
run(['python3','scripts/lab/r128-shareware/map_format_lab.py'])
silent=work/'res/silent.vgm'
if not silent.exists():
    commands=bytes([0x52,0x28,0,0x62,0x66])
    header=bytearray(64);header[:4]=b'Vgm '
    for offset,value in ((4,64+len(commands)-4),(8,0x150),(0x2c,7670454),(0x18,735),(0x34,12)):
        struct.pack_into('<I',header,offset,value)
    silent.write_bytes(header+commands)
run(['python3','scripts/repack_wad.py'])
run(['python3','scripts/genpal.py'])
if not (work/'maplab-sfx-ready').exists():
    run(['python3','scripts/lab/gen_r31_sfx.py','--mode','mixed'])
    (work/'maplab-sfx-ready').touch()
for name in ('sega.s','rom_head.c'):
    boot=work/'src/boot'/name
    if boot.exists():boot.rename(boot.with_suffix(boot.suffix+'.disabled'))
flags=(work/'out/.render_options').read_text().strip()
if ' -DDOOM_BUILD_VARIANT ' in flags:
    flags,identity=flags.rsplit(' -DDOOM_BUILD_VARIANT ',1)
    flags+=' -DDOOM_BUILD_VARIANT'
else:
    identity='doom-md-r60-r128-all-sw-pl'
run(['python3','scripts/set_rom_identity.py','--id',identity])
gcc=gdk/'bin/m68k-elf-gcc'
libgcc=subprocess.check_output([str(gcc),'-m68000','-print-libgcc-file-name'],text=True).strip()
run(['make',f'GDK={gdk}','PREFIX=m68k-elf-','JAVA=java',
     f'EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 {flags}',f'LIBGCC={libgcc} -lgcc','-j1'])
rom='doom-md-r60-r128-all-sw-pl'
run(['python3','scripts/lab/finish_r35_rom.py','out/rom.bin',str(out/(rom+'.bin'))])
shutil.copy2(work/'out/rom.out',out/(rom+'.elf'))
shutil.copy2(work/'src/rmap_lab_report.json',out/'map-format.json')
print(f'FAST BUILD {args.format}: {time.monotonic()-start:.1f} seconds')
