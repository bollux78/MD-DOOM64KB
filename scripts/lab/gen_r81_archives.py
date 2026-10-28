"""Generate private-module state adapters; run on the pristine source tree."""
from pathlib import Path
root=Path('src')
common='\n#if defined(DOOM_R81_SAVE)\n#include "r81_save_io.h"\n#include "z_zone.h"\n'
def append(file,code):
 p=root/file;p.write_text(p.read_text()+common+code+'\n#endif\n')
append('m_random.c','''void R81_RandomArchive(r81_io_t *io){
 uint32_t a=R81_U(io,io->mode<R81_LOAD?rndindex:0),b=R81_U(io,io->mode<R81_LOAD?prndindex:0);
 if(a>255 || b>255)io->error=1;
 if(io->mode==R81_LOAD){rndindex=a;prndindex=b;}
}''')
append('r24_romthings.c','''void R81_RomThingsArchive(r81_io_t *io){
 if(io->mode!=R81_VALIDATE && count!=io->statics){io->error=1;return;}
 for(uint16_t i=0;i<(io->statics+7u)/8u;i++){
  uint32_t v=R81_U(io,io->mode<R81_LOAD?removed[i]:0);if(v>255)io->error=1;
  if(io->mode==R81_LOAD)removed[i]=v;
 }
 for(uint16_t i=0;i<io->statics;i++){
  uint32_t v=R81_U(io,io->mode<R81_LOAD?delays[i]:0);if(v>65535u)io->error=1;
  if(io->mode==R81_LOAD)delays[i]=v;
 }
}''')
append('p_mobj.c','''mobj_t *R81_AllocMobj(void){return P_NewMobj();}
uint8_t R81_MobjFunction(const thinker_t *th){
 if(!th->function)return 0;
 if(th->function==(think_t)P_MobjThinker)return 1;
 if(th->function==(think_t)P_MobjBrainlessThinker)return 2;
 return R81_PendingThing(th)?3:255;
}
void R81_SetMobjFunction(mobj_t *mo,uint8_t kind){
 mo->thinker.function=kind==1?(think_t)P_MobjThinker:kind==2?(think_t)P_MobjBrainlessThinker:NULL;
 if(kind==3)P_RemoveThing(mo);
}''')
append('p_tick.c','''int R81_PendingThing(const thinker_t *th){return th->function==(think_t)P_RemoveThingDelayed;}
int R81_PendingSpecial(const thinker_t *th){return th->function==(think_t)P_RemoveThinkerDelayed;}''')
# All adapters validate into local structs before allocating or mutating a level.
def archive(file,typ,name,fields,fn,extra='',attach='floordata'):
 desc=','.join('R81_F('+typ+','+f+')' for f in fields.split())
 code=f'''void R81_{name}Archive(r81_io_t *io,thinker_t *th){{
 {typ} v;memset(&v,0,sizeof(v));if(io->mode<R81_LOAD)v=*({typ}*)th;
 uint32_t sector=R81_U(io,io->mode<R81_LOAD?R81_SectorId(io,v.sector):0);
 if(!sector || sector>io->sectors){{io->error=1;return;}}
 static const r81_field_t fields[]={{{desc}}};
 R81_Fields(io,&v,fields,sizeof(fields)/sizeof(fields[0]));
 {extra}
 if(io->mode==R81_LOAD && !io->error){{
  {typ} *p=Z_CallocLevel(sizeof(*p));*p=v;p->sector=_g_sectors+sector-1;
  p->thinker.function=(think_t){fn};
  {('p->sector->'+attach+'=p;') if attach else ''}
  P_AddThinker(&p->thinker);
  {'if(!enabled)p->thinker.function=NULL;P_AddActivePlat(p);' if name=='Plat' else ''}
 }}
}}'''
 append(file,'#include <string.h>\n'+code)
archive('p_floor.c','floormove_t','Floor','type direction texture floordestheight speed','T_MoveFloor')
append('p_floor.c','int R81_IsFloor(const thinker_t *th){return th->function==(think_t)T_MoveFloor;}')
archive('p_doors.c','vldoor_t','Door','type topheight speed direction topwait topcountdown lighttag','T_VerticalDoor','''uint32_t line=R81_U(io,io->mode<R81_LOAD && v.line?(uint32_t)(v.line-_g_maplines+1):0);
 if(line>io->lines)io->error=1;
 if(io->mode>=R81_LOAD)v.line=line?_g_maplines+line-1:NULL;''','ceilingdata')
archive('p_plats.c','plat_t','Plat','speed low high wait count status tag type','T_PlatRaise','''uint32_t enabled=R81_U(io,io->mode<R81_LOAD?(th->function!=NULL):0);
 if(enabled>1)io->error=1;''')
append('p_plats.c','''int R81_IsPlat(const thinker_t *th){
 if(th->function==(think_t)T_PlatRaise)return 1;
 if(th->function)return 0;
 for(platlist_t *p=activeplats;p;p=p->next)if(&p->plat->thinker==th)return 1;
 return 0;
}''')
# Light variants share the same sector reference but distinct private layouts.
c='''#include <string.h>
int R81_LightKind(const thinker_t *th){
 if(th->function==(think_t)T_LightFlash)return 1;
 if(th->function==(think_t)T_StrobeFlash)return 2;
 if(th->function==(think_t)T_Glow)return 3;
 return 0;
}
void R81_LightArchive(r81_io_t *io,thinker_t *th,uint8_t kind){
'''
for k,typ,fn,fields in [(5,'lightflash_t','T_LightFlash','count maxlight minlight maxtime mintime'),(6,'strobe_t','T_StrobeFlash','count minlight maxlight darktime brighttime'),(7,'glow_t','T_Glow','minlight maxlight direction')]:
 c+=f'''if(kind=={k}){{
 {typ} v;memset(&v,0,sizeof(v));if(io->mode<R81_LOAD)v=*({typ}*)th;
 uint32_t sector=R81_U(io,io->mode<R81_LOAD?R81_SectorId(io,v.sector):0);
 if(!sector || sector>io->sectors){{io->error=1;return;}}
 static const r81_field_t fields[]={{{','.join('R81_F('+typ+','+f+')' for f in fields.split())}}};
 R81_Fields(io,&v,fields,sizeof(fields)/sizeof(fields[0]));
 if(io->mode==R81_LOAD && !io->error){{{typ} *p=Z_CallocLevel(sizeof(*p));*p=v;p->sector=_g_sectors+sector-1;p->thinker.function=(think_t){fn};P_AddThinker(&p->thinker);}}
 return;
}}
'''
c+='io->error=1;\n}'
append('p_lights.c',c)
print('PASS generated R81 private archive adapters')

append('p_spec.c','''int R81_IsScroll(const thinker_t *th){return th->function==(think_t)T_Scroll;}
void R81_ScrollArchive(r81_io_t *io,thinker_t *th){
 uint32_t side=R81_U(io,io->mode<R81_LOAD?(uint32_t)(((scroll_t*)th)->side-_g_sides):0);
 if(side>=io->sides){io->error=1;return;}
 if(io->mode==R81_LOAD){scroll_t *s=Z_CallocLevSpec(sizeof(*s));s->side=_g_sides+side;s->thinker.function=(think_t)T_Scroll;P_AddThinker(&s->thinker);}
}''')
