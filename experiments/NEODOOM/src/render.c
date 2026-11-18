#include "neodoom.h"
#ifdef __m68k__
#include <genesis.h>
#else
#include <string.h>
#endif
extern const uint16_t nd_tex_width[],nd_tex_height[];
NdStats nd_stats;
uint16_t nd_flat;
/* Positive 32/16 -> saturated 16-bit quotient, native DIVU on the 68000. */
static uint16_t quotient(uint32_t n,uint16_t d){
 if(!d || (n>>16)>=d)return 65535;
#ifdef __m68k__
 __asm__("divu.w %1,%0":"+d"(n):"d"(d):"cc");return (uint16_t)n;
#else
 return n/d;
#endif
}
static int16_t project(int16_t z,int16_t eye,uint16_t t){
 int32_t n=((int32_t)z-eye)*(ND_FOCAL*16);
 int16_t a=(int16_t)quotient(n<0?-n:n,t?t:1);
 if(a<0 || a>30000)a=30000;
 return ND_H/2+(n<0?a:-a);
}
static int inside(int16_t x,int16_t y,uint16_t r){
 const NdRoom *room=&nd_rooms[r];
 for(uint16_t j=0;j<room->count;j++){
  const NdEdge *e=&nd_edges[room->first+j];
  if((int32_t)e->nx*x+(int32_t)e->ny*y>e->plane+128)return 0;
 }
 return 1;
}
int16_t nd_locate(int16_t x,int16_t y,int16_t hint){
 if(hint>=0 && hint<nd_room_count && inside(x,y,hint))return hint;
 if(hint>=0 && hint<nd_room_count){
  const NdRoom *r=&nd_rooms[hint];
  for(uint16_t i=0;i<r->count;i++){uint16_t n=nd_edges[r->first+i].next;if(n!=65535 && inside(x,y,n))return n;}
 }
 for(uint16_t i=0;i<nd_room_count;i++)if(inside(x,y,i))return i;
 return -1;
}
static void fill(uint8_t *column,int16_t a,int16_t b,uint8_t c){
 if(a<0)a=0;if(b>=ND_H)b=ND_H-1;
 if(a<=b)memset(column+a,c,b-a+1);
}
static int32_t signed_width(int32_t n,uint16_t w){
 if(w==64)return n>>6;if(w==128)return n>>7;if(w==256)return n>>8;if(w==32)return n>>5;return n/w;
}
static void wall(uint8_t *column,int16_t a,int16_t b,uint16_t tex,int16_t top,const NdCamera *cam,const NdEdge *e,int16_t dx,int16_t dy,uint16_t t){
 if(a<0)a=0;if(b>=ND_H)b=ND_H-1;if(a>b)return;
 if(nd_flat){fill(column,a,b,12);return;}
 if(!tex){fill(column,a,b,9);return;}
 int16_t half=(int16_t)(t>>1);
 int16_t hx=cam->x+(((int32_t)dx*half)>>9),hy=cam->y+(((int32_t)dy*half)>>9);
 int32_t u=(((hx*e->ux+hy*e->uy-e->origin)>>10)+e->xoff)*64;
 u=signed_width(u,nd_tex_width[tex]);
 uint16_t h=nd_tex_height[tex];
 uint32_t step=quotient((uint32_t)t<<10,(uint16_t)(ND_FOCAL*h));
 int32_t v=signed_width(((int32_t)top-cam->z+e->yoff)*16384,h)+(int32_t)(int16_t)(a-ND_H/2)*(int16_t)step;
 const uint8_t *source=nd_textures[tex]+((uint16_t)u&63)*64;
 while(a<=b){column[a++]=source[(v>>8)&63];v+=step;}
}
static const uint16_t patterns[16]={0x0000,0x1111,0x2222,0x3333,0x4444,0x5555,0x6666,0x7777,0x8888,0x9999,0xAAAA,0xBBBB,0xCCCC,0xDDDD,0xEEEE,0xFFFF};
void nd_pack(const uint8_t *pixels,uint32_t *tiles){
#ifdef __m68k__
 register const uint8_t *src __asm__("a0")=pixels;
 register uint32_t *dst __asm__("a1")=tiles;
 register const uint16_t *lut __asm__("a2")=patterns;
 __asm__ volatile(
 "moveq #19,%%d3\n\t"
 "1: moveq #35,%%d2\n\t"
 "2: moveq #0,%%d0\n\tmove.b (%0),%%d0\n\tadd.w %%d0,%%d0\n\tmove.w (%2,%%d0.w),%%d1\n\tswap %%d1\n\t"
 "moveq #0,%%d0\n\tmove.b 40(%0),%%d0\n\tadd.w %%d0,%%d0\n\tmove.w (%2,%%d0.w),%%d1\n\t"
 "move.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\t"
 "moveq #0,%%d0\n\tmove.b 1(%0),%%d0\n\tadd.w %%d0,%%d0\n\tmove.w (%2,%%d0.w),%%d1\n\tswap %%d1\n\t"
 "moveq #0,%%d0\n\tmove.b 41(%0),%%d0\n\tadd.w %%d0,%%d0\n\tmove.w (%2,%%d0.w),%%d1\n\t"
 "move.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\tmove.l %%d1,(%1)+\n\t"
 "lea 80(%0),%0\n\tdbra %%d2,2b\n\tlea -2878(%0),%0\n\tdbra %%d3,1b"
 : "+a"(src),"+a"(dst):"a"(lut):"d0","d1","d2","d3","cc","memory");
#else

 /* 4x4 logical samples, column-major framebuffer -> row-major VDP tiles. */
 for(uint16_t ty=0;ty<ND_H/2;ty++)for(uint16_t tx=0;tx<ND_W/2;tx++){
  uint32_t *out=tiles+(ty*(ND_W/2)+tx)*8;
  uint16_t a=(tx*2)*ND_H+ty*2,b=a+ND_H;
  uint32_t top=(uint32_t)(patterns[pixels[a]])<<16 | patterns[pixels[b]];
  uint32_t bottom=(uint32_t)(patterns[pixels[a+1]])<<16 | patterns[pixels[b+1]];
  out[0]=out[1]=out[2]=out[3]=top;out[4]=out[5]=out[6]=out[7]=bottom;
 }
#endif
}

