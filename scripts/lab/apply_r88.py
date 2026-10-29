#!/usr/bin/env python3
"""PLAY benchmark map selector. PERF source path remains unchanged."""
from pathlib import Path
import os,subprocess
mode=os.environ['R88_CANDIDATE'];assert mode in ('control','ai')
if mode=='ai':
 sky=Path('src/r_sky.c').read_bytes()
 subprocess.run(['python3','scripts/lab/apply_r87.py'],env={**os.environ,'R87_CANDIDATE':'ai'},check=True)
 Path('src/r_sky.c').write_bytes(sky)
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:90],s.count(a));p.write_text(s.replace(a,b))
patch('src/d_main.c','static boolean r50_bench_from_menu;', '''static boolean r50_bench_from_menu;
static uint8_t r88_bench_map=1;
void D_R88_SelectBenchmarkMap(int16_t choice){r88_bench_map=choice==1?7:1;}
uint8_t D_R88_BenchmarkMap(void){return r88_bench_map;}''')
patch('src/d_main.h','void D_R50_BenchmarkStart(void);','void D_R50_BenchmarkStart(void);\nvoid D_R88_SelectBenchmarkMap(int16_t choice);\nuint8_t D_R88_BenchmarkMap(void);')
patch('src/g_game.c','if (_g_timingdemo) map = 1;','if (_g_timingdemo) map = D_R88_BenchmarkMap();')
patch('src/r22_benchmark.inc','    VDP_drawText("DEMO3 / NTSC 60HZ", 5, 5);','''#if defined(DOOM_R50_PLAY_BENCH)
    extern uint8_t D_R88_BenchmarkMap(void);
    VDP_drawText(D_R88_BenchmarkMap()==7?"DEMO3 E1M7 / NTSC 60HZ":"DEMO3 E1M1 / NTSC 60HZ", 3, 5);
#else
    VDP_drawText("DEMO3 / NTSC 60HZ", 5, 5);
#endif''')
a='''static void M_RunBenchmark(int16_t choice)
{
    UNUSED(choice);
    M_ClearMenus();
    D_R50_BenchmarkStart();
}'''
b='''static void M_R88RunSelected(int16_t choice){
    D_R88_SelectBenchmarkMap(choice);
    M_ClearMenus();D_R50_BenchmarkStart();
}
static void M_R88DrawBenchmark(void){V_DrawString(9,2,12,"BENCHMARK MAP");}
static const menuitem_t R88BenchItems[]={
    {1,"E1M1 Hangar",M_R88RunSelected},
    {1,"E1M7 Computer Station",M_R88RunSelected}
};
static const menu_t R88BenchDef={2,R88BenchItems,M_R88DrawBenchmark,6,8,&MainDef,0};
static void M_RunBenchmark(int16_t choice){
    UNUSED(choice);M_SetupNextMenu(&R88BenchDef);itemOn=0;
}'''
patch('src/m_text.c',a,b)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
if mode=='control':s=s.replace("'r85-'","'r88-'").replace("('all',0)","('control',0)")
else:s=s.replace("'r87-'","'r88-'")
# Deliver only new PLAY ROMs. Existing PERF binaries remain the reference.
s=s.replace("for suffix,mode in (('pf','perf'),('pl','play'))", "for suffix,mode in (('pl','play'),)")
s=s.replace('assert len(records) == 2','assert len(records) == 1')
p.write_text(s)
print('R88',mode,'PLAY-only menu E1M1/E1M7, original sky, PERF retained')
