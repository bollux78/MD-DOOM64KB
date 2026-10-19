/*-----------------------------------------------------------------------------
 *
 *  Sega Genesis / Mega Drive implementation of i_system.h
 *  (Doom64KB の i_neogeo.c をベースに ngdevkit -> SGDK へ置換)
 *
 *  Copyright (C) 2026 Frenkel Smeijers
 *  GPL v2 or later.
 *-----------------------------------------------------------------------------*/

#include <stddef.h>
#include <stdint.h>
#include <genesis.h>

#include "doomdef.h"
#include "doomtype.h"
#include "compiler.h"
#include "d_main.h"
#include "i_system.h"
#if defined PLAYTEST
#include "g_game.h"
#endif

#include "globdata.h"
#include "r39e_audio.h"
#if defined(DOOM_R39E_AUDIO_TOGGLES) && !defined(DOOM_R29_XGM2)
#error R39e independent music/PCM toggles require XGM2
#endif
#include "r21_textscreen.h"
#include "r20_stackguard.h"
#include "r20_dma.h"
#include "r22_mapdiag.h"
#include "music.h"        // rescomp 生成: const u8 bgm_e1m1[]（res/music.res）


void I_InitGraphicsHardwareSpecificCode(void);
void I_ShutdownGraphics(void);

// XGM の毎フレーム同期は SGDK の VInt ISR(boot/sega.s)が PROCESS_XGM_TASK フラグを見て
// 自動で行う（XGM_startPlay がフラグを立てる）。ここで手動に XGM_doVBlankProcess を呼ぶと
// 二重駆動になり曲が倍速になるため呼ばない。


static boolean isGraphicsModeSet = false;


//**************************************************************************************
//
// Screen
//

void I_InitGraphics(void)
{
	I_InitGraphicsHardwareSpecificCode();
	isGraphicsModeSet = true;
}


//**************************************************************************************
//
// Keyboard / joypad
//

static boolean isKeyboardIsrSet = false;


void I_InitKeyboard(void)
{
	JOY_init();
	isKeyboardIsrSet = true;
}


static void I_PostEvent(boolean keyup, int16_t data1)
{
	event_t ev;
	ev.type  = keyup ? ev_keyup : ev_keydown;
	ev.data1 = data1;
	D_PostEvent(&ev);
}


// Genesis ボタン -> Doom KEYD_* の対応表（Doom 32X 風）。
//   方向キー : 前後移動 / 旋回（C 押下中は左右が横歩き=strafe になる）
//   A        : KEYD_A  (Use/ドア開閉 / ダッシュ / メニュー決定。A+C=武器送り上, A+X=下)
//   B        : KEYD_B  (Fire)
//   C        : KEYD_R  (Strafe 修飾キー。単押しでは動かない。C+左右で横歩き)
//   X / Z    : KEYD_L  (Strafe 修飾キー / 6ボタン時。X/Z+左右で横歩き)
//   Start    : KEYD_START (Menu 開閉 / 戻る)
typedef struct { uint16_t mask; int16_t key; } joymap_t;

static const joymap_t joymap[] = {
	{ BUTTON_UP,    KEYD_UP    },
	{ BUTTON_DOWN,  KEYD_DOWN  },
	{ BUTTON_LEFT,  KEYD_LEFT  },
	{ BUTTON_RIGHT, KEYD_RIGHT },
	{ BUTTON_A,     KEYD_A     },
	{ BUTTON_B,     KEYD_B     },
	{ BUTTON_C,     KEYD_R     },
	{ BUTTON_X,     KEYD_L     },
	{ BUTTON_Z,     KEYD_L     },
	{ BUTTON_START, KEYD_START },
};
#define NJOYMAP (sizeof(joymap)/sizeof(joymap[0]))


