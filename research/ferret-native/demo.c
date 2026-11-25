/* FERRET-MD R01 diagnostic: same native renderer on host and 68000.
 * No game logic or original ROM needed at runtime. Camera collision is not
 * implemented; movement is restricted to valid BSP leaf clearance.
 */
#include <stdint.h>
#include <stddef.h>
#include "core.c"
#include "frv2.c"
#include "presentation.c"
#include "md_video.c"
#include "scene.h"
static Frame frame;
static uint8_t sky[11520];
static uint8_t worktiles[23040] __attribute__((aligned(2)));
static FRV vis;
static int ready;
typedef struct {uint32_t candidates,projected,errors,closed,hash,tiles_hash,leaf,tests;} DemoStats;
static uint32_t hash_bytes(const uint8_t *p,uint32_t n){
    uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;
}
static int leaf_at(int16_t x,int16_t y){
    uint16_t node=SC_NODES?SC_NODES-1:32768u;
    unsigned limit=0;
    while(!(node&32768u)){
        if(node>=SC_NODES||++limit>SC_NODES)return -1;
        const int16_t *p=sc_planes+4u*node;
        int64_t s=(int64_t)p[2]*((int32_t)y-p[1])-(int64_t)p[3]*((int32_t)x-p[0]);
        node=sc_children[2u*node+(s>=0)];
    }
    return (node&32767u)<SC_LEAVES?(int)(node&32767u):-1;
}
static int scene_init(void){
    if(!ready){if(frv_open(&vis,sc_frv,SC_FRV_BYTES))return -1;ready=1;}return 0;
}
static int closed(void){
    for(unsigned x=0;x<160;x++)if(frame.top[x]||frame.bottom[x])return 0;
    return 1;
}
static Asset texture_at(unsigned i){
    Asset a={NULL,0,0};
    if(i<SC_ASSETS){a.data=sc_textures+4096u*i;a.size=4096;a.origin=8192;}
    return a;
}
static int render_pose(int16_t x,int16_t y,int16_t z,int16_t angle,DemoStats *s){
    if(scene_init())return -1;
    unsigned a=(unsigned)((angle%360+360)%360);
    int16_t co=sc_trig[a*2],si=sc_trig[a*2+1];
    for(unsigned i=0;i<11520;i++)frame.pixels[i]=0;
    for(unsigned i=0;i<160;i++)frame.depth[i]=0;
    fr_begin(&frame);
    for(unsigned i=0;i<160;i++)for(unsigned j=0;j<72;j++)
        sky[i*72+j]=sc_sky[(j*SC_SKYH/72)*SC_SKYW+(a*SC_SKYW/360+i*SC_SKYW/640)%SC_SKYW];
    s->candidates=s->projected=s->errors=s->closed=s->hash=s->tiles_hash=s->tests=0;
    int cell=leaf_at(x,y);if(cell<0)return -2;
    s->leaf=(uint32_t)cell;
    FRIter it;if(frv_begin(&it,&vis,(uint16_t)cell,x,y,sc_planes,SC_NODES)!=1)return -3;
    uint16_t leaf;int rc;
    while((rc=frv_next(&it,&leaf))>0){
        if(closed())break;
        unsigned n=sc_leaves[leaf*2],first=sc_leaves[leaf*2+1];
        for(unsigned j=first;j<first+n;j++){
            if(!frv_keep(&it,(uint16_t)j))continue;
            s->candidates++;
            const int16_t *w=sc_walls+14u*j;
            if(w[2]==255)continue;
            int32_t tx,tz,ux,uz;
            fr_transform(sc_vertices[2u*w[0]],sc_vertices[2u*w[0]+1],(int32_t)x*8,(int32_t)y*8,co,si,&tx,&tz);
            fr_transform(sc_vertices[2u*w[1]],sc_vertices[2u*w[1]+1],(int32_t)x*8,(int32_t)y*8,co,si,&ux,&uz);
            WallJob job;job.variant=w[2];job.z=-z;
            for(unsigned k=0;k<4;k++)job.heights[k]=w[6+k];
            job.ceiling=w[10];job.floor=w[11];
            int r=fr_project(tx,tz,ux,uz,w[3],w[4],w[5],&job);
            if(r<0){s->errors++;continue;}if(!r)continue;s->projected++;
            if(fr_wall_indexed(&frame,&job,texture_at((uint16_t)w[12]),texture_at((uint16_t)w[13]),sc_scalers,sc_indices,sky))s->errors++;
        }
    }
    if(rc<0)return -4;
    s->tests=it.tests;
    for(unsigned i=0;i<160;i++)s->closed+=!frame.top[i]&&!frame.bottom[i];
    s->hash=hash_bytes(frame.pixels,11520);return 0;
}
static int pose(unsigned i,DemoStats *s){
    if(i>=SC_POSES)return -1;
    const int16_t *p=sc_poses+i*4;
    return render_pose(p[0],p[1],p[2],p[3],s);
}
#ifndef __m68k__
int fr_demo_frame(unsigned i,DemoStats *s,uint8_t *fb,uint8_t *tiles){
    int r=pose(i,s);if(r)return r;
    if(fr_tiles(frame.pixels,worktiles,sizeof(worktiles))!=23040)return -5;
    s->tiles_hash=hash_bytes(worktiles,23040);
    for(unsigned j=0;j<11520;j++)fb[j]=frame.pixels[j];
    for(unsigned j=0;j<23040;j++)tiles[j]=worktiles[j];
    return 0;
}
#else
#define IO8(a) (*(volatile uint8_t *)(a))
#define IO16(a) (*(volatile uint16_t *)(a))
#define IO32(a) (*(volatile uint32_t *)(a))
#define CTRL IO16(0xc00004ul)
#define DATA IO16(0xc00000ul)
#define MB ((volatile uint32_t *)0xfff000ul)
static void reg(unsigned i,unsigned v){CTRL=(uint16_t)(0x8000u|(i<<8)|v);}
static void vraddr(uint32_t a){IO32(0xc00004ul)=0x40000000u|((a&0x3fffu)<<16)|((a&0xc000u)>>14);}
static void init_vdp(void){
    static const uint8_t regs[24]={4,0x14,0x30,0x3c,7,0x78,0,0,0,0,0,0,0x81,0x3f,0,2,1,0,0,0,0,0,0,0};
    (void)CTRL;
    for(unsigned i=0;i<24;i++)reg(i,regs[i]);
    vraddr(0);for(uint32_t i=0;i<32768u;i++)DATA=0;
    IO32(0xc00004ul)=0xc0000000u;
    for(unsigned i=0;i<64;i++)DATA=i<16?sc_palette[i]:0;
    IO32(0xc00004ul)=0x40000010u;for(unsigned i=0;i<40;i++)DATA=0;
    vraddr(0xc000u);
    for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++)
        DATA=(uint16_t)((y>=5&&y<23&&x<40)?1+(y-5)*40+x:0);
    reg(1,0x54);
}
static int probe_sram(void){
    volatile uint16_t *p=(volatile uint16_t *)0x20a600ul;
    volatile uint16_t *q=(volatile uint16_t *)0x20fffeul;
    IO8(0xa130f1ul)=1;
    /* Diagnostic cartridge owns the whole declared SRAM area. */
    *p=0x5aa5;*q=0xa55a;
    if(*p==0x5aa5&&*q==0xa55a){*p=0xa55a;*q=0x5aa5;if(*p==0xa55a&&*q==0x5aa5)return 1;}
    IO8(0xa130f1ul)=0;return 0;
}
static unsigned pad(void){
    IO8(0xa10009ul)=0x40;IO8(0xa10003ul)=0x40;
    __asm__ volatile("nop\n\tnop\n\t");
    unsigned high=(unsigned)(~IO8(0xa10003ul))&0x3f;
    IO8(0xa10003ul)=0;
    __asm__ volatile("nop\n\tnop\n\t");
    unsigned low=(unsigned)(~IO8(0xa10003ul))&0x30;
    IO8(0xa10003ul)=0x40;
    return high|(low<<2);
}
static void next_blank(void){
    /* Bounded polling: interrupts remain disabled in the diagnostic ROM. */
    for(uint32_t n=0;n<1000000u&&(CTRL&8u);n++){}
    for(uint32_t n=0;n<1000000u&&!(CTRL&8u);n++){}
}
void *memset(void *p,int c,size_t n){uint8_t *d=p;while(n--)*d++=(uint8_t)c;return p;}
void *memcpy(void *p,const void *q,size_t n){uint8_t *d=p;const uint8_t *s=q;while(n--)*d++=*s++;return p;}
void md_main(void){
    MB[0]=0x46523031u;MB[1]=0;MB[2]=1;
    if(IO8(0xa10001ul)&15u)IO32(0xa14000ul)=0x53454741u;
    IO16(0xa11100ul)=0x0100;IO16(0xa11200ul)=0x0000;
    init_vdp();
    int has_sram=probe_sram(),use_sram=has_sram;
    MB[3]=(uint32_t)has_sram;MB[2]=2;
    unsigned seq=0,idx=0,last=0;
    int16_t x=sc_poses[0],y=sc_poses[1],z=sc_poses[2],a=sc_poses[3];
    for(;;){
        DemoStats s;int rc;
        if(seq<SC_POSES){idx=seq;x=sc_poses[4*idx];y=sc_poses[4*idx+1];z=sc_poses[4*idx+2];a=sc_poses[4*idx+3];}
        else {
            unsigned p=pad(),pressed=p&~last;last=p;
            if((pressed&0x40u)&&has_sram)use_sram=!use_sram; /* A */
            if(pressed&0x10u){idx=(idx+1)%SC_POSES;x=sc_poses[idx*4];y=sc_poses[idx*4+1];z=sc_poses[idx*4+2];a=sc_poses[idx*4+3];}
            if(p&4u)a=(int16_t)((a+355)%360);
            if(p&8u)a=(int16_t)((a+5)%360);
            int dir=(p&1u)?1:(p&2u)?-1:0;
            if(dir){
                int16_t nx=(int16_t)(x+dir*(sc_trig[2u*a+1]/2048)),ny=(int16_t)(y+dir*(sc_trig[2u*a]/2048));
                int leaf=leaf_at(nx,ny);
                if(leaf>=0&&sc_ceiling[leaf]-sc_floor[leaf]>=42){x=nx;y=ny;z=(int16_t)(sc_floor[leaf]+41);}
            }
        }
        MB[2]=3;
        rc=render_pose(x,y,z,a,&s);
        if(rc){MB[2]=0x80000000u|(uint32_t)(-rc);for(;;){}}
        uint8_t *dst=use_sram?(uint8_t *)0x20a600ul:worktiles;
        MB[2]=4;
        if(fr_tiles(frame.pixels,dst,23040)!=23040){MB[2]=0x80000005u;for(;;){}}
        s.tiles_hash=hash_bytes(dst,23040);
        next_blank();reg(1,0x14);
        rc=fr_md_dma((uint32_t)(uintptr_t)dst,0x20,23040);
        reg(1,0x54);
        MB[4]=idx;MB[5]=s.hash;MB[6]=s.tiles_hash;MB[7]=s.candidates;MB[8]=s.projected;
        MB[9]=s.errors;MB[10]=s.closed;MB[11]=(uint32_t)use_sram;MB[12]=(uint32_t)rc;
        MB[13]=(uint32_t)(uint16_t)x;MB[14]=(uint32_t)(uint16_t)y;MB[15]=(uint32_t)(uint16_t)a;MB[16]=s.tests;
        MB[2]=rc?0x80000006u:5;MB[1]=++seq;
        if(rc)for(;;){}
    }
}
#endif
