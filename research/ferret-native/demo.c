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
static uint8_t worktiles[23040] __attribute__((aligned(2)));
static FRV vis;
static int ready;
typedef struct {uint32_t candidates,projected,errors,closed,hash,tiles_hash,leaf,tests;} DemoStats;
static uint32_t hash_bytes(const uint8_t *p,uint32_t n){
#ifdef FR_BENCH
    (void)p;(void)n;return 0; /* benchmark build: no diagnostic hashing (verification builds keep it) */
#else
    uint32_t h=2166136261u;while(n--){h^=*p++;h=(h<<24)+(h<<8)+(h<<7)+(h<<4)+(h<<1)+h;} /* == h*16777619u without a __mulsi3 call per byte */return h;
#endif
}
static int leaf_at(int16_t x,int16_t y){
    uint16_t node=SC_NODES?SC_NODES-1:32768u;
    unsigned limit=0;
    while(!(node&32768u)){
        if(node>=SC_NODES||++limit>SC_NODES)return -1;
        const int16_t *p=sc_planes+4u*node;
        /* |p|<=32768 and |dx|,|dy|<=65535: each product fits int32 (<2^31), so compare them instead of subtracting in 64 bits */
        int32_t pa=(int32_t)p[2]*((int32_t)y-p[1]),pb=(int32_t)p[3]*((int32_t)x-p[0]);
        node=sc_children[2u*node+(pa>=pb)];
    }
    return (node&32767u)<SC_LEAVES?(int)(node&32767u):-1;
}
static int scene_init(void){
    if(!ready){if(frv_open(&vis,sc_frv,SC_FRV_BYTES))return -1;ready=1;}return 0;
}
static unsigned closed_scan; /* columns never reopen once top=bottom=0, so resume the scan where it stopped */
static int closed(void){
    for(unsigned x=closed_scan;x<160;x++)if(frame.top[x]||frame.bottom[x]){closed_scan=x;return 0;}
    return 1;
}
static Asset texture_at(unsigned i){
    Asset a={NULL,0,0};
    if(i<SC_ASSETS){a.data=sc_textures+SC_ASSET_BYTES*i;a.size=SC_ASSET_BYTES;a.origin=8192;}
    return a;
}
/* Sky, drawn straight from the SKY texture by fill(): nothing is built or stored when no sky is visible.
 * Default mapping follows classic Doom: 256 texels per 90 degrees (the texture wraps 4x per turn) and the
 * horizon (row 36) at texel 100, scaled 128 texels per 72 rows. FR_SKY_LEGACY keeps the R04 mapping
 * (whole texture over 360 degrees, texel 0 at the top), for regression against R02-R04 hashes. */
static uint16_t sky_rows[72];static unsigned sky_base;static int sky_rows_ready;
static const uint8_t *sky_column(int x){
#ifdef FR_SKY_LEGACY
    return sc_sky+(sky_base+(unsigned)x*SC_SKYW/640)%SC_SKYW;
#else
    return sc_sky+((sky_base+(unsigned)x*8u/5u)%256u)*SC_SKYW/256u; /* 160 columns = 90 degrees = 256 texel units */
#endif
}
static void sky_setup(unsigned a){
    if(!sky_rows_ready){
        for(unsigned j=0;j<72;j++){
#ifdef FR_SKY_LEGACY
            sky_rows[j]=(uint16_t)((j*SC_SKYH/72)*SC_SKYW);
#else
            sky_rows[j]=(uint16_t)((((128u*j+11808u)/72u)%128u*SC_SKYH/128u)*SC_SKYW);
#endif
        }
        sky_rows_ready=1;
    }
#ifdef FR_SKY_LEGACY
    sky_base=a*SC_SKYW/360;
#else
    sky_base=(a*1024u/360u)%256u;
#endif
    fr_sky_rows=sky_rows;fr_sky_column=sky_column;fr_sky_cols_ok=0;
}
/* Cache transformed shared vertices for one pose; no approximation or
 * visibility change. 5 bytes per vertex, bounded by actual scene size. */
