#include <stdint.h>
#include <stdio.h>
#include "r99_recip.h"
int main(void){uint64_t n=0,bad=0;uint32_t x=1;
for(uint64_t v=0x10000;v<=0xffffffffu;v+= (v<0x1000000? 1 : (v>>12))){uint32_t a=R99_Recip((uint32_t)v),b=0xffffffffu/(uint32_t)v;n++;if(a!=b){if(bad<10)printf("v=%llx got %x want %x\n",(unsigned long long)v,a,b);bad++;}}
for(int i=0;i<20000000;i++){x=x*1664525u+1013904223u;uint32_t v=x|0x10000;if(R99_Recip(v)!=0xffffffffu/v){bad++;}n++;}
for(uint32_t v=1;v<0x10000;v++){if(R99_Recip(v)!=0xffffffffu/v)bad++;n++;}
printf("tested %llu bad %llu\n",(unsigned long long)n,(unsigned long long)bad);return bad!=0;}
