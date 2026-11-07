/* S1b: actual MD Word-RAM DIR/LUMP server integration test.
 * Boot sub, let it fetch WAD directory and three E1M1 lumps, compare CRCs.
 * Diagnostic then START (or timeout) launches unmodified R128 All on MD.
 * Does NOT claim the Doom ticker already executes on the Sega CD. */
#include <stdint.h>
#include <genesis.h>
#include "doomtype.h"
#include "w_wad.h"
#include "i_system.h"
#include "r21_textscreen.h"
#include "scd_proto.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_HI (*(volatile const u16 *)0xA1202A)
#define CD_SUB_LO (*(volatile const u16 *)0xA1202C)
#define CD_PRGRAM ((volatile u16 *)0x420000)
#include "s1b_sub.h"

extern void SCD_MdServeReset(void);
extern int16_t SCD_MdServeOnce(void);
extern uint16_t SCD_MdTransactions(void), SCD_MdErrors(void);
extern uint32_t SCD_MdBytes(void), SCD_MdTimeouts(void);

static bool wait_sub(u8 mask,u8 expected)
{
    for(u32 n=0;n<400000UL;n++)
        if ((CD_SUB_BYTE & mask)==expected) return TRUE;
    return FALSE;
}
static bool boot_sub(void)
{
    CD_MEMCTRL=0xFF00;
    CD_SUB_BYTE=3;CD_SUB_BYTE=2;CD_SUB_BYTE=0;
    for(u16 i=0;i<128;i++)__asm__ volatile("nop");
    if(!wait_sub(1,0))return FALSE;
    CD_SUB_BYTE=3;
    if(!wait_sub(3,3))return FALSE;
    CD_MEMCTRL=0;CD_MAIN_SWAP=0;
    for(u32 i=0;i<SUB_PROGRAM_WORDS;i++)CD_PRGRAM[i]=sub_program[i];
    for(u32 i=0;i<SUB_PROGRAM_WORDS;i++)
        if(CD_PRGRAM[i]!=sub_program[i])return FALSE;
    CD_SUB_BYTE=0;
    if(!wait_sub(1,0))return FALSE;
    CD_SUB_BYTE=1;
    if(!wait_sub(3,1))return FALSE;
    for(u32 n=0;n<4000000UL;n++)
        if(CD_SUB_SIG==0x5343u && (CD_MEMCTRL&5u)==4u)return TRUE;
    return FALSE;
}
void __attribute__((noipa)) s1b_complete(void) {__asm__ volatile("" ::: "memory");}
void __attribute__((noipa)) s1b_continue(void) {__asm__ volatile("" ::: "memory");}
typedef struct {
    u16 stage, serviced, errors, reserved;
    u32 bytes, md_crc, sub_crc, timeouts;
} S1bReport;
/* Test report resides in MD-owned Word RAM, not MD BSS. */
#define REPORT (*(volatile S1bReport *)0x61F000)
static u32 crc32_sample(u32 crc,const u8 *p,u16 n)
{
    while(n--)
    {
        crc^=*p++;
        for(u16 i=0;i<8;i++)
            crc=(crc>>1)^((crc&1u)?0xEDB88320UL:0);
    }
    return crc;
}
static void diagnose(S1bReport *result)
{
    if((HW_VERSION&0x20u)||CD_BIOS_HEADER!=0x53454741UL)
    {result->stage=1;return;}
    if(!boot_sub()){result->stage=2;return;}
    result->stage=3;
    W_Init();
    const int16_t map=W_GetNumForName("E1M1");
    /* The sub requests THINGS, LINEDEFS, SIDEDEFS from the MD. */
    u32 expected=0xFFFFFFFFUL;
    for(u16 i=1;i<=3;i++)
    {
        const u16 n=(u16)(map+i);
        expected=crc32_sample(expected,W_GetLumpByNum(n),W_LumpLength(n));
    }
    SCD_MdServeReset();
    for(u32 spins=0;spins<50000000UL;spins++)
    {
        const int16_t served=SCD_MdServeOnce();
        if(served<0){result->stage=4;break;}
        if(CD_SUB_SIG==0x51B1u){result->stage=5;break;}
        if(CD_SUB_SIG==0xDEADu){result->stage=6;break;}
    }
    result->serviced=SCD_MdTransactions();
    result->errors=SCD_MdErrors();
    result->timeouts=SCD_MdTimeouts();
    result->bytes=SCD_MdBytes();
    result->md_crc=expected^0xFFFFFFFFUL;
    result->sub_crc=((u32)CD_SUB_HI<<16)|CD_SUB_LO;
}
void S1B_Test(void)
{
    S1bReport r;
    memset(&r,0,sizeof r);
    SYS_disableInts();
    diagnose(&r);
    REPORT=r;
    SYS_enableInts();
    s1b_complete();
    const bool pass=r.stage==5 && r.serviced==4 && !r.errors &&
                    !r.timeouts && r.md_crc==r.sub_crc;
    char t[40];
    I_R21_TextScreen();
    VDP_drawText("S1B SUB WAD TRANSPORT",1,2);
    sprintf(t,"TRANSFER %s  STAGE %u",pass?"PASS":"FAIL",(unsigned)r.stage);
    VDP_drawText(t,1,4);
    sprintf(t,"REQUESTS %u ERRORS %u",(unsigned)r.serviced,(unsigned)r.errors);
    VDP_drawText(t,1,6);
    sprintf(t,"BYTES %lu",(unsigned long)r.bytes);
    VDP_drawText(t,1,7);
    sprintf(t,"MD CRC %08lX",(unsigned long)r.md_crc);
    VDP_drawText(t,1,9);
    sprintf(t,"CD CRC %08lX",(unsigned long)r.sub_crc);
    VDP_drawText(t,1,10);
    VDP_drawText("START: PLAY R128 ON MEGA DRIVE",1,13);
    VDP_drawText("AUTO START AFTER 15 SECONDS",1,14);
    volatile u8 *const data=(volatile u8 *)0xA10003;
    volatile u8 *const ctrl=(volatile u8 *)0xA10009;
    volatile const u16 *const vdp=(volatile const u16 *)0xC00004;
    *ctrl=0x40;
    for(u16 frames=0;frames<900;frames++)
    {
        while(*vdp&8u);
        while(!(*vdp&8u));
        *data=0;__asm__ volatile("nop; nop; nop; nop");
        const u8 b=*data;*data=0x40;
        if(!(b&0x20u))break;
    }
    s1b_continue();
}
