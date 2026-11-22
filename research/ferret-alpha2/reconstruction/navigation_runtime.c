#include "navigation.h"
uint8_t navigation_framebuffer[11520];
static uint16_t tilemap[18][64];
volatile uint32_t navigation_frames;
volatile uint16_t navigation_vblanks,navigation_buttons,navigation_debug_pause;
extern void pipeline_write(const uint8_t*);
static volatile uint16_t*const ctrl=(void*)0xc00004;
static void command(uint16_t a){*(volatile uint32_t*)ctrl=0x40000000u|((uint32_t)(a&0x3fff)<<16)|(a>>14);}
static void publish(uint16_t base){
 for(uint16_t y=0;y<18;y++)for(uint16_t x=0;x<40;x++)tilemap[y][x]=base+y*40+x;
 /* Start at a fresh VBlank: all 2304 attribute bytes fit, including stride padding. */
 while(*ctrl&8){}while(!(*ctrl&8)){}
 uint32_t source=(uint32_t)tilemap>>1;*ctrl=0x9300|(1152&255);*ctrl=0x9400|(1152>>8);*ctrl=0x9500|(source&255);*ctrl=0x9600|((source>>8)&255);*ctrl=0x9700|((source>>16)&127);
 *(volatile uint32_t*)ctrl=0x61000083u;
}
void scene_main(void){
 uint16_t shown=0,last=0;navigation_reset();
 *(volatile uint8_t*)0xa10009=0x40;*(volatile uint8_t*)0xa10003=0x40;
 *ctrl=0x8134;
 __asm__ volatile("move.w #0x2000,%%sr":::"cc");
 for(;;){
  while(navigation_debug_pause){}
  uint16_t now=navigation_vblanks,dt=now-last;last=now;
  navigation_update(navigation_buttons,dt);
  render_view(navigation_framebuffer,&navigation_camera,navigation_cell);
  uint16_t base=shown?16:736;command(base*32);pipeline_write(navigation_framebuffer);*ctrl=0x8174;publish(base);
  *ctrl=0x8174;shown^=1;navigation_frames++;
 }
}
