#!/usr/bin/env python3
"""Validate pinned tracks and exercise actual dispatch/play/stop code with an XGM mock."""
from pathlib import Path
import tempfile,subprocess,json,base64,hashlib
from prepare_r25_music import ROOT,decode,validate
payload=json.loads((ROOT/'assets/r25-music.json').read_text())
assert [t['name'] for t in payload['tracks']]==[f'E1M{i}' for i in range(1,10)]+['Intro','Inter','End']
for t in payload['tracks']:
    packed=base64.b64decode(t['zgm'],validate=True);raw=decode(packed);validate(raw)
    assert hashlib.sha256(packed).hexdigest()==t['sha256_zgm']
    assert hashlib.sha256(raw).hexdigest()==t['sha256_vgm']

with tempfile.TemporaryDirectory() as td:
    p=Path(td)
    labels=['e1m'+str(i) for i in range(1,10)]+['intro','inter','victor','silent']
    (p/'genesis.h').write_text('typedef unsigned char u8;\n')
    (p/'sounds.h').write_bytes((ROOT/'src/sounds.h').read_bytes())
    (p/'music.h').write_text(''.join(f'extern const unsigned char bgm_{n}[1];\n' for n in labels))
    (p/'dispatch.c').write_bytes((ROOT/'src/r25_music.c').read_bytes())
    source=(ROOT/'src/i_genesis.c').read_text()
    play=source[source.index('#if defined(DOOM_R25_MUSIC)\n#if defined(DOOM_R29_XGM2)'):source.index('void I_SetMusicVolume')]
    (p/'test.c').write_text('''#include <assert.h>
#include "genesis.h"
#include "sounds.h"
#include "music.h"
typedef int boolean;
static const u8 *current;static int loop,starts,stops,registered;
void XGM_setLoopNumber(int n){loop=n;}
void XGM_startPlay(const u8 *p){current=p;loop=0;starts++;}
void XGM_stopPlay(void){stops++;}
void DMX_RegisterPCM(void){registered++;}
'''+''.join(f'const u8 bgm_{n}[1]={{{i}}};\n' for i,n in enumerate(labels))+play+'''
int main(void){
 const u8 *expected[]={bgm_silent,'''+','.join(f'bgm_e1m{i}' for i in range(1,10))+''',bgm_inter,bgm_intro,bgm_victor,bgm_intro};
 for(int n=1;n<NUMMUSIC;n++){
  I_PlaySong(n,1);assert(current==expected[n] && loop==-1);
  I_PlaySong(n,0);assert(current==expected[n] && loop==0);
  I_StopSong(n);
 }
 I_PlaySong(-1,0);assert(current==bgm_silent);
 I_PlaySong(NUMMUSIC,0);assert(current==bgm_silent);
 assert(registered==starts && stops==NUMMUSIC-1);
 return 0;
}
''')
    subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-I'+str(p),'-DDOOM_R25_MUSIC',str(p/'dispatch.c'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
print('PASS 12 pinned tracks: hashes, EOF, loops, GD3, YM2612/PSG; actual song routing, one-shot/loop, PCM registration and stop')
