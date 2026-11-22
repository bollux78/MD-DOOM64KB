#include "world.h"
#ifdef DREAD_GAMEPLAY
#include "mapcounts.h"
#include "levelmeta.h"
#include "game_sfx.h"
#include "actors.h"
static int16_t floor_target[MAP_NSECTORS],floor_return[MAP_NSECTORS],ceil_target[MAP_NSECTORS];
static uint16_t floor_wait[MAP_NSECTORS],ceil_wait[MAP_NSECTORS];
static uint8_t floor_active[MAP_NSECTORS],ceil_active[MAP_NSECTORS];
static uint8_t used_lines[2048];
static uint16_t map_id,hazard_clock,boss_done;
static uint16_t invuln,suit,invisible,bright,berserk,berserk_red,scroll_clock;
extern uint16_t r_fullbright,r_scroll;
void World_Power(uint16_t kind){if(kind==70)invuln=1800;else if(kind==71){berserk=1;berserk_red=1200;}else if(kind==72)invisible=3600;else if(kind==73)suit=3600;else if(kind==75)bright=7200;}
extern uint16_t cheat_god;
uint16_t World_Invulnerable(void){return invuln || cheat_god;}
uint16_t World_Invisible(void){return invisible;}
uint16_t World_Berserk(void){return berserk;}

