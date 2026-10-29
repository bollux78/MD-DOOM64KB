#!/usr/bin/env python3
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
def fn(s,name):
 a=s.index(name);i=s.index('{',a);j=i+1;n=1
 while n:n+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)/'work';shutil.copytree(ROOT,d,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for f,env in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'}),('apply_r88.py',{'R88_CANDIDATE':'ai'}),('apply_r89.py',{})]:
  subprocess.run(['python3','scripts/lab/'+f],cwd=d,env={**os.environ,**env},check=True,stdout=subprocess.DEVNULL)
 s=(d/'src/p_enemy2.c').read_text();m=(d/'src/m_text.c').read_text()
 c=Path(tmp)/'ai.c';c.write_text('''#include <stdint.h>
#include <assert.h>
#define FRACUNIT 65536
typedef struct {int32_t x,y;int type;} mobj_t;
static struct {mobj_t *mo;} _g_player;static uint32_t _g_leveltime;
static uint8_t r89_ai_low=1;
'''+fn(s,'uint8_t R89_AIMode(')+fn(s,'void R89_SetAIMode(')+fn(s,'static int R87_DeferDecision(')+fn(m,'static void M_R89ChangeAI(')+'''int main(void){mobj_t p={0},a={.x=513*FRACUNIT};_g_player.mo=&p;
assert(R89_AIMode()==1);
for(int t=0;t<16;t++){_g_leveltime=t;assert(R87_DeferDecision(&a)==((t&3)!=0));}
M_R89ChangeAI(0);assert(!R89_AIMode());for(int t=0;t<16;t++){_g_leveltime=t;assert(!R87_DeferDecision(&a));}
M_R89ChangeAI(1);assert(R89_AIMode());a.x=512*FRACUNIT;for(int t=0;t<16;t++){_g_leveltime=t;assert(!R87_DeferDecision(&a));}
for(int i=0;i<100;i++){uint8_t prev=R89_AIMode();M_R89ChangeAI(i&1);assert(R89_AIMode()!=prev);}return 0;}''')
 subprocess.run(['cc','-O2',str(c),'-o',str(Path(tmp)/'ai')],check=True);subprocess.run([str(Path(tmp)/'ai')],check=True)
 assert '  ai_mode,' in m and '{2,"AI mode:",     M_R89ChangeAI}' in m
 assert '"Low   ":"Normal"' in m
 b=(d/'scripts/lab/build_r71a12mul_hud.py').read_text();assert "(('pl','play'),)" in b
 assert 'AI MODE: LOW' in (d/'src/r22_benchmark.inc').read_text()
 print('PASS actual C menu toggling, Low default, Normal disables defer, Low near/distant cadence, PLAY-only builder and result label')
