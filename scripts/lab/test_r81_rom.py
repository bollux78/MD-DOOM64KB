#!/usr/bin/env python3
"""Invoke real save/load functions on a stopped BlastEm CPU; no ROM patches.
The injected caller uses framebuffer bytes beyond the 512-entry object table.
The CPU stays in this caller, so gameplay never renders over it during the test.
All tests share one emulation capped at 10000 frames; this is not a benchmark.
"""
from pathlib import Path
import argparse,json,struct,time,subprocess,sys
from r64a_rsp_capture import RSP,symbols
p=argparse.ArgumentParser();p.add_argument('--blastem',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--elf',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--case',type=int,nargs=2,metavar=('MAP','SKILL'));a=p.parse_args()
if a.case is None:
 combined={'frames_cap_per_process':10000,'tests':[],'status':'running'}
 cases=a.out.parent/'save-cases';cases.mkdir(parents=True,exist_ok=True)
 try:
  for skill in (0,2,4):
   for map in range(1,10):
    out=cases/f'map{map}-skill{skill}.json'
    subprocess.run([sys.executable,__file__,'--blastem',a.blastem,'--rom',str(a.rom.resolve()),'--elf',str(a.elf.resolve()),'--out',str(out.resolve()),'--case',str(map),str(skill)],check=True)
    case=json.loads(out.read_text());assert case['status']=='passed';combined['tests']+=case['tests']
  combined['status']='passed'
 finally:
  a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(combined,indent=2)+'\n')
 raise SystemExit(0)
sy=symbols(a.elf)
# Use ELF object sizes when writing booleans (GCC/SGDK may choose 1 or 4 bytes).
b=a.elf.read_bytes();sizes={}
shoff=struct.unpack_from('>I',b,32)[0];ents,n=struct.unpack_from('>HH',b,46)
sections=[struct.unpack_from('>10I',b,shoff+i*ents) for i in range(n)]
for h in sections:
 if h[1]!=2:continue
 st=sections[h[6]];names=b[st[4]:st[4]+st[5]]
 for off in range(h[4],h[4]+h[5],h[9]):
  name,value,size=struct.unpack_from('>III',b,off)
  sizes[names[name:].split(b'\0',1)[0].decode()]=size
def sym(name):
 if name in sy:return sy[name]
 match=[v for k,v in sy.items() if k.startswith(name+'.')]
 assert len(match)==1,(name,match)
 return match[0]
g=RSP(a.blastem,a.rom,10000,60);report={'frames_cap':10000,'tests':[],'status':'running'}
def write(addr,data):assert g.req('M%x,%x:%s'%(addr,len(data),data.hex()))=='OK'
def u32(addr):return int.from_bytes(g.readmem(addr,4),'big')
def word(v):return struct.pack('>I',v&0xffffffff)
def string(addr):return g.readmem(addr,80).split(b'\0')[0].decode(errors='replace') if addr else None
def slot():
 write(0xA130F1,b'\x01')
 data=g.readmem(0x200000+26624*2,6144*2)[1::2]
 write(0xA130F1,b'\x00')
 assert data[:4]==b'R81S',data[:16].hex()
 n=int.from_bytes(data[8:10],'big')
 return data[:16+n]
def putslot(off,value):
 call('_QA_WriteByte',0x200001+2*(26624+off),value)
 assert g.readmem(0x200001+2*(26624+off),1)==bytes([value]),'CPU corruption write failed'
