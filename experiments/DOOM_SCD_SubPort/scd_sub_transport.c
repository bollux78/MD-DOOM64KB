/* S1 sub-CPU synchronous bridge, matching scd_md_server.c.
 * The sub NEVER asserts DMNA; MD writes $A12018 to request a 1M swap.
 * Each transaction copies its data out of Word RAM before returning so
 * persistent Doom lump pointers remain valid across subsequent swaps.
 *
 * This module intentionally has no dependencies on SGDK or main CPU memory.
 */
#include <stdint.h>
#include "scd_proto.h"

#define SCD_SUB_CMD_REG 0xFF8022UL
#define SCD_SUB_ARG_REG 0xFF8024UL
#define SCD_SUB_MAIN_REQUEST_REG 0xFF8018UL
#define SCD_SUB_MODE_REG 0xFF8002UL
#define SCD_SUB_MEMCTRL_REG 0xFF8002UL
#if defined(SCD_LIVE)
#define SCD_SUB_MAX_SPINS 200000000UL
#else
#define SCD_SUB_MAX_SPINS 4000000UL
#endif

typedef struct {
    char name[8];
    uint16_t size;
} scd_lump_dirent_t;

#if defined(SCD_REALTIME)
extern void S2F_ClockPoll(void);
#endif
#if defined(SCD_M15)
static uint16_t m15_busy;
int SCD_SubBusy(void){return m15_busy;}
#define M15_BUSY(x) (m15_busy=(x))
#else
#define M15_BUSY(x) ((void)0)
#endif
static uint16_t sub_seq, sub_mode = 4u;
static uint32_t sub_requests, sub_bytes, sub_timeouts;

static uint16_t get16(const volatile uint8_t *p)
{
    return ((uint16_t)p[0] << 8) | p[1];
}
static uint32_t get32(const volatile uint8_t *p)
{
    return ((uint32_t)get16(p) << 16) | get16(p+2);
}
void SCD_SubTransportReset(void)
{
    M15_BUSY(0);
    sub_seq=0;
    sub_mode=4u; /* matches S1a boot after selecting mode 1M RET=0 */
    sub_requests=0;
    sub_bytes=0;
    sub_timeouts=0;
    SCD_SUB_REG16(SCD_SUB_REQUEST_REG)=0;
    SCD_SUB_REG16(SCD_SUB_ACK_REG)=0;
    SCD_SUB_REG16(SCD_SUB_DONE_REG)=0;
}
uint32_t SCD_SubRequests(void) { return sub_requests; }
uint32_t SCD_SubBytes(void) { return sub_bytes; }
uint32_t SCD_SubTimeouts(void) { return sub_timeouts; }

/* Run from sub main loop AFTER the proven S1a boot sequence.
 * On success, points to the bank now owned by sub, with the payload
 * beginning at SCD_PAYLOAD_OFFSET. */
static const volatile uint8_t *scd_exchange(uint16_t command,
                                             uint16_t argument, uint16_t *length)
{
    M15_BUSY(1);
    uint16_t seq=++sub_seq;
    if(!seq) seq=++sub_seq;
    SCD_SUB_REG16(SCD_SUB_CMD_REG)=command;
    SCD_SUB_REG16(SCD_SUB_ARG_REG)=argument;
    SCD_SUB_REG16(SCD_SUB_ACK_REG)=0;
    SCD_SUB_REG16(SCD_SUB_DONE_REG)=0;
    __asm__ volatile("" ::: "memory");
    SCD_SUB_REG16(SCD_SUB_REQUEST_REG)=seq;
    for (uint32_t spins=0; spins<SCD_SUB_MAX_SPINS; spins++)
    {
#if defined(SCD_REALTIME)
        if(!(spins&255u))S2F_ClockPoll();
#endif
        if (SCD_SUB_REG16(SCD_SUB_MAIN_REQUEST_REG)!=seq) continue;
        sub_mode^=1u;
        SCD_SUB_REG16(SCD_SUB_MODE_REG)=sub_mode;
        __asm__ volatile("" ::: "memory");
        SCD_SUB_REG16(SCD_SUB_ACK_REG)=seq;
        const volatile uint8_t *const bank=(const volatile uint8_t *)SCD_SUB_BANK_BASE;
        const uint16_t version=get16(bank);
        const uint16_t cmd=get16(bank+2);
        const uint16_t got_seq=get16(bank+4);
        const uint16_t status=get16(bank+6);
        const uint32_t got_len=get32(bank+12);
        const uint32_t room=SCD_BANK_BYTES-SCD_PAYLOAD_OFFSET;
        if (version!=SCD_PROTO_VERSION || cmd!=command || got_seq!=seq ||
            !status || got_len>room || got_len>65535ul)
        {
            SCD_SUB_REG16(SCD_SUB_DONE_REG)=seq;
            M15_BUSY(0);return 0;
        }
        *length=(uint16_t)got_len;
        sub_requests++;
        sub_bytes+=got_len;
        /* The caller MUST copy payload before issuing another request. */
        SCD_SUB_REG16(SCD_SUB_DONE_REG)=seq;
        M15_BUSY(0);return bank+SCD_PAYLOAD_OFFSET;
    }
    sub_timeouts++;
    M15_BUSY(0);return 0;
}
int scd_fetch_directory(scd_lump_dirent_t *entries, uint16_t capacity,
                        uint16_t *count)
{
    uint16_t length=0;
    const volatile uint8_t *p=scd_exchange(SCD_CMD_DIR,0,&length);
    if (!p || length<2u) return 0;
    const uint16_t n=get16(p);
    if (!n || n>capacity || (uint32_t)length!=2ul+10ul*n) return 0;
    for (uint16_t i=0; i<n; i++)
    {
        const volatile uint8_t *const row=p+2ul+10ul*i;
        for (uint16_t j=0; j<8; j++) entries[i].name[j]=(char)row[j];
        entries[i].size=get16(row+8);
    }
    *count=n;
    return 1;
}
int scd_fetch_lump(uint16_t lump, void *destination, uint16_t bytes)
{
    uint16_t length=0;
    const volatile uint8_t *p=scd_exchange(SCD_CMD_LUMP,lump,&length);
    if (!p || length!=bytes) return 0;
    uint8_t *const out=(uint8_t *)destination;
    for (uint16_t i=0; i<bytes; i++) out[i]=p[i];
    return 1;
}

