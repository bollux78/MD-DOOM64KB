"""Install M1.5 transport/application changes after the unchanged M01 profiler."""
import shutil

def install(tree,common,boot):
    for name in ('compact.h',):shutil.copyfile(common/'m15'/name,tree/'src'/name)
    shutil.copyfile(common/'m15/md_actors.c',tree/'src/s2c_md_actors.c')
    p=tree/'src/s2b_md_world.c';p.write_text('#define SCD_M15 1\n'+p.read_text())
    p=tree/'src/s2d_md_live.c';s=p.read_text()
    s=s.replace('#include "live_wire.h"','#include "live_wire.h"\n#include "compact.h"\nextern void M15_PrepareSwap(void);')
    s=s.replace('h[0]!=S2D_MAGIC || h[1]!=S2D_VERSION','h[0]!=M15_MAGIC || h[1]!=3')
    s=s.replace('S2E_Checksum(h,total)!=h[7]', 'M15_Check(h,63)!=h[63] || M15_Check((volatile const uint32_t *)(src+256),(total-256)/4)!=h[7]')
    s=s.replace('boot[3]!=S2D_MARKER','boot[3]!=0x5ABDu')
    s=s.replace('R16(0xA12012UL)=0;R16(0xA12010UL)=0xD04D;', '*(volatile uint16_t *)0x618180UL=0;R16(0xA12012UL)=0;R16(0xA12010UL)=0xD04D;')
    # No work-RAM globals: timing survives the swap on the existing main stack.
    helper='''static uint32_t m15_delta(uint16_t start,uint32_t vb){
        uint32_t raw=(R16(0xA1200CUL)-start)&4095u,estimate=(_g_vblankCount-vb)*542UL;
        if(estimate>raw)raw+=((estimate-raw+2048UL)/4096UL)*4096UL;return raw;
    }
'''
    s=s.replace('void S2D_Run(void){',helper+'void S2D_Run(void){')
    s=s.replace('uint32_t t0=_g_vblankCount;', 'if(initialized)M15_PrepareSwap();\n        uint32_t t0=_g_vblankCount;uint16_t c0=R16(0xA1200CUL);')
    s=s.replace('uint32_t t1=_g_vblankCount;', 'uint32_t wait=m15_delta(c0,t0),t1=_g_vblankCount;uint16_t c1=R16(0xA1200CUL);')
    s=s.replace('uint32_t t2=_g_vblankCount;', 'uint32_t copied=m15_delta(c1,t1),t2=_g_vblankCount;uint16_t c2=R16(0xA1200CUL);')
    s=s.replace('S2B_ApplyFrame(0);uint32_t t3=_g_vblankCount;', 'S2B_ApplyFrame(0);uint32_t world=m15_delta(c2,t2),t3=_g_vblankCount;uint16_t c3=R16(0xA1200CUL);')
    s=s.replace('S2C_ApplyFrame(0);apply_player();uint32_t t4=_g_vblankCount;', 'S2C_ApplyFrame(0);apply_player();uint32_t actors=m15_delta(c3,t3),t4=_g_vblankCount;')
    s=s.replace('S2D_MDFrameDone();expected_tic++;','''volatile uint32_t *latency=(volatile uint32_t *)0x61B280UL;
        latency[0]=wait;latency[1]=copied;latency[2]=world;latency[3]=actors;latency[4]=m15_delta(c0,t0);
        S2D_MDFrameDone();expected_tic++;''')
    p.write_text(s)
    return boot.replace('M01 REALTIME SUB LOGIC','M15 READY STATE / COMPACT ACTORS').replace('0x5AAD','0x5ABD').replace('AI NORMAL','AI NORMAL / M15')
