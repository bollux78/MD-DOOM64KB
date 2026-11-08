/* Per-bank persistent render proxies. No MD simulation or foreign pointers. */
#include <stddef.h>
#include <stdint.h>
#include "actors_wire.h"
#include "compact.h"
#include "i_system.h"
#define BASE ((volatile const uint8_t *)S2C_MD_BASE)
#define HEAD ((volatile const uint32_t *)S2C_MD_BASE)
#define POOL ((mobj_t *)S2C_MD_POOL)
#define IDS ((uint16_t *)0x618000UL)
#define SEC ((uint16_t *)0x618080UL)
#define LINK ((uint16_t *)0x618100UL)
#define VALID (*(uint16_t *)0x618180UL)
#define HC (*(uint16_t *)0x618182UL)
#define HS ((uint16_t *)0x618200UL)
#define HP ((mobj_t **)0x618280UL)
#define REP ((subsector_t **)0x618400UL)
#define SLOTS ((uint16_t *)0x617C00UL)
#define SAVED_ROM ((uint32_t *)0x61C000UL)
#define SAVED_PLAYER ((int32_t *)0x61CC00UL)
#define SAVED_HEADS ((mobj_t **)0x61C800UL)
static uint16_t romcount;
void M15_PrepareSwap(void){
 if(VALID!=0x1531)return;
 for(uint16_t i=0;i<HC;i++){HP[i]=_g_sectors[HS[i]].thinglist;_g_sectors[HS[i]].thinglist=0;}
}
void S2C_Begin(void){
 if(sizeof(mobj_t)*64>0x3000 || _g_numsectors>256)I_Error("M15 PROXY MEMORY");
 romcount=S2C_RomCount();
 if(HEAD[0]!=S2C_MAGIC || HEAD[1]!=2 || HEAD[2]!=1 || HEAD[3]!=romcount || HEAD[6]!=24 || romcount>512)I_Error("M15 ACTOR HEADER");
 SAVED_PLAYER[0]=_g_player.mo->x;SAVED_PLAYER[1]=_g_player.mo->y;SAVED_PLAYER[2]=_g_player.mo->z;
 SAVED_PLAYER[3]=_g_player.mo->angle;SAVED_PLAYER[4]=_g_player.viewz;SAVED_PLAYER[5]=_g_player.health;SAVED_PLAYER[6]=_g_leveltime;
 for(uint16_t i=0;i<romcount;i++)SAVED_ROM[i]=((uint32_t)S2C_RomDead(i)<<16)|S2C_RomDelay(i);
 for(uint16_t i=0;i<_g_numsectors;i++)SAVED_HEADS[i]=_g_sectors[i].thinglist;
}
void S2C_End(void){
 _g_player.mo->x=SAVED_PLAYER[0];_g_player.mo->y=SAVED_PLAYER[1];_g_player.mo->z=SAVED_PLAYER[2];
 _g_player.mo->angle=SAVED_PLAYER[3];_g_player.viewz=SAVED_PLAYER[4];_g_player.health=SAVED_PLAYER[5];
 _g_player.mo->subsector=R_PointInSubsector(_g_player.mo->x,_g_player.mo->y);_g_leveltime=SAVED_PLAYER[6];
 for(uint16_t i=0;i<_g_numsectors;i++)_g_sectors[i].thinglist=SAVED_HEADS[i];
 for(uint16_t i=0;i<romcount;i++)S2C_RomApply(i,SAVED_ROM[i]>>16,SAVED_ROM[i]);
 *(volatile uint32_t *)0x61B0A0UL=1;
}
static void unlink_slot(uint16_t i){mobj_t *m=&POOL[i];if(LINK[i]){if(m->snext)m->snext->sprev=m->sprev;*m->sprev=m->snext;LINK[i]=0;}}
void S2C_ApplyFrame(uint16_t frame){
 if(frame || HEAD[0]!=S2C_MAGIC || HEAD[1]!=2 || HEAD[6]!=24 || HEAD[4]<272 || HEAD[4]>8192)I_Error("M15 FRAME HEADER");
 volatile const uint8_t *p=BASE+256;
 uint16_t n=*(volatile const uint16_t *)(p+4),nr=*(volatile const uint16_t *)(p+6),player=*(volatile const uint16_t *)(p+12);
 uint32_t want=*(volatile const uint32_t *)(p+8);
 if(!n || n>64 || nr>romcount || 272UL+(uint32_t)n*24+(uint32_t)nr*8!=HEAD[4])I_Error("M15 RECORD BOUNDS");
 if(VALID!=0x1531){
  for(uint16_t i=0;i<64;i++){IDS[i]=0;LINK[i]=0;}
  for(uint16_t s=0;s<_g_numsectors;s++){_g_sectors[s].thinglist=0;REP[s]=0;}
  for(uint16_t i=0;i<_g_numsubsectors;i++){
   subsector_t *ss=&_g_subsectors[i];uint16_t s=SUBSECTOR_SECTOR(ss)-_g_sectors;if(s>=_g_numsectors)I_Error("M15 MAP SECTOR");
   if(!REP[s])REP[s]=ss;
  }
  HC=0;VALID=0x1531;
 }else for(uint16_t i=0;i<HC;i++)_g_sectors[HS[i]].thinglist=HP[i];
 uint8_t seen[64]={0};uint16_t assigned[64],fresh=0,moved=0,removed=0,found=0;
 p+=16;
 for(uint16_t j=0;j<n;j++){
  uint16_t id=*(volatile const uint16_t *)(p+(uint32_t)j*24);if(!id)I_Error("M15 ZERO ID");
  assigned[j]=65535;
  for(uint16_t i=0;i<64;i++)if(IDS[i]==id){if(seen[i])I_Error("M15 DUPLICATE ID");seen[i]=1;assigned[j]=i;break;}
  for(uint16_t k=0;k<j;k++)if(*(volatile const uint16_t *)(p+(uint32_t)k*24)==id)I_Error("M15 DUPLICATE NEW ID");
 }
 for(uint16_t i=0;i<64;i++)if(IDS[i] && !seen[i]){unlink_slot(i);IDS[i]=0;removed++;}
 extern volatile uint8_t s2e_test_deep;
 uint16_t checked=s2e_test_deep || !(*(volatile const uint32_t *)0x61A008UL&31u);
 uint32_t h=checked?M15_Mix(M15_Mix(M15_Mix(2166136261UL,n),romcount),player):0;
 HC=0;uint16_t linked=0;
 for(uint16_t j=0;j<n;j++,p+=24){
  uint16_t id=*(volatile const uint16_t *)p,type=*(volatile const uint16_t *)(p+2),sector=*(volatile const uint16_t *)(p+22),i=assigned[j];
  if(type>=NUMMOBJTYPES || sector>=_g_numsectors || !REP[sector] || *(volatile const uint16_t *)(p+18)>=NUMSPRITES)I_Error("M15 ACTOR FIELDS");
  if(i==65535){for(i=0;i<64 && IDS[i];i++){}if(i==64)I_Error("M15 POOL FULL");
   uint32_t *z=(uint32_t *)&POOL[i];for(uint16_t k=0;k<sizeof(mobj_t)/4;k++)z[k]=0;
   for(uint16_t k=(sizeof(mobj_t)/4)*4;k<sizeof(mobj_t);k++)((uint8_t *)&POOL[i])[k]=0;
   IDS[i]=id;SEC[i]=65535;LINK[i]=0;POOL[i].type=type;
   MOBJ_SET_RADIUS(&POOL[i],mobjinfo[type].radius);MOBJ_SET_HEIGHT(&POOL[i],mobjinfo[type].height);fresh++;
  }else if(POOL[i].type!=type)I_Error("M15 ID TYPE CHANGED");
  SLOTS[j]=i;mobj_t *m=&POOL[i];uint32_t flags=M15_Expand(p[17]);
  uint16_t relink=SEC[i]!=sector || LINK[i]!=!(flags&MF_NOSECTOR);
  if(relink){unlink_slot(i);moved++;}
  m->x=*(volatile const int32_t *)(p+4);m->y=*(volatile const int32_t *)(p+8);m->z=*(volatile const int32_t *)(p+12);
  m->angle=(uint32_t)p[16]<<24;m->flags=flags;m->sprite=*(volatile const uint16_t *)(p+18);m->frame=*(volatile const uint16_t *)(p+20);
  m->subsector=REP[sector];SEC[i]=sector;
  m->floorz=m->dropoffz=_g_sectors[sector].floorheight;m->ceilingz=_g_sectors[sector].ceilingheight;
  if(checked && SUBSECTOR_SECTOR(R_PointInSubsector(m->x,m->y))!=&_g_sectors[sector])I_Error("M15 SPATIAL SECTOR");
  if(relink && !(flags&MF_NOSECTOR)){mobj_t **head=&_g_sectors[sector].thinglist;m->snext=*head;m->sprev=head;if(*head)(*head)->sprev=&m->snext;*head=m;LINK[i]=1;}
  if(LINK[i]){linked++;uint16_t k;for(k=0;k<HC && HS[k]!=sector;k++){}if(k==HC){HS[HC++]=sector;}}
  if(id==player)found++;
  uint32_t v[10];M15_Values(m,id,v);if(checked)for(uint16_t k=0;k<10;k++)h=M15_Mix(h,v[k]);
  M15_Write((volatile uint8_t *)(S2C_MD_APPLIED+(uint32_t)j*24),v);
 }
 if(found!=1)I_Error("M15 PLAYER MEMBERSHIP");
 for(uint16_t j=0;j<nr;j++,p+=8){uint16_t id=*(volatile const uint16_t *)p,dead=*(volatile const uint16_t *)(p+2),delay=*(volatile const uint16_t *)(p+4);if(id>=romcount || dead>1)I_Error("M15 ROM DELTA");S2C_RomApply(id,dead,delay);}
 if(checked){
  uint16_t count=0;
  for(uint16_t j=0;j<HC;j++){mobj_t **prev=&_g_sectors[HS[j]].thinglist;
   for(mobj_t *m=*prev;m;m=m->snext){if(++count>n || m<POOL || m>=POOL+64 || m->sprev!=prev || *prev!=m || SUBSECTOR_SECTOR(m->subsector)!=&_g_sectors[HS[j]])I_Error("M15 SPATIAL LINKS");prev=&m->snext;}}
  if(count!=linked)I_Error("M15 LINK COUNT");
  for(uint16_t i=0;i<romcount;i++)h=M15_Mix(M15_Mix(h,S2C_RomDead(i)),S2C_RomDelay(i));
  if(h!=want)I_Error("M15 APPLIED ACTOR HASH");
 }
 volatile uint32_t *r=(volatile uint32_t *)S2C_MD_REPORT;
 r[0]=want;r[1]=h;r[2]=n;r[3]=player;r[4]=nr;r[5]=linked;r[6]=sizeof(mobj_t);r[7]=offsetof(mobj_t,snext);r[8]=offsetof(mobj_t,sprev);r[9]=offsetof(mobj_t,subsector);r[10]=sizeof(sector_t);r[11]=offsetof(sector_t,thinglist);r[12]=checked;r[13]=moved;r[14]=fresh;r[15]=removed;
 volatile uint32_t *o=(volatile uint32_t *)0x61B300UL;
 o[0]=offsetof(mobj_t,type);o[1]=offsetof(mobj_t,x);o[2]=offsetof(mobj_t,y);o[3]=offsetof(mobj_t,z);o[4]=offsetof(mobj_t,angle);o[5]=offsetof(mobj_t,flags);o[6]=offsetof(mobj_t,sprite);o[7]=offsetof(mobj_t,frame);

}
