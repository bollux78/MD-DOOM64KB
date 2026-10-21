/* R47A pixel4 flat-clipping oracle. Host-only, no SGDK or emulator.
 * Compare reference R22_Plot versus the opt-in R47A inner loop with
 * identical random framebuffer state, palette LUT, coordinates and borders.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
enum { W=76, H=44, P=38, B=P*H };
static uint8_t original[B], optimized[B], pal[256];
static uint32_t seed=0xA47A20u;
static uint32_t rng(void){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
static void plot(int16_t x,int16_t y,uint8_t c,int level){
    if((uint16_t)x>=W||(uint16_t)y>=H)return;
    if(level&&(x<2||y<2))return;
    uint8_t *p=original+y*P+((uint16_t)x>>1);
    c&=15;
    *p=(x&1)?(uint8_t)((*p&240u)|c):(uint8_t)((*p&15u)|(c<<4));
}
static void orig(int16_t x,int16_t a,int16_t b,uint8_t c,int level){
    c=pal[c];
    for(int16_t y=a;y<=b;y++)plot(x,y,c,level);
}
static void fast(int16_t x,int16_t a,int16_t b,uint8_t c,int level){
    if(b<a||(uint16_t)x>=W)return;
    int16_t border=level?2:0;
    if(x<border)return;
    if(a<border)a=border;
    if(a<0)a=0;
    if(b>=H)b=H-1;
    if(a>b)return;
    uint8_t sample=(uint8_t)(pal[c]&15u);
    uint8_t keep=(x&1)?0xf0u:0x0fu;
    uint8_t put=(x&1)?sample:(uint8_t)(sample<<4);
    uint8_t *dst=optimized+(uint16_t)a*P+((uint16_t)x>>1);
    uint16_t n=(uint16_t)(b-a);
    do{*dst=(uint8_t)((*dst&keep)|put);dst+=P;}while(n--);
}
int main(void){
    for(unsigned t=0;t<120000;t++){
        for(unsigned i=0;i<B;i++) original[i]=optimized[i]=(uint8_t)rng();
        for(unsigned i=0;i<256;i++)pal[i]=(uint8_t)rng();
        int16_t x=(int16_t)((int)(rng()%116)-20);
        int16_t y0=(int16_t)((int)(rng()%160)-65);
        int16_t y1=(int16_t)((int)(rng()%160)-65);
        uint8_t c=(uint8_t)rng();
        int level=(int)(rng()&1u);
        orig(x,y0,y1,c,level);
        fast(x,y0,y1,c,level);
        if(memcmp(original,optimized,B)!=0){
            fprintf(stderr,"R47A mismatch trial=%u x=%d y0=%d y1=%d level=%d\n",t,x,y0,y1,level);
            return 1;
        }
    }
    puts("R47A PASS: 120000 randomized flat-column cases, entire packed framebuffer byte-identical");
    return 0;
}
