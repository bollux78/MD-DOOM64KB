#include "neodoom.h"
#include <genesis.h>
extern uint16_t nd_flat;
static uint8_t pixels[ND_BYTES];
static uint32_t packed[ND_TILE_BYTES/4];
static uint16_t tilemap[ND_TILES];
static uint16_t bank;
volatile uint32_t nd_bench_done,nd_bench_draw,nd_bench_pack,nd_bench_total,nd_bench_edges,nd_bench_portals,nd_bench_errors,nd_bench_frames;
static uint32_t draw_ticks,pack_ticks,total_ticks;
static void number(uint32_t n,uint16_t x,uint16_t y){char s[12];uintToStr(n,s,1);VDP_drawText("        ",x,y);VDP_drawText(s,x,y);}
static void display(const NdCamera *cam){
 uint32_t start=getSubTick();nd_render(cam,pixels);uint32_t rendered=getSubTick();
 uint16_t next=bank^1,base=TILE_USER_INDEX+next*ND_TILES;
 uint16_t mixed=nd_pack_mixed(pixels,packed,tilemap,TILE_ATTR_FULL(PAL1,0,0,0,base),TILE_ATTR_FULL(PAL1,0,0,0,TILE_USER_INDEX+2*ND_TILES));
 uint32_t ready=getSubTick();
 uint16_t sent=0;
 while(sent<mixed){
  uint16_t count=mixed-sent;if(count>180)count=180;
  SYS_doVBlankProcessEx(ON_VBLANK_START);
  VDP_loadTileData(packed+sent*8,base+sent,count,DMA);DMA_waitCompletion();sent+=count;
 }
 SYS_doVBlankProcessEx(ON_VBLANK_START);
 VDP_setTileMapDataRect(BG_A,tilemap,2,3,ND_W/2,ND_H/2,ND_W/2,DMA);DMA_waitCompletion();bank=next;
 draw_ticks=rendered-start;pack_ticks=ready-rendered;total_ticks=getSubTick()-start;
}
static int pose(NdCamera *cam,uint16_t n){
 cam->x=nd_poses[n].x;cam->y=nd_poses[n].y;cam->angle=nd_poses[n].angle;int16_t r=nd_locate(cam->x,cam->y,-1);
 if(r<0)return 0;cam->room=r;cam->z=nd_rooms[r].floor+41;return 1;
}
static void hud(void){
 VDP_drawText(nd_flat?"FLAT  START: TEXTURES":"TEXTURED  START: FLAT",1,23);
 VDP_drawText("DRAW MS  PACK MS  TOTAL MS",1,24);
 number((draw_ticks+38)/77,1,25);number((pack_ticks+38)/77,10,25);number((total_ticks+38)/77,20,25);
 VDP_drawText("EDGES    PORTALS  LIMIT",1,26);number(nd_stats.edges,1,27);number(nd_stats.portals,10,27);number(nd_stats.overflow,20,27);
}
static void benchmark(void){
 NdCamera cam;nd_bench_done=0;nd_bench_frames=nd_bench_draw=nd_bench_pack=nd_bench_total=nd_bench_edges=nd_bench_portals=nd_bench_errors=0;
 VDP_drawText("NEODOOM E1M1 BENCH RUNNING",1,1);
 for(uint16_t p=0;p<nd_pose_count;p++){
  if(!pose(&cam,p)){nd_bench_errors++;continue;}
  for(uint16_t turn=0;turn<4;turn++){
   cam.angle=(nd_poses[p].angle+turn*64)&255;display(&cam);
   nd_bench_frames++;nd_bench_draw+=draw_ticks;nd_bench_pack+=pack_ticks;nd_bench_total+=total_ticks;
   nd_bench_edges+=nd_stats.edges;nd_bench_portals+=nd_stats.portals;nd_bench_errors+=nd_stats.overflow;
  }
 }
 VDP_clearPlane(BG_A,TRUE);VDP_drawText("NEODOOM P0 - E1M1 BENCH",2,2);
 VDP_drawText("ROOM PORTALS - 72X40",2,4);
 VDP_drawText(nd_flat?"FLAT WALLS":"TEXTURED WALLS",2,5);
 VDP_drawText("SAMPLES",2,7);number(nd_bench_frames,25,7);
 VDP_drawText("DRAW AVG MS",2,9);number(nd_bench_draw/nd_bench_frames/77,25,9);
 VDP_drawText("PACK AVG MS",2,11);number(nd_bench_pack/nd_bench_frames/77,25,11);
 VDP_drawText("FRAME AVG MS",2,13);number(nd_bench_total/nd_bench_frames/77,25,13);
 VDP_drawText("EDGES AVG",2,15);number(nd_bench_edges/nd_bench_frames,25,15);
 VDP_drawText("PORTALS AVG",2,17);number(nd_bench_portals/nd_bench_frames,25,17);
 VDP_drawText("LIMIT OR POSE ERRORS",2,19);number(nd_bench_errors,25,19);
 VDP_drawText("ANY BUTTON RETURNS",2,23);nd_bench_done=1;
 while(JOY_readJoypad(JOY_1))SYS_doVBlankProcess();
 while(!JOY_readJoypad(JOY_1))SYS_doVBlankProcess();
}
int main(bool hard){
 (void)hard;VDP_setScreenWidth320();VDP_setPlaneSize(64,32,TRUE);
 /* Two 720-tile frame banks fit below the relocated font and maps. */
 VDP_setWindowAddress(0xD000);VDP_setBGAAddress(0xE000);VDP_setBGBAddress(0xE000);
 VDP_loadFont(&font_default,DMA);DMA_waitCompletion();
 PAL_setPalette(PAL1,nd_palette,CPU);VDP_setTextPalette(PAL0);
 for(uint16_t c=0;c<16;c++)for(uint16_t j=0;j<8;j++)packed[c*8+j]=0x11111111u*c;
 VDP_loadTileData(packed,TILE_USER_INDEX+2*ND_TILES,16,DMA);DMA_waitCompletion();
 NdCamera cam;uint16_t p=0;pose(&cam,0);uint16_t previous=0;
 VDP_drawText("NEODOOM P0  E1M1  PORTALS",1,0);
 VDP_drawText("ARROWS MOVE A/B POSES C BENCH",1,1);
 display(&cam);hud();
 for(;;){
  SYS_doVBlankProcess();uint16_t held=JOY_readJoypad(JOY_1),pressed=held&~previous;previous=held;int redraw=0;
  if(pressed&BUTTON_START){nd_flat^=1;redraw=1;}
  if(pressed&BUTTON_C){benchmark();VDP_drawText("NEODOOM P0  E1M1  PORTALS",1,0);redraw=1;}
  if(pressed&(BUTTON_A|BUTTON_B)){p=(p+((pressed&BUTTON_A)?nd_pose_count-1:1))%nd_pose_count;pose(&cam,p);redraw=1;}
  if(held&(BUTTON_LEFT|BUTTON_RIGHT)){cam.angle=(cam.angle+((held&BUTTON_LEFT)?3:-3))&255;redraw=1;}
  if(held&(BUTTON_UP|BUTTON_DOWN)){
   int16_t step=(held&BUTTON_UP)?32:-32;
   int16_t x=cam.x+((int32_t)nd_sines[(cam.angle+64)&255]*step>>8),y=cam.y+((int32_t)nd_sines[cam.angle]*step>>8);
   int16_t r=nd_locate(x,y,cam.room);
   if(r>=0 && nd_rooms[r].ceiling-nd_rooms[r].floor>=56 && nd_rooms[r].floor<=nd_rooms[cam.room].floor+24){cam.x=x;cam.y=y;cam.room=r;cam.z=nd_rooms[r].floor+41;redraw=1;}
  }
  if(redraw){display(&cam);hud();}
 }
 return 0;
}
