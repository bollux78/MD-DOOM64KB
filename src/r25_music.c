#if defined(DOOM_R25_MUSIC)
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "sounds.h"
#include "music.h"
#if defined(DOOM_R29_XGM2) && defined(DOOM_R29_MULTI)
/* Multi-track IDs: E1M1..9 = 0..8; intro 9, inter 10, victor 11, silence 12. */
const u8 r25_track_indices[NUMMUSIC]={
 [mus_None]=12,
 [mus_e1m1]=0,[mus_e1m2]=1,[mus_e1m3]=2,
 [mus_e1m4]=3,[mus_e1m5]=4,[mus_e1m6]=5,
 [mus_e1m7]=6,[mus_e1m8]=7,[mus_e1m9]=8,
 [mus_inter]=10,[mus_intro]=9,[mus_victor]=11,[mus_introa]=9,
};
#else
#if defined(DOOM_R27_SINGLE_TRACK)
/* Diagnostic: the exact E1M1 used by the full soundtrack, aliased for all IDs. */
const u8 *const r25_tracks[NUMMUSIC]={
 [mus_None]=bgm_silent,
 [mus_e1m1]=bgm_e1m1,[mus_e1m2]=bgm_e1m1,[mus_e1m3]=bgm_e1m1,
 [mus_e1m4]=bgm_e1m1,[mus_e1m5]=bgm_e1m1,[mus_e1m6]=bgm_e1m1,
 [mus_e1m7]=bgm_e1m1,[mus_e1m8]=bgm_e1m1,[mus_e1m9]=bgm_e1m1,
 [mus_inter]=bgm_e1m1,[mus_intro]=bgm_e1m1,[mus_victor]=bgm_e1m1,[mus_introa]=bgm_e1m1,
};
#else
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
#endif

#endif
