/* Emacs style mode select   -*- C++ -*-
 *-----------------------------------------------------------------------------
 *
 *
 *  PrBoom: a Doom port merged with LxDoom and LSDLDoom
 *  based on BOOM, a modified and improved DOOM engine
 *  Copyright (C) 1999 by
 *  id Software, Chi Hoang, Lee Killough, Jim Flynn, Rand Phares, Ty Halderman
 *  Copyright (C) 1999-2004 by
 *  Jess Haas, Nicolas Kalkhof, Colin Phipps, Florian Schulze
 *  Copyright 2005, 2006 by
 *  Florian Schulze, Colin Phipps, Neil Stevens, Andrey Budko
 *  Copyright 2023-2026 by
 *  Frenkel Smeijers
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 *  02111-1307, USA.
 *
 * DESCRIPTION:
 *  DOOM main program (D_DoomMain) and game loop (D_DoomLoop),
 *  plus functions to
 *  parse command line parameters, configure game parameters (turbo),
 *  and call the startup functions.
 *
 *-----------------------------------------------------------------------------
 */

#include <stdint.h>
#include <strings.h>

#include "doomdef.h"
#include "doomtype.h"
#include "d_player.h"
#include "d_englsh.h"
#include "sounds.h"
#include "z_zone.h"
#include "w_wad.h"
#include "s_sound.h"
#include "v_video.h"
#include "f_finale.h"
#include "f_wipe.h"
#include "m_menu.h"
#include "i_system.h"
#include "i_sound.h"
#include "g_game.h"
#include "hu_stuff.h"
#include "wi_stuff.h"
#include "st_stuff.h"
#include "am_map.h"
#include "p_setup.h"
#include "r_main.h"
#include "d_main.h"
#include "am_map.h"
#include "m_cheat.h"
#include "globdata.h"
#include "r24_romthings.h"
#include "r22_mapdiag.h"

static void D_DoAdvanceDemo(void);
static void D_PageDrawer(void);
static void D_UpdateFPS(void);


// CPhipps - removed wadfiles[] stuff


//jff 1/22/98 parms for disabling music and sound
      boolean nosfxparm   = false;
const boolean nomusicparm = false;   // Genesis: XGM で BGM を鳴らすため有効化（元は true=無音）

const boolean nodrawers = false;


#if defined(DOOM_R54D_COMPENSATED)
uint8_t r54d_steps = 1;
static uint8_t r54d_fraction;
#endif
static int32_t maketic;
#if defined(DOOM_R54_LOGIC_HZ)
uint32_t r54_game_tics;
#define R54_LOGIC_TIME() I_GetGameTime()
#else
#define R54_LOGIC_TIME() I_GetTime()
#endif
#if defined(DOOM_R50_PLAY_BENCH)
/* Shared with D_BuildNewTiccmds so returning from single-tic benchmark can
 * discard the accumulated real-time input backlog deterministically. */
static int32_t r50_lastmadetic;
#endif


static int16_t  pagetic;

static boolean singletics; // debug flag to cancel adaptiveness
static boolean advancedemo;
#if defined(DOOM_R50_PLAY_BENCH)
static boolean r50_bench_from_menu;
static boolean r50_bench_return_pending;
boolean D_R50_IsMenuBenchmark(void) { return r50_bench_from_menu; }
boolean D_R50_BenchmarkReturnPending(void) { return r50_bench_return_pending; }
void D_R50_BenchmarkRequestReturn(void)
{
    /* G_ReadDemoTiccmd/G_Ticker still own the stack. Never transition the
     * game, menu or clocks from the middle of a demo command decode. */
    r50_bench_return_pending=true;
}
void D_R50_BenchmarkStart(void)
{
    if(r50_bench_from_menu)return;
    /* PERF mode advances exactly one Doom gametic per outer iteration.
     * This is required to compare DEMO3 PLAY runs with PERF controls. */
    r50_bench_from_menu=true;
    r50_bench_return_pending=false;
    /* A pending title-screen demo transition must not replace our explicit
     * DEMO3 request on the next game tic. */
    advancedemo=false;
    singletics=true;
    _g_timingdemo=true;
    _g_singledemo=false;
    G_DeferedPlayDemo("demo3");
}
/* Execute ONLY at the outer D_DoomLoop boundary, after the current
 * G_Ticker has returned and the final game tic has been accounted for. */