void I_StartTic(void)
{
#if defined MENU_TEST
	// 検証用: START でメニューを開き、A で "New Game" を選択して進む様子を自動再現
	static uint16_t bootframes = 0;
	if (bootframes < 400)
	{
		bootframes++;
		if (bootframes == 120) I_PostEvent(false, KEYD_START); // メニューを開く
		if (bootframes == 124) I_PostEvent(true,  KEYD_START);
		if (bootframes == 200) I_PostEvent(false, KEYD_A);     // New Game 決定
		if (bootframes == 204) I_PostEvent(true,  KEYD_A);
		if (bootframes == 280) I_PostEvent(false, KEYD_A);     // 難易度決定（あれば）
		if (bootframes == 284) I_PostEvent(true,  KEYD_A);
		if (bootframes == 360) I_PostEvent(false, KEYD_UP);    // 前進（押しっぱ＝離さない）
	}
#endif
#if defined PLAYTEST
	// 検証用: メニュー経路を経ずに E1M1 を直接開始する
	static uint16_t pf = 0;
	if (++pf == 30) G_DeferedInitNew(sk_medium);
#endif
	// SGDK のジョイパッド状態更新。SYS_doVBlankProcess() の中でしか呼ばれないため、
	// VDP_waitVSync() しか使わない本ループでは毎 tic ここで明示的に更新する。
	// これを呼ばないと JOY_readJoypad() が常に無入力を返し、実機の操作が一切効かない。
	JOY_update();

	static uint16_t prev = 0;
	uint16_t cur = JOY_readJoypad(JOY_1);
	uint16_t diff = cur ^ prev;
	prev = cur;

	for (uint16_t i = 0; i < NJOYMAP; i++)
	{
		if (diff & joymap[i].mask)
			I_PostEvent((cur & joymap[i].mask) == 0, joymap[i].key);
	}
}


//**************************************************************************************
//
// Audio : SFX を XGM(classic) ドライバの PCM 機能で再生する。
// データは gen_sfx.h（scripts/gen_sfx.py が doom1.wad から生成、8bit符号付き/14kHz/256整列）。
//

#include "gen_sfx.h"

// 各 SFX を XGM ドライバの PCM サンプル表へ登録（PCM id = 基点 + sfxenum）。
// XGM ドライバのロード(= Z80 RAM リセット)後でないと表が消えるため、
// DMX_Init と各 XGM_startPlay 直後の両方から呼ぶ。
#if !defined(DOOM_R29_XGM2)
static void DMX_RegisterPCM(void)
{
	for (uint16_t i = 1; i <= GENSFX_COUNT; i++)
		XGM_setPCM(GENSFX_PCM_ID_BASE + i, gensfx[i].data, gensfx[i].len);
}
#endif

#if defined(DOOM_R39E_AUDIO_TOGGLES)
/* Audio toggles do not modify Doom's music state or demo timing.
 * Music pause/resume affects only the XGM2 song, not PCM SFX channels.
 * OFF/ON survives music track and level changes, but resets on boot. */
static uint16_t r39e_music_enabled = 1;
static uint16_t r39e_sfx_enabled = 1;
static uint16_t r39e_song_active;

uint16_t R39E_MusicEnabled(void) { return r39e_music_enabled; }
uint16_t R39E_SfxEnabled(void) { return r39e_sfx_enabled; }

void R39E_SetMusicEnabled(uint16_t enabled)
{
    enabled = enabled != 0;
    if (enabled == r39e_music_enabled) return;
    r39e_music_enabled = enabled;
    if (!r39e_song_active) return;
    if (enabled) XGM2_resume();
    else XGM2_pause();
}
void R39E_SetSfxEnabled(uint16_t enabled)
{
    enabled = enabled != 0;
    if (enabled == r39e_sfx_enabled) return;
    r39e_sfx_enabled = enabled;
    if (!enabled) {
        /* Stop already-playing Doom effects immediately. Channel 1 remains
         * reserved for soundtrack PCM; it must not be interrupted here. */
        XGM2_stopPCM(SOUND_PCM_CH2);
        XGM2_stopPCM(SOUND_PCM_CH3);
    }
}
#endif

