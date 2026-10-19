/*
 * R35 EverDrive-MD V2 / firmware 12 / OS 36 compatibility probe.
 * Standalone SGDK ROM, not the Doom game. Tests SSF2 bank switching AND
 * SRAM coexistence with ROM above 2 MiB on the user's physical cartridge.
 * Requires a 5 MiB image with sentinel bytes at offsets 0x80000,
 * 0x200001, 0x280001, 0x40000, 0x400000 and 0x480000.
 * NO OS updates, no firmware programming, no SD access.
 */
#include <genesis.h>
#include <stdint.h>

#define MMIO8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define SRAM_ON  0x00A130F1UL
#define BANK_ONE 0x00A130F3UL
#define BANK_TWO 0x00A130F5UL
#define SLOT_ONE 0x00080000UL
#define ROM_HIGH_A 0x00200001UL
#define ROM_HIGH_B 0x00280001UL
#define SRAM_TEST 0x00200001UL

static void result_text(const char *tag, uint16_t pass, uint16_t row)
{
    VDP_drawText(tag, 2, row);
    VDP_drawText(pass ? "PASS" : "FAIL", 25, row);
}

int main(void)
{
    VDP_drawText("DOOM MD R35 - SSF2 HARDWARE PROBE", 2, 2);
    VDP_drawText("EverDrive-MD V2 / FW12 / OS36", 2, 4);
    VDP_drawText("NO FLASH OR FIRMWARE CHANGES", 2, 6);

    /* On the physical cart: initial mapping should be linear. */
    const uint8_t slot0 = MMIO8(SLOT_ONE);
    const uint8_t hi0a = MMIO8(ROM_HIGH_A);
    const uint8_t hi0b = MMIO8(ROM_HIGH_B);
    const uint16_t baseline =
        (slot0 == 0x11 && hi0a == 0x22 && hi0b == 0x33);

    /* Standard SSF2 bank-select window: 0x080000-0x0fffff.
       Bank page 8 and 9 live at offsets 4 and 4.5 MiB. */
    MMIO8(BANK_ONE) = 8;
    const uint8_t bank8 = MMIO8(SLOT_ONE);
    MMIO8(BANK_ONE) = 9;
    const uint8_t bank9 = MMIO8(SLOT_ONE);
    MMIO8(BANK_ONE) = 1;
    const uint8_t bank1 = MMIO8(SLOT_ONE);
    const uint16_t bank_ok = (bank8 == 0x88 && bank9 == 0x99 && bank1 == 0x11);

    /* SRAM probe: preserve and restore one byte. Written only to the
       standard cartridge SRAM aperture, never the flash programming ports.
       If the device ignores SRAM_ON, the ROM should remain read-only. */
    MMIO8(SRAM_ON) = 1;
    uint8_t original = MMIO8(SRAM_TEST);
    const uint8_t changed = (uint8_t)(original ^ 0x5Au);
    MMIO8(SRAM_TEST) = changed;
    const uint8_t observed = MMIO8(SRAM_TEST);
    const uint16_t sram_ok = (observed == changed);
    const uint8_t high_visible = MMIO8(ROM_HIGH_B);
    MMIO8(SRAM_TEST) = original;
    MMIO8(SRAM_ON) = 0;

    const uint8_t restored = MMIO8(ROM_HIGH_A);
    const uint16_t upper_rom_ok =
        (high_visible == 0x33 && restored == 0x22);

    result_text("LINEAR ROM 0-3MiB", baseline, 9);
    result_text("SSF2 BANK 8 / 9", bank_ok, 11);
    result_text("SRAM READ/WRITE", sram_ok, 13);
    result_text("UPPER ROM WITH SRAM", upper_rom_ok, 15);

    VDP_drawText("INITIAL DATA:", 2, 18);
    VDP_drawText(baseline ? "OK" : "BAD - CHECK MAPPER MODE", 16, 18);
    if (baseline && bank_ok && sram_ok && upper_rom_ok)
        VDP_drawText("COMBINED ROM+SRAM: PASS", 2, 21);
    else
        VDP_drawText("COMBINED ROM+SRAM: NOT VERIFIED", 2, 21);
    VDP_drawText("PHOTOGRAPH THIS SCREEN", 2, 24);
    while (1) SYS_doVBlankProcess();
    return 0;
}
