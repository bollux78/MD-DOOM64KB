/* S1b sub engine WAD I/O exercise: fetch real remote directory and 3 E1M1
 * lumps through scd_sub_transport + scd_sub_w_wad. The full Doom thinker
 * loop is intentionally deferred to S1. No ROM will be labelled S1 full. */
#include <stdint.h>
#include <stdarg.h>
#include "w_wad.h"
#include "scd_proto.h"

#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
extern void SCD_SubTransportReset(void);
extern uint32_t SCD_SubRequests(void), SCD_SubBytes(void);

static uint32_t crc32_sample(uint32_t crc,const uint8_t *p,uint16_t n)
{
    while(n--)
    {
        crc^=*p++;
        for(uint16_t i=0;i<8;i++)
            crc=(crc>>1)^((crc&1u)?0xEDB88320UL:0);
    }
    return crc;
}
void I_Error(const char *fmt,...)
{
    (void)fmt;
    REG16(0xFF8020)=0xDEADu;
    for(;;);
}
void sub_main(void)
{
    REG16(0xFF8002)=4; /* 1M RET=0, same as successful S1a */
    SCD_SubTransportReset();
    REG16(0xFF8020)=0x5343; /* ready for MD server */
    W_Init();
    const int16_t map=W_GetNumForName("E1M1");
    uint32_t crc=0xFFFFFFFFUL;
    for(uint16_t i=1;i<=3;i++)
    {
        const int16_t lump=map+(int16_t)i;
        const uint16_t size=W_LumpLength(lump);
        const uint8_t *const p=W_GetLumpByNum(lump);
        crc=crc32_sample(crc,p,size);
    }
    crc^=0xFFFFFFFFUL;
    REG16(0xFF802A)=(uint16_t)(crc>>16);
    REG16(0xFF802C)=(uint16_t)crc;
    /* Nonzero counters prove that remote WAD callbacks were used. */
    if(SCD_SubRequests()!=4 || !SCD_SubBytes())
        I_Error("S1B BAD WAD REQUEST COUNT");
    REG16(0xFF8020)=0x51B1u;
    for(;;);
}
