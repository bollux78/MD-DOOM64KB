#include "scene.h"
#ifndef HOLD_AFTER
#define HOLD_AFTER 0
#endif
#ifndef INITIAL_POSE
#define INITIAL_POSE 0
#endif
uint8_t phase3_framebuffer[11520];
volatile uint32_t phase3_frames;
volatile uint16_t phase3_pose;
extern void pipeline_write(const uint8_t *);
static volatile uint16_t *const ctrl=(void*)0xc00004;
static void command(uint16_t addr){*(volatile uint32_t*)ctrl=0x40000000u|((uint32_t)(addr&0x3fff)<<16)|(addr>>14);}
void scene_main(void){
 uint16_t shown=0,previous=15;phase3_pose=INITIAL_POSE;
 *(volatile uint8_t*)0xa10009=0x40;
 for(;;){
  *(volatile uint8_t*)0xa10003=0x40;
  uint16_t buttons=*(volatile uint8_t*)0xa10003;
  if(!(buttons&4)&&(previous&4))phase3_pose=(phase3_pose-1)&15;
  if(!(buttons&8)&&(previous&8))phase3_pose=(phase3_pose+1)&15;
  previous=buttons;
  render_scene(phase3_framebuffer,phase3_pose);
  uint16_t base=shown?16:736;command(base*32);pipeline_write(phase3_framebuffer);
  while(!(*ctrl&8)){}
  for(uint16_t y=0;y<18;y++){
   command(0xe100+y*128);for(uint16_t x=0;x<40;x++)*(volatile uint16_t*)0xc00000=base+y*40+x;
  }
  *ctrl=0x8144;shown^=1;phase3_frames++;
#if HOLD_AFTER
  while(phase3_frames>=HOLD_AFTER){}
#endif
 }
}
