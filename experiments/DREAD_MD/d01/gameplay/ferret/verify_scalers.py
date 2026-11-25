"""Verify the *linked 68000 machine code* before accepting a Ferret ROM."""
from pathlib import Path
import sys,subprocess,struct,json
rom=Path(sys.argv[1]).read_bytes();elf=Path(sys.argv[2]);nm=sys.argv[3]
symbols={}
for line in subprocess.check_output([nm,str(elf)],text=True).splitlines():
 p=line.split()
 if len(p)==3:symbols[p[2]]=int(p[0],16)
base=symbols['ferret_scalers_byte'];targets=struct.unpack_from('>2048I',rom,base);unique=set(targets)
for address in unique:
 for y in range(72):
  pc=address+y*12;move,source,destination,dbra,displacement,ret=struct.unpack_from('>6H',rom,pc)
  displacement=displacement-65536 if displacement&32768 else displacement
  assert move==0x1169 and destination==y*4,(hex(pc),'MOVE/destination')
  assert dbra==0x51ce and ret==0x4e75,(hex(pc),'DBRA/RTS')
  # DBRA displacement is relative to its extension-word address, not its end.
  assert pc+8+displacement==pc+12,(hex(pc),'DBRA must skip the early RTS',displacement)
 assert struct.unpack_from('>H',rom,address+72*12)[0]==0x4e75
print(json.dumps({'selectors':len(targets),'kernels':len(unique),'rows_verified':len(unique)*72,'machine_code':'68000 MOVE/DBRA/RTS verified'}))
