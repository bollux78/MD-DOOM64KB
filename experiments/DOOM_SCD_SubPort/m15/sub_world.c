/* Conservative dirty union: every field ever changed is resent. This small
 * superset of delivery deltas allows an old immutable snapshot to be delivered
 * while a new snapshot is being assembled, including A->B->A reversions. */
#include <stdint.h>
#include "world_wire.h"
#include "world_values.h"
#include "w_wad.h"
#include "i_system.h"
static uint32_t prev_sector[S2B_MAX_SECTORS][4],prev_side[S2B_MAX_SIDES][2];
static uint8_t dirty_sector[S2B_MAX_SECTORS],dirty_side[S2B_MAX_SIDES];
static uint16_t nsec,nside,initialized,delivered;
static uint32_t used;
extern void S2F_ClockPoll(void);
#define BASE ((volatile uint8_t *)S2B_SUB_WORLD)
#define HEAD ((volatile uint32_t *)S2B_SUB_WORLD)
static volatile uint8_t *reserve(uint16_t n){if(used+n>S2B_CAPACITY)I_Error("M15 WORLD CAPACITY");volatile uint8_t *p=BASE+used;used+=n;return p;}
void S2B_Capture(uint16_t tic){
 if(tic)I_Error("M15 WORLD ORDER");
 if(!nsec){nsec=_g_numsectors;nside=W_LumpLength(W_GetNumForName("E1M1")+3)/sizeof(mapsidedef_t);if(!nsec || nsec>S2B_MAX_SECTORS || !nside || nside>S2B_MAX_SIDES)I_Error("M15 WORLD COUNTS");}
 used=256;for(uint16_t i=0;i<64;i++)HEAD[i]=0;
 HEAD[0]=S2B_MAGIC;HEAD[1]=1;HEAD[2]=1;HEAD[3]=nsec;HEAD[4]=nside;HEAD[8]=256;
 volatile uint8_t *header=reserve(16);uint16_t ns=0,nd=0;
 uint32_t h=S2B_Mix(S2B_Mix(2166136261UL,nsec),nside);
 for(uint16_t i=0;i<nsec;i++){
  if(!(i&15))S2F_ClockPoll();
  uint32_t v[5];S2B_SectorValues(i,v);for(uint16_t j=0;j<5;j++)h=S2B_Mix(h,v[j]);
  uint32_t packed=((uint32_t)(uint16_t)v[2]<<16)|(uint16_t)v[3];
  if(initialized && (prev_sector[i][0]!=v[0] || prev_sector[i][1]!=v[1] || prev_sector[i][2]!=packed || prev_sector[i][3]!=v[4]))dirty_sector[i]=1;
  if(!delivered || dirty_sector[i]){
   volatile uint8_t *p=reserve(16);*(volatile uint16_t *)p=i;*(volatile uint16_t *)(p+2)=v[4];*(volatile uint32_t *)(p+4)=v[0];*(volatile uint32_t *)(p+8)=v[1];*(volatile uint16_t *)(p+12)=v[2];*(volatile uint16_t *)(p+14)=v[3];ns++;
  }
  prev_sector[i][0]=v[0];prev_sector[i][1]=v[1];prev_sector[i][2]=packed;prev_sector[i][3]=v[4];
 }
 for(uint16_t i=0;i<nside;i++){
  if(!(i&15))S2F_ClockPoll();
  uint32_t v[4];S2B_SideValues(i,v);for(uint16_t j=0;j<4;j++)h=S2B_Mix(h,v[j]);
  uint32_t a=((uint32_t)(uint16_t)v[0]<<16)|((uint32_t)(uint8_t)v[1]<<8)|(uint8_t)v[2],b=(uint8_t)v[3];
  if(initialized && (prev_side[i][0]!=a || prev_side[i][1]!=b))dirty_side[i]=1;
  if(!delivered || dirty_side[i]){volatile uint16_t *p=(volatile uint16_t *)reserve(12);p[0]=i;for(uint16_t j=0;j<4;j++)p[j+1]=v[j];p[5]=0;nd++;}
  prev_side[i][0]=a;prev_side[i][1]=b;
 }
 *(volatile uint32_t *)header=0;*(volatile uint16_t *)(header+4)=ns;*(volatile uint16_t *)(header+6)=nd;*(volatile uint32_t *)(header+8)=h;*(volatile uint32_t *)(header+12)=_g_leveltime;
 initialized=1;
}
void S2B_Finish(void){HEAD[5]=used;HEAD[6]=0;}
void M15_WorldDelivered(void){delivered=1;}
