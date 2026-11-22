from pathlib import Path
import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--objdump',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
ranges=[('transfer-direct',0x7e368,0x7e3ea),('transfer-ram',0x7e3ea,0x7e446),('framebuffer-init',0x7e0c6,0x7e0f6),('visible-list',0x77402,0x77576),('projection',0x770b6,0x77402),('wall-column-example',0x6ff16,0x6ff80),('sprite-example',0x6f6e6,0x6f7ac),('dispatch',0x86c70,0x86c8c),('sram-detection',0x81cc0,0x81e26)]
for name,start,end in ranges:
 s=subprocess.check_output([a.objdump,'-D','-b','binary','-m','m68k:68000',f'--start-address={start}',f'--stop-address={end}',str(a.rom)],text=True);(a.out/(name+'.txt')).write_text(s)