try:
 g.req('qSupported');ifu=sym('I_FinishUpdate');err=sym('I_Error')
 assert g.req('Z0,%x,2'%ifu)=='OK';assert g.req('Z0,%x,2'%err)=='OK'
 for _ in range(80):
  g.cont();regs=g.req('g');pc=int(regs[17*8:18*8],16)&0xffffff
  assert pc!=err&0xffffff,'boot I_Error'
  if u32(sym('_g_gametic'))>=8:break
 else:raise AssertionError('No gameplay frame')
 sp=int(regs[15*8:16*8],16);codeaddr=sym('r22_fb')+4+2304;result=codeaddr+116
 # SaveScratch uses only the first 2048 framebuffer bytes for object IDs.
 # The remaining buffer is idle while these calls keep gameplay paused.
 code=bytes.fromhex('48e7fffe')
 loop=len(code);maparg=codeaddr+100;skillarg=codeaddr+104;targetarg=codeaddr+108
 # Read call parameters from RAM on every iteration. Changing immediate
 # operands through RSP does not invalidate BlastEm's translated RAM code.
 code+=bytes.fromhex('13fc000000a130f1') # CPU disables SRAM before ROM calls
 code+=bytes.fromhex('2f39')+word(maparg)+bytes.fromhex('2f39')+word(skillarg)
 code+=bytes.fromhex('2079')+word(targetarg)+bytes.fromhex('4e90')
 code+=bytes.fromhex('508f23c0')+word(result)
 code+=bytes.fromhex('13fc000100a130f1') # CPU enables SRAM for host inspection
 stop=codeaddr+len(code);code+=bytes.fromhex('4e714ef9')+word(codeaddr+loop)
 # SRAM corruption must be a CPU store: RSP writes bypass cartridge handlers.
 helper=codeaddr+200
 writer=bytes.fromhex('13fc000100a130f12079')+word(skillarg)+bytes.fromhex('2039')+word(maparg)+bytes.fromhex('10804e75')
 write(helper,writer);sy['_QA_WriteByte']=helper
 assert len(code)<100
 write(codeaddr,code);write(maparg,word(1));write(skillarg,word(2));write(targetarg,word(sym('G_InitNew')));write(sp,word(codeaddr))
 assert g.req('z0,%x,2'%ifu)=='OK';assert g.req('Z0,%x,2'%stop)=='OK';assert g.req('Z0,%x,2'%(stop&0xffffff))=='OK'
 def call(name,skill=2,map=1):
  write(maparg,word(map));write(skillarg,word(skill));write(targetarg,word(sym(name)))
  g.cont();regs=g.req('g');pc=int(regs[17*8:18*8],16)&0xffffff
  if pc==err&0xffffff:
   s=int(regs[15*8:16*8],16);raise AssertionError('I_Error: '+str(string(u32(s+4))))
  assert pc==stop&0xffffff,(hex(pc),hex(stop))
  return u32(result)
 # The first injected call is G_InitNew at medium E1M1.
 write(sym('_g_demoplayback'),bytes(sizes['_g_demoplayback']));write(sym('_g_timingdemo'),bytes(sizes['_g_timingdemo']))
 for skill in (a.case[1],):
  for map in (a.case[0],):
   call('G_InitNew',skill,map)
   error=string(call('R81_SaveGame'));assert error is None,(map,skill,error)
   before=slot();player=sym('_g_player');mo=u32(player)
   healthoff=int.from_bytes(g.readmem(sym('r81_player_fields')+7*4,2),'big')
   oldhealth=g.readmem(player+healthoff,2);oldx=g.readmem(mo+12,4)
   write(player+healthoff,b'\x00\x21');write(mo+12,word(u32(mo+12)+64*65536))
   sectors=u32(sym('_g_sectors'));oldfloor=g.readmem(sectors,4);write(sectors,word(u32(sectors)+65536))
   error=string(call('R81_LoadGame'));assert error is None,(map,skill,error)
   assert g.readmem(player+healthoff,2)==oldhealth
   assert g.readmem(u32(player)+12,4)==oldx
   assert g.readmem(u32(sym('_g_sectors')),4)==oldfloor
   error=string(call('R81_SaveGame'));assert error is None,(map,skill,error)
   after=slot();assert before==after,(map,skill,'canonical save mismatch',len(before),len(after))
   # Corrupt the payload: load must reject it and retain the live player.
   original=after[16];putslot(16,original^1)
   mo=u32(player);error=string(call('R81_LoadGame'));assert error and 'CORRUPT' in error,error
   assert u32(player)==mo and g.readmem(player+healthoff,2)==oldhealth
   putslot(16,original)
   row={'map':map,'skill':skill,'payload_bytes':len(after)-16,'canonical_roundtrip':True,'corruption_rejected':True}
   report['tests'].append(row);print('PASS',row,flush=True)
 # Exercise private archive adapters with live door/floor/platform thinkers.
 for function,targetkind in ([('EV_DoDoor','T_VerticalDoor'),('EV_DoFloor','T_MoveFloor'),('EV_DoPlat','T_PlatRaise')] if a.case==[1,2] else []):
  call('G_InitNew',2,1)
  ms=u32(sym('_g_mapsectors'));ns=int.from_bytes(g.readmem(sym('_g_numsectors'),2),'big')
  tags={int.from_bytes(g.readmem(ms+i*12+10,2),'big',signed=True) for i in range(ns)}
  lines=u32(sym('_g_maplines'));nl=int.from_bytes(g.readmem(sym('_g_numlines'),2),'big')
  chosen=None;line_tags=[]
  for index in range(nl):
   tag=int.from_bytes(g.readmem(lines+31*index+26,2),'big',signed=True)
   line_tags.append(tag)
   if tag>0 and tag in tags:chosen=(lines+31*index,tag);break
  if not chosen:
   probe={'map':a.case[0],'skill':a.case[1],'numlines':nl,'numsectors':ns,
          'maplines':hex(lines),'mapsectors':hex(ms),
          'sector_tag_sample':sorted(tags)[:20],
          'line_tag_sample':line_tags[:20],
          'positive_line_tags':sorted(set(t for t in line_tags if t>0))[:20],
          'matching_tags':sorted(set(t for t in line_tags if t>0)&tags)[:20],
          'first_line_bytes':g.readmem(lines, min(64,nl*31)).hex() if nl else ''}
   report['map_probe']=probe
   raise AssertionError('No tagged test sector: '+json.dumps(probe))
  assert call(function,chosen[1] if function=='EV_DoFloor' else chosen[0],0),function
  def count_kind():
   cap=sym('_g_thinkerclasscap');th=u32(cap+4);count=0
   for _ in range(1024):
    if th==cap:return count
    if u32(th+8)==sym(targetkind):count+=1
    th=u32(th+4)
   raise AssertionError('Thinker list cycle')
  count=count_kind();assert count>0,function
  assert string(call('R81_SaveGame')) is None;before=slot()
  assert string(call('R81_LoadGame')) is None
  assert count_kind()==count,function
  assert string(call('R81_SaveGame')) is None;after=slot();assert before==after,function
  row={'active_event':function,'thinkers':count,'canonical_roundtrip':True,'payload_bytes':len(after)-16}
  report['tests'].append(row);print('PASS',row,flush=True)
 report['status']='passed'
finally:
 g.close();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed'
