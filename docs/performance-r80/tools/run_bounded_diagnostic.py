#!/usr/bin/env python3
"""Opt-in partial diagnostic, never more than 10,000 emulated frames."""
import argparse,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--blastem',required=True)
 p.add_argument('--mode',choices=('profile','capture'),default='profile')
 p.add_argument('--frames',type=int,default=8000)
 p.add_argument('--out',type=pathlib.Path,required=True)
 p.add_argument('--rom',type=pathlib.Path,default=ROOT/'control-build/doom-md-r60-r79-base-pf.bin')
 p.add_argument('--elf',type=pathlib.Path,default=ROOT/'control-build/doom-md-r60-r79-base-pf.elf')
 a=p.parse_args()
 if not 1<=a.frames<=10000:p.error('--frames must be between 1 and 10000')
 if not a.rom.is_file() or not a.elf.is_file():p.error('ROM or ELF missing')
 scripts=ROOT.parents[1]/'scripts/lab'
 script=scripts/('r71_pcsample.py' if a.mode=='profile' else 'r70_capture.py')
 cmd=[sys.executable,str(script),'--blastem',a.blastem,'--rom',str(a.rom.resolve()),'--elf',str(a.elf.resolve()),'--out',str(a.out.resolve()),'--label','R79-base-partial-'+a.mode,'--max-emulated-frames',str(a.frames),'--timeout','60']
 if a.mode=='profile':cmd+=['--max-samples','20000','--max-seconds','600']
 print('Partial diagnostic only; not a complete DEMO3 benchmark.',flush=True)
 return subprocess.run(cmd,check=False).returncode
if __name__=='__main__':raise SystemExit(main())
