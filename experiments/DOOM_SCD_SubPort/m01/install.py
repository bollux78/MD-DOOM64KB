"""M0/M1 changes confined to the disposable realtime build."""
def install(tree,boot):
    p=tree/'src/s2d_md_live.c';s=p.read_text()
    s=s.replace('_g_gametic=expected_tic;','_g_gametic=h[9];')
    s=s.replace('R16(0xA12010UL)=0xD04D;','R16(0xA12012UL)=0;R16(0xA12010UL)=0xD04D;')
    s=s.replace('uint32_t t0=_g_vblankCount;','uint32_t t0=_g_vblankCount;\n        R16(0xA12012UL)=(uint16_t)(expected_tic%65535UL)+1;')
    a=s.index('            SYS_disableInts();',s.index('if(expected_tic){'))
    b=s.index('SYS_enableInts();',a)+len('SYS_enableInts();')
    s=s[:a]+s[b:]
    # Preserve the final DMA fence until M0 measurements establish redundancy.
    s=s.replace('static uint32_t expected_tic;',"""static uint32_t expected_tic;
volatile uint16_t s2f_test_mode __attribute__((section(".data")))=0;
static uint32_t stage_start[2],stage_cost[2];
void __attribute__((noipa,noinline)) S2F_M0FrameDone(void){__asm__ volatile("":::"memory");}
static void frozen_benchmark(void){
    for(uint16_t i=0;i<24;i++){
        _g_gametic++;uint32_t start=_g_vblankCount;
        S2A_Display();uint32_t drawn=_g_vblankCount;R20_StopVideo();
        volatile uint32_t *m=(volatile uint32_t *)0x61B1C0UL;
        m[0]=i;m[1]=stage_cost[0];m[2]=stage_cost[1];
        m[3]=_g_vblankCount-drawn;m[4]=_g_vblankCount-start;
        S2F_M0FrameDone();
    }
    for(;;){}
}
void S2F_ProfileBegin(uint16_t stage){stage_start[stage]=_g_vblankCount;}
void S2F_ProfileEnd(uint16_t stage){stage_cost[stage]=_g_vblankCount-stage_start[stage];}
""")
    s=s.replace('S2D_MDFrameDone();expected_tic++;',"""volatile uint32_t *m=(volatile uint32_t *)0x61B180UL;
        m[0]=stage_cost[0];m[1]=stage_cost[1];m[2]=t5;
        S2D_MDFrameDone();expected_tic++;""")
    s=s.replace('expected_tic=0;stop_sent=0;',"""expected_tic=0;stop_sent=0;
    if(s2f_test_mode==1){extern void G_Ticker(void);G_Ticker();frozen_benchmark();}
    R16(0xA12014UL)=s2f_test_mode==2;
""")
    s=s.replace('if(expected_tic){','if(s2f_test_mode==2)frozen_benchmark();\n        if(expected_tic){')
    p.write_text(s)
    p=tree/'src/d_main.c' ;s=p.read_text()
    s='extern void S2F_ProfileBegin(unsigned short),S2F_ProfileEnd(unsigned short);\n'+s
    anchor='R_RenderPlayerView (&_g_player);'
    assert s.count(anchor)==1
    s=s.replace(anchor,'{S2F_ProfileBegin(0);'+anchor+'S2F_ProfileEnd(0);}')
    p.write_text(s)
    p=tree/'src/r22_video.inc'
    if not p.exists():
        candidates=list(tree.rglob('r22_video.inc'));assert len(candidates)==1;candidates and None
        p=candidates[0]
    s=p.read_text();a=s.index('        R92_ShadowPass(');b=s.index(';',a)+1
    s=s[:a]+'        S2F_ProfileBegin(1);\n'+s[a:b]+'\n        S2F_ProfileEnd(1);'+s[b:]
    s='extern void S2F_ProfileBegin(unsigned short),S2F_ProfileEnd(unsigned short);\n'+s
    p.write_text(s)
    return boot.replace('S2E FAST LIVE SUB LOGIC','M01 REALTIME SUB LOGIC').replace('DELTA WORLD / CHECKED WORD COPIES','35 HZ LOGIC / A USE B FIRE C STRAFE')
