/* R46 M3C: caller-owned two-bank VRAM staging protocol.
 * IMPORTANT: both banks' tile PATTERNS may coexist in VRAM, but only
 * ONE BG_A tilemap at 0xE000 is available. No truly atomic map-page flip.
 * Map writes must be made with DISPLAY DISABLED and committed at VBlank.
 * State machine tracks explicit caller acknowledgments; not hardware.
 */
#ifndef R46_M3C_BANK_HEADER_H
#define R46_M3C_BANK_HEADER_H
#include <stdint.h>
enum { R46_M3C_COLUMNS=38, R46_M3C_ROWS=21,
       R46_M3C_DYNAMIC_TILES=798,
       R46_M3C_NO_BANK=0xffffu };
typedef struct {
    uint16_t visible_bank,pending_bank,uploaded,commits;
    uint32_t mapped_rows;
} r46_m3c_bank_t;
#if defined(DOOM_R46_M2C)
void R46_M3C_BankInit(r46_m3c_bank_t *s);
uint16_t R46_M3C_StageBank(r46_m3c_bank_t *s,uint16_t bank);
uint16_t R46_M3C_BankWritable(const r46_m3c_bank_t *s,uint16_t bank);
/* Caller acknowledges tiles only AFTER a successful tile-pattern upload. */
uint16_t R46_M3C_TilesUploaded(r46_m3c_bank_t *s,uint16_t count);
/* Rows 1..21 are written only while VDP display is blanked.
 * Caller acknowledges each row after the CPU map write completes. */
uint16_t R46_M3C_MapRowWritten(r46_m3c_bank_t *s,uint16_t row);
/* Requires the caller to have blanked video, waited for VBlank, then
 * completed all 21 map rows. The flag is an explicit caller assertion,
 * not proof that hardware VBlank occurred. */
uint16_t R46_M3C_CommitBank(r46_m3c_bank_t *s,
                           uint16_t display_blanked_and_vblank);
uint16_t R46_M3C_BankValidate(void);
#endif
#endif
