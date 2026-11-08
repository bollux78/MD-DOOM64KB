/* Z8: original G_Ticker/decoder, real P_Init and separate controlled rebirth.
 * Trace contains only the natural 2600-tic run. The extra rebirth stimulus
 * happens afterwards, and is never presented as natural demo behavior. */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "g_game.h"
#include "p_setup.h"
#include "p_tick.h"
#include "p_mobj.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#if defined(SCD_VISUAL)
#include "camera_wire.h"
#endif
#if defined(SCD_WORLD)
extern void S2B_Capture(uint16_t),S2B_Finish(void);
#endif
#if defined(SCD_ACTORS)
extern void S2C_Capture(uint16_t),S2C_Finish(void);
#endif
#define TRACE ((volatile uint32_t *)0x7C000UL)
extern void SCD_SubTransportReset(void),SCD_SubSetTime(uint32_t),SCD_MetadataInit(void);
extern uint16_t M_R47RandomState(void);
extern void R89_SetAIMode(uint8_t);
static uint32_t hash=2166136261UL;
static uint32_t firstdead=0xFFFFFFFFUL;
static void checkpoint(uint16_t tic)
{
    uint32_t count=0;
    for(thinker_t *t=P_NextThinker(0);t;t=P_NextThinker(t))
        if(t->function==(think_t)P_MobjThinker)count++;
    uint32_t v[8]={tic,_g_player.mo->x,_g_player.mo->y,_g_player.mo->z,
        _g_player.mo->angle,(int32_t)_g_player.health,count,M_R47RandomState()&255u};
    for(uint16_t i=0;i<8;i++){TRACE[(tic/100u)*8u+i]=v[i];hash=(hash^v[i])*16777619UL;}
#if defined(SCD_WORLD)
    S2B_Capture(tic);
#if defined(SCD_ACTORS)
    S2C_Capture(tic);
#endif
#endif

#if defined(SCD_VISUAL)
    volatile uint32_t *cam=(volatile uint32_t *)(S2A_SUB_CAMERA+(uint32_t)(tic/100u)*S2A_CAMERA_BYTES);
    uint32_t c[8]={S2A_CAMERA_MAGIC,tic,_g_player.mo->x,_g_player.mo->y,
        _g_player.mo->z,_g_player.mo->angle,_g_player.viewz,(int32_t)_g_player.health};
    for(uint16_t i=0;i<8;i++)cam[i]=c[i];
#endif

}
void sub_main(void)
{
    REG16(0xFF8002UL)=4;SCD_SubTransportReset();REG16(0xFF8020UL)=0x5343u;
    Z_Init();W_Init();REG16(0xFF8024UL)=0x5802;
    SCD_MetadataInit();P_Init();R89_SetAIMode(0);
    const int16_t lump=W_GetNumForName("DTE1M1");
    const uint8_t *demo=W_GetLumpByNum(lump);
    if(W_LumpLength(lump)!=10414 || demo[0]!=109 || demo[1]!=3 ||
       demo[2]!=1 || demo[3]!=1 || demo[9]!=1)I_Error("Z8 DEMO INPUT");
    _g_gametic=0;_g_basetic=0;_g_menuactive=false;_g_timingdemo=false;
    G_DeferedPlayDemo("DTE1M1");
    /* First original G_Ticker loads map, decodes command and runs P_Ticker.
     * Capture t=0 inside real P_Ticker before its first simulation step. */
    for(uint16_t tic=0;tic<2600;tic++){
        SCD_SubSetTime(tic);G_Ticker();_g_gametic++;
        if(!_g_player.mo || _g_gamestate!=GS_LEVEL)I_Error("Z8 LEFT LEVEL");
        if(_g_player.health<=0 && firstdead==0xFFFFFFFFUL)firstdead=tic+1;
        REG16(0xFF8026UL)=tic+1;
        if((tic+1)%100u==0){Z_CheckHeap();checkpoint(tic+1);}
    }
    /* Separate controlled test: request a new genuine demo, then set the
     * same PST_REBORN event G_Ticker receives after death+use. */
    _g_player.playerstate=PST_LIVE;G_DeferedPlayDemo("DTE1M1");
    G_Ticker();_g_gametic++;
    _g_player.playerstate=PST_REBORN;G_Ticker();_g_gametic++;
    if(_g_leveltime!=1 || _g_player.playerstate!=PST_LIVE ||
       !_g_player.mo || _g_player.health!=100)I_Error("Z8 REBIRTH FAILED");
    Z_CheckHeap();
    TRACE[216]=2600;TRACE[217]=1;TRACE[218]=firstdead;TRACE[219]=_g_leveltime;
#if defined(SCD_VISUAL)
    volatile const uint32_t *cam=(volatile const uint32_t *)S2A_SUB_CAMERA;
    uint32_t h=2166136261UL;
    for(uint16_t i=0;i<S2A_CAMERA_COUNT*S2A_CAMERA_WORDS;i++)h=(h^cam[i])*16777619UL;
    volatile uint32_t *meta=(volatile uint32_t *)S2A_SUB_META;
    meta[0]=S2A_META_MAGIC;meta[1]=S2A_CAMERA_COUNT;meta[2]=S2A_CAMERA_BYTES;meta[3]=h;
#endif
#if defined(SCD_WORLD)
    S2B_Finish();
#if defined(SCD_ACTORS)
    S2C_Finish();
#endif
#endif
    REG16(0xFF8028UL)=1;
    REG16(0xFF802AUL)=hash>>16;REG16(0xFF802CUL)=hash;
    REG16(0xFF8024UL)=0x5A8D;REG16(0xFF8020UL)=0x51B1u;
    for(;;){}
}
void SCD_EngineInitialCheckpoint(void){checkpoint(0);}