static void D_R50_BenchmarkFinish(void)
{
    if(!r50_bench_return_pending)return;
    r50_bench_return_pending=false;
    r50_bench_from_menu=false;
    _g_timingdemo=false;
    _g_singledemo=false;
    singletics=false;
    /* Single-tic mode did not call D_BuildNewTiccmds for the full DEMO3.
     * Without resync, ordinary PLAY consumes several minutes of missed
     * input tics before it can respond to Start or navigate the menu. */
    maketic=_g_gametic;
    r50_lastmadetic=R54_LOGIC_TIME();
    /* Don't leave the just-finished demo's GS_LEVEL and its stale view/
     * player state alive while the post-benchmark menu is shown. Set up
     * the title immediately, not via a deferred advance on the next tick. */
    D_StartTitle();
    D_DoAdvanceDemo();
    M_StartControlPanel();
}
#endif
boolean _g_fps_show;

//fps counter stuff
int16_t _g_fps_framerate;


static int16_t titlepicnum;


/*
 * D_PostEvent - Event handling
 *
 * Called by I/O functions when an event is received.
 * Try event handlers for each code area in turn.
 * cph - in the true spirit of the Boom source, let the 
 *  short ciruit operator madness begin!
 */

void D_PostEvent(event_t *ev)
{
#if defined(DOOM_R50_PLAY_BENCH)
    /* The benchmark must be deterministic even if buttons are pressed.
     * The result screen polls the joypad directly after the demo finishes. */
    if(r50_bench_from_menu)return;
#endif
    /* cph - suppress all input events at game start
   * FIXME: This is a lousy kludge */
    if (_g_gametic < 3)
        return;

    if (!M_Responder(ev))
        if (!(_g_gamestate == GS_LEVEL && (C_Responder(ev) || AM_Responder(ev))))
            G_Responder(ev);
}


static void D_BuildNewTiccmds(void)
{
    #if defined(DOOM_R50_PLAY_BENCH)
    int16_t newtics = R54_LOGIC_TIME() - r50_lastmadetic;
    r50_lastmadetic += newtics;
#else
    static int32_t lastmadetic = 0;
    int16_t newtics = R54_LOGIC_TIME() - lastmadetic;
    lastmadetic += newtics;
#endif

    while (newtics--)
    {
        I_StartTic();
        if ((int16_t)(maketic - _g_gametic) > 3)
            break;

        G_BuildTiccmd();
        maketic++;
    }
}


//
// D_Display
//  draw current display, possibly wiping it from the previous
//

gamestate_t wipegamestate = GS_DEMOSCREEN; // wipegamestate can be set to -1 to force a wipe on the next draw

static void D_Display (void)
{
    static gamestate_t oldgamestate = GS_LEVEL;

    if (nodrawers)                    // for comparative timing / profiling
        return;

#if defined(DOOM_R22_PIXEL4)
    extern void R22_BeginFrame(void);
    R22_BeginFrame();
#endif
    // save the current screen if about to wipe
    boolean wipe = (_g_gamestate != wipegamestate);

    if (wipe)
        wipe_StartScreen();

    if (_g_gamestate != GS_LEVEL) { // Not a level
        if (oldgamestate == GS_LEVEL)
            I_SetPalette(0); // cph - use default (basic) palette

        switch (_g_gamestate)
        {
            case GS_INTERMISSION:
                WI_Drawer();
                break;
            case GS_FINALE:
                F_Drawer();
                break;
            case GS_DEMOSCREEN:
                D_PageDrawer();
                break;
            default:
                break;
        }
    }
    else if (_g_gametic != _g_basetic)
    { // In a level

        // Work out if the player view is visible, and if there is a border
        boolean viewactive = (!(automapmode & am_active) || (automapmode & am_overlay));

        // Now do the drawing
        /* R50: menus do not need to redraw the expensive 3D scene.
         * M_Drawer draws its own background and glyphs. Keep game ticking
         * normally: only presentation is skipped, never simulation. */
#if defined(DOOM_R50_MENU_FREEZE)
        if(!_g_menuactive || _g_demoplayback)
#endif
        {
            if (viewactive)
                R_RenderPlayerView (&_g_player);

            if (automapmode & am_active)
                AM_Drawer();

            ST_doPaletteStuff();  // Do red-/gold-shifts from damage/items
#if !defined(DOOM_CLASSIC_TEXT_HUD)
            ST_Drawer();
#endif
            HU_Drawer();
        }
    }

    oldgamestate = wipegamestate = _g_gamestate;

    // menus go directly to the screen
    M_Drawer();          // menu is drawn even on top of everything

    D_BuildNewTiccmds();

    if (wipe)
        // wipe update
        D_Wipe();
    else
        // normal update
        I_FinishUpdate ();              // page flip or blit buffer
}


