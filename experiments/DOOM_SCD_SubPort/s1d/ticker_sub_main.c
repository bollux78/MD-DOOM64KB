/* Z6: real P_Ticker simulation on sub-68000, no renderer.
 * Deliberately NOT a claim of full G_Ticker integration. Demo input is v1.9
 * DTE1M1 from the same private WAD as R116, decoded exactly as G_ReadDemoTiccmd.
 * Unexpected level transitions, rebirth or demo exhaustion fail closed.
 */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "g_game.h"
#include "p_setup.h"
#include "p_tick.h"
#include "p_map.h"
#include "p_mobj.h"
#include "m_random.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define TRACE ((volatile uint32_t *)0x7C000UL)
extern void SCD_SubTransportReset(void), SCD_SubSetTime(uint32_t);
extern uint16_t M_R47RandomState(void);
extern void R89_SetAIMode(uint8_t);
static uint32_t hash=2166136261UL;
static void checkpoint(uint16_t tic)
{
    uint32_t count=0;
    for(thinker_t *t=P_NextThinker(0);t;t=P_NextThinker(t))
        if(t->function==(think_t)P_MobjThinker)count++;
    uint32_t values[8]={tic,(uint32_t)_g_player.mo->x,
        (uint32_t)_g_player.mo->y,(uint32_t)_g_player.mo->z,
        _g_player.mo->angle,(uint32_t)(int32_t)_g_player.health,
        count,M_R47RandomState()&255u};
    for(uint16_t i=0;i<8;i++){
        TRACE[(tic/100u)*8u+i]=values[i];
        hash=(hash^values[i])*16777619UL;
    }
}
void sub_main(void)
{
    REG16(0xFF8002UL)=4;
    SCD_SubTransportReset();
    REG16(0xFF8020UL)=0x5343u;
    Z_Init(); W_Init();
    int16_t lump=W_GetNumForName("DTE1M1");
    const uint8_t *demo=W_GetLumpByNum(lump);
    uint16_t size=W_LumpLength(lump);
    if(size<13u+2600u*4u+1u || demo[0]!=109 || demo[1]!=3 ||
       demo[2]!=1 || demo[3]!=1 || demo[9]!=1 ||
       demo[4] || demo[5] || demo[6] || demo[7] || demo[8] ||
       demo[10] || demo[11] || demo[12]) I_Error("Z6 DEMO HEADER");
    M_ClearRandom(); R89_SetAIMode(0);
    _g_gamestate=GS_LEVEL; _g_gameskill=(skill_t)demo[1]; _g_gamemap=1;
    _g_player.playerstate=PST_REBORN;
    REG16(0xFF8024UL)=0x5801u;
    P_SetSecnodeFirstpoolToNull(); P_SetupLevel(1);
    _g_gameaction=ga_nothing; _g_demoplayback=true; _g_usergame=false;
    _g_gametic=0; _g_basetic=0; _g_menuactive=false;
    if(!_g_player.mo || _g_player.health!=100 || _g_totalkills<=0)
        I_Error("Z6 SETUP");
    checkpoint(0);
    for(uint16_t tic=0;tic<2600;tic++){
        const uint8_t *p=demo+13u+(uint32_t)tic*4u;
        if(*p==0x80 || _g_gameaction!=ga_nothing ||
           _g_gamestate!=GS_LEVEL || _g_player.playerstate==PST_REBORN)
            I_Error("Z6 UNEXPECTED TRANSITION");
        _g_player.cmd.forwardmove=(int8_t)p[0];
        _g_player.cmd.sidemove=(int8_t)p[1];
        _g_player.cmd.angleturn=(uint16_t)p[2]<<8;
        _g_player.cmd.buttons=p[3];
        SCD_SubSetTime(tic);
        P_MapEnd();
        P_Ticker(); /* actual engine: player, monsters, thinkers, specials */
        _g_gametic++;
        REG16(0xFF8026UL)=tic+1;
        if((tic+1)%100u==0){Z_CheckHeap();checkpoint(tic+1);}
    }
    if(_g_leveltime!=2600 || _g_gametic!=2600) I_Error("Z6 TIC COUNT");
    REG16(0xFF802AUL)=hash>>16; REG16(0xFF802CUL)=hash;
    REG16(0xFF8024UL)=0x5A7Du;
    REG16(0xFF8020UL)=0x51B1u;
    for(;;){}
}