/* Reverse snapshot path: sub has already filled its owned bank. After this
 * MD-initiated exchange, MD owns that state and sub receives the next input. */
int SCD_SubLiveInput(uint32_t tick,uint8_t out[16])
{
    uint16_t len=0;const volatile uint8_t *p=scd_exchange(SCD_CMD_TIC,0,&len);
    if(!p || len!=16 || get32(p)!=0x53324449UL || get32(p+4)!=tick)return 0;
    uint32_t h=2166136261UL;
    for(uint16_t i=0;i<16;i++){out[i]=p[i];h=(h^out[i])*16777619UL;}
    const volatile uint8_t *bank=(const volatile uint8_t *)SCD_SUB_BANK_BASE;
    return h==get32(bank+16);
}

#if defined(SCD_REALTIME)
/* Advertise only between logic ticks; no WAD transaction can overlap. */
void SCD_SubLiveBegin(void){
    uint16_t seq=++sub_seq;if(!seq)seq=++sub_seq;
    SCD_SUB_REG16(SCD_SUB_CMD_REG)=SCD_CMD_TIC;
    SCD_SUB_REG16(SCD_SUB_ARG_REG)=0;
    SCD_SUB_REG16(SCD_SUB_ACK_REG)=0;SCD_SUB_REG16(SCD_SUB_DONE_REG)=0;
    __asm__ volatile("" ::: "memory");
    SCD_SUB_REG16(SCD_SUB_REQUEST_REG)=seq;
}
int SCD_SubLiveReady(void){return SCD_SUB_REG16(SCD_SUB_MAIN_REQUEST_REG)==sub_seq;}
int SCD_SubLiveCommit(uint32_t frame,uint8_t out[16]){
    sub_mode^=1u;SCD_SUB_REG16(SCD_SUB_MODE_REG)=sub_mode;
    __asm__ volatile("" ::: "memory");
    SCD_SUB_REG16(SCD_SUB_ACK_REG)=sub_seq;
    const volatile uint8_t *b=(const volatile uint8_t *)SCD_SUB_BANK_BASE;
    const volatile uint8_t *p=b+SCD_PAYLOAD_OFFSET;
    int ok=get16(b)==SCD_PROTO_VERSION && get16(b+2)==SCD_CMD_TIC &&
        get16(b+4)==sub_seq && get16(b+6) && get32(b+12)==16 &&
        get32(p)==0x53324449UL && get32(p+4)==frame;
    uint32_t h=2166136261UL;
#if defined(SCD_M15)
    for(uint16_t i=0;i<16;i++)out[i]=p[i];
    for(uint16_t i=0;i<4;i++){uint32_t v=((volatile const uint32_t *)p)[i];h=(((h<<5)|(h>>27))^v)+0x9e3779b9UL;}
#else
    for(uint16_t i=0;i<16;i++){out[i]=p[i];h=(h^out[i])*16777619UL;}
#endif
    ok=ok && h==get32(b+16);
    sub_requests++;sub_bytes+=16;
    SCD_SUB_REG16(SCD_SUB_DONE_REG)=sub_seq;return ok;
}
#endif