//? how many ticks to run?
static void TryRunTics (void)
{
    int16_t runtics;
    int32_t entertime = R54_LOGIC_TIME();

    // Wait for tics to run
    while (1)
    {

        D_BuildNewTiccmds();

        runtics = maketic - _g_gametic;
        if (runtics <= 0)
        {
            if ((int16_t)(R54_LOGIC_TIME() - entertime) > 10)
            {
                M_Ticker();
                return;
            }
        }
        else
            break;
    }

    while (runtics-- > 0)
    {

        if (advancedemo)
            D_DoAdvanceDemo ();

        M_Ticker ();
#if defined(DOOM_R54D_COMPENSATED)
        /* Wall-time 35/Hz conversion; exactly 35 simulated tic-units per second.
         * One G_Ticker/P_RunThinkers call per slower scheduling tick, not 2.
         * Demo playback stays at one step because demo inputs are 35-Hz. */
        if (_g_demoplayback) { r54d_steps = 1; r54d_fraction = 0; }
        else {
            r54d_fraction += 35;
            r54d_steps = r54d_fraction / DOOM_R54_LOGIC_HZ;
            r54d_fraction %= DOOM_R54_LOGIC_HZ;
        }
#endif
        G_Ticker ();
        _g_gametic++;
#if defined(DOOM_R54_LOGIC_HZ)
        r54_game_tics++;
#endif
    }
}


//
//  D_DoomLoop()
//
// Not a globally visible function,
//  just included for source reference,
//  called by D_DoomMain, never exits.
// Manages timing and IO,
//  calls all ?_Responder, ?_Ticker, and ?_Drawer,
//  calls I_GetTime and I_StartTic
//
_Noreturn static void D_DoomLoop(void)
{
    for (;;)
    {
        // frame syncronous IO operations
#if defined(DOOM_PROFILE)
        uint32_t profile_start_vb = _g_vblankCount;
#endif
        // process one or more tics
        if (singletics)
        {
#if defined(DOOM_R54D_COMPENSATED)
            /* Timedemo must remain byte-compatible with 35-Hz demo commands. */
            r54d_steps = 1;
            r54d_fraction = 0;
#endif
            I_StartTic ();
            G_BuildTiccmd ();

            if (advancedemo)
                D_DoAdvanceDemo ();

            M_Ticker ();
            G_Ticker ();
#if defined(DOOM_R54_LOGIC_HZ)
            r54_game_tics++;
#endif
            _g_gametic++;
            maketic++;
        }
        else
            TryRunTics (); // will run at least one tic

#if defined(DOOM_R50_PLAY_BENCH)
        /* Safe outer-loop handoff: all nested G_Ticker/G_ReadDemoTiccmd
         * calls have unwound, so screen and menu state can be restored. */
        if(r50_bench_return_pending)D_R50_BenchmarkFinish();
#endif

#if defined(DOOM_PROFILE)
        I_ProfileLogic(_g_vblankCount - profile_start_vb);
        profile_start_vb = _g_vblankCount;
#endif

        // killough 3/16/98: change consoleplayer to displayplayer
        if (_g_player.mo) // cph 2002/08/10
            S_UpdateSounds();// move positional sounds

#if defined SFXDEBUG
        // SFXDEBUG: BGM 無音の裏で約1秒ごとに発砲音を強制発火し、PCM 経路を分離検証する。
        {
            // 内部描画は ~5fps。数ループ毎に 3 つの異なる音を 3 つの doom 論理ch へ同時投入し、
            // PCM ch2..ch4 の同時発音(ミキシング)を検証する。
            static uint16_t sfxdbg_cnt = 0;
            if (++sfxdbg_cnt >= 6)
            {
                sfxdbg_cnt = 0;
                DMX_Play(sfx_pistol, 0);   // CH2
                DMX_Play(sfx_shotgn, 1);   // CH3
                DMX_Play(sfx_barexp, 2);   // CH4
            }
        }
#endif

        // Update display, next frame, with current state.
        D_Display();
#if defined(DOOM_PROFILE)
        I_ProfileRender(_g_vblankCount - profile_start_vb);
#endif

        if(_g_fps_show)
        {
            D_UpdateFPS();
        }
    }
}

