#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "doomdef.h"
#include "globdata.h"
#include "r_main.h"
#include "i_system.h"
#include "live_wire.h"
#define R16(a) (*(volatile uint16_t *)(a))
extern void S2A_InitLocalMap(void),S2A_Display(void),S2A_ClearMenus(void),R20_StopVideo(void);
extern void S2B_Init(void),S2B_ApplyFrame(uint16_t),S2C_Begin(void),S2C_ApplyFrame(uint16_t),S2C_End(void);
extern int16_t SCD_MdServeOnce(void);
extern uint16_t SCD_MdLastCommand(void);
volatile uint16_t s2d_test_buttons __attribute__((section(".data")))=0xffff;
volatile uint8_t s2d_test_exit __attribute__((section(".data")))=0;
static uint32_t expected_tic;
static uint16_t stop_sent;
void __attribute__((noipa,noinline)) S2D_MDFrameDone(void){__asm__ volatile("":::"memory");}
uint16_t S2D_PrepareInput(void){
    JOY_update(); /* required on the R128 hardware path; no MD ticker */
    uint16_t joy=s2d_test_buttons==0xffff?JOY_readJoypad(JOY_1):s2d_test_buttons;
    stop_sent=s2d_test_exit || (joy&BUTTON_START);
    int8_t forward=0,side=0;int16_t turn=0;uint16_t buttons=0;
    if(joy&BUTTON_UP)forward=(joy&BUTTON_C)?50:25;
    if(joy&BUTTON_DOWN)forward=(joy&BUTTON_C)?-50:-25;
    if(joy&BUTTON_C){if(joy&BUTTON_LEFT)side=-24;if(joy&BUTTON_RIGHT)side=24;}
    else{if(joy&BUTTON_LEFT)turn=640;if(joy&BUTTON_RIGHT)turn=-640;}
    if(joy&BUTTON_A)buttons|=BT_USE;
    if(joy&BUTTON_B)buttons|=BT_ATTACK;
    volatile uint8_t *p=(volatile uint8_t *)0x600100UL;
    *(volatile uint32_t *)p=S2D_INPUT_MAGIC;*(volatile uint32_t *)(p+4)=expected_tic;
    p[8]=forward;p[9]=side;*(volatile int16_t *)(p+10)=turn;
    *(volatile uint16_t *)(p+12)=buttons;*(volatile uint16_t *)(p+14)=stop_sent;
    return 16;
}
static void copy_frame(void){
    volatile const uint8_t *src=(volatile const uint8_t *)0x601000UL;
    volatile const uint32_t *h=(volatile const uint32_t *)src;
    uint32_t total=h[3],wb=h[4],ab=h[5];
    if(h[0]!=S2D_MAGIC || h[1]!=1 || h[2]!=expected_tic || h[6] ||
       wb<272 || wb>8192 || ab<272 || ab>8192 || total!=256+wb+ab || total>S2D_MAX_FRAME)I_Error("S2D LIVE HEADER");
    uint32_t hash=2166136261UL;
    for(uint16_t i=0;i<total;i++)hash=(hash^((i>=28 && i<32)?0:src[i]))*16777619UL;
    if(hash!=h[7])I_Error("S2D LIVE CHECKSUM");
    volatile uint8_t *camera=(volatile uint8_t *)0x61A000UL;
    for(uint16_t i=0;i<256;i++)camera[i]=src[i];
    /* Forward copy is safe: world destination precedes its source. Actor
     * source ends below0x608000 for the bounded combined frame. */
    for(uint16_t i=0;i<wb;i++)((volatile uint8_t *)0x600000UL)[i]=src[256+i];
    for(uint16_t i=0;i<ab;i++)((volatile uint8_t *)0x608000UL)[i]=src[256+wb+i];
    if(*(volatile const uint32_t *)0x600008UL!=1 || *(volatile const uint32_t *)0x608008UL!=1)I_Error("S2D BLOB COUNT");
}
static void apply_player(void){
    volatile const uint32_t *h=(volatile const uint32_t *)0x61A000UL;
    _g_player.mo->x=h[10];_g_player.mo->y=h[11];_g_player.mo->z=h[12];_g_player.mo->angle=h[13];
    _g_player.viewz=h[14];_g_player.health=h[16];_g_player.mo->health=h[16];_g_player.armorpoints=h[17];
    _g_player.mo->subsector=R_PointInSubsector(_g_player.mo->x,_g_player.mo->y);
    for(uint16_t i=0;i<4;i++)_g_player.ammo[i]=h[18+i];
    if(h[22]>=NUMWEAPONS || (h[23]>=NUMWEAPONS && h[23]!=wp_nochange))I_Error("S2D WEAPON ID");
    _g_player.readyweapon=h[22];_g_player.pendingweapon=h[23];
    for(uint16_t i=0;i<NUMWEAPONS;i++)_g_player.weaponowned[i]=!!(h[24]&(1UL<<i));
    _g_player.damagecount=h[25];_g_player.bonuscount=h[26];_g_player.armortype=h[27];
    for(uint16_t i=0;i<NUMPOWERS;i++)_g_player.powers[i]=h[28+i];
    _g_player.killcount=h[34];_g_player.itemcount=h[35];_g_player.secretcount=h[36];
    for(uint16_t i=0;i<NUMPSPRITES;i++){
        volatile const uint32_t *v=h+40+i*4;
        if(v[0]!=0xffffffffUL && v[0]>=NUMSTATES)I_Error("S2D PSPRITE ID");
        _g_player.psprites[i].state=v[0]==0xffffffffUL?0:&states[v[0]];
        _g_player.psprites[i].sx=v[1];_g_player.psprites[i].sy=v[2];_g_player.psprites[i].tics=v[3];
    }
    volatile uint32_t *audit=(volatile uint32_t *)0x61B100UL;
    audit[0]=_g_player.readyweapon;audit[1]=_g_player.pendingweapon;
    for(uint16_t i=0;i<NUMPSPRITES;i++){
        audit[2+i*4]=_g_player.psprites[i].state?(uint32_t)(_g_player.psprites[i].state-states):0xffffffffUL;
        audit[3+i*4]=(int32_t)_g_player.psprites[i].sx;
        audit[4+i*4]=_g_player.psprites[i].sy;audit[5+i*4]=(int32_t)_g_player.psprites[i].tics;
    }
    _g_gametic=expected_tic;
}
void S2D_Run(void){
    volatile const uint16_t *boot=(volatile const uint16_t *)0x61F000UL;
    if(boot[0]!=5 || boot[3]!=0x5A9D)return;
    S2A_ClearMenus();S2A_InitLocalMap();
    JOY_update();
    while(JOY_readJoypad(JOY_1)&BUTTON_START){SYS_doVBlankProcess();JOY_update();}
    _g_menuactive=false;_g_demoplayback=false;wipegamestate=GS_LEVEL;
    expected_tic=0;stop_sent=0;
    uint32_t saved[256];uint16_t nr=0,ns=0,initialized=0;
    R16(0xA12010UL)=0xD04D;
    for(;;){
        int16_t served=0;
        for(uint32_t spins=0;spins<200000000UL;spins++){
            if(R16(0xA12020UL)==0xDEAD)I_Error("S2D SUB ERROR");
            if(R16(0xA12020UL)==0xD04F)goto done;
            served=SCD_MdServeOnce();
            if(served<0)I_Error("S2D SWAP TIMEOUT");
            if(served>0 && SCD_MdLastCommand()==3)break;
        }
        if(served<=0)I_Error("S2D NO FRAME");
        copy_frame();
        if(!initialized){
            S2B_Init();S2C_Begin();
            nr=*(volatile const uint32_t *)0x60800CUL;ns=_g_numsectors;
            if(nr+ns+7>256)I_Error("S2D BANK BACKUP LIMIT");
            for(uint16_t i=0;i<nr;i++)saved[i]=((volatile uint32_t *)0x61C000UL)[i];
            for(uint16_t i=0;i<ns;i++)saved[nr+i]=((volatile uint32_t *)0x61C800UL)[i];
            for(uint16_t i=0;i<7;i++)saved[nr+ns+i]=((volatile uint32_t *)0x61CC00UL)[i];
            initialized=1;
        }
        /* Owned Word RAM bank alternates every transaction. Reinstall the
         * original local-state backup before application and eventual exit. */
        for(uint16_t i=0;i<nr;i++)((volatile uint32_t *)0x61C000UL)[i]=saved[i];
        for(uint16_t i=0;i<ns;i++)((volatile uint32_t *)0x61C800UL)[i]=saved[nr+i];
        for(uint16_t i=0;i<7;i++)((volatile uint32_t *)0x61CC00UL)[i]=saved[nr+ns+i];
        S2B_ApplyFrame(0);S2C_ApplyFrame(0);apply_player();
        if(expected_tic){
            S2A_Display();R20_StopVideo();
            SYS_disableInts();VDP_drawText("S2D LOGIC ON SEGA CD / LIVE INPUT",1,1);
            VDP_drawText("A USE B FIRE C STRAFE / START EXIT",1,2);SYS_enableInts();
        }
        volatile uint32_t *r=(volatile uint32_t *)0x61B000UL;
        r[0]=expected_tic;r[1]=_g_player.mo->x;r[2]=_g_player.mo->y;r[3]=_g_player.mo->angle;
        r[4]=_g_player.health;r[5]=_g_player.ammo[0];r[6]=R16(0xA12002UL)&5u;
        S2D_MDFrameDone();expected_tic++;
        if(stop_sent)goto done;
    }
 done:
    if(initialized)S2C_End();
    R16(0xA12010UL)=0;R20_StopVideo();
}