void DMX_Init(void)
{
	// XGM ドライバを明示ロードしてから PCM を登録する。
	// 遅延ロード任せだと、後続の XGM_startPlay がドライバをロードする際に
	// Z80 RAM ごとリセットされ、先に登録した PCM サンプル表が消えて SFX が無音になる。
#if defined(DOOM_R29_XGM2)
	XGM2_loadDriver(TRUE);
#else
	XGM_loadDriver(TRUE);
	DMX_RegisterPCM();
#endif
}

void DMX_Init2(void)         { }

void DMX_Play(sfxenum_t id, int16_t channel)
{
	if (id <= sfx_None || id > GENSFX_COUNT)
		return;
#if defined(DOOM_R39E_AUDIO_TOGGLES)
    if (!r39e_sfx_enabled) return;
#endif
#if defined(DOOM_R29_XGM2)
	/* Music may use channel 1; only channels 2 and 3 available for SFX. */
	SoundPCMChannel pcmch = (channel & 1) ? SOUND_PCM_CH3 : SOUND_PCM_CH2;
	XGM2_playPCMEx(gensfx[id].data, gensfx[id].len, pcmch,
	                 gensfx[id].prio,
#if defined(DOOM_R31_SFX)
	                 gensfx[id].half_rate != 0,
#else
	                 FALSE,
#endif
	                 FALSE);
#else
	// classic XGM は ch を CH1..CH4 で明示指定する(CH_AUTO は XGM2 専用で無効)。
	// doom 論理ch(0..2)を PCM ch2..ch4 に対応させ最大3音同時(ch1は音楽用に温存)。
	SoundPCMChannel pcmch = (SoundPCMChannel)(SOUND_PCM_CH2 + channel);
	XGM_startPlayPCM(GENSFX_PCM_ID_BASE + id, gensfx[id].prio, pcmch);
#endif
}

void DMX_Shutdown(void)      { }
// I_ShutdownSound は i_audio.c が定義する


//**************************************************************************************
//
// Music: R25 routes Doom music IDs to the matching Episode 1 / screen track.
// Legacy builds retain their original single-track baseline.
//

#if defined(DOOM_R25_MUSIC)
#if defined(DOOM_R29_XGM2) && defined(DOOM_R29_MULTI)
extern const u8 r25_track_indices[NUMMUSIC];
#else
extern const u8 *const r25_tracks[NUMMUSIC];
#endif
#endif
void I_PlaySong(musicenum_t handle, boolean looping)
{
	(void)handle;
#if defined(DOOM_R29_XGM2)
	XGM2_setLoopNumber(looping ? -1 : 0);
#else
	XGM_setLoopNumber(looping ? -1 : 0);   // -1 = 無限ループ
#endif
#if defined SFXDEBUG
	// SFXDEBUG: 無音VGM(bgm_silent)を XGM で再生する。FM/PSG は無音だが XGM ドライバは
	// 正常に駆動される(PROCESS_XGM_TASK が立ち毎フレーム処理が回る)ので、PCM/SFX を
	// 実条件のまま BGM 音から分離して検証できる。
#if defined(DOOM_R29_XGM2) && defined(DOOM_R29_MULTI)
	static bool sfxdebug_multi_loaded = FALSE;
	if (!sfxdebug_multi_loaded) { XGM2_load(bgm_episode); sfxdebug_multi_loaded = TRUE; }
	XGM2_playTrack(12);
#elif defined(DOOM_R29_XGM2)
	XGM2_play(bgm_silent);
#else
	XGM_startPlay(bgm_silent);
	DMX_RegisterPCM();
#endif
#else
#if defined(DOOM_R25_MUSIC)
#if defined(DOOM_R29_XGM2) && defined(DOOM_R29_MULTI)
    static bool episode_loaded = FALSE;
    if (!episode_loaded) { XGM2_load(bgm_episode); episode_loaded = TRUE; }
    XGM2_playTrack((handle>mus_None && handle<NUMMUSIC)?r25_track_indices[handle]:12);
    XGM2_setLoopNumber(looping ? -1 : 0);
#elif defined(DOOM_R29_XGM2)
    const u8 *song=(handle>mus_None && handle<NUMMUSIC)?r25_tracks[handle]:bgm_silent;
    XGM2_play(song);
    XGM2_setLoopNumber(looping ? -1 : 0);
#else
    const u8 *song=(handle>mus_None && handle<NUMMUSIC)?r25_tracks[handle]:bgm_silent;
    XGM_startPlay(song);
    XGM_setLoopNumber(looping ? -1 : 0);
#endif
#else
#if defined(DOOM_R29_XGM2)
	XGM2_play(bgm_e1m1);
#else
	XGM_startPlay(bgm_e1m1);               // VInt ISR が以降自動で XGM を 60Hz 前進させる
#endif
#endif
	// XGM_startPlay がドライバを(再)ロードした場合に備え、PCM サンプル表を再登録する。
#if !defined(DOOM_R29_XGM2)
	DMX_RegisterPCM();
#endif
#endif
#if defined(DOOM_R39E_AUDIO_TOGGLES)
    /* Even after title/level transitions, Music OFF must remain muted. */
    r39e_song_active = 1;
    if (!r39e_music_enabled) XGM2_pause();
#endif
}