static void D_UpdateFPS()
{
    static uint32_t fps_frames = 0;
    static uint32_t fps_timebefore = 0;

    fps_frames++;

    uint32_t timenow = I_GetTime();
    if(timenow >= (fps_timebefore + TICRATE))
    {
        uint32_t tics_elapsed = timenow - fps_timebefore;
        fixed_t f_realfps = FixedApproxDiv((fps_frames*(TICRATE*10)) << FRACBITS, tics_elapsed <<FRACBITS);

        _g_fps_framerate = (f_realfps >> FRACBITS);

        fps_frames = 0;
        fps_timebefore = timenow;
    }
    else if(timenow < fps_timebefore)
    {
        //timer overflow.
        fps_timebefore = timenow;
        fps_frames = 0;
    }
}

//
//  DEMO LOOP
//


//
// D_PageTicker
// Handles timing for warped projection
//
void D_PageTicker(void)
{
#if defined(DOOM_R26_FLOW) && defined(DOOM_R24_EPISODE)
    /* Keep the title visible until Start opens the level selector. */
    return;
#endif
    if (--pagetic < 0)
        D_AdvanceDemo();
}

//
// D_PageDrawer
//

static void D_PageDrawer(void)
{
	V_DrawRawFullScreen(titlepicnum);
}

//
// D_AdvanceDemo
// Called after each demo or intro demosequence finishes
//
void D_AdvanceDemo (void)
{
    advancedemo = true;
}


static void D_DrawTitle1(const char *name)
{
	UNUSED(name);

	S_StartMusic(mus_intro);
	pagetic = (TICRATE * TITLE_DEMO_SECONDS);
}


static struct
{
    void (*func)(const char *);
    const char *name;
}
const demostates[] =
{
    {D_DrawTitle1, NULL},
    {G_DeferedPlayDemo, "demo3"},
    {NULL, NULL},
};

static int16_t  demosequence;

/*
 * This cycles through the demo sequences.
 */

static void D_DoAdvanceDemo(void)
{
    _g_player.playerstate = PST_LIVE;  /* not reborn */
    advancedemo = _g_usergame = false;
    _g_gameaction = ga_nothing;

    pagetic = TICRATE * 11;
    _g_gamestate = GS_DEMOSCREEN;


    if (!demostates[++demosequence].func)
        demosequence = 0;

    demostates[demosequence].func(demostates[demosequence].name);
}

//
// D_StartTitle
//
void D_StartTitle (void)
{
    _g_gameaction = ga_nothing;
    demosequence = -1;
    D_AdvanceDemo();
}


/*
=================
=
= M_CheckParm
=
= Checks for the given parameter in the program's command line arguments
=
= Returns the argument number (1 to argc - 1) or 0 if not present
=
=================
*/

static int myargc;
static const char * const * myargv;

int16_t M_CheckParm(char *check)
{
	for (int16_t i = 1; i < myargc; i++)
		if (!strcasecmp(check, myargv[i]))
			return i;

	return 0;
}


static void D_Init(void)
{
	titlepicnum = W_GetNumForName("TITLEPIC");
}


//
// D_DoomMainSetup
//
// CPhipps - the old contents of D_DoomMain, but moved out of the main
//  line of execution so its stack space can be freed

