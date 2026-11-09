/* Sub CPU has no sound hardware of the MD: the MD-side sound layer (Z80/YM/PSG pokes at
 * 0xA0xxxx/0xC000xx alias PRG-RAM on the sub!) is replaced by no-ops. Sound stays on the MD. */
#include <stdint.h>
#include "doomdef.h"
#include "s_sound.h"
void S_Init(int16_t sfxVolume, int16_t musicVolume) { (void)sfxVolume; (void)musicVolume; }
void S_Start(void) {}
void S_StartSound(mobj_t __far *origin, sfxenum_t sfx_id) { (void)origin; (void)sfx_id; }
void S_StopSound(void __far *origin) { (void)origin; }
void S_UpdateSounds(void) {}
void S_SetMusicVolume(int16_t volume) { (void)volume; }
void S_SetSfxVolume(int16_t volume) { (void)volume; }
void S_StartMusic(musicenum_t m_id) { (void)m_id; }
void S_ChangeMusic(musicenum_t musicnum, boolean looping) { (void)musicnum; (void)looping; }
