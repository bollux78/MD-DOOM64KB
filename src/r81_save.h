#ifndef R81_SAVE_H
#define R81_SAVE_H
#include <stdint.h>
#define R81_SAVE_BASE 26624u
#define R81_SAVE_CAPACITY (32768u-R81_SAVE_BASE)
/* One explicit, CRC-checked full-state slot in the existing 32 KiB SRAM. */
const char *R81_SaveGame(void) __attribute__((noinline,used));
const char *R81_LoadGame(void) __attribute__((noinline,used));
void R81_UpdateSaveStrings(void);
void *R81_SaveScratch(void);
void R81_ResyncInput(void);
#endif
