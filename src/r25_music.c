#if defined(DOOM_R25_MUSIC)
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "sounds.h"
#include "music.h"
const u8 *const r25_tracks[NUMMUSIC]={
    [mus_None]=bgm_silent,
    [mus_e1m1]=bgm_e1m1,
    [mus_e1m2]=bgm_e1m2,
    [mus_e1m3]=bgm_e1m3,
    [mus_e1m4]=bgm_e1m4,
    [mus_e1m5]=bgm_e1m5,
    [mus_e1m6]=bgm_e1m6,
    [mus_e1m7]=bgm_e1m7,
    [mus_e1m8]=bgm_e1m8,
    [mus_e1m9]=bgm_e1m9,
    [mus_inter]=bgm_inter,
    [mus_intro]=bgm_intro,
    [mus_victor]=bgm_victor,
    [mus_introa]=bgm_intro,
};
#endif