void I_StopSong(musicenum_t handle)
{
	(void)handle;
#if defined(DOOM_R39E_AUDIO_TOGGLES)
    r39e_song_active = 0;
#endif
#if defined(DOOM_R25_MUSIC)
#if defined(DOOM_R29_XGM2)
    XGM2_stop();
#else
    XGM_stopPlay();
#endif
#endif
}

void I_SetMusicVolume(int16_t volume)
{
	(void)volume;   // XGM クラシックは全体音量制御を持たない
}


//**************************************************************************************
//
// Timer : 1/35 秒 tic を返す（VBlank 60Hz を数える）
//

static volatile int32_t ticcount;
static boolean isTimerSet;

// VBlank の総数（実時間の基準・60Hz）。デバッグ表示(i_genesisv.c)が参照する。
volatile uint32_t _g_vblankCount;
#if defined(DOOM_ROUTINE_PROFILE)
volatile uint16_t doom_profile_stage;
volatile uint32_t doom_profile_samples[11];
void I_ProfileSampleReset(void)
{
    for (uint16_t j = 0; j < 11; j++) doom_profile_samples[j] = 0;
    doom_profile_stage = 0;
}
#endif

#if defined(DOOM_R38_TIME_PROFILE)
/* Observe which routine was interrupted by each 60 Hz VBlank, rather than
 * inferring time from geometry counts. This is a statistical wall-time
 * estimate; it does not resolve individual CPU cycles. Only 48 B of data.
 * Live gameplay freezes the 10-second (600-sample) window until a camera
 * turn or player movement. Timedemo accumulates the full DEMO3. */
volatile uint16_t doom_profile_stage;
volatile uint32_t doom_profile_samples[11];
volatile uint32_t r38_sample_total;
static volatile uint16_t r38_active;

void R38_ResetSamples(void)
{
    uint16_t saved;
    __asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr"
                     : "=d"(saved) : : "cc","memory");
    r38_active = 0;
    for (uint16_t i=0; i<11; ++i) doom_profile_samples[i] = 0;
    r38_sample_total = 0;
    doom_profile_stage = 0;
    __asm__ volatile("move.w %0,%%sr" : : "d"(saved) : "cc","memory");
}

void R38_BeginView(int32_t x, int32_t y, uint32_t angle)
{
#if !defined(TIMEDEMO)
    static uint8_t have_view;
    static int32_t last_x, last_y;
    static uint32_t last_angle;
    if (!have_view || last_x != x || last_y != y || last_angle != angle)
    {
        have_view = 1;
        last_x = x;
        last_y = y;
        last_angle = angle;
        R38_ResetSamples();
    }
#else
    (void)x; (void)y; (void)angle;
#endif
    r38_active = 1;
}
#endif


