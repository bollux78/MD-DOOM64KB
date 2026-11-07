/* Sega CD S1/S2 shared protocol — cartridge MD is the sole initiator of Word RAM 1M swaps.
 * Hardware comm words: sub writes $FF8026 (ack), $FF8028 (done),
 * $FF802A/$FF802C (result); MD sees these at $A12026/28/2A/2C.
 *
 * IMPORTANT: this is the wire format, not the completed S1/S2 engine port.
 * S1a's verified transport remains the boot fallback.
 */
#ifndef DOOM_SCD_PROTO_H
#define DOOM_SCD_PROTO_H
#include <stdint.h>

#define SCD_PROTO_VERSION 1u
#define SCD_SUB_REG16(addr) (*(volatile uint16_t *)(uintptr_t)(addr))
#define SCD_MD_REG16(addr)  (*(volatile uint16_t *)(uintptr_t)(addr))
#define SCD_SUB_ACK_REG    0xFF8026UL
#define SCD_SUB_DONE_REG   0xFF8028UL
#define SCD_SUB_HI_REG     0xFF802AUL
#define SCD_SUB_LO_REG     0xFF802CUL
#define SCD_SUB_REQUEST_REG 0xFF802EUL
#define SCD_MD_REQUEST_REG 0xA1202EUL
#define SCD_MD_ACK_REG     0xA12026UL
#define SCD_MD_DONE_REG    0xA12028UL
#define SCD_MD_HI_REG      0xA1202AUL
#define SCD_MD_LO_REG      0xA1202CUL
#define SCD_MD_SWAP_REG    0xA12018UL
#define SCD_SUB_SWAP_REG   0xFF8002UL
#define SCD_MD_BANK_BASE   0x600000UL
#define SCD_SUB_BANK_BASE  0x0C0000UL
#define SCD_BANK_BYTES     (128UL * 1024UL)
#define SCD_MAX_LUMP_BYTES 65535u
#define SCD_PACKET_OFFSET  0x0000u
#define SCD_PAYLOAD_OFFSET 0x0100u
#define SCD_FRAME_OFFSET   0x1000u
#define SCD_FRAME_BYTES    3344u

/* The first two bytes of request are a monotonically increasing nonzero seq.
 * The sub publishes request after payload; MD responds with an explicit result.
 * Every transition is initiated by MD through SCD_MD_SWAP_REG.
 * No DMNA writes are allowed in the sub-port.
 */
enum scd_cmd {
    SCD_CMD_NONE = 0,
    SCD_CMD_DIR = 1,
    SCD_CMD_LUMP = 2,
    SCD_CMD_TIC = 3,
    SCD_CMD_SFX = 4,
    SCD_CMD_MUSIC = 5,
    SCD_CMD_HUD = 6,
    SCD_CMD_ERROR = 7,
    SCD_CMD_FRAME = 8
};

/* All packet fields big-endian as written by the 68000. Keep this layout
 * independent of SGDK packing and host compiler padding. */
typedef struct {
    uint16_t version;
    uint16_t command;
    uint16_t sequence;
    uint16_t status;
    uint32_t argument;
    uint32_t length;
    uint32_t payload_crc32;
    uint32_t gametic;
} scd_packet_t;

typedef char scd_packet_must_be_24_bytes[(sizeof(scd_packet_t) == 24u) ? 1 : -1];
typedef char scd_frame_fits_wordram[(SCD_FRAME_OFFSET + SCD_FRAME_BYTES < SCD_BANK_BYTES) ? 1 : -1];
typedef char scd_payload_fits_wordram[(SCD_PAYLOAD_OFFSET + SCD_MAX_LUMP_BYTES < SCD_BANK_BYTES) ? 1 : -1];
#endif
