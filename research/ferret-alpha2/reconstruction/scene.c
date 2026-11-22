/* New scalar implementation. No Ferret executable instructions are embedded. */
#include "scene.h"
static int16_t top_clip[160],bottom_clip[160];
static int32_t sd(int32_t a,int16_t b) {
#ifdef __m68k__
 __asm__("divs.w %1,%0":"+d"(a):"d"(b):"cc");return (int16_t)a;
#else
 return a/b;
#endif
}
static uint16_t ud(int32_t a,uint16_t b) {
#ifdef __m68k__
 __asm__("divu.w %1,%0":"+d"(a):"d"(b):"cc");return (uint16_t)a;
#else
 return (uint32_t)a/b;
#endif
}
static uint32_t divlong(uint32_t a,uint16_t b) {
 uint32_t hi=a>>16;
#ifdef __m68k__
 __asm__("divu.w %1,%0":"+d"(hi):"d"(b):"cc");
 uint32_t lo=(hi&0xffff0000u)|(a&65535);uint32_t q=(hi&65535)<<16;
 __asm__("divu.w %1,%0":"+d"(lo):"d"(b):"cc");return q|(lo&65535);
#else
 return a/b;
#endif
}
static int16_t mn(int16_t a,int16_t b){return a<b?a:b;}
static int16_t mx(int16_t a,int16_t b){return a>b?a:b;}
static void vertex(int16_t x,int16_t y,const Camera *c,int16_t *tx,int16_t *tz) {
 x=(int16_t)((uint16_t)x*8-c->x);y=(int16_t)((uint16_t)y*8-c->y);
 *tx=(int16_t)(((uint32_t)((int32_t)x*c->co-(int32_t)y*c->si)<<2)>>16);
 *tz=(int16_t)(((uint32_t)((int32_t)x*c->si+(int32_t)y*c->co)<<2)>>16);
}
typedef struct {int16_t x,n,step;uint16_t inv0,inv1;uint32_t u,du;uint8_t linear,textured;} Job;
static int project(const Wall*w,const Camera*c,Job*j) {
 int16_t x0,z0,x1,z1,u0=w->u0,u1=w->u1;vertex(w->x0,w->y0,c,&x0,&z0);vertex(w->x1,w->y1,c,&x1,&z1);
 int16_t near=w->variant==4?82:81;j->textured=near&1;
 int16_t d=(int16_t)(x0+z0);
 if(d<0){int16_t d1=(int16_t)(x1+z1);if(d1<0)return 0;int16_t den=(int16_t)(d1-d);if(j->textured)u0=(int16_t)(u0-sd((int16_t)(u1-u0)*(int32_t)d,den));x0=(int16_t)(x0-sd((int16_t)(x1-x0)*(int32_t)d,den));z0=(int16_t)-x0;}
 d=(int16_t)(z1-x1);
 if(d<0){int16_t d0=(int16_t)(z0-x0);if(d0<0)return 0;int16_t den=(int16_t)(d0-d);x1=(int16_t)(x1-sd((int16_t)(x0-x1)*(int32_t)d,den));if(j->textured)u1=(int16_t)(u1-sd((int16_t)(u0-u1)*(int32_t)d,den));z1=x1;}
 z0=(int16_t)(z0-near);z1=(int16_t)(z1-near);
 if(z0<0){if(z1<0)return 0;int16_t den=(int16_t)(z0-z1);if(j->textured)u0=(int16_t)(u0-sd((int16_t)(u0-u1)*(int32_t)z0,den));x0=(int16_t)(x0-sd((int16_t)(x0-x1)*(int32_t)z0,den));z0=0;}
 else if(z1<0){int16_t den=(int16_t)(z0-z1);if(j->textured)u1=(int16_t)(u1-sd((int16_t)(u0-u1)*(int32_t)z1,den));x1=(int16_t)(x1-sd((int16_t)(x0-x1)*(int32_t)z1,den));z1=0;}
 z0=(int16_t)(z0+near);z1=(int16_t)(z1+near);
 int16_t sx0=mx(0,(int16_t)(sd(x0*80L,z0)+80)),sx1=mn(160,(int16_t)(sd(x1*80L,z1)+80));j->n=(int16_t)(sx1-sx0);if(j->n<=0)return 0;j->x=sx0;j->inv0=ud(0x500000,z0);j->inv1=ud(0x500000,z1);j->step=sd((int32_t)j->inv1-j->inv0,j->n);
 if(j->textured){uint16_t a=(uint16_t)((uint16_t)u0<<7),b=(uint16_t)((uint16_t)u1<<7);uint32_t p0=(uint32_t)a*j->inv0,p1=(uint32_t)b*j->inv1;uint16_t mean_inv=((uint32_t)j->inv0+j->inv1)/2,mean_u=((uint32_t)a+b)/2;uint32_t mean_product=(p0>>1)+(p1>>1)+((p0&p1)&1);uint16_t approx=ud(mean_product,mean_inv),err=(uint16_t)(mean_u-approx);if((int16_t)mean_u<(int16_t)approx)err=(uint16_t)-err;j->linear=err<512 || (uint16_t)(err-512)<ud(10000000,mean_inv);uint32_t left=j->linear?a:p0,right=j->linear?b:p1;j->u=left;j->du=right>=left?divlong(right-left,j->n):0-divlong(left-right,j->n);}
 return 1;
}
static void span(uint8_t*fb,int16_t x,int16_t lo,int16_t hi,uint8_t color,const uint8_t*sky,const uint8_t*tex,uint16_t inv) {
 lo=mx(lo,top_clip[x]);hi=mn(hi,bottom_clip[x]);if(lo>=hi)return;
 uint8_t*d=fb+(x/2)*144+(x&1)+lo*2;
 for(int16_t y=lo;y<hi;y++,d+=2)*d=tex?tex[sample_offsets[inv>>5][y]]:(sky?sky[y]:color);
}
void render_scene(uint8_t*fb,uint16_t pose) {
 const Camera*c=&scene_cameras[pose&15];for(uint16_t i=0;i<11520;i++)fb[i]=0;for(uint16_t x=0;x<160;x++){top_clip[x]=0;bottom_clip[x]=72;}
 for(uint16_t wi=0;wi<scene_wall_count;wi++){
  const Wall*w=&scene_walls[wi];Job j;if(!project(w,c,&j))continue;uint16_t v=w->variant;
  uint16_t sky=v==2||v==3||v>=12,ceiling=v!=4&&v!=5,upper=v<=3||(v>=9&&v<=11)||v>=15,lower=v==1||v==3||v==5||v==8||v==11||v==14||v==17,floor=v<=5||v==7||v==8||v==10||v==11||v==13||v==14||v==16||v==17;
  int32_t edges[4];int16_t delta[4];for(uint16_t k=0;k<4;k++){int16_t h=(int16_t)(w->h[k]-c->z);edges[k]=(j.inv0>>5)*(int32_t)h+9344;delta[k]=sd(((j.inv1>>5)-(j.inv0>>5))*(int32_t)h,j.n);}
  uint32_t u=j.u;uint16_t inv=j.inv0;
  for(int16_t col=0;col<j.n;col++,u+=j.du,inv=(uint16_t)(inv+j.step)){
   int16_t x=j.x+col,top=top_clip[x],bottom=bottom_clip[x],rows[4];for(uint16_t k=0;k<4;k++){rows[k]=(int16_t)(edges[k]>>8);edges[k]+=delta[k];}if(top>=bottom)continue;
   uint16_t off=j.textured?(j.linear?((uint16_t)u&0x1f80):(ud(u,inv)&0x1f80)):0;const uint8_t*t0=texture_blob+w->tex0+(c->z>>1)+off,*t1=texture_blob+w->tex1+(c->z>>1)+off;
   if(ceiling)span(fb,x,top,rows[0],w->color0,sky?sky_columns[(c->sky+x)&127]:0,0,inv);
   if(upper)span(fb,x,rows[0],rows[1],0,0,t0,inv);
   int16_t low=(v==1||v==3)?rows[1]:rows[2],fl=(v==0||v==2)?rows[1]:(lower?rows[3]:rows[2]);
   if(lower)span(fb,x,low,rows[3],0,0,t1,inv);if(floor)span(fb,x,fl,bottom,w->color1,0,0,inv);
   if(v<=3)top_clip[x]=bottom_clip[x]=0;else{top_clip[x]=mn(bottom,mx(top,upper?rows[1]:(ceiling?rows[0]:top)));bottom_clip[x]=mx(top,mn(bottom,lower?low:(floor?fl:bottom)));}
  }
 }
}
