#include <stdio.h>
#include <stdlib.h>
#include "m68k.h"
static unsigned char mem[0x1000000],sram[65536];
static unsigned bank,switches,reads,writes,romreads,done;static unsigned long long total,t0;
static unsigned rd8(unsigned a){a&=0xffffff;if(a>=0x200000&&a<0x400000){if(bank){if(a>0x20ffff){fprintf(stderr,"ROM read with SRAM on: %x\n",a);exit(5);}reads++;return sram[a&65535];}romreads++;}return mem[a];}
static unsigned rd16(unsigned a){return (rd8(a)<<8)|rd8(a+1);}
unsigned m68k_read_memory_8(unsigned a){return rd8(a);}unsigned m68k_read_memory_16(unsigned a){return rd16(a);}unsigned m68k_read_memory_32(unsigned a){return (rd16(a)<<16)|rd16(a+2);}unsigned m68k_read_disassembler_16(unsigned a){return rd16(a);}unsigned m68k_read_disassembler_32(unsigned a){return m68k_read_memory_32(a);}
static void marker(unsigned a,unsigned v){if(a==0xA00000)t0=total;else if(a==0xA00002)printf("tag %u cycles %llu\n",v,total-t0);else if(a==0xA00004)done=1;}
void m68k_write_memory_8(unsigned a,unsigned v){a&=0xffffff;if(a>=0xA00000&&a<0xA00010){marker(a,v);return;}if(a==0xA130F1){bank=v&1;switches++;return;}if(a>=0x200000&&a<0x400000){if(!bank||a>0x20ffff||!(a&1)){fprintf(stderr,"Invalid SRAM write %x\n",a);exit(6);}sram[a&65535]=v;writes++;return;}mem[a]=v;}
void m68k_write_memory_16(unsigned a,unsigned v){a&=0xffffff;if(a>=0xA00000&&a<0xA00010){marker(a,v);return;}m68k_write_memory_8(a,v>>8);m68k_write_memory_8(a+1,v);}
void m68k_write_memory_32(unsigned a,unsigned v){m68k_write_memory_16(a,v>>16);m68k_write_memory_16(a+2,v);}
int main(int argc,char **argv){FILE *f=fopen(argv[1],"rb");if(!f)return 1;fread(mem,1,sizeof mem,f);fclose(f);m68k_init();m68k_set_cpu_type(M68K_CPU_TYPE_68000);m68k_pulse_reset();unsigned long guard=0;while(!done&&guard++<200000000)total+=m68k_execute(1);if(argc>2){f=fopen(argv[2],"wb");fwrite(mem,1,sizeof mem,f);fclose(f);}printf("mapper=%u switches=%u SRAM reads=%u writes=%u upper-ROM reads=%u\n",bank,switches,reads,writes,romreads);return !done?2:0;}