static void D_DoomMainSetup(void)
{
    // init subsystems
    I_InitKeyboard();

    I_InitTimer();

    I_InitSound();

    printf("Z_Init: Init zone memory allocation daemon.\n");
    Z_Init();

    G_ReloadDefaults();    // killough 3/4/98: set defaults just loaded.

    printf("W_Init: Init WADfiles.\n");
    W_Init(); // CPhipps - handling of wadfiles init changed

    I_InitSound2();

    D_Init();
    F_Init();
    WI_Init();

    printf("M_Init: Init miscellaneous info.\n");
    M_Init();

    printf("R_Init: DOOM refresh daemon - [...................]\n");
    R_Init();

    printf("P_Init: Init Playloop state.\n");
    P_Init();

    S_Init(snd_SfxVolume /* *8 */, snd_MusicVolume /* *8*/ );

    printf("HU_Init: Setting up heads up display.\n");
    HU_Init();

    printf("ST_Init: Init status bar.\n");
    ST_Init();

    G_LoadSettings();

    _g_fps_show = false;

    I_InitGraphics();

    int16_t p = M_CheckParm("-timedemo");
    if (p && p < myargc - 1)
    {
        singletics = true;
        _g_timingdemo = true;            // show stats after quit
        G_DeferedPlayDemo(myargv[p + 1]);
        _g_singledemo = true;            // quit after one demo
    }
    else
    {
#if defined(DOOM_R22_MAP8_DIRECT) || defined(DOOM_R23_MAP2_DIRECT)
        G_DeferedInitNew(sk_medium);
#else
        D_StartTitle();                 // start up intro loop
#if defined(DOOM_R24_EPISODE) && !defined(DOOM_R26_FLOW)
        M_R24OpenLevels();
#endif
#endif
    }
}

//
// D_DoomMain
//

void D_DoomMain(int argc, const char * const * argv)
{
    myargc = argc;
    myargv = argv;

    D_DoomMainSetup();

    D_DoomLoop ();  // never returns
}

#if defined(DOOM_R23_CPU_PROBE)
__attribute__((used,externally_visible)) void R23_ProbeMain(void){
    *(volatile uint16_t*)0xA00000=0;
    Z_Init();W_Init();R_Init();P_Init();S_Init(8,8);
    _g_gameskill=sk_medium;
#if defined(DOOM_R24_EPISODE)
    const int16_t maps[]={1,2,3,4,5,6,7,8,9,1,2,3,4,5,6,7,8,9};
    uint16_t loads=18;
#else
    const int16_t maps[]={1,2,8,2};uint16_t loads=4;
#endif
    for(uint16_t i=0;i<loads;i++){
#if defined(DOOM_R24_EPISODE)
        if(i>=9)_g_gameskill=sk_hard;
#else
        if(i==3)_g_gameskill=sk_hard;
#endif
        _g_gamemap=maps[i];_g_player.playerstate=PST_REBORN;
        P_SetupLevel(maps[i]);
#if defined(DOOM_R24_EPISODE)
        R24_ValidateThings();
#endif
#if defined(DOOM_R27_RENDER_PROBE)
        extern uint32_t R27_FrameHash(void);
        _g_player.viewz=_g_player.mo->z+_g_player.viewheight;
        for(uint16_t frame=0;frame<2;frame++){
            _g_gametic++;
            *(volatile uint16_t*)0xA00000=0;
            R_RenderPlayerView(&_g_player);
            *(volatile uint16_t*)0xA00002=0x7000+i*2+frame;
            uint32_t hash=R27_FrameHash();
            *(volatile uint16_t*)0xA00002=hash>>16;
            *(volatile uint16_t*)0xA00002=hash;
            _g_player.mo->angle+=ANG90;
        }
#endif
        if(1){
            mobj_t *effects[10];
            for(uint16_t j=0;j<10;j++)effects[j]=P_SpawnMobj(_g_player.mo->x,_g_player.mo->y,ONFLOORZ,MT_PUFF);
            for(uint16_t j=0;j<10;j++)P_RemoveMobj(effects[j]);
        }
        Z_CheckHeap();
        *(volatile uint16_t*)0xA00002=maps[i];
        *(volatile uint16_t*)0xA00002=r22_map_trace[(r22_map_head+15)&15].free;
        *(volatile uint16_t*)0xA00002=r22_map_trace[(r22_map_head+15)&15].largest;
    }
    *(volatile uint16_t*)0xA00002=0;
    *(volatile uint16_t*)0xA00004=0;for(;;){}
}
#endif
