#include "navigation.h"
Camera navigation_camera;
uint16_t navigation_cell,navigation_angle;
uint16_t map_find_cell(int16_t x,int16_t y){
 int16_t node=0;
 for(uint16_t depth=0;depth<map_node_count;depth++){
  const MapNode*n=&map_nodes[node];int32_t side=(int32_t)((uint32_t)((int32_t)n->nx*x)+(uint32_t)((int32_t)n->ny*y)+(uint32_t)n->distance);
  node=n->child[side>=0];if(node<0)return (uint16_t)~node;
 }
 return 0xffff;
}
static int valid(uint16_t cell){return cell<map_cell_count&&map_cell_offsets[cell]<map_cell_offsets[cell+1];}
static uint16_t variant_for(uint16_t cell,uint16_t wi){
 for(uint32_t r=map_cell_offsets[cell];r<map_cell_offsets[cell+1];r++)if((map_cell_walls[r]&32767)==wi)return (map_cell_walls[r]&32768)?scene_walls[wi].back_variant:scene_walls[wi].variant;
 /* Same surface can be absent from an occluded part of the PVS. */
 uint16_t a=scene_walls[wi].variant,b=scene_walls[wi].back_variant;return a<=3?a:(b<=3?b:a);
}
static int blocked_surface(uint16_t cell,uint16_t wi){
 const Wall*w=&scene_walls[wi];uint16_t v=variant_for(cell,wi);if(v<=3||v>17)return 1;
 int upper=(v>=9&&v<=11)||v>=15,ceiling=v!=4&&v!=5,lower=v==5||v==8||v==11||v==14||v==17;
 int floor=v==4||v==5||v==7||v==8||v==10||v==11||v==13||v==14||v==16||v==17;
 int32_t top=upper?w->h[1]:(ceiling?w->h[0]:-32768),bottom=lower?w->h[2]:(floor?w->h[2]:32767);
 return bottom-top<56;
}
static int near_segment(int16_t x,int16_t y,const Wall*w){
 const int32_t radius=16;int32_t minx=w->x0<w->x1?w->x0:w->x1,maxx=w->x0>w->x1?w->x0:w->x1,miny=w->y0<w->y1?w->y0:w->y1,maxy=w->y0>w->y1?w->y0:w->y1;
 if(x<minx-radius||x>maxx+radius||y<miny-radius||y>maxy+radius)return 0;
 int32_t dx=w->x1-w->x0,dy=w->y1-w->y0,vx=x-w->x0,vy=y-w->y0;uint32_t len2=(uint32_t)(dx*dx+dy*dy);int32_t dot=vx*dx+vy*dy;
 if(!len2||dot<=0)return vx*vx+vy*vy<radius*radius;
 if((uint32_t)dot>=len2){vx=x-w->x1;vy=y-w->y1;return vx*vx+vy*vy<radius*radius;}
 int32_t cross=dx*vy-dy*vx;uint32_t ac=cross<0?(uint32_t)-cross:(uint32_t)cross;
 return (uint64_t)ac*ac<(uint64_t)(radius*radius)*len2;
}
static int collision(int16_t x,int16_t y,uint16_t oldcell,uint16_t *cell){
 *cell=map_find_cell(x,y);if(!valid(*cell))return 1;
 if((int32_t)map_cell_floor[oldcell]-map_cell_floor[*cell]>24)return 1;
 int16_t wx=x>>3,wy=y>>3;int16_t gx0=(wx-16-collision_origin_x)>>7,gx1=(wx+16-collision_origin_x)>>7,gy0=(wy-16-collision_origin_y)>>7,gy1=(wy+16-collision_origin_y)>>7;
 for(int16_t gy=gy0;gy<=gy1;gy++)for(int16_t gx=gx0;gx<=gx1;gx++){
  if(gx<0||gy<0||gx>=collision_width||gy>=collision_height)continue;
  uint16_t bucket=gy*collision_width+gx;
  for(uint32_t p=collision_offsets[bucket];p<collision_offsets[bucket+1];p++){
   uint16_t wi=collision_walls[p];if(near_segment(wx,wy,&scene_walls[wi])&&blocked_surface(oldcell,wi))return 1;
  }
 }
 return 0;
}
void navigation_reset(void){
 navigation_camera=map_spawn;navigation_angle=0;navigation_cell=map_find_cell(navigation_camera.x,navigation_camera.y);
 if(valid(navigation_cell))navigation_camera.z=(map_cell_floor[navigation_cell]-40)&~1;
}
void navigation_update(uint16_t buttons,uint16_t ticks){
 if(!ticks)ticks=1;if(ticks>30)ticks=30;
 if(buttons&128){navigation_reset();return;}
 if(buttons&4)navigation_angle=(navigation_angle-ticks)&255;
 if(buttons&8)navigation_angle=(navigation_angle+ticks)&255;
 navigation_camera.si=map_sine[navigation_angle];navigation_camera.co=map_sine[(navigation_angle+64)&255];navigation_camera.sky=(map_spawn.sky+2*navigation_angle)&127;
 int dir=((buttons&1)!=0)-((buttons&2)!=0);if(!dir)return;
 int32_t speed=(buttons&64)?24:16;speed*=dir*(int32_t)ticks;
 int16_t dx=(int16_t)(((int32_t)navigation_camera.si*speed)>>14),dy=(int16_t)(((int32_t)navigation_camera.co*speed)>>14);
 int16_t ax=dx<0?-dx:dx,ay=dy<0?-dy:dy,n=(ax>ay?ax:ay)/32+1;int16_t startx=navigation_camera.x,starty=navigation_camera.y,prevx=startx,prevy=starty;
 for(int16_t i=1;i<=n;i++){
  int16_t targetx=startx+(int32_t)dx*i/n,targety=starty+(int32_t)dy*i/n;int16_t sx=targetx-prevx,sy=targety-prevy;prevx=targetx;prevy=targety;
  int16_t x=navigation_camera.x,y=navigation_camera.y,nx=x+sx,ny=y+sy;uint16_t cell;
  if(!collision(nx,ny,navigation_cell,&cell)){navigation_camera.x=nx;navigation_camera.y=ny;navigation_cell=cell;}
  else {
   if(!collision(nx,y,navigation_cell,&cell)){navigation_camera.x=nx;navigation_cell=cell;}
   if(!collision(navigation_camera.x,ny,navigation_cell,&cell)){navigation_camera.y=ny;navigation_cell=cell;}
  }
 }
 navigation_camera.z=(map_cell_floor[navigation_cell]-40)&~1;
}
