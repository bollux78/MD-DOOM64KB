/* R47 sprite-column clipping/stride-hoist oracle. Host-only. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
enum { W=76,H=44,P=38,B=P*H };
static uint8_t a[B],b[B],src[128],map[256],color[256];
static uint32_t seed=0x47505249u;
static uint32_t rng(void){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
static void plot(uint8_t *p,int16_t x,int16_t y,uint8_t c,int level){
    if((uint16_t)x>=W||(uint16_t)y>=H)return;if(level&&(x<2||y<2))return;
    uint8_t *d=p+y*P+((uint16_t)x>>1);c&=15;
    *d=(x&1)?(uint8_t)((*d&0xf0)|c):(uint8_t)((*d&0x0f)|(c<<4));
}
static void ref(int16_t x,int16_t y0,int16_t y1,uint16_t tex,uint16_t step,int level,int usemap){
    uint16_t f=(uint16_t)(tex+(int32_t)y0*step);
    for(int16_t y=y0;y<=y1;y++){uint8_t c=src[f>>9];if(usemap)c=map[c];plot(a,x,y,color[c],level);f+=step;}
}
static void fast(int16_t x,int16_t y0,int16_t y1,uint16_t tex,uint16_t step,int level,int usemap){
    if(y1<y0||(uint16_t)x>=W)return;int16_t border=level?2:0;if(x<border)return;
    int16_t first=y0;if(first<border)first=border;if(first<0)first=0;if(y1>=H)y1=H-1;if(first>y1)return;
    uint16_t f=(uint16_t)(tex+(int32_t)y0*step);
    f=(uint16_t)(f+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)step));
    uint8_t *d=b+first*P+((uint16_t)x>>1);uint16_t n=(uint16_t)(y1-first);
    if(x&1)do{uint8_t c=src[f>>9];if(usemap)c=map[c];*d=(uint8_t)((*d&0xf0)|(color[c]&15));d+=P;f+=step;}while(n--);
    else do{uint8_t c=src[f>>9];if(usemap)c=map[c];*d=(uint8_t)((*d&0x0f)|((color[c]&15)<<4));d+=P;f+=step;}while(n--);
}
int main(void){
    for(unsigned t=0;t<100000;t++){
        for(unsigned i=0;i<B;i++)a[i]=b[i]=(uint8_t)rng();
        for(unsigned i=0;i<128;i++)src[i]=(uint8_t)rng();
        for(unsigned i=0;i<256;i++){map[i]=(uint8_t)rng();color[i]=(uint8_t)rng();}
        int16_t x=(int16_t)((int)(rng()%110)-17),y0=(int16_t)((int)(rng()%120)-40),y1=(int16_t)((int)(rng()%120)-20);
        uint16_t tex=(uint16_t)rng(),step=(uint16_t)rng();int level=rng()&1,usemap=rng()&1;
        ref(x,y0,y1,tex,step,level,usemap);fast(x,y0,y1,tex,step,level,usemap);
        if(memcmp(a,b,B)){fprintf(stderr,"R47 sprite mismatch %u\n",t);return 1;}
    }
    puts("R47 PASS: 100000 randomized sprite columns byte-identical");
    return 0;
}
