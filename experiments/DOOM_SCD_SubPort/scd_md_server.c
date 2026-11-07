/* S1 Mega Drive-side directory/lump server.
 * MD owns one 1M Word RAM bank and is the ONLY initiator of bank swaps.
 * Sub publishes CMD/ARG/SEQ in communication words. MD fills its bank,
 * writes seq to $A12018, and waits for the sub to swap+ACK+DONE.
 * The resident WAD is still read by the original w_wad.c on MD.
 *
 * Not installed in the player ROM yet. Its integration requires the
 * sub-CPU boot/runtime and the original R128 START fallback.
 */
#include <stdint.h>
#include "doomtype.h"
#include "w_wad.h"
#include "scd_proto.h"

#define SCD_MD_CMD_REG 0xA12022UL
#define SCD_MD_ARG_REG 0xA12024UL
#define SCD_MD_MEMCTRL_REG 0xA12002UL
#define SCD_MD_MAX_SPINS 4000000UL
#define SCD_MD_DIR_ENTRY_BYTES 10u

/* Returns the BE WAD header count; installed in the R128 WAD module later. */
extern uint16_t SCD_MdLumpCount(void);

static uint16_t last_request, transactions, errors;
static uint32_t bytes_sent, timeouts;

static void put16(volatile uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)(value >> 8);
    p[1] = (uint8_t)value;
}
static void put32(volatile uint8_t *p, uint32_t value)
{
    put16(p, (uint16_t)(value >> 16));
    put16(p + 2, (uint16_t)value);
}

/* Put the packet with explicit byte stores so no compiler packing or
 * alignment differences can affect the wire format. */
static void response(uint16_t cmd, uint16_t seq, uint16_t status,
                     uint32_t arg, uint32_t length)
{
    volatile uint8_t *const bank = (volatile uint8_t *)SCD_MD_BANK_BASE;
    put16(bank + 0, SCD_PROTO_VERSION);
    put16(bank + 2, cmd);
    put16(bank + 4, seq);
    put16(bank + 6, status);
    put32(bank + 8, arg);
    put32(bank + 12, length);
    put32(bank + 16, 0); /* CRC reserved for S2 */
    put32(bank + 20, 0); /* gametic reserved for S2 */
}

void SCD_MdServeReset(void)
{
    last_request = 0;
    transactions = 0;
    errors = 0;
    bytes_sent = 0;
    timeouts = 0;
}
uint16_t SCD_MdTransactions(void) { return transactions; }
uint16_t SCD_MdErrors(void) { return errors; }
uint32_t SCD_MdBytes(void) { return bytes_sent; }
uint32_t SCD_MdTimeouts(void) { return timeouts; }

static uint16_t prepare_dir(uint16_t *bytes)
{
    const uint16_t count = SCD_MdLumpCount();
    if (!count || count > 2048u) return 0;
    const uint32_t total = 2ul + (uint32_t)count * SCD_MD_DIR_ENTRY_BYTES;
    if (SCD_PAYLOAD_OFFSET + total > SCD_BANK_BYTES) return 0;
    volatile uint8_t *const p = (volatile uint8_t *)(SCD_MD_BANK_BASE + SCD_PAYLOAD_OFFSET);
    put16(p, count);
    for (uint16_t i = 0; i < count; i++)
    {
        volatile uint8_t *const e = p + 2ul + 10ul*i;
        const char __far *name = W_GetNameForNum((int16_t)i);
        for (uint16_t j = 0; j < 8; j++) e[j] = (uint8_t)name[j];
        put16(e + 8, W_LumpLength((int16_t)i));
    }
    *bytes = (uint16_t)total;
    return 1;
}
static uint16_t prepare_lump(uint16_t lump, uint16_t *bytes)
{
    if (lump >= SCD_MdLumpCount()) return 0;
    const uint16_t len = W_LumpLength((int16_t)lump);
    if (SCD_PAYLOAD_OFFSET + (uint32_t)len > SCD_BANK_BYTES) return 0;
    const uint8_t __far *source = W_GetLumpByNum((int16_t)lump);
    volatile uint8_t *const p = (volatile uint8_t *)(SCD_MD_BANK_BASE + SCD_PAYLOAD_OFFSET);
    for (uint16_t i = 0; i < len; i++) p[i] = source[i];
    *bytes = len;
    return 1;
}

/* Returns 0 when idle, 1 when one request completed, -1 on invalid
 * command/transport timeout. Wait only after a request has been observed. */
int16_t SCD_MdServeOnce(void)
{
    const uint16_t seq = SCD_MD_REG16(SCD_MD_REQUEST_REG);
    if (!seq || seq == last_request) return 0;
    const uint16_t cmd = SCD_MD_REG16(SCD_MD_CMD_REG);
    const uint16_t arg = SCD_MD_REG16(SCD_MD_ARG_REG);
    last_request = seq;
    uint16_t status = 0, size = 0;
    if (cmd == SCD_CMD_DIR)
        status = prepare_dir(&size);
    else if (cmd == SCD_CMD_LUMP)
        status = prepare_lump(arg, &size);
    /* Even invalid requests are acknowledged, so the sub does not hang. */
    response(cmd, seq, status, arg, size);
    __asm__ volatile("" ::: "memory");
    const uint16_t previous = SCD_MD_REG16(SCD_MD_MEMCTRL_REG) & 5u;
    SCD_MD_REG16(SCD_MD_SWAP_REG) = seq;
    for (uint32_t spins = 0; spins < SCD_MD_MAX_SPINS; spins++)
    {
        if (SCD_MD_REG16(SCD_MD_ACK_REG) == seq &&
            SCD_MD_REG16(SCD_MD_DONE_REG) == seq &&
            (SCD_MD_REG16(SCD_MD_MEMCTRL_REG) & 5u) != previous)
        {
            transactions++;
            if (status) bytes_sent += size;
            else errors++;
            return status ? 1 : -1;
        }
    }
    timeouts++;
    return -1;
}
