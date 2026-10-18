#!/usr/bin/env python3
"""Reuse production SRAM mock, adding grouped reads/writes and field invariants."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'scripts/lab/test_r25_window.py').read_text()
s=s.replace("'-DDOOM_R25_MUSIC'", "'-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE','-DDOOM_R25_MUSIC'")
needle=' byte in[128],out[128];'
assert needle in s
s=s.replace(needle,''' for(unsigned i=0;i<805;i++){
  side_t *p=(void*)(uintptr_t)(0x220000+i*10);side_t snap;memset(&snap,0xC3,sizeof snap);
  R23_SET(p,textureoffset,-(int)i*11);R23_SET(p,toptexture,i%125);R23_SET(p,bottomtexture,-1);R23_SET(p,midtexture,124-i%125);
  R27_ReadBlock(p,offsetof(side_t,textureoffset),5,(uint8_t*)&snap+offsetof(side_t,textureoffset));
  uint8_t *raw=(uint8_t*)&snap+offsetof(side_t,textureoffset);\n  assert(!bank && snap.sector==0xC3C3C3C3u && (int16_t)((raw[0]<<8)|raw[1])==-(int)i*11);
  assert(snap.toptexture==(int)(i%125) && snap.bottomtexture==-1 && snap.midtexture==(int)(124-i%125));
 }
 for(unsigned i=0;i<1352;i++){
  linedata_t *p=(void*)(uintptr_t)(0x210000+i*8);uint16_t old=i*31,flags=i*17;
  R23_SET(p,validcount,old);R23_SET(p,r_validcount,i);R23_SET(p,r_flags,flags);R23_SET(p,special,-(int)i);
  assert(R27_OrFlags(p,256)==(uint16_t)(flags|256) && !bank);
  assert(R23_MapRead(p,offsetof(linedata_t,r_validcount),4)==((i<<16)|(flags|256)));
  R23_MapWrite(p,offsetof(linedata_t,r_validcount),4,((uint32_t)(uint16_t)(i+1)<<16)|flags);
  assert(!bank && R23_GET(p,validcount)==old && R23_GET(p,special)==-(int)i);
  assert(R23_GET(p,r_validcount)==i+1 && (uint16_t)R23_GET(p,r_flags)==flags);
 }
'''+needle)
# Preserve the repository root used by the reused test.
s=s.replace('ROOT=Path(__file__).resolve().parents[2]', 'ROOT=R')
exec(compile(s,str(R/'scripts/lab/test_r25_window.py'),'exec'),dict(R=R,__file__=__file__))
print('PASS 805 grouped sides / 1352 grouped line updates: signed fields, counters, masks, adjacent fields, mapper state')