static void I_VBlankCallback(void)
{
	ticcount++;
	_g_vblankCount++;
    R20_VBlankVideo();
#if defined(DOOM_R20_STACKGUARD)
    R20_PROBE();
#endif
#if defined(DOOM_ROUTINE_PROFILE)
    if (doom_profile_stage < 11) doom_profile_samples[doom_profile_stage]++;
#elif defined(DOOM_R38_TIME_PROFILE)
    if (r38_active)
    {
#if !defined(TIMEDEMO)
        /* 600 VBlanks = 10 seconds at NTSC 60Hz; freeze until next turn. */
        if (r38_sample_total < 600u)
#endif
        {
            uint16_t stage = doom_profile_stage;
            if (stage < 11u)
            {
                ++doom_profile_samples[stage];
                ++r38_sample_total;
            }
        }
    }
#endif
}


int32_t I_GetTime(void)
{
	return ticcount * TICRATE / 60;
}


void I_InitTimer(void)
{
	SYS_setVIntCallback(I_VBlankCallback);
	isTimerSet = true;
}


static void I_ShutdownTimer(void)
{
	SYS_setVIntCallback(NULL);
}


//**************************************************************************************
//
// Memory : Doom の zone ヒープ。Genesis は RAM 64KB なので SGDK 使用分を除いた静的配列。
//

// 調整可能。リンク時 RAM 使用量を見て増減する。
#ifndef HEAP_SIZE
#if defined(DOOM_R23_MAPMEM)
#define HEAP_SIZE (43 * 1024 + 2176) /* 1920 freed cache bytes + 256 SGDK margin. */
#else
#define HEAP_SIZE (43 * 1024)
#endif
#endif


uint8_t __far* I_ZoneBase(uint32_t *heapSize)
{
	static uint8_t heap[HEAP_SIZE];
	uint32_t paragraphs = HEAP_SIZE / PARAGRAPH_SIZE;
	uint8_t *ptr = heap;

	uint32_t m = (uint32_t) ptr;
	if ((m & (PARAGRAPH_SIZE - 1)) != 0)
	{
		paragraphs--;
		while ((m & (PARAGRAPH_SIZE - 1)) != 0)
			m = (uint32_t) ++ptr;
	}

	*heapSize = paragraphs * PARAGRAPH_SIZE;
	return ptr;
}


//**************************************************************************************
//
// Exit
//

static void I_Shutdown(void)
{
	if (isGraphicsModeSet)
		I_ShutdownGraphics();

	I_ShutdownSound();

	if (isTimerSet)
		I_ShutdownTimer();
}


void I_Quit(void)
{
	I_Shutdown();
	for (;;) { SYS_doVBlankProcess(); }
}


#if defined(DOOM_R22_MAP_DIAG)
void R22_MapReport(void){
    static const char *const names[]={"PRE-FREE","POSTFREE","THINGS","SECTORS","LINES","SEGS","BLOCKMAP","NODES","SIDES","REJECT","SUBSECT","GROUP","SPAWN","DONE","FAIL"};
    char b[48];
    VDP_drawText("MAP MEMORY DIAGNOSTIC",1,3);
    sprintf(b,"MAP E1M%u STAGE %u",r22_map_current,r22_map_request?r22_map_failed_stage:r22_map_stage);VDP_drawText(b,1,4);
    sprintf(b,"REQUEST %u NEED %lu TAG %u",r22_map_request,(unsigned long)r22_map_need,r22_map_tag);VDP_drawText(b,1,5);
    VDP_drawText("MAP STAGE     FREE     MAX",1,7);
    for(uint16_t i=0;i<r22_map_count;i++){
        const r22_map_entry *e=&r22_map_trace[(r22_map_head+16-r22_map_count+i)&15];
        sprintf(b,"%u %-8s %5lu %5lu",e->map,names[e->stage],(unsigned long)e->free,(unsigned long)e->largest);VDP_drawText(b,1,8+i);
    }
    VDP_drawText("FREE/MAX INCLUDE BLOCK HEADERS",1,25);
    VDP_drawText("DIAG STOPS AFTER E1M8 LOAD",1,26);
}
#endif

