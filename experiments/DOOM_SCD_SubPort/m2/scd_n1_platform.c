/* N1 link probe: MD-only hooks the R128 renderer calls, stubbed for the sub. Signatures are
 * placeholders for the link report; the real N2 program replaces them with checked ones. */
#include <stdint.h>
#include "doomdef.h"
#include "r57_viewport.h"
#if defined(DOOM_R57_CROP16) && defined(DOOM_R57_VIEW_MENU)
R57ViewConfig r57_view = {0, 0, 0, 2, 76, 2, 44};
#endif
volatile uint32_t _g_vblankCount;
void R64A_FrameBegin(void) {}
void R64A_FrameEnd(void) {}
void R95_FlatSetup(void) {}
void R96_WallSetup(void) {}
void R115_LevelStart(void) {}
void R115_LevelEnd(void) {}
void R117_LoadDone(void) {}
void I_BenchmarkReset(void) {}
void I_BenchmarkShowResults(void) {}
void I_BenchmarkWindowReset(void) {}
void DMX_Play(int id, int16_t ch) { (void)id; (void)ch; }
void I_PlaySong(int h, int loop) { (void)h; (void)loop; }
void I_StopSong(int h) { (void)h; }
void SYS_doVBlankProcess(void) {}
void *R81_SaveScratch(void) { return 0; }
int sprintf(char *b, const char *f, ...) { (void)f; b[0] = 0; return 0; }
