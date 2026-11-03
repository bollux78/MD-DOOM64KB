#!/usr/bin/env python3
"""R116 demotest (after the R115 dbuf chain): per-map demo tests. TEST ROM ONLY, never a deliverable.

- scripts/lab/r116_add_demos.py appends DTE1M1..DTE1M9 (DSDA UV-Max, v1.9) and the generated
  DTE1M6S special to the converted WAD (build step, needs R116_DEMO_DIR) and writes src/r116_demos.h.
- r116_sel (1..10) replaces DEMO3 in G_DoPlayDemo; the header map is used as recorded (no E1M1/E1M7
  forcing), AI follows the Normal/Low selection from Options.
- r116_nocap (from the table) disables the R115 E1M6 UV->HMP spawn cap: needed by the human E1M6
  UV-Max demo (index 6). The special (index 10) runs with the cap.
- At the first G_DoCompleted the exit stats are stored in r116_res and the demo stops on the next tic
  (results screen on console, R116_Done breakpoint for the BlastEm probe).
  Sync check (UV-Max): exit leveltime == round(DSDA time * 35) +-1, kills == total, secrets == total.
- Zone minimum (total / largest free) sampled every 4 tics in GS_LEVEL.
- r116_norender (probe only) skips D_Display entirely: logic-only playback.
- Menu: Benchmark directly lists Run All Demos in Sequence and 10 individual demos.
All new state is in .data (BSS unchanged).
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


G = 'src/g_game.c'
rep(G, '#include "r81_save.h"\n', '''#include "r81_save.h"
#include "r116_demos.h"
/* R116 demo tests (test ROM). */
#define R116_D __attribute__((section(".data")))
volatile uint8_t r116_sel R116_D = 0;       /* menu/probe selection, 0 = DEMO3 */
volatile uint8_t r116_norender R116_D = 0;  /* probe: skip D_Display */
uint8_t r116_active R116_D = 0, r116_stop R116_D = 0, r116_nocap R116_D = 0;
volatile uint8_t r116_seq_on R116_D = 0, r116_seq_pending R116_D = 0;
uint8_t r116_seq_completed R116_D = 0;
uint16_t r116_seq_min_total R116_D = 0xffffu, r116_seq_min_largest R116_D = 0xffffu;
r116_res_t r116_res R116_D = {-1};
extern uint32_t R115_ZoneTotal(void);
extern uint32_t R115_ZoneLargest(void);
void __attribute__((noipa,noinline)) R116_Done(void){ __asm__ volatile("":::"memory"); }
void __attribute__((noipa,noinline)) R116_End(void){ __asm__ volatile("":::"memory"); }
/* Deferred handoff at the outer game loop, never inside demo decoder. */
void __attribute__((noipa,noinline)) R116_SequenceContinue(void){
    if(!r116_seq_pending)return;
    r116_seq_pending=0;
    r116_active=0;r116_stop=0;r116_nocap=0;
    G_ReloadDefaults(); /* Only clears demo flags; Options remain unchanged. */
    G_DeferedPlayDemo("demo3");
}
static void R116_Zone(void){
    uint32_t t=R115_ZoneTotal(), l=R115_ZoneLargest();
    if(t<r116_res.zmin_total)r116_res.zmin_total=(uint16_t)t;
    if(l<r116_res.zmin_largest)r116_res.zmin_largest=(uint16_t)l;
}
''')
# Selection and header map.
rep(G, '''    ExtractFileBase(defdemoname,basename);           // killough
    basename[8] = 0;''', '''    r116_active=0;r116_nocap=0;
    if(r116_sel>=1 && r116_sel<=R116_DEMO_COUNT){
        const r116_demo_t *d=&r116_demos[r116_sel];
        memset(basename,0,sizeof(basename));
        for(uint8_t i=0;i<8 && d->lump[i];i++)basename[i]=d->lump[i];
        r116_active=r116_sel;r116_nocap=d->nocap;
        memset(&r116_res,0,sizeof(r116_res));
        r116_res.exit_time=-1;r116_res.zmin_total=0xFFFFu;r116_res.zmin_largest=0xFFFFu;r116_res.sel=r116_sel;
        r116_stop=0; /* Keep Options AI mode Normal/Low untouched. */
    }else
    ExtractFileBase(defdemoname,basename);           // killough
    basename[8] = 0;''')
rep(G, '''    /* PERF uses original E1M1 geometry for recorded DEMO3. */
    map = 1;''', '''    /* PERF uses original E1M1 geometry for recorded DEMO3 (R116 tests: as recorded). */
    if(!r116_active) map = 1;''')
rep(G, '    if (_g_timingdemo) map = D_R88_BenchmarkMap();', '    if (_g_timingdemo && !r116_active) map = D_R88_BenchmarkMap();')
rep(G, '    if (*demo_p == DEMOMARKER)\n', '    if (*demo_p == DEMOMARKER || r116_stop)\n')
rep(G, '''static void G_DoCompleted (void)
{
    _g_gameaction = ga_nothing;
''', '''static void G_DoCompleted (void)
{
    _g_gameaction = ga_nothing;
    if(r116_active && r116_res.exit_time<0){
        R116_Zone();
        r116_res.exit_time=_g_leveltime;r116_res.exit_gametic=_g_gametic;
        r116_res.kills=(int16_t)_g_player.killcount;r116_res.tkills=(int16_t)_g_totalkills;
        r116_res.items=(int16_t)_g_player.itemcount;r116_res.titems=(int16_t)_g_totalitems;
        r116_res.secrets=(int16_t)_g_player.secretcount;r116_res.tsecrets=(int16_t)_g_totalsecret;
        r116_res.map=(uint8_t)_g_gamemap;r116_res.secretexit=(uint8_t)(secretexit!=0);
        r116_stop=1;R116_Done();
    }
''')
rep(G, '''static void G_DoReborn(void)
{
''', '''static void G_DoReborn(void)
{
    if(r116_active)r116_res.deaths++;
''')
rep(G, '''    if(_g_player.playerstate == PST_REBORN)
        G_DoReborn ();
''', '''    if(_g_player.playerstate == PST_REBORN)
        G_DoReborn ();
    if(r116_active && _g_gamestate==GS_LEVEL && !(_g_gametic&3)) R116_Zone();
''')
rep(G, '''void G_CheckDemoStatus (void)
{
''', '''void G_CheckDemoStatus (void)
{
    if(r116_seq_pending)return; /* A demo may notify more than once per tic. */
    if(r116_seq_on && r116_active){
        R116_Zone();
        if(r116_res.zmin_total<r116_seq_min_total)r116_seq_min_total=r116_res.zmin_total;
        if(r116_res.zmin_largest<r116_seq_min_largest)r116_seq_min_largest=r116_res.zmin_largest;
        r116_seq_completed++;
        if(r116_seq_completed<R116_DEMO_COUNT){
            r116_sel=(uint8_t)(r116_seq_completed+1);
            r116_seq_pending=1;
            return; /* start next demo at safe outer loop handoff */
        }
    }
    if(r116_active){ r116_res.done=1; R116_End(); }
''')
# After the results (menu benchmark return path and the generic path): leave test mode.
rep(G, '''            G_ReloadDefaults();
            D_R50_BenchmarkRequestReturn();
            return;''', '''            G_ReloadDefaults();
            if(r116_active){r116_active=0;r116_stop=0;r116_nocap=0;}
            r116_seq_on=0;r116_seq_pending=0;r116_seq_completed=0;
            D_R50_BenchmarkRequestReturn();
            return;''')
rep(G, '#include "r116_demos.h"\n', '#include "r116_demos.h"\nextern uint8_t R89_AIMode(void);\nextern void R89_SetAIMode(uint8_t low);\n')

# R116 Run All keeps benchmark FPS counters and uses deferred transitions.
rep(G, '    if (_g_timingdemo) I_BenchmarkReset();',
       '    if (_g_timingdemo && !(r116_seq_on && r116_seq_completed)) I_BenchmarkReset();')
rep(G, 'if(D_R50_BenchmarkReturnPending())return;',
       'if(D_R50_BenchmarkReturnPending() || r116_seq_pending)return;')
rep(G, '    if (!_g_demoplayback && _g_menuactive)',
       '    if (r116_seq_pending)return; /* wait until outer loop handles handoff */\n    if (!_g_demoplayback && _g_menuactive)')

P = 'src/p_setup.c'
rep(P, 'r115_spawnskill=(uint8_t)((map==6 && _g_gameskill>=sk_hard)?sk_medium:_g_gameskill);',
       '{ extern uint8_t r116_nocap; r115_spawnskill=(uint8_t)((map==6 && _g_gameskill>=sk_hard && !r116_nocap)?sk_medium:_g_gameskill); }')

D = 'src/d_main.c'
rep(D, '    if (nodrawers)                    // for comparative timing / profiling\n',
       '    extern volatile uint8_t r116_norender;\n    if (nodrawers || r116_norender)   // for comparative timing / profiling (R116 probe)\n')
rep(D, 'void D_R88_SelectBenchmarkMap(int16_t choice){r88_bench_map=choice==1?7:1;}',
       'extern volatile uint8_t r116_sel;\nvoid D_R88_SelectBenchmarkMap(int16_t choice){r88_bench_map=choice==1?7:1;r116_sel=0;}\n'
       '''void D_R116_SelectDemo(int16_t choice){
    extern volatile uint8_t r116_seq_on, r116_seq_pending;
    extern uint8_t r116_seq_completed;
    extern uint16_t r116_seq_min_total, r116_seq_min_largest;
    r116_seq_on=(choice==0);
    r116_seq_pending=0;r116_seq_completed=0;
    r116_seq_min_total=0xffffu;r116_seq_min_largest=0xffffu;
    r116_sel=(uint8_t)(choice==0?1:choice);
}''')

# After nested G_Ticker returns, switch WAD/demo at the outer loop boundary.
rep(D, '''        if(r50_bench_return_pending)D_R50_BenchmarkFinish();
#endif

#if defined(DOOM_PROFILE)''', '''        if(r50_bench_return_pending)D_R50_BenchmarkFinish();
#endif
        /* Common to PLAY and PERF: safe handoff after G_Ticker has returned. */
        {
            extern volatile uint8_t r116_seq_pending;
            extern void R116_SequenceContinue(void);
            if(r116_seq_pending)R116_SequenceContinue();
        }

#if defined(DOOM_PROFILE)''')

M = 'src/m_text.c'
rep(M, '''static const menuitem_t R88BenchItems[]={
    {1,"E1M1 Hangar",M_R88RunSelected},
    {1,"E1M7 Computer Station",M_R88RunSelected}
};
static const menu_t R88BenchDef={2,R88BenchItems,M_R88DrawBenchmark,6,8,&MainDef,0};''', '''/* Direct Benchmark list: no old DEMO3 benchmarks or demo submenu. */
extern void D_R116_SelectDemo(int16_t choice);
static void M_R116Run(int16_t choice){ D_R116_SelectDemo(choice); M_ClearMenus(); D_R50_BenchmarkStart(); }
static void M_R116Draw(void){V_DrawString(10,2,12,"BENCHMARK");}
static const menuitem_t R88BenchItems[]={
    {1,"Run All Demos in Sequence",M_R116Run},
    {1,"E1M1 UV-Max",M_R116Run},{1,"E1M2 UV-Max",M_R116Run},{1,"E1M3 UV-Max",M_R116Run},
    {1,"E1M4 UV-Max",M_R116Run},{1,"E1M5 UV-Max",M_R116Run},{1,"E1M6 UV-Max no cap",M_R116Run},
    {1,"E1M7 UV-Max",M_R116Run},{1,"E1M8 UV-Max",M_R116Run},{1,"E1M9 UV-Max",M_R116Run},
    {1,"E1M6 Special cap",M_R116Run}
};
static const menu_t R88BenchDef={11,R88BenchItems,M_R116Draw,5,5,&MainDef,0};''')

B = 'src/r22_benchmark.inc'
rep(B, '''    VDP_drawText(D_R88_BenchmarkMap()==7?"DEMO3 E1M7 / NTSC 60HZ":"DEMO3 E1M1 / NTSC 60HZ", 3, 5);''',
       '''    {
        extern uint8_t r116_active;
        if(r116_active) VDP_drawText(R116_Label(), 3, 5);
        else VDP_drawText(D_R88_BenchmarkMap()==7?"DEMO3 E1M7 / NTSC 60HZ":"DEMO3 E1M1 / NTSC 60HZ", 3, 5);
    }''')
rep(B, '''    VDP_drawText("TIME (SECONDS)", 5, 17);
    bench_fixed(buffer, seconds_x100, 2);
    VDP_drawText(buffer, 24, 17);
''', '''    VDP_drawText("TIME (SECONDS)", 5, 17);
    bench_fixed(buffer, seconds_x100, 2);
    VDP_drawText(buffer, 24, 17);
    R116_DrawResults(buffer);
''')
s = Path(B).read_text()
i = s.index('void I_BenchmarkShowResults(void)')
s = s[:i] + '''/* R116 demo test block (rows 19-25). */
#include "r116_demos.h"
static const char * __attribute__((unused)) R116_Label(void){
    extern uint8_t r116_active, r116_seq_completed;
    extern volatile uint8_t r116_seq_on;
    if(r116_seq_on && r116_seq_completed==R116_DEMO_COUNT)
        return "ALL 10 DEMOS / NTSC 60HZ";
    return r116_demos[r116_active].label;
}
static void R116_Pair(char *b, int32_t a, int32_t c){
    char t[16]; bench_u32(b,(uint32_t)(a<0?0:a)); uint16_t n=0; while(b[n])n++;
    b[n++]='/'; bench_u32(t,(uint32_t)(c<0?0:c)); for(uint16_t k=0;t[k];k++)b[n++]=t[k]; b[n]=0;
}
static void __attribute__((unused)) R116_DrawResults(char *buffer){
    extern uint8_t r116_active;
    if(!r116_active)return;
    {
        extern volatile uint8_t r116_seq_on;
        extern uint8_t r116_seq_completed;
        extern uint16_t r116_seq_min_total, r116_seq_min_largest;
        if(r116_seq_on && r116_seq_completed==R116_DEMO_COUNT){
            VDP_drawText("ALL 10 DEMOS FINISHED", 3, 19);
            VDP_drawText("TOTAL DEMOS", 3, 20);
            bench_u32(buffer,r116_seq_completed);VDP_drawText(buffer,23,20);
            VDP_drawText("ZONE MIN TOTAL", 3, 21);
            bench_u32(buffer,r116_seq_min_total);VDP_drawText(buffer,23,21);
            VDP_drawText("ZONE MIN BLOCK", 3, 22);
            bench_u32(buffer,r116_seq_min_largest);VDP_drawText(buffer,23,22);
            VDP_drawText("FPS: ALL MAPS / SETTINGS", 3, 24);
            return;
        }
    }
    const r116_demo_t *d=&r116_demos[r116_active];
    const r116_res_t *r=&r116_res;
    char b[24];
    if(r->exit_time<0) VDP_drawText("EXIT TIC         NO EXIT", 3, 19);
    else { VDP_drawText("EXIT TIC", 3, 19); R116_Pair(b,r->exit_time,d->want); VDP_drawText(b, 20, 19); }
    VDP_drawText("KILLS", 3, 20); R116_Pair(b,r->kills,r->tkills); VDP_drawText(b, 20, 20);
    VDP_drawText("SECRETS", 3, 21); R116_Pair(b,r->secrets,r->tsecrets); VDP_drawText(b, 20, 21);
    VDP_drawText("ZONE MIN FREE", 3, 22); R116_Pair(b,r->zmin_total,r->zmin_largest); VDP_drawText(b, 20, 22);
    VDP_drawText("DEATHS", 3, 23); bench_u32(buffer,r->deaths); VDP_drawText(buffer, 20, 23);
    if(!d->want) VDP_drawText(r->exit_time<0?"SPECIAL: RAN, NO KEY":"SPECIAL: EXITED", 3, 25);
    else {
        /* Gameplay need not match vanilla Doom, no synchronization verdict. */
        VDP_drawText(r->exit_time>=0?"MAP EXITED":"DEMO FINISHED", 3, 25);
    }
}

''' + s[i:]
Path(B).write_text(s)

# Build: inject the demos after the map alignment of the converted WAD.
F = 'scripts/lab/build_r35_linear.fish'
rep(F, '    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n',
       '''    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1
    if not set -q R116_DEMO_DIR
        echo 'R116 demotest needs R116_DEMO_DIR'; exit 2
    end
    python3 scripts/lab/r116_add_demos.py --wad scripts/doom64.wad --dir "$R116_DEMO_DIR" --manifest assets/r116-demos.json --header src/r116_demos.h; or exit 1
''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r115-'" in s and "('dbuf', 1)" in s
p.write_text(s.replace("'r115-'", "'r116-'").replace("('dbuf', 1)", "('demotest', 1)"))
print('R116 demotest')
