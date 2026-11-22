from pathlib import Path
import sys,json,struct
rom=Path(sys.argv[1]);manifest=json.loads(Path(sys.argv[2]).read_text());data=bytearray(rom.read_bytes())
if len(data)>0x200000:raise ValueError('Fixed code/UI/music exceeds2MiB: '+str(len(data)))
for entry in manifest:
 b=Path(entry['file']).read_bytes();start=entry['physical'];end=start+len(b)
 if len(data)<end:data.extend(bytes([255])*(end-len(data)))
 data[start:end]=b
pad=(-len(data))%131072;data.extend(bytes([255])*pad)
if len(data)>15*1024*1024:raise ValueError('Exceeds15MiB')
data[0x100:0x110]=b'SEGA SSF        ';struct.pack_into('>I',data,0x1a4,len(data)-1)
struct.pack_into('>H',data,0x18e,sum(struct.unpack('>%dH'%((len(data)-512)//2),data[512:]))&65535)
rom.write_bytes(data);print('SSF ROM bytes',len(data))