#define SC_VERTEX_COUNT (sizeof(sc_vertices)/sizeof(sc_vertices[0])/2u)
static int16_t vertex_tx[SC_VERTEX_COUNT],vertex_tz[SC_VERTEX_COUNT];
static uint8_t vertex_valid[SC_VERTEX_COUNT];
static void transform_vertex(unsigned i,int32_t cx,int32_t cy,int16_t co,int16_t si,int32_t *tx,int32_t *tz){
    if(!vertex_valid[i]){
        fr_transform(sc_vertices[2u*i],sc_vertices[2u*i+1],cx,cy,co,si,tx,tz);
        vertex_tx[i]=(int16_t)*tx;vertex_tz[i]=(int16_t)*tz;vertex_valid[i]=1;
    }else{*tx=vertex_tx[i];*tz=vertex_tz[i];}
}
static inline int32_t s16i(int32_t v){return (int16_t)v;} /* same wrap as core.c s16() */
static int span_hidden(int x0,int width){
    const uint16_t *t=frame.top+x0,*b=frame.bottom+x0;
    for(int i=0;i<width;i++)if(t[i]|b[i])return 0;
    return 1;
}
static int render_pose(int16_t x,int16_t y,int16_t z,int16_t angle,DemoStats *s){
    if(scene_init())return -1;
    unsigned a=(unsigned)((angle%360+360)%360);
    int16_t co=sc_trig[a*2],si=sc_trig[a*2+1];
#ifdef __m68k__
    {extern void fr_clear11520(void *p);fr_clear11520(frame.pixels);} /* MOVEM clear; pixels is word aligned */
#else
    {uint32_t *z=(uint32_t *)(void *)frame.pixels;for(unsigned i=0;i<11520/4;i++)z[i]=0;}
#endif
    for(unsigned i=0;i<160;i++)frame.depth[i]=0;
    fr_begin(&frame);closed_scan=0;fr_span_hidden=span_hidden;
    for(unsigned i=0;i<SC_VERTEX_COUNT;i++)vertex_valid[i]=0;
        sky_setup(a);
    s->candidates=s->projected=s->errors=s->closed=s->hash=s->tiles_hash=s->tests=0;
    int cell=leaf_at(x,y);if(cell<0)return -2;
    s->leaf=(uint32_t)cell;
    FRIter it;
    int begin_rc=frv_begin(&it,&vis,(uint16_t)cell,x,y,sc_planes,SC_NODES);
#ifdef __m68k__
    /* Record the precise operands before any error loop. */
    volatile uint32_t *diag=(volatile uint32_t *)0xfff044ul;
    diag[0]=(uint32_t)begin_rc;diag[1]=(uint32_t)(int32_t)x;diag[2]=(uint32_t)(int32_t)y;
    diag[3]=(uint32_t)cell;diag[4]=vis.nc;diag[5]=vis.ns;
    diag[6]=(uint32_t)(uintptr_t)vis.cells;diag[7]=(uint32_t)(uintptr_t)sc_frv;
    diag[8]=SC_FRV_BYTES;diag[9]=SC_NODES;
    if(cell>=0&&cell<vis.nc){
        const uint8_t *b=vis.cells+12u*(unsigned)cell;
        for(unsigned k=0;k<4;k++)diag[10+k]=(uint32_t)(int32_t)(int16_t)be16(b+2*k);
        diag[14]=be16(b+8);diag[15]=be16(b+10);
    }
#endif
    if(begin_rc!=1)return -3;
    uint16_t leaf;int rc;
    while((rc=frv_next(&it,&leaf))>0){
        if(closed())break;
        unsigned n=sc_leaves[leaf*2],first=sc_leaves[leaf*2+1];
        for(unsigned j=first;j<first+n;j++){
            if(!frv_keep(&it,(uint16_t)j))continue;
            s->candidates++;
            const int16_t *w=sc_walls+14u*j;
            if(w[2]==255)continue;
            {   /* Back-face reject before transform/projection: the camera is on the back side of the wall line.
                 * Such walls never project (measured: 0 of 495 projected walls had cross>0 over the 12 R04 poses); cross==0 still goes to fr_project. Map coordinates fit 16 bits. */
                const uint16_t i0=(uint16_t)w[0],i1=(uint16_t)w[1];
                const int16_t X0=sc_vertices[2u*i0],Y0=sc_vertices[2u*i0+1];
                const int32_t cr=fr_muls16((int16_t)(sc_vertices[2u*i1]-X0),(int16_t)(y-Y0))-fr_muls16((int16_t)(sc_vertices[2u*i1+1]-Y0),(int16_t)(x-X0));
                if(cr>0)continue;
            }
            int32_t tx,tz,ux,uz;
            transform_vertex((uint16_t)w[0],(int32_t)x*8,(int32_t)y*8,co,si,&tx,&tz);
            transform_vertex((uint16_t)w[1],(int32_t)x*8,(int32_t)y*8,co,si,&ux,&uz);
            {   /* Same first two tests as fr_project (left and right of the 90-degree frustum), done inline so the
                 * ~80% of candidates rejected there skip the call and the job setup. The right test is only
                 * repeated when no left clip happened (fr_project would have moved the first endpoint). */
                const int32_t l0=s16i(tx+tz),l1=s16i(ux+uz);
                if(l0<0&&l1<0)continue;
                if(l0>=0&&s16i(uz-ux)<0&&s16i(tz-tx)<0)continue;
            }
            WallJob job;job.variant=w[2];job.z=-z;
            for(unsigned k=0;k<4;k++)job.heights[k]=w[6+k];
            job.ceiling=w[10];job.floor=w[11];
            int r=fr_project(tx,tz,ux,uz,w[3],w[4],w[5],&job);
            if(r<0){s->errors++;continue;}if(!r)continue;s->projected++;
            if(r==2)continue; /* fully occluded span: nothing to draw */
            #if SC_ART_PAIR
            if(fr_wall_indexed_pair(&frame,&job,texture_at((uint16_t)w[12]),texture_at((uint16_t)w[13]),sc_scalers,sc_indices,sc_sky))s->errors++;
#else
            if(fr_wall_indexed(&frame,&job,texture_at((uint16_t)w[12]),texture_at((uint16_t)w[13]),sc_scalers,sc_indices,sc_sky))s->errors++;
#endif
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
static uint8_t probe_pattern(unsigned i,unsigned pass){
    return (uint8_t)((i*73u+(i>>8)*19u+pass*91u)^((i&1u)?0x5au:0xa5u));
}
static int probe_sram(void){
    volatile uint8_t *p=(volatile uint8_t *)0x20a600ul;
    IO8(0xa130f1ul)=1;
    /* Whole staging block, byte lane and address alias tests. No game saves
       are stored in this diagnostic cartridge's staging area. */
    for(unsigned pass=0;pass<2;pass++){
        for(unsigned i=0;i<23040;i++)p[i]=probe_pattern(i,pass);
        for(unsigned i=0;i<23040;i++)if(p[i]!=probe_pattern(i,pass)){
            IO8(0xa130f1ul)=0;return 0;
        }
    }
    IO8(0xa130f1ul)=0;return 1;
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
/* Read-only debugger checkpoint, after DMA and mailbox update. */
__attribute__((noinline,used)) void fr_published(void){__asm__ volatile("" ::: "memory");}
void md_main(void){
    for(unsigned i=0;i<64;i++)MB[i]=0;
    MB[0]=0x46523031u;MB[1]=0;MB[2]=1;
    if(IO8(0xa10001ul)&15u)IO32(0xa14000ul)=0x53454741u;
    IO16(0xa11100ul)=0x0100;IO16(0xa11200ul)=0x0000;
    init_vdp();
    int has_sram=probe_sram(),use_sram=0;
    MB[3]=(uint32_t)has_sram;MB[2]=2;
    unsigned seq=0,idx=0,last=0;
    int16_t x=sc_poses[0],y=sc_poses[1],z=sc_poses[2],a=sc_poses[3];
    for(;;){
        DemoStats s;int rc;
        if(seq<SC_POSES){idx=seq;x=sc_poses[4*idx];y=sc_poses[4*idx+1];z=sc_poses[4*idx+2];a=sc_poses[4*idx+3];}
        else {
            unsigned p=pad(),pressed=p&~last;last=p;
            if((pressed&0x40u)&&has_sram){use_sram=!use_sram;IO8(0xa130f1ul)=use_sram?1:0;} /* A */
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
        /* WRAM is the reference and always works. Optional SRAM is not
           claimed as accelerated until a future direct-conversion backend. */
        uint8_t *dst=worktiles;
        MB[2]=4;
        if(fr_tiles(frame.pixels,worktiles,23040)!=23040){MB[2]=0x80000005u;for(;;){}}
        s.tiles_hash=hash_bytes(worktiles,23040);
        if(use_sram){
            volatile uint8_t *p=(volatile uint8_t *)0x20a600ul;
            for(unsigned i=0;i<23040;i++)p[i]=worktiles[i];
            for(unsigned i=0;i<23040;i++)if(p[i]!=worktiles[i]){
                has_sram=use_sram=0;MB[3]=0;MB[36]++;IO8(0xa130f1ul)=0;break;
            }
            if(use_sram)dst=(uint8_t *)0x20a600ul;
        }
        next_blank();reg(1,0x14);
        rc=fr_md_dma((uint32_t)(uintptr_t)dst,0x20,23040);
        if(rc&&use_sram){has_sram=use_sram=0;MB[3]=0;MB[36]++;IO8(0xa130f1ul)=0;
            rc=fr_md_dma((uint32_t)(uintptr_t)worktiles,0x20,23040);}
        reg(1,0x54);
        MB[4]=idx;MB[5]=s.hash;MB[6]=s.tiles_hash;MB[7]=s.candidates;MB[8]=s.projected;
        MB[9]=s.errors;MB[10]=s.closed;MB[11]=(uint32_t)use_sram;MB[12]=(uint32_t)rc;
        MB[13]=(uint32_t)(uint16_t)x;MB[14]=(uint32_t)(uint16_t)y;MB[15]=(uint32_t)(uint16_t)a;MB[16]=s.tests;
        MB[2]=rc?0x80000006u:5;MB[1]=++seq;
        fr_published();
        if(rc)for(;;){}
#ifndef FR_BENCH
        next_blank(); /* one observable, fully published frame before next render (verification builds only) */
#endif
    }
}
#endif
