/* S1d staging layer for the Sega CD sub-68000: direct PRG-RAM zone,
 * clock and no-render hooks. Deliberately not used by the approved S1b ROM.
 * All writable data, including the zone, must be accounted for by the final
 * 512 KiB PRG-RAM linker map. This source is NOT a complete engine port.
 */
#include <stdint.h>
#include "i_system.h"

/* Conservative initial zone budget, to be validated against E1M1 heap peak. */
#define SCD_SUB_ZONE_BYTES (112UL * 1024UL)
#define REG16(addr) (*(volatile uint16_t *)(uintptr_t)(addr))

static uint8_t sub_zone[SCD_SUB_ZONE_BYTES] __attribute__((aligned(16)));
static volatile uint32_t sub_tic_clock;

uint8_t __far* I_ZoneBase(uint32_t *size)
{
    *size = sizeof sub_zone;
    return sub_zone;
}

void SCD_SubSetTime(uint32_t ticks) { sub_tic_clock = ticks; }
int32_t I_GetTime(void) { return (int32_t)sub_tic_clock; }
void I_InitTimer(void) {}
void I_StartTic(void) {}

/* S1d logic-only: no hardware video, input polling, or VDP access on sub. */
void I_InitKeyboard(void) {}
void I_InitGraphics(void) {}
void I_FinishUpdate(void) {}
void I_ReloadPalette(void) {}
void I_SetPalette(int8_t pal) { (void)pal; }

_Noreturn void I_Quit(void)
{
    REG16(0xFF8020UL) = 0x5154u;  /* 'QT' */
    for (;;) {}
}
_Noreturn void I_Error(const char *message, ...)
{
    (void)message;
    REG16(0xFF8020UL) = 0xDEADu;
    for (;;) {}
}
