/* Read-only observer of the original MD G_Ticker / P_Ticker path.
 * Word RAM scratch only: no persistent MD BSS, no gameplay replacements.
 */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "p_tick.h"
#include "p_mobj.h"
extern uint8_t r116_active;
extern uint16_t M_R47RandomState(void);
void __attribute__((noipa,noinline)) S1E_MDCheckpoint(void)
{ __asm__ volatile("" ::: "memory"); }
void __attribute__((noipa,noinline)) S1E_MDObserve(void)
{
    if(r116_active!=1 || _g_gamestate!=GS_LEVEL || !_g_player.mo ||
       _g_leveltime<0 || _g_leveltime>2600 || _g_leveltime%100) return;
    uint32_t count=0;
    for(thinker_t *t=P_NextThinker(0);t;t=P_NextThinker(t))
        if(t->function==(think_t)P_MobjThinker)count++;
    volatile uint32_t *dst=(volatile uint32_t *)0x61C000UL;
    dst[0]=_g_leveltime;
    dst[1]=_g_player.mo->x;dst[2]=_g_player.mo->y;dst[3]=_g_player.mo->z;
    dst[4]=_g_player.mo->angle;dst[5]=(int32_t)_g_player.health;
    dst[6]=count;dst[7]=M_R47RandomState()&255u;
    dst[8]=_g_gametic;dst[9]=_g_basetic;
    S1E_MDCheckpoint();
}
