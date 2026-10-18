#!/usr/bin/env python3
"""Load target ELF ROM/RAM sections in the existing Musashi CPU harness."""
import argparse,struct,subprocess,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('elf',type=Path);p.add_argument('--harness',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.elf.read_bytes()
assert b[:6]==b'\x7fELF\x01\x02'
shoff=struct.unpack_from('>I',b,32)[0];sz,n=struct.unpack_from('>HH',b,46);headers=[struct.unpack_from('>10I',b,shoff+i*sz) for i in range(n)];memory=bytearray(0x1000000);symbols={}
for h in headers:
 if h[2]&2 and h[1]!=8:
  address=h[3]&0xffffff;assert address+h[5]<=len(memory);memory[address:address+h[5]]=b[h[4]:h[4]+h[5]]
 if h[1]==2:
  st=headers[h[6]];strings=b[st[4]:st[4]+st[5]]
  for off in range(h[4],h[4]+h[5],h[9]):
   name,value,size=struct.unpack_from('>III',b,off);symbols[strings[name:].split(b'\0',1)[0].decode()]=(value,size)
assert 'R23_ProbeMain' in symbols
struct.pack_into('>II',memory,0,0xE0FFF5FC,symbols['R23_ProbeMain'][0]);a.out.mkdir(parents=True,exist_ok=True);flat=a.out/'probe.bin';flat.write_bytes(memory);dump=a.out/'memory.bin'
r=subprocess.run([str(a.harness.resolve()),str(flat),str(dump)],capture_output=True,text=True);report=dict(returncode=r.returncode,output=r.stdout,stderr=r.stderr,symbols={})
if dump.exists():
 data=dump.read_bytes()
 for name in ['r24_cpu_error','r22_map_stage','r22_map_current','r22_map_request','r22_map_need','r22_map_failed_stage','_g_numsectors','_g_numlines','_g_thingPoolSize','r22_map_head','r22_map_count','r22_map_trace']:
  if name in symbols:
   addr,size=symbols[name];raw=data[addr&0xffffff:(addr&0xffffff)+size];report['symbols'][name]=int.from_bytes(raw,'big') if size<=4 else raw.hex()
 if report['symbols'].get('r24_cpu_error'):
  addr=report['symbols']['r24_cpu_error']&0xffffff;report['error']=data[addr:addr+160].split(b'\0',1)[0].decode(errors='replace')
(a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert r.returncode==0 and 'tag 0 cycles' in r.stdout,'CPU loader did not complete all map loads'
