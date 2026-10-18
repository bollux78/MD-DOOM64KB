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

#if defined(DOOM_R34_AUDIO)
/* R34-AUDIO is deliberately isolated from WAD changes.
   Two 256-aligned PCM buffers, one for each SFX DAC channel.
   Large samples remain raw ROM PCM and never require RAM buffers. */
#if defined(DOOM_R34_PCM_2048)
#define R34_PCM_CAP 2048
#elif defined(DOOM_R34_PCM_3072)
#define R34_PCM_CAP 3072
#else
#define R34_PCM_CAP 4096
#endif
static uint8_t r34_pcm_buffer[2][R34_PCM_CAP] __attribute__((aligned(256)));
static const uint16_t r34_ima_step[89]={
    7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,
    50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,
    253,279,307,337,371,408,449,494,544,598,658,724,796,876,
    963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,
    2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,
    7132,7845,8630,9493,10442,11487,12635,13899,15289,
    16818,18500,20350,22385,24623,27086,29794,32767
};
static const int8_t r34_ima_delta_index[16]={
    -1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8
};
static bool R34_AudioDecode(const gensfx_t *sample, uint8_t *dest)
{
    const uint8_t *src=sample->data;
    const uint16_t size=sample->packed_len;
    const uint16_t expected=(uint16_t)sample->len;
    if(expected>R34_PCM_CAP || !size || expected==0)return FALSE;
    if(sample->codec==1) /* PackBits, bit-exact */
    {
        uint16_t in=0,out=0;
        while(in<size)
        {
            const uint8_t tag=src[in++];
            const uint16_t n=(tag&127u)+1u;
            if(out+n>expected)return FALSE;
            if(tag&128)
            {
                if(in>=size)return FALSE;
                const uint8_t b=src[in++];
                for(uint16_t j=0;j<n;j++)dest[out++]=b;
            }
            else
            {
                if(in+n>size)return FALSE;
                for(uint16_t j=0;j<n;j++)dest[out++]=src[in++];
            }
        }
        return out==expected;
    }
    if(sample->codec==2) /* 4bit IMA/DVI ADPCM */
    {
        if(size!=(expected+1u)/2u)return FALSE;
        int32_t predictor=0;
        int16_t index=0;
        for(uint16_t i=0;i<expected;i++)
        {
            const uint8_t packed=src[i>>1];
            const uint8_t code=(i&1u)?((packed>>4)&15u):(packed&15u);
            const int32_t step=r34_ima_step[index];
            int32_t change=step>>3;
            if(code&4)change+=step;
            if(code&2)change+=step>>1;
            if(code&1)change+=step>>2;
            predictor+=(code&8)?-change:change;
            if(predictor>32767)predictor=32767;
            else if(predictor< -32768)predictor=-32768;
            index+=r34_ima_delta_index[code];
            if(index<0)index=0;
            else if(index>88)index=88;
            int32_t out=(predictor+128)>>8;
            if(out>127)out=127;
            else if(out< -128)out=-128;
            dest[i]=(uint8_t)(int8_t)out;
        }
        return TRUE;
    }
    return FALSE;
}
#endif



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
#if defined(DOOM_R29_XGM2)
	/* Music may use channel 1; only channels 2 and 3 available for SFX. */
	SoundPCMChannel pcmch = (channel & 1) ? SOUND_PCM_CH3 : SOUND_PCM_CH2;
	const u8 *pcmdata=gensfx[id].data;
#if defined(DOOM_R34_AUDIO)
	if(gensfx[id].codec)
	{
	    /* Explicitly stop the old sample before rewriting its channel buffer.
	       This intentionally differs from XGM2 priority arbitration and is
	       an audible preemption edge case to test on original hardware. */
	    XGM2_stopPCM(pcmch);
	    u8 *dest=r34_pcm_buffer[channel&1];
	    if(!R34_AudioDecode(&gensfx[id],dest))return;
	    pcmdata=dest;
	}
#endif
	XGM2_playPCMEx(pcmdata, gensfx[id].len, pcmch,
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
}

void I_StopSong(musicenum_t handle)
{
	(void)handle;
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
