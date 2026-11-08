#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "g_game.h"
#include "p_setup.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#include "live_wire.h"
#define R16(a) (*(volatile uint16_t *)(a))
extern void SCD_SubTransportReset(void),SCD_SubSetTime(uint32_t),SCD_MetadataInit(void),R89_SetAIMode(uint8_t);
extern void S2B_Capture(uint16_t),S2B_Finish(void),S2C_Capture(uint16_t),S2C_Finish(void);
extern int SCD_SubLiveInput(uint32_t,uint8_t *);
extern void S2D_SetCommand(int8_t,int8_t,int16_t,uint8_t);
static uint8_t echo[16];
static void publish(uint32_t tic){
    S2B_Capture(0);S2B_Finish();S2C_Capture(0);S2C_Finish();
    uint32_t wb=*(volatile const uint32_t *)0x74014UL,ab=*(volatile const uint32_t *)0x68010UL;
    uint32_t total=256+wb+ab;
    if(wb>8192 || ab>8192 || total>S2D_MAX_FRAME)I_Error("S2D FRAME BOUNDS");
    volatile uint8_t *p=(volatile uint8_t *)(0xC0000UL+S2D_FRAME_OFFSET);
    for(uint16_t i=0;i<256;i++)p[i]=0;
    volatile uint32_t *h=(volatile uint32_t *)p;
    h[0]=S2D_MAGIC;h[1]=1;h[2]=tic;h[3]=total;h[4]=wb;h[5]=ab;h[6]=0;h[7]=0;
    h[8]=0x53324341UL;h[9]=tic;h[10]=_g_player.mo->x;h[11]=_g_player.mo->y;
    h[12]=_g_player.mo->z;h[13]=_g_player.mo->angle;h[14]=_g_player.viewz;h[15]=(int32_t)_g_player.health;
    h[16]=_g_player.health;h[17]=_g_player.armorpoints;
    for(uint16_t i=0;i<4;i++)h[18+i]=_g_player.ammo[i];
    h[22]=_g_player.readyweapon;h[23]=_g_player.pendingweapon;
    uint32_t owned=0;for(uint16_t i=0;i<NUMWEAPONS;i++)if(_g_player.weaponowned[i])owned|=1UL<<i;
    h[24]=owned;h[25]=_g_player.damagecount;h[26]=_g_player.bonuscount;h[27]=_g_player.armortype;
    for(uint16_t i=0;i<NUMPOWERS;i++)h[28+i]=_g_player.powers[i];
    h[34]=_g_player.killcount;h[35]=_g_player.itemcount;h[36]=_g_player.secretcount;
    for(uint16_t i=0;i<NUMPSPRITES;i++){
        volatile uint32_t *v=h+40+i*4;
        v[0]=_g_player.psprites[i].state?(uint32_t)(_g_player.psprites[i].state-states):0xffffffffUL;
        v[1]=_g_player.psprites[i].sx;v[2]=_g_player.psprites[i].sy;v[3]=(int32_t)_g_player.psprites[i].tics;
    }
    for(uint16_t i=0;i<16;i++)p[192+i]=echo[i];
    for(uint16_t i=0;i<wb;i++)p[256+i]=((volatile const uint8_t *)0x74000UL)[i];
    for(uint16_t i=0;i<ab;i++)p[256+wb+i]=((volatile const uint8_t *)0x68000UL)[i];
    uint32_t hash=2166136261UL;for(uint16_t i=0;i<total;i++)hash=(hash^p[i])*16777619UL;h[7]=hash;
}
void SCD_EngineInitialCheckpoint(void){} /* no offline checkpoint observer */
void sub_main(void){
    R16(0xFF8002UL)=4;SCD_SubTransportReset();R16(0xFF8020UL)=0x5343;
    Z_Init();W_Init();SCD_MetadataInit();P_Init();R89_SetAIMode(0);
    const uint8_t *demo=W_GetLumpByName("DTE1M1");if(demo[0]!=109)I_Error("S2D BASE DEMO");
    _g_gametic=0;_g_basetic=0;_g_menuactive=false;_g_timingdemo=false;
    G_InitNew(sk_hard,1);_g_demoplayback=false;
    R16(0xFF8024UL)=0x5A9D;R16(0xFF802AUL)=0;R16(0xFF802CUL)=0;R16(0xFF8020UL)=0x51B1;
    while(R16(0xFF8010UL)!=0xD04D){} /* startup screen: no timed transport wait */
    for(uint32_t tic=0;;tic++){
        publish(tic);
        uint8_t input[16];if(!SCD_SubLiveInput(tic,input))I_Error("S2D INPUT TRANSPORT");
        for(uint16_t i=0;i<16;i++)echo[i]=input[i];
        if(input[14] || input[15])break;
        if(_g_gameaction!=ga_nothing && _g_gameaction!=ga_loadlevel)break; /* level-end boundary */
        int16_t turn=(int16_t)(((uint16_t)input[10]<<8)|input[11]);
        S2D_SetCommand((int8_t)input[8],(int8_t)input[9],turn,input[13]);
        SCD_SubSetTime(tic);G_Ticker();_g_gametic++;
        if(!_g_player.mo || _g_gamestate!=GS_LEVEL)break;
        if(!(tic&63))Z_CheckHeap();
    }
    R16(0xFF8020UL)=0xD04F;for(;;){}
}