#if defined(DOOM_R23_CPU_PROBE)
const char * volatile r24_cpu_error;
#endif
void I_Error(const char *error, ...)
{
#if defined(DOOM_R23_CPU_PROBE)
    r24_cpu_error=error;
    *(volatile uint16_t*)0xA00002=100+r22_map_stage;
    *(volatile uint16_t*)0xA00002=r22_map_failed_stage;
    *(volatile uint16_t*)0xA00002=r22_map_request;
    *(volatile uint16_t*)0xA00004=0;for(;;){}
#endif
	va_list argptr;
	char buffer[80];

    R20_AbortVideo();
	I_Shutdown();

	va_start(argptr, error);
	vsprintf(buffer, error, argptr);
	va_end(argptr);

	R21_TEXT_SCREEN();   /* R21 F1: VDP_init() unless DOOM_R21_NO_VDP_INIT */
	VDP_setTextPalette(PAL0);
	PAL_setColor(15, 0x0EEE);
#if defined(DOOM_R22_MAP_DIAG)
    if(r22_map_count){VDP_drawText(buffer,1,1);R22_MapReport();}
    else
#endif
    {
        /* Wrap long/error lines to38visible characters without allocations. */
        char line[39];uint16_t y=1,n=0;
        for(const char *p=buffer;;p++){
            char c=*p;
            if(c=='\n'||c==0||n==38){
                line[n]=0;VDP_drawText(line,1,y++);n=0;
                if(!c||y>=27)break;
                if(c=='\n')continue;
            }
            line[n++]=c;
        }
    }

	for (;;) { SYS_doVBlankProcess(); }
}


//**************************************************************************************
//
// Entry point (SGDK が main を呼ぶ)
//

#if defined(DOOM_SRAM_CACHE16)
extern int R_SramCacheInit(void);
#endif

#if defined(DOOM_R23_CPU_PROBE)
extern void R23_ProbeMain(void);
#endif
int main(bool hardReset)
{
#if defined(DOOM_R23_CPU_PROBE)
    R23_ProbeMain();
#endif
	(void)hardReset;
#if defined(DOOM_R20_STACKGUARD)
    R20_StackPaint();   /* first: SP is at its shallowest here */
#endif

#if defined(DOOM_R20_SGDK_HEAP)
    /* R21: SGDK uses 65535 for unlimited queue capacity; zero is a zero-byte limit. */
    DMA_initEx(DMA_QUEUE_SIZE_MIN, (uint16_t)-1, DMA_BUFFER_SIZE_MIN);
    void *r20_dma_test=DMA_allocateTemp(1);
    if (!r20_dma_test) I_Error("R20g SGDK DMA buffer allocation");
    DMA_releaseTemp(1);
#endif
#if defined(DOOM_SRAM_CACHE16)
    /* Verify odd-lane SRAM before entering Doom; never benchmark open bus. */
    if (!R_SramCacheInit())
    {
        VDP_drawText("SRAM CACHE16: SRAM NOT FOUND", 1, 10);
        VDP_drawText("CHECK BLASTEM SAVE RAM SUPPORT", 1, 12);
        for (;;) SYS_doVBlankProcess();
    }
#endif

#if defined TIMEDEMO || defined SFXDEBUG
	int argc = 3;
	const char * const argv[] = {"Doom64KB", "-timedemo", "demo3"};
#else
	int argc = 1;
	const char * const argv[] = {"Doom64KB"};
#endif
	D_DoomMain(argc, argv);

	return 0;
}