static void neighbours(uint16_t s,int16_t *low,int16_t *high,int16_t *next,int16_t *ceil)
{
    *low=*high=map_sectors[s].floor;*next=32767;*ceil=32767;
    for(uint16_t i=0;i<map_counts[5];i++) {
        const MapLine *l=&map_lines[i];if(l->back==NO_MAP_SECTOR)continue;
        uint16_t n=l->front==s?l->back:l->back==s?l->front:NO_MAP_SECTOR;if(n==NO_MAP_SECTOR || n==s)continue;
        const int16_t f=map_sectors[n].floor;
        if(f<*low)*low=f;if(f>*high)*high=f;if(f>map_sectors[s].floor && f<*next)*next=f;
        if(sec_ceil[n]<*ceil)*ceil=sec_ceil[n];
    }
    if(*next==32767)*next=map_sectors[s].floor;
    if(*ceil==32767)*ceil=sec_ceil[s];
}
uint16_t World_Tint(void){
    if(invuln && (invuln>240 || (invuln&32)))return 3;
    if(suit && (suit>240 || (suit&32)))return 4;
    if(berserk_red)return berserk_red>800?5:berserk_red>400?6:7;
    return 0;
}
void World_Init(uint16_t m)
{
    map_id=m;hazard_clock=0;boss_done=0;invuln=suit=invisible=bright=berserk=berserk_red=scroll_clock=0;r_fullbright=0;r_scroll=0;
    for(uint16_t s=0;s<map_counts[4];s++) {
        floor_active[s]=ceil_active[s]=0;floor_wait[s]=ceil_wait[s]=0;
        floor_target[s]=floor_return[s]=map_sectors[s].floor;ceil_target[s]=sec_ceil[s];
    }
    for(uint16_t i=0;i<sizeof(used_lines);i++)used_lines[i]=0;
}
void World_Door(uint16_t s,uint16_t manual)
{
    int16_t lo,hi,next,ce;neighbours(s,&lo,&hi,&next,&ce);
    ceil_target[s]=ce-4;ceil_active[s]=1;ceil_wait[s]=manual?240:0;Game_Sound(8);
}
static void floor_move(uint16_t s,int16_t target,uint16_t lift)
{
    if(floor_active[s])return;
    floor_return[s]=map_sectors[s].floor;floor_target[s]=target;floor_active[s]=1;floor_wait[s]=lift?180:0;
}
void World_Activate(uint16_t index,uint16_t crossing,View *view)
{
    const MapLine *l=&map_lines[index];const uint16_t sp=l->special;
    if(index>=sizeof(used_lines) || used_lines[index])return;
    if(crossing) {
        switch(sp){case 2:case 5:case 8:case 16:case 22:case 35:case 36:case 76:case 82:case 86:case 88:case 90:case 91:case 97:case 98:break;default:return;}
    }else{
        switch(sp){case 7:case 9:case 18:case 20:case 23:case 62:case 63:case 70:case 103:break;default:return;}
    }
    if(!l->tag)return;
    if(sp==97){
        const LevelMeta *meta=&level_meta[map_id];
        for(uint16_t i=0;i<meta->nteleports;i++){
            const int16_t *p=meta->teleports[i];const uint16_t sub=R_PointInSub(p[0],p[1]),s=map_subs[sub].sector;
            if(map_sector_tag[s]!=l->tag)continue;
            view->x=(int32_t)p[0]<<16;view->y=(int32_t)p[1]<<16;view->angle=(uint16_t)((int32_t)p[2]*65536/360);view->z=map_sectors[s].floor+41;
            Game_Sound(19);return;
        }return;
    }
    uint16_t activated=0;
    for(uint16_t s=0;s<map_counts[4];s++)if(map_sector_tag[s]==l->tag){
        int16_t lo,hi,next,ce;neighbours(s,&lo,&hi,&next,&ce);activated=1;
        switch(sp){
        case 2:case 86:case 103:World_Door(s,0);break;
        case 63:case 90:World_Door(s,1);break;
        case 16:case 76:ceil_target[s]=map_sectors[s].floor;ceil_active[s]=2;ceil_wait[s]=1800;break;
        case 62:case 88:floor_move(s,lo,1);break;
        case 18:case 20:case 22:floor_move(s,next,0);break;
        case 23:case 82:floor_move(s,lo,0);break;
        case 36:case 70:case 98:{int16_t target=lo;
            /* highest neighbouring floor below this sector, plus Doom's 8-unit lip */
            for(uint16_t i=0;i<map_counts[5];i++){const MapLine *q=&map_lines[i];if(q->back==NO_MAP_SECTOR)continue;uint16_t n=q->front==s?q->back:q->back==s?q->front:NO_MAP_SECTOR;if(n!=NO_MAP_SECTOR && map_sectors[n].floor<map_sectors[s].floor && map_sectors[n].floor>target)target=map_sectors[n].floor;}
            floor_move(s,target<map_sectors[s].floor?target+8:target,0);break;}
        case 5:case 91:floor_move(s,ce<sec_ceil[s]?ce:sec_ceil[s],0);break;
        case 7:case 8:{
            /* Build a connected rising stair chain on the same source flat. */
            uint16_t current=s,guard=0;int16_t target=map_sectors[s].floor+8;
            while(guard++<map_counts[4]){
                floor_move(current,target,0);uint16_t following=NO_MAP_SECTOR;
                for(uint16_t i=0;i<map_counts[5];i++){const MapLine *q=&map_lines[i];if(q->front!=current || q->back==NO_MAP_SECTOR || floor_active[q->back])continue;
                    if(level_meta[map_id].floorflat[q->back]==level_meta[map_id].floorflat[s]){following=q->back;break;}}
                if(following==NO_MAP_SECTOR)break;current=following;target+=8;
            }break;}
        case 9:{
            uint16_t ring=NO_MAP_SECTOR,outer=NO_MAP_SECTOR;
            for(uint16_t i=0;i<map_counts[5];i++){const MapLine *q=&map_lines[i];if(q->back==NO_MAP_SECTOR)continue;if(q->front==s){ring=q->back;break;}if(q->back==s){ring=q->front;break;}}
            if(ring==NO_MAP_SECTOR)break;
            for(uint16_t i=0;i<map_counts[5];i++){const MapLine *q=&map_lines[i];if(q->back==NO_MAP_SECTOR)continue;uint16_t n=q->front==ring?q->back:q->back==ring?q->front:NO_MAP_SECTOR;if(n!=NO_MAP_SECTOR && n!=s){outer=n;break;}}
            if(outer!=NO_MAP_SECTOR){floor_move(s,map_sectors[outer].floor,0);floor_move(ring,map_sectors[outer].floor,0);map_sectors[ring].floorcol=map_sectors[outer].floorcol;}break;}
        case 35:map_sectors[s].bucket=3;break;
        }
    }
    if(activated){Game_Sound(10);switch(sp){case 2:case 5:case 7:case 8:case 9:case 16:case 18:case 20:case 22:case 23:case 35:case 36:case 103:used_lines[index]=1;break;}}
}
void World_Shoot(const View *view)
{
    const int32_t x=view->x>>16,y=view->y>>16;
    const uint16_t angle=view->angle>>6;
    const int32_t dx=((2048L*sintab[(angle+256)&1023])>>14),dy=((2048L*sintab[angle])>>14);
    int best=-1;uint32_t nearest=65537;
    for(uint16_t i=0;i<map_counts[5];i++){
        const MapLine *l=&map_lines[i];
        if(l->back!=NO_MAP_SECTOR && !(l->flags&1) && l->special!=46){
            const int16_t lo=map_sectors[l->front].floor>map_sectors[l->back].floor?map_sectors[l->front].floor:map_sectors[l->back].floor;
            const int16_t hi=sec_ceil[l->front]<sec_ceil[l->back]?sec_ceil[l->front]:sec_ceil[l->back];
            if(view->z>lo && view->z<hi)continue;
        }
        const int32_t ax=map_verts[l->v1][0],ay=map_verts[l->v1][1],lx=map_verts[l->v2][0]-ax,ly=map_verts[l->v2][1]-ay;
        int32_t den=dx*ly-dy*lx,tn=(ax-x)*ly-(ay-y)*lx,un=(ax-x)*dy-(ay-y)*dx;
        if(den<0){den=-den;tn=-tn;un=-un;}if(!den || tn<0 || tn>den || un<0 || un>den)continue;
        const uint32_t t=(uint32_t)(((int64_t)tn<<16)/den);if(t<nearest){nearest=t;best=i;}
    }
    if(best>=0 && map_lines[best].special==46)for(uint16_t s=0;s<map_counts[4];s++)if(map_sector_tag[s]==map_lines[best].tag)World_Door(s,0);
}
uint16_t World_Tick(uint16_t dt,View *view,HudState *hud)
{
    invuln=invuln>dt?invuln-dt:0;suit=suit>dt?suit-dt:0;invisible=invisible>dt?invisible-dt:0;bright=bright>dt?bright-dt:0;r_fullbright=bright || invuln;
    berserk_red=berserk_red>dt?berserk_red-dt:0;
    HUD_WeaponInvisible(invisible && (invisible>240 || (invisible&32)));
    scroll_clock+=dt*35;while(scroll_clock>=60){scroll_clock-=60;r_scroll++;}
    const uint16_t player_sector=map_subs[R_PointInSub(view->x>>16,view->y>>16)].sector;
    for(uint16_t s=0;s<map_counts[4];s++){
        if(floor_active[s]){
            int16_t *f=&map_sectors[s].floor;const int16_t delta=2*dt;
            if(*f<floor_target[s]){*f+=delta;if(*f>floor_target[s])*f=floor_target[s];}
            else if(*f>floor_target[s]){*f-=delta;if(*f<floor_target[s])*f=floor_target[s];}
            else if(floor_wait[s]){if(floor_wait[s]>dt)floor_wait[s]-=dt;else{floor_wait[s]=0;floor_target[s]=floor_return[s];}}
            else floor_active[s]=0;
        }
        if(ceil_active[s]){
            const int16_t delta=2*dt;
            if(sec_ceil[s]<ceil_target[s]){sec_ceil[s]+=delta;if(sec_ceil[s]>ceil_target[s])sec_ceil[s]=ceil_target[s];}
            else if(sec_ceil[s]>ceil_target[s]){
                if(player_sector==s && sec_ceil[s]-map_sectors[s].floor<64){World_Door(s,1);continue;}
                sec_ceil[s]-=delta;if(sec_ceil[s]<ceil_target[s])sec_ceil[s]=ceil_target[s];
            }else if(ceil_wait[s]){
                if(ceil_wait[s]>dt)ceil_wait[s]-=dt;else{ceil_wait[s]=0;if(ceil_active[s]==2)World_Door(s,0);else ceil_target[s]=map_sectors[s].floor;}
            }else ceil_active[s]=0;
        }
    }
    if(map_id==7 && !boss_done && Actors_BossDone()){
        boss_done=1;for(uint16_t s=0;s<map_counts[4];s++)if(map_sector_tag[s]==666){int16_t lo,hi,n,c;neighbours(s,&lo,&hi,&n,&c);floor_move(s,lo,0);}
    }
    hazard_clock+=dt;
    if(hazard_clock>=55){
        hazard_clock-=55;const uint16_t sp=level_meta[map_id].specials[player_sector];
        uint16_t damage=sp==5?10:sp==7?5:(sp==16 || sp==11)?20:0;
        if((suit && sp!=11) || invuln || cheat_god)damage=0;
        if(sp==11 && hud->health<=damage+10){hud->health=10;return 1;}
        if(damage){hud->health=hud->health>damage?hud->health-damage:0;HUD_Draw(hud);Game_Sound(11);}
        if(sp==11 && hud->health<=10)return 1;
    }
    return 0;
}
#endif
