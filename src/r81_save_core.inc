/* Full-state save/load, explicit records rather than RAM or pointer dumps.
 * Included at the end of g_game.c, where G_InitNew is available. */
#include <string.h>
#include "p_spec.h"
#include "r22_blocklinks.h"
#include "r81_save_io.h"
#include "r81_save_codec.inc"
#define R81_COUNT(a) (sizeof(a)/sizeof((a)[0]))
static const r81_field_t r81_player_fields[]={
 R81_F(player_t,playerstate),
 R81_F(player_t,viewz),R81_F(player_t,viewheight),R81_F(player_t,deltaviewheight),R81_F(player_t,bob),R81_F(player_t,momx),R81_F(player_t,momy),
 R81_F(player_t,health),R81_F(player_t,armorpoints),R81_F(player_t,armortype),R81_A(player_t,powers,NUMPOWERS),R81_A(player_t,cards,NUMCARDS),
 R81_F(player_t,backpack),R81_F(player_t,readyweapon),R81_F(player_t,pendingweapon),R81_A(player_t,weaponowned,NUMWEAPONS),
 R81_A(player_t,ammo,NUMAMMO),R81_A(player_t,maxammo,NUMAMMO),R81_F(player_t,attackdown),R81_F(player_t,usedown),R81_F(player_t,cheats),
 R81_F(player_t,refire),R81_F(player_t,killcount),R81_F(player_t,itemcount),R81_F(player_t,secretcount),R81_F(player_t,damagecount),
 R81_F(player_t,bonuscount),R81_F(player_t,extralight),R81_F(player_t,fixedcolormap),R81_F(player_t,didsecret)
};
static const r81_field_t r81_mobj_fields[]={
 R81_F(mobj_t,z),R81_F(mobj_t,angle),R81_F(mobj_t,sprite),R81_F(mobj_t,frame),R81_F(mobj_t,floorz),R81_F(mobj_t,ceilingz),R81_F(mobj_t,dropoffz),
 R81_F(mobj_t,radius_q8),R81_F(mobj_t,height_q8),R81_F(mobj_t,momx),R81_F(mobj_t,momy),R81_F(mobj_t,momz),R81_F(mobj_t,health),
 R81_F(mobj_t,tics),R81_F(mobj_t,flags),R81_F(mobj_t,movedir),R81_F(mobj_t,threshold),R81_F(mobj_t,pursuecount),
 R81_F(mobj_t,movecount),R81_F(mobj_t,reactiontime)
};
static const r81_field_t r81_sector_fields[]={
 R81_F(sector_t,floorheight),R81_F(sector_t,ceilingheight),R81_F(sector_t,floorpic),R81_F(sector_t,ceilingpic),
 R81_F(sector_t,lightlevel),R81_F(sector_t,special),R81_F(sector_t,oldspecial)
};
static uint32_t R81_DeltaMask(const void *actual,const void *base,const r81_field_t *f,uint16_t n){
 uint32_t mask=0;for(uint16_t i=0;i<n;i++)if(R81_GetField(actual,&f[i])!=R81_GetField(base,&f[i]))mask|=1UL<<i;return mask;
}
static void R81_Delta(r81_io_t *io,void *actual,const void *base,const r81_field_t *f,uint16_t n){
 uint32_t mask=R81_U(io,io->mode<R81_LOAD?R81_DeltaMask(actual,base,f,n):0);
 if(mask>>n){io->error=1;return;}
 for(uint16_t i=0;i<n;i++)if(mask&(1UL<<i))R81_Fields(io,actual,&f[i],1);
}
static uint16_t R81_Ref(r81_io_t *io,const mobj_t *p){
 uint32_t id=R81_U(io,io->mode<R81_LOAD?R81_ObjectId(io,p):0);
 if(id>io->object_count){io->error=1;return 0;}return (uint16_t)id;
}
static uint8_t R81_Kind(const thinker_t *th){
 if(R81_PendingSpecial(th))return 8;
 if(R81_IsScroll(th))return 9;
 if(R81_IsFloor(th))return 2;
 if(th->function==(think_t)T_VerticalDoor)return 3;
 if(R81_IsPlat(th))return 4;
 int light=R81_LightKind(th);if(light)return (uint8_t)(4+light);
 return R81_MobjFunction(th)<=3u?1u:255u;
}
static int R81_Map(r81_io_t *io,uint8_t map,uint8_t skill){
 if(map<1u || map>9u || skill>sk_nightmare)return 0;
 char name[5]={'E','1','M',(char)('0'+map),0};int16_t lump=W_GetNumForName(name);
 if(lump<0)return 0;
 io->map=map;io->skill=skill;
 io->maplines=W_GetLumpByNum(lump+2);io->mapsides=W_GetLumpByNum(lump+3);io->mapsectors=W_GetLumpByNum(lump+7);
 io->lines=W_LumpLength(lump+2)/sizeof(line_t);io->sides=W_LumpLength(lump+3)/sizeof(mapsidedef_t);io->sectors=W_LumpLength(lump+7)/sizeof(mapsector_t);
 char key[9]={'S',(char)('0'+map),'R','T','H','I','N','G',0};int16_t stat=W_GetNumForName(key);
 if(stat<0)return 0;io->statics=W_LumpLength(stat)/8u;
 return io->sectors>0u && io->sectors<255u && io->lines<2048u && io->sides<2048u;
}
static int R81_BuildIds(r81_io_t *io){
 io->object_count=0;
 for(thinker_t *th=P_NextThinker(NULL);th;th=P_NextThinker(th)){
  uint8_t kind=R81_Kind(th);if(kind==255u)return 0;
  if(kind==1u){if(io->object_count>=R81_MAX_OBJECTS)return 0;io->objects[io->object_count++]=(mobj_t*)th;}
 }
 return 1;
}
static void R81_Player(r81_io_t *io){
 player_t p;
 if(io->mode<R81_LOAD)p=_g_player;else memset(&p,0,sizeof(p));
 io->player_id=R81_Ref(io,io->mode<R81_LOAD?p.mo:NULL);
 uint16_t attacker=R81_Ref(io,io->mode<R81_LOAD?p.attacker:NULL);
 R81_Fields(io,&p,r81_player_fields,R81_COUNT(r81_player_fields));
 if(p.playerstate>PST_REBORN || p.readyweapon>=NUMWEAPONS || p.pendingweapon>wp_nochange || p.armortype>2 || (p.cheats&~7))io->error=1;
 for(uint16_t i=0;i<NUMAMMO;i++)if(p.ammo[i]<0 || p.maxammo[i]<0 || p.ammo[i]>10000 || p.maxammo[i]>10000)io->error=1;
 for(uint16_t i=0;i<NUMPSPRITES;i++){
  uint32_t state=R81_U(io,io->mode<R81_LOAD && p.psprites[i].state?(uint32_t)(p.psprites[i].state-states+1):0);
  if(state>NUMSTATES){io->error=1;return;}
  int32_t tics=R81_N(io,io->mode<R81_LOAD?p.psprites[i].tics:0);
  int32_t x=R81_N(io,io->mode<R81_LOAD?p.psprites[i].sx:0),y=R81_N(io,io->mode<R81_LOAD?p.psprites[i].sy:0);
  if(io->mode>=R81_LOAD){p.psprites[i].state=state?&states[state-1]:NULL;p.psprites[i].tics=(int16_t)tics;p.psprites[i].sx=x;p.psprites[i].sy=y;}
 }
 if(io->mode==R81_LOAD){p.mo=(mobj_t*)(uintptr_t)io->player_id;p.attacker=(mobj_t*)(uintptr_t)attacker;p.message=NULL;_g_player=p;}
}
static void R81_World(r81_io_t *io){
 for(uint16_t i=0;i<io->sectors && !io->error;i++){
  const mapsector_t *ms=io->mapsectors+i;sector_t base,sec;memset(&base,0,sizeof(base));
  base.floorheight=(int32_t)ms->floorheight*FRACUNIT;base.ceilingheight=(int32_t)ms->ceilingheight*FRACUNIT;
  base.floorpic=ms->floorpic;base.ceilingpic=ms->ceilingpic;
  base.lightlevel=ms->lightlevel;base.special=base.oldspecial=ms->special;
  sec=io->mode<R81_LOAD?_g_sectors[i]:base;
  R81_Delta(io,&sec,&base,r81_sector_fields,R81_COUNT(r81_sector_fields));
  uint16_t target=R81_Ref(io,io->mode<R81_LOAD?sec.soundtarget:NULL);
  if(io->mode==R81_LOAD){
   sector_t *dst=_g_sectors+i;
   for(uint16_t f=0;f<R81_COUNT(r81_sector_fields);f++)R81_PutField(dst,&r81_sector_fields[f],R81_GetField(&sec,&r81_sector_fields[f]));
   dst->soundtarget=(mobj_t*)(uintptr_t)target;dst->validcount=0;dst->soundtraversed=0;
  }
 }
 for(uint16_t i=0;i<io->lines && !io->error;i++){
  int32_t special=io->mode<R81_LOAD?R23_GET(&_g_lines[i],special)-io->maplines[i].const_special:0;
  uint32_t mapped=R81_U(io,io->mode<R81_LOAD?((R23_GET(&_g_lines[i],r_flags)&ML_MAPPED)!=0):0);
  special=R81_N(io,special)+io->maplines[i].const_special;
  if(mapped>1u || special< -128 || special>127){io->error=1;return;}
  if(io->mode==R81_LOAD){R23_SET(&_g_lines[i],special,special);R23_SET(&_g_lines[i],r_flags,mapped?ML_MAPPED:0);R23_SET(&_g_lines[i],r_validcount,(uint16_t)(_g_gametic-1));R23_SET(&_g_lines[i],validcount,0);}
 }
 for(uint16_t i=0;i<io->sides && !io->error;i++){
  const mapsidedef_t *ms=io->mapsides+i;
  int32_t vals[4]={ms->textureoffset,ms->toptexture,ms->bottomtexture,ms->midtexture},original[4];memcpy(original,vals,sizeof(vals));
  if(io->mode<R81_LOAD){vals[0]=R23_GET(&_g_sides[i],textureoffset);vals[1]=R23_GET(&_g_sides[i],toptexture);vals[2]=R23_GET(&_g_sides[i],bottomtexture);vals[3]=R23_GET(&_g_sides[i],midtexture);}
  uint32_t mask=0;for(uint16_t k=0;k<4;k++)if(vals[k]!=original[k])mask|=1u<<k;
  mask=R81_U(io,mask);if(mask>15u){io->error=1;return;}
  for(uint16_t k=0;k<4;k++)if(mask&(1u<<k))vals[k]=R81_N(io,io->mode<R81_LOAD?vals[k]:0);
  if(vals[0]< -32768L || vals[0]>32767L)io->error=1;
  for(uint16_t k=1;k<4;k++)if(vals[k]< -128 || vals[k]>127)io->error=1;
  if(io->mode==R81_LOAD){R23_SET(&_g_sides[i],textureoffset,vals[0]);R23_SET(&_g_sides[i],toptexture,vals[1]);R23_SET(&_g_sides[i],bottomtexture,vals[2]);R23_SET(&_g_sides[i],midtexture,vals[3]);}
 }
 R81_RomThingsArchive(io);
}
static void R81_Mobj(r81_io_t *io,mobj_t *source){
 uint32_t type=R81_U(io,io->mode<R81_LOAD?(uint32_t)source->type:0);
 uint32_t state=R81_U(io,io->mode<R81_LOAD && source->state?(uint32_t)(source->state-states+1):0);
 uint32_t function=R81_U(io,io->mode<R81_LOAD?R81_MobjFunction(&source->thinker):0);
 int32_t x=R81_N(io,io->mode<R81_LOAD?source->x:0),y=R81_N(io,io->mode<R81_LOAD?source->y:0);
 if(type>=NUMMOBJTYPES || state>NUMSTATES || function>3u || io->object_index>=io->object_count){io->error=1;return;}
 mobj_t base,actual;memset(&base,0,sizeof(base));
 const mobjinfo_t *info=mobjinfo+type;base.type=(mobjtype_t)type;base.x=x;base.y=y;base.state=state?states+state-1:NULL;
 base.flags=info->flags&~MF_POOLED;base.health=info->spawnhealth;MOBJ_SET_RADIUS(&base,info->radius);MOBJ_SET_HEIGHT(&base,info->height);
 if(base.state){base.sprite=base.state->sprite;base.frame=base.state->frame;base.tics=base.state->tics;}
 if(io->mode!=R81_VALIDATE){sector_t *s=SUBSECTOR_SECTOR(R_PointInSubsector(x,y));base.z=base.floorz=base.dropoffz=s->floorheight;base.ceilingz=s->ceilingheight;}
 actual=io->mode<R81_LOAD?*source:base;actual.flags&=~MF_POOLED;
 R81_Delta(io,&actual,&base,r81_mobj_fields,R81_COUNT(r81_mobj_fields));
 uint16_t target=R81_Ref(io,io->mode<R81_LOAD?source->target:NULL),last=R81_Ref(io,io->mode<R81_LOAD?source->lastenemy:NULL);
 if((uint32_t)actual.sprite>=NUMSPRITES || (actual.frame&0x7fffu)>=32u || actual.movedir>8u)io->error=1;
 if(io->mode==R81_LOAD && !io->error){
  mobj_t *mo=R81_AllocMobj();uint32_t alloc=mo->flags&MF_POOLED;*mo=actual;mo->flags=(actual.flags&~MF_POOLED)|alloc;
  mo->target=(mobj_t*)(uintptr_t)target;mo->lastenemy=(mobj_t*)(uintptr_t)last;
  io->objects[io->object_index]=mo;
  if(io->object_index+1u==io->player_id)_g_player.mo=mo;
  R81_SetMobjFunction(mo,(uint8_t)function);
  if(function!=3u){P_SetSeclist(NULL);P_SetThingPosition(mo);}else mo->subsector=R_PointInSubsector(x,y);
  P_AddThinker(&mo->thinker);
 }
 io->object_index++;
}
static void R81_Buttons(r81_io_t *io){
 for(uint16_t i=0;i<MAXBUTTONS;i++){
  button_t b;if(io->mode<R81_LOAD)b=_g_buttonlist[i];else memset(&b,0,sizeof(b));
  int32_t timer=R81_N(io,io->mode<R81_LOAD?b.btimer:0);
  if(timer<0 || timer>32767){io->error=1;return;}
  if(!timer){if(io->mode==R81_LOAD)memset(&_g_buttonlist[i],0,sizeof(b));continue;}
  uint32_t line=R81_U(io,io->mode<R81_LOAD?(uint32_t)(b.line-_g_maplines):0),where=R81_U(io,io->mode<R81_LOAD?b.where:0);
  int32_t texture=R81_N(io,io->mode<R81_LOAD?b.btexture:0);
  if(line>=io->lines || where>2u || texture< -128 || texture>127){io->error=1;return;}
  if(io->mode==R81_LOAD){b.line=_g_maplines+line;b.where=(bwhere_e)where;b.btexture=(int8_t)texture;b.btimer=(int16_t)timer;b.soundorg=SECTOR_SOUND(LN_FRONTSECTOR(b.line));_g_buttonlist[i]=b;}
 }
}
static void R81_Stream(r81_io_t *io){
 int32_t g[8]={_g_gametic,_g_basetic,_g_leveltime,totalleveltimes,_g_totalkills,_g_totallive,_g_totalitems,_g_totalsecret};
 for(uint16_t i=0;i<8;i++)g[i]=R81_N(io,io->mode<R81_LOAD?g[i]:0);
 if(io->mode==R81_LOAD){_g_gametic=g[0];_g_basetic=g[1];_g_leveltime=g[2];totalleveltimes=g[3];_g_totalkills=g[4];_g_totallive=g[5];_g_totalitems=g[6];_g_totalsecret=g[7];validcount=0;}
 R81_Player(io);R81_World(io);R81_Buttons(io);io->object_index=0;
 thinker_t *th=io->mode<R81_LOAD?P_NextThinker(NULL):NULL;
 for(uint16_t n=0;n<1024u && !io->error;n++){
  uint32_t kind=R81_U(io,io->mode<R81_LOAD?(th?R81_Kind(th):0):0);
  if(!kind)break;
  if(kind==1u)R81_Mobj(io,(mobj_t*)th);
  else if(kind==2u)R81_FloorArchive(io,th);
  else if(kind==3u)R81_DoorArchive(io,th);
  else if(kind==4u)R81_PlatArchive(io,th);
  else if(kind>=5u && kind<=7u)R81_LightArchive(io,th,(uint8_t)kind);
  else if(kind==9u)R81_ScrollArchive(io,th);
  else if(kind==8u){if(io->mode==R81_LOAD){thinker_t *dead=Z_CallocLevel(sizeof(*dead));P_RemoveThinker(dead);P_AddThinker(dead);}}
  else io->error=1;
  if(io->mode<R81_LOAD)th=P_NextThinker(th);
  if(n==1023u)io->error=1;
 }
 if(io->object_index!=io->object_count || !io->player_id)io->error=1;
 R81_RandomArchive(io);
 if(io->mode<R81_LOAD)R81_Flush(io);
 else if(io->pos!=io->limit || io->zero_run)io->error=1;
}
static void R81_ClearFreshWorld(void){
 thinker_t *th=P_NextThinker(NULL);
 while(th){thinker_t *next=P_NextThinker(th);uint8_t kind=R81_Kind(th);
  if(kind!=1u || !(((mobj_t*)th)->flags&MF_POOLED))Z_Free(th);th=next;
 }
 P_RemoveAllActivePlats();
 for(int16_t i=0;i<_g_thingPoolSize;i++)_g_thingPool[i].type=MT_NOTHING;
 P_InitThinkers();P_SetSeclist(NULL);R81_ResetMapLinks();
 for(int16_t i=0;i<_g_numsectors;i++){sector_t *s=_g_sectors+i;s->thinglist=NULL;s->touching_thinglist=NULL;s->floordata=NULL;s->ceilingdata=NULL;s->soundtarget=NULL;}
}
static mobj_t *R81_Resolve(r81_io_t *io,const mobj_t *ordinal){uint16_t n=(uint16_t)(uintptr_t)ordinal;return n&&n<=io->object_count?io->objects[n-1]:NULL;}
static uint16_t R81_Read16(uint16_t off){return (uint16_t)((uint16_t)R81_SramRead(R81_SAVE_BASE+off)<<8)|R81_SramRead(R81_SAVE_BASE+off+1u);}
static int R81_Header(r81_io_t *io){
 if(R81_SramRead(R81_SAVE_BASE)!='R' || R81_SramRead(R81_SAVE_BASE+1u)!='8' || R81_SramRead(R81_SAVE_BASE+2u)!='1' || R81_SramRead(R81_SAVE_BASE+3u)!='S')return 0;
 if(R81_SramRead(R81_SAVE_BASE+4u)!=1u || R81_Read16(14)!=0x8101u)return -1;
 io->limit=R81_Read16(8);io->object_count=R81_Read16(12);
 if(!io->limit || io->limit>R81_SAVE_CAPACITY-16u || !io->object_count || io->object_count>R81_MAX_OBJECTS)return -1;
 if(!R81_Map(io,R81_SramRead(R81_SAVE_BASE+5u),R81_SramRead(R81_SAVE_BASE+6u)))return -1;
 uint16_t crc=65535u;for(uint16_t i=0;i<io->limit;i++)crc=R81_Crc(crc,R81_SramRead((uint16_t)(R81_SAVE_BASE+16u+i)));
 return crc==R81_Read16(10)?1:-1;
}
void R81_UpdateSaveStrings(void){
 r81_io_t io;memset(&io,0,sizeof(io));int status=R81_Header(&io);
 const char *s=status>0?"E1M1":status<0?"CORRUPT":"EMPTY";
 strcpy(_g_savegamestrings[0],s);if(status>0)_g_savegamestrings[0][3]=(char)('0'+io.map);
}
const char *R81_SaveGame(void){
 if(_g_gamestate!=GS_LEVEL || !_g_usergame || _g_demoplayback || !_g_player.mo || _g_player.playerstate==PST_DEAD)return "START A LIVE GAME FIRST";
 r81_io_t io;memset(&io,0,sizeof(io));io.objects=R81_SaveScratch();
 if(!R81_Map(&io,(uint8_t)_g_gamemap,(uint8_t)_g_gameskill) || !R81_BuildIds(&io))return "SAVE: UNSUPPORTED STATE";
 io.mode=R81_MEASURE;io.limit=R81_SAVE_CAPACITY-16u;io.crc=65535u;R81_Stream(&io);
 if(io.error)return "SAVE DOES NOT FIT 6KB";
 uint16_t length=io.pos,crc=io.crc;
 for(uint16_t i=0;i<4;i++)R81_SramWrite(R81_SAVE_BASE+i,0);
 io.mode=R81_WRITE;io.pos=0;io.zero_run=0;io.error=0;io.crc=65535u;R81_Stream(&io);
 if(io.error || io.pos!=length || io.crc!=crc)return "SAVE WRITE FAILED";
 uint16_t check=65535u;for(uint16_t i=0;i<length;i++)check=R81_Crc(check,R81_SramRead((uint16_t)(R81_SAVE_BASE+16u+i)));
 if(check!=crc)return "SRAM WRITE CHECK FAILED";
 uint8_t header[16]={'R','8','1','S',1,io.map,io.skill,1,(uint8_t)(length>>8),(uint8_t)length,(uint8_t)(crc>>8),(uint8_t)crc,(uint8_t)(io.object_count>>8),(uint8_t)io.object_count,0x81,1};
 for(uint16_t i=4;i<16;i++)R81_SramWrite(R81_SAVE_BASE+i,header[i]);
 for(uint16_t i=0;i<4;i++)R81_SramWrite(R81_SAVE_BASE+i,header[i]);
 R81_UpdateSaveStrings();memset(&netcmd,0,sizeof(netcmd));R81_ResyncInput();_g_player.message=GGSAVED;return NULL;
}
const char *R81_LoadGame(void){
 r81_io_t io;memset(&io,0,sizeof(io));int status=R81_Header(&io);
 if(status<=0)return status<0?"SAVE CORRUPT/INCOMPATIBLE":"NO SAVED GAME";
 io.objects=R81_SaveScratch();io.mode=R81_VALIDATE;io.crc=65535u;R81_Stream(&io);
 if(io.error)return "SAVE DATA INVALID";
 uint8_t map=io.map,skill=io.skill;_g_demoplayback=false;_g_timingdemo=false;
 G_InitNew((skill_t)skill,map);R81_ClearFreshWorld();
 io.mode=R81_LOAD;io.pos=0;io.zero_run=0;io.error=0;io.crc=65535u;R81_Stream(&io);
 if(io.error)I_Error("R81 VALIDATED SAVE LOAD FAILED");
 for(uint16_t i=0;i<io.object_count;i++){mobj_t *m=io.objects[i];m->target=R81_Resolve(&io,m->target);m->lastenemy=R81_Resolve(&io,m->lastenemy);}
 for(int16_t i=0;i<_g_numsectors;i++)_g_sectors[i].soundtarget=R81_Resolve(&io,_g_sectors[i].soundtarget);
 _g_player.mo=io.objects[io.player_id-1u];_g_player.attacker=R81_Resolve(&io,_g_player.attacker);_g_player.message="GAME LOADED";
 _g_usergame=true;_g_gameaction=ga_nothing;memset(&netcmd,0,sizeof(netcmd));R81_ResyncInput();return NULL;
}
