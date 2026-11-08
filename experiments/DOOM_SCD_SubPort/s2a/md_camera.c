/* Real sub-camera -> original MD renderer. This is NOT a full world snapshot.
 * The local map/actors are initialized once; MD simulation is never ticked. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "doomdef.h"
#include "globdata.h"
#include "r_main.h"
#include "i_system.h"
#include "camera_wire.h"
#if defined(SCD_WORLD)
extern void S2B_Init(void),S2B_ApplyFrame(uint16_t);
#endif
#if defined(SCD_ACTORS)
extern void S2C_Begin(void),S2C_ApplyFrame(uint16_t),S2C_End(void);
#define REPLAY_EXIT() do {S2C_End();return;} while(0)
#else
#define REPLAY_EXIT() return
#endif
extern void S2A_InitLocalMap(void),S2A_Display(void),S2A_ClearMenus(void),R20_StopVideo(void);
volatile uint8_t s2a_test_exit __attribute__((section(".data")))=0; /* debugger only */
void __attribute__((noipa,noinline)) S2A_MDFrameDone(void){__asm__ volatile("":::"memory");}
void __attribute__((noipa,noinline)) S2A_VisualDone(void){__asm__ volatile("":::"memory");}
static uint32_t camera_hash(void)
{
    volatile const uint32_t *p=(volatile const uint32_t *)S2A_MD_CAMERA;
    uint32_t h=2166136261UL;
    for(uint16_t i=0;i<S2A_CAMERA_COUNT*S2A_CAMERA_WORDS;i++)h=(h^p[i])*16777619UL;
    return h;
}
void S2A_Run(void)
{
    volatile const uint16_t *report=(volatile const uint16_t *)0x61F000UL;
    if(report[0]!=5 || report[3]!=0x5A8Du)return;
    volatile const uint32_t *meta=(volatile const uint32_t *)S2A_MD_META;
    if(meta[0]!=S2A_META_MAGIC || meta[1]!=S2A_CAMERA_COUNT ||
       meta[2]!=S2A_CAMERA_BYTES || meta[3]!=camera_hash())I_Error("S2A CAMERA PACKET");
    S2A_ClearMenus();S2A_InitLocalMap();
#if defined(SCD_WORLD)
    S2B_Init();
#if defined(SCD_ACTORS)
    S2C_Begin();
#endif
#endif
    while(JOY_readJoypad(JOY_1)&BUTTON_START)SYS_doVBlankProcess();
    _g_menuactive=false;_g_demoplayback=false;_g_basetic=0;
    wipegamestate=GS_LEVEL;
    for(;;){
        if(s2a_test_exit)REPLAY_EXIT();
#if defined(SCD_WORLD)
        S2B_ApplyFrame(0);
#if defined(SCD_ACTORS)
        S2C_ApplyFrame(0);
#endif
#endif
        /* Skip pre-first-tic camera0 (viewz=1 by original setup contract). */
        for(uint16_t i=1;i<S2A_CAMERA_COUNT;i++){
            volatile const uint32_t *p=(volatile const uint32_t *)(S2A_MD_CAMERA+(uint32_t)i*S2A_CAMERA_BYTES);
            if(p[0]!=S2A_CAMERA_MAGIC || p[1]!=(uint32_t)i*100u)I_Error("S2A CAMERA ORDER");
#if defined(SCD_WORLD)
            S2B_ApplyFrame(i);
#if defined(SCD_ACTORS)
            S2C_ApplyFrame(i);
#endif
#endif
            _g_player.mo->x=(int32_t)p[2];_g_player.mo->y=(int32_t)p[3];
            _g_player.mo->z=(int32_t)p[4];_g_player.mo->angle=p[5];
            _g_player.viewz=(int32_t)p[6];_g_player.health=(int32_t)p[7];
            _g_player.mo->subsector=R_PointInSubsector(_g_player.mo->x,_g_player.mo->y);
            if(!_g_player.mo->subsector)I_Error("S2A CAMERA SUBSECTOR");
            _g_gametic=p[1];
            S2A_Display();
            R20_StopVideo(); /* complete posted DMA before text overlays */
            SYS_disableInts();
#if defined(SCD_ACTORS)
            VDP_drawText("S2C CAMERA WORLD ACTORS FROM CD",1,1);
            VDP_drawText("OFFLINE REPLAY / START EXIT",1,2);
#elif defined(SCD_WORLD)
            VDP_drawText("S2B CAMERA AND WORLD FROM CD",1,1);
            VDP_drawText("ACTORS LOCAL FROZEN / START EXIT",1,2);
#else
            VDP_drawText("S2A CAMERA FROM SEGA CD",1,1);
            VDP_drawText("LOCAL ACTORS FROZEN / START EXIT",1,2);
#endif
            SYS_enableInts();
            volatile uint32_t *out=(volatile uint32_t *)S2A_MD_REPORT;
            out[0]=i;out[1]=p[1];out[2]=_g_player.mo->x;out[3]=_g_player.mo->y;
            out[4]=_g_player.mo->z;out[5]=_g_player.mo->angle;
            out[6]=_g_player.viewz;out[7]=(int32_t)_g_player.health;
            S2A_MDFrameDone();
            for(uint16_t hold=0;hold<45;hold++){
                SYS_doVBlankProcess();
                if(JOY_readJoypad(JOY_1)&BUTTON_START)REPLAY_EXIT();
            }
        }
        S2A_VisualDone();
    }
}