typedef struct {uint16_t room;int16_t left,right;} PortalTask;
static PortalTask tasks[128];
static int16_t cliptop[ND_W],clipbottom[ND_W],raydx[ND_W],raydy[ND_W];
static const int16_t slopes[ND_W]={-252,-245,-238,-231,-224,-216,-209,-202,-195,-188,-181,-174,-167,-160,-152,-145,-138,-131,-124,-117,-110,-103,-96,-88,-81,-74,-67,-60,-53,-46,-39,-32,-24,-17,-10,-3,3,10,17,24,32,39,46,53,60,67,74,81,88,96,103,110,117,124,131,138,145,152,160,167,174,181,188,195,202,209,216,224,231,238,245,252};

static int32_t signed_ratio(int32_t n,uint16_t den){return n<0?-(int32_t)quotient(-n,den):(int32_t)quotient(n,den);}
void nd_render(const NdCamera *cam,uint8_t *pixels){

 memset(&nd_stats,0,sizeof(nd_stats));memset(pixels,0,ND_BYTES);
 int16_t cs=nd_sines[(cam->angle+64)&255],sn=nd_sines[cam->angle&255];
 for(uint16_t x=0;x<ND_W;x++){
  cliptop[x]=0;clipbottom[x]=ND_H-1;
  raydx[x]=cs+((int32_t)sn*slopes[x]>>8);raydy[x]=sn-((int32_t)cs*slopes[x]>>8);
 }
 uint16_t pending=1;tasks[0]=(PortalTask){cam->room,0,ND_W-1};uint16_t visits=0;
 while(pending){
  PortalTask task=tasks[--pending];const NdRoom *r=&nd_rooms[task.room];
  if(++visits>1024){nd_stats.overflow++;break;}
  for(uint16_t index=0;index<r->count;index++){
   const NdEdge *e=&nd_edges[r->first+index];nd_stats.edges++;
   int32_t plane=e->plane-(int32_t)e->nx*cam->x-(int32_t)e->ny*cam->y;
   if(plane<=0)continue; /* entrance/back-facing boundary */
   int16_t ax=e->ax-cam->x,ay=e->ay-cam->y,bx=e->bx-cam->x,by=e->by-cam->y;
   int16_t az=((int32_t)ax*cs+(int32_t)ay*sn)>>8,bz=((int32_t)bx*cs+(int32_t)by*sn)>>8;
   int16_t as=((int32_t)ax*sn-(int32_t)ay*cs)>>8,bs=((int32_t)bx*sn-(int32_t)by*cs)>>8;
   if(az<4 && bz<4)continue;
   if(az<4){as+=((int32_t)(bs-as)*(4-az))/(bz-az);az=4;}
   if(bz<4){bs+=((int32_t)(as-bs)*(4-bz))/(az-bz);bz=4;}
   int32_t pa=ND_W*128+signed_ratio((int32_t)as*(ND_FOCAL*256),(uint16_t)az);
   int32_t pb=ND_W*128+signed_ratio((int32_t)bs*(ND_FOCAL*256),(uint16_t)bz);
   int16_t left=((pa<pb?pa:pb)+127)>>8,right=(((pa>pb?pa:pb)+127)>>8)-1;
   if(left<task.left)left=task.left;if(right>task.right)right=task.right;
   if(left>right)continue;
   int16_t nextleft=ND_W,nextright=-1;
   const NdRoom *n=e->next==65535?0:&nd_rooms[e->next];
   int32_t dl=((int32_t)e->nx*raydx[left]+(int32_t)e->ny*raydy[left])>>8;
   int32_t dr=((int32_t)e->nx*raydx[right]+(int32_t)e->ny*raydy[right])>>8;
   if(dl<=0 || dr<=0)continue;
   uint16_t tl=quotient((uint32_t)plane<<2,(uint16_t)dl),tr=quotient((uint32_t)plane<<2,(uint16_t)dr);
   int16_t c0=project(r->ceiling,cam->z,tl),c1=project(r->ceiling,cam->z,tr);
   int16_t f0=project(r->floor,cam->z,tl),f1=project(r->floor,cam->z,tr);
   int16_t nc0=n?project(n->ceiling,cam->z,tl):0,nc1=n?project(n->ceiling,cam->z,tr):0;
   int16_t nf0=n?project(n->floor,cam->z,tl):0,nf1=n?project(n->floor,cam->z,tr):0;
   uint16_t span=(right>left)?right-left:1;
   int32_t cp=(int32_t)c0*256,fp=(int32_t)f0*256,ncp=(int32_t)nc0*256,nfp=(int32_t)nf0*256;
   int32_t dc=signed_ratio(((int32_t)c1-c0)*256,span),df=signed_ratio(((int32_t)f1-f0)*256,span);
   int32_t dnc=signed_ratio(((int32_t)nc1-nc0)*256,span),dnf=signed_ratio(((int32_t)nf1-nf0)*256,span);
   for(int16_t x=left;x<=right;x++,cp+=dc,fp+=df,ncp+=dnc,nfp+=dnf){
    int16_t upper=cliptop[x],lower=clipbottom[x];if(upper>lower)continue;
    int16_t dx=raydx[x],dy=raydy[x];
    int32_t den=((int32_t)e->nx*dx+(int32_t)e->ny*dy)>>8;
    if(den<=0)continue;
    uint16_t t=nd_flat?tl:quotient((uint32_t)plane<<2,(uint16_t)den);
    if(!t || t==65535)continue;
    uint8_t *column=pixels+x*ND_H;nd_stats.rays++;
    int16_t cy=cp>>8,fy=fp>>8;
    fill(column,upper,cy-1,8);fill(column,fy+1,lower,9);
    if(cy>upper)upper=cy;if(fy<lower)lower=fy;
    if(upper<=lower){
     if(!n || n->ceiling<=r->floor || n->floor>=r->ceiling || n->ceiling<=n->floor){
      uint16_t tex=e->mid?e->mid:(e->upper?e->upper:e->lower);
      int16_t anchor=(e->flags&16)?r->floor+nd_tex_height[tex]:r->ceiling;
      wall(column,upper,lower,tex,anchor,cam,e,dx,dy,t);upper=ND_H;
     }else{
      if(n->ceiling<r->ceiling){int16_t bottom=(ncp>>8)-1;wall(column,upper,bottom<lower?bottom:lower,e->upper,r->ceiling,cam,e,dx,dy,t);if(bottom>=upper)upper=bottom+1;}
      if(n->floor>r->floor){int16_t top=(nfp>>8)+1;wall(column,top>upper?top:upper,lower,e->lower,n->floor,cam,e,dx,dy,t);if(top<=lower)lower=top-1;}
     }
    }
    cliptop[x]=upper;clipbottom[x]=lower;
    if(n && upper<=lower){if(x<nextleft)nextleft=x;nextright=x;}
   }
   if(nextright>=nextleft){
    if(pending==128){nd_stats.overflow++;continue;}
    tasks[pending++]=(PortalTask){e->next,nextleft,nextright};nd_stats.portals++;
   }
  }
 }
}

uint16_t nd_pack_mixed(const uint8_t *pixels,uint32_t *tiles,uint16_t *map,uint16_t base,uint16_t solid){
 uint16_t count=0;
 for(uint16_t ty=0;ty<ND_H/2;ty++)for(uint16_t tx=0;tx<ND_W/2;tx++){
  uint16_t a=(tx*2)*ND_H+ty*2,b=a+ND_H;
  uint8_t p=pixels[a],q=pixels[a+1],r=pixels[b],s=pixels[b+1];
  if(p==q && p==r && p==s){*map++=solid+p;continue;}
  *map++=base+count++;
  uint32_t top=(uint32_t)patterns[p]<<16 | patterns[r],bottom=(uint32_t)patterns[q]<<16 | patterns[s];
  tiles[0]=tiles[1]=tiles[2]=tiles[3]=top;tiles[4]=tiles[5]=tiles[6]=tiles[7]=bottom;tiles+=8;
 }
 return count;
}
