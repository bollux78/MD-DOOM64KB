/* R39e: runtime music + sound-effects switches for XGM2 8x8 builds.
 * Default ON, state preserved across level/song changes during this session.
 * No SRAM persistence and no change to the demo input stream. */
#ifndef R39E_AUDIO_H
#define R39E_AUDIO_H
#include <stdint.h>
#if defined(DOOM_R39E_AUDIO_TOGGLES)
uint16_t R39E_MusicEnabled(void);
uint16_t R39E_SfxEnabled(void);
void R39E_SetMusicEnabled(uint16_t enabled);
void R39E_SetSfxEnabled(uint16_t enabled);
#endif
#endif
