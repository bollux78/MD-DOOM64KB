/* DREAD-MD: opening image, Doom status bar (Claudio's HUD from the WAD, as in R128/Manifold) and the
 * pistol view sprite. Mega Drive only. */
#include <genesis.h>
#include "render.h"
#include "game_hud.h"
#include "hud_assets.h"
#ifdef DREAD_EPISODE
#include "image_tiles.h"
#endif

extern const uint16_t weap_pal[16], weap_x, weap_y, weap_tiles, weap_nframes, weap_npieces;
extern const uint8_t weap_piece[][4];
extern const uint32_t weap_data[];
extern const uint16_t title_ntiles, title_pal[64], title_mapa[1120], title_mapb[1120];
extern const uint32_t title_tiles[];

#define TILE_HUD    1024                       /* 0x8000: bar tiles, then the 16-tile face slot */
#define TILE_FACE   (TILE_HUD + HUDW_NTILES)
#define TILE_WEAP   848                        /* right after the framebuffer tiles (128 + 720); up to 176 tiles before the HUD at 1024 */
#define TILE_TITLE  112                        /* the opening tiles end below the SGDK font at the top of tile VRAM */
#define BGB         0xC000                     /* SGDK 2.x plane B */
#define BGA         0xE000
#define SLIST       0xF400

static inline void vram_addr(uint16_t a) { *(volatile uint32_t *)0xC00004 = 0x40000000UL | ((uint32_t)(a & 0x3FFF) << 16) | (a >> 14); }
static inline void vram_w(uint16_t v) { *(volatile uint16_t *)0xC00000 = v; }
static inline void cram_set(uint16_t idx, const uint16_t *src, uint16_t n)
{
    *(volatile uint32_t *)0xC00004 = 0xC0000000UL | ((uint32_t)(idx * 2) << 16);
    while (n--) *(volatile uint16_t *)0xC00000 = *src++;
}
static void vram_copy32(uint16_t dst_tile, const uint32_t *src, uint16_t ntiles)
{
    vram_addr(dst_tile * 32);
    for (uint32_t i = 0; i < (uint32_t)ntiles * 8; i++) {
        const uint32_t w = src[i];
        vram_w((uint16_t)(w >> 16)); vram_w((uint16_t)w);
    }
}

void HUD_ShowOpening(void)
{
    SYS_disableInts();
    VDP_setEnable(FALSE);
    VDP_setHInterrupt(FALSE);SYS_setHIntCallback(0);
    VDP_setReg(2,0x38);VDP_setReg(3,0x34);VDP_setReg(4,6);
    VDP_setScrollingMode(HSCROLL_PLANE,VSCROLL_PLANE);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    VDP_setVerticalScroll(BG_A,0);VDP_setVerticalScroll(BG_B,0);
    VDP_setHilightShadow(FALSE);
    VDP_setScreenWidth320();
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setAutoInc(2);
    cram_set(0, title_pal, 64);
    vram_copy32(TILE_TITLE, title_tiles, title_ntiles);
    for (int plane = 0; plane < 2; plane++) {
        const uint16_t *m = plane ? title_mapa : title_mapb;
        for (uint16_t y = 0; y < 32; y++) {
            vram_addr((plane ? BGA : BGB) + y * 128);
            for (uint16_t x = 0; x < 64; x++) {
                uint16_t v = 0;
                if (x < 40 && y < 28 && (plane == 0 || m[y * 40 + x])) { const uint16_t w = m[y * 40 + x]; v = (uint16_t)((w & 0xE000) | (TILE_TITLE + (w & 0x7FF))); }
                vram_w(v);
            }
        }
    }
    VDP_setEnable(TRUE);
    SYS_enableInts();
}

void HUD_ClearOpening(void)
{
    SYS_disableInts();
    VDP_setEnable(FALSE);
    VDP_setHilightShadow(FALSE);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
#ifdef DREAD_EPISODE
    /* The opening and gameplay reuse the same pattern memory. */
    VDP_fillTileData(0, TILE_TITLE, TILE_WEAP - TILE_TITLE, TRUE);
    VDP_setTextPalette(PAL0);
#endif
    VDP_setEnable(TRUE);
    SYS_enableInts();
}

/* Standalone demo opening. START (or 8 s) continues. */
void HUD_Opening(void)
{
    HUD_ShowOpening();
    extern volatile uint16_t vints, bench_req;
    const uint16_t t0 = vints;
    while ((uint16_t)(vints - t0) < 8 * 60 && !bench_req) {
        JOY_update();
        if (JOY_readJoypad(JOY_1) & BUTTON_START) break;
    }
    while (!bench_req) { JOY_update(); if (!(JOY_readJoypad(JOY_1) & BUTTON_START)) break; }   /* wait release */
    HUD_ClearOpening();
}

/* ---- status bar on plane B rows [row0, row0+4) */
#ifdef DREAD_EPISODE
static uint32_t face_frame[16*8];

static void unpack_tiles(uint32_t *dst, const uint16_t *refs, uint16_t count)
{
    while (count--) {
        memcpy(dst, image_tiles + (uint32_t)*refs++ * 8, 32);
        dst += 8;
    }
}
#endif

static uint16_t hud_row0, hud_col0 = HUD_COL0;
static int16_t weap_dx;
static int16_t cur_face = -1;
static uint16_t hud_nt[4][32];
static volatile uint8_t hud_dirty, face_dirty, sat_dirty;
static int16_t bob_x, bob_y;
static uint16_t txt_nt[2][40];
static volatile uint8_t txt_dirty;

#ifdef DREAD_GAMEPLAY
extern const uint16_t weap_frame_refs[];
static uint32_t weapon_frame[160*8];
static uint16_t weapon_refs[160];
static volatile int16_t weapon_pending = -1;
static int16_t weapon_next=-1,weapon_last=4;
static uint16_t weapon_pos,weapon_fuzz,weapon_fuzz_request;
static volatile uint16_t weapon_building,weapon_paused;
static volatile int16_t weapon_anim=-1;
static volatile uint16_t weapon_anim_step,weapon_anim_ticks;
static const uint8_t anim_frames[6][5]={{1,2,3,0,0},{1,2,3,0,0},{1,2,3,2,0},{1,2,0,0,0},{1,2,0,0,0},{1,2,0,0,0}};
static const uint8_t anim_ticks[6][5]={{8,8,8,0,0},{6,6,5,0,0},{5,10,10,10,0},{4,3,0,0,0},{8,6,0,0,0},{4,3,0,0,0}};
void HUD_WeaponPause(uint16_t on){weapon_paused=on;}
void HUD_RestoreTextColor(void){cram_set(63,hudw_pal+15,1);}
void HUD_WeaponFire(uint16_t weapon){
    weapon_anim=-1;weapon_anim_step=0;weapon_anim_ticks=anim_ticks[weapon][0];
    HUD_WeaponFrame(weapon*4+1);weapon_anim=weapon;
}
void HUD_WeaponInvisible(uint16_t on){
    weapon_fuzz_request=on;
    if(weapon_pending<0 && weapon_fuzz!=on)HUD_WeaponFrame(weapon_last<0?4:weapon_last);
}
static void weapon_unpack(uint16_t f)
{
    const uint16_t *refs = weap_frame_refs + f * 160;
    for (uint16_t i=0;i<160;i++){
        memcpy(weapon_frame+i*8,weap_data+(uint32_t)refs[i]*8,32);
        if(weapon_fuzz)for(uint16_t row=0;row<8;row++)weapon_frame[i*8+row]&=(row&1)?0x0f0f0f0fUL:0xf0f0f0f0UL;
    }
}
#endif
void HUD_Init(uint16_t row0)
{
    hud_row0 = row0;cur_face=-1;hud_dirty=face_dirty=sat_dirty=txt_dirty=0;
#ifdef DREAD_GAMEPLAY
    weapon_anim=-1;weapon_building=weapon_paused=0;weapon_next=weapon_pending=-1;weapon_fuzz=weapon_fuzz_request=0;weapon_last=4;bob_x=bob_y=0;
#endif
    SYS_disableInts();
    /* The text title clears plane B with DMA fill, which leaves increment 1. */
    VDP_setAutoInc(2);
    cram_set(16, weap_pal, 16);               /* PAL1: weapon */
    cram_set(32, hudw_fpal, 16);              /* PAL2: faces */
    cram_set(48, hudw_pal, 16);               /* PAL3: bar, digits, text */
#ifdef DREAD_EPISODE
    for (uint16_t i = 0; i < HUDW_NTILES; i++)
        vram_copy32(TILE_HUD + i, image_tiles + (uint32_t)hudw_tiles_refs[i] * 8, 1);
#ifdef DREAD_GAMEPLAY
    weapon_unpack(4);
    vram_copy32(TILE_WEAP, weapon_frame, weap_tiles);
    memcpy(weapon_refs, weap_frame_refs+160*4, sizeof(weapon_refs));
#else
    vram_copy32(TILE_WEAP, weap_data, weap_tiles);
#endif
#else
    vram_copy32(TILE_HUD, &hudw_tiles[0][0], HUDW_NTILES);
#ifdef DREAD_GAMEPLAY
    weapon_unpack(4);
    vram_copy32(TILE_WEAP, weapon_frame, weap_tiles);
    memcpy(weapon_refs, weap_frame_refs+160*4, sizeof(weapon_refs));
#else
    vram_copy32(TILE_WEAP, weap_data, weap_tiles);
#endif
#endif
    /* weapon sprites: one entry per piece, linked */
    vram_addr(SLIST);
    for (uint16_t i = 0; i < weap_npieces; i++) {
        const uint8_t *p = weap_piece[i];
        uint16_t tile = TILE_WEAP;
        for (uint16_t k = 0; k < i; k++) tile += weap_piece[k][2] * weap_piece[k][3];
        vram_w((uint16_t)(128 + weap_y + p[1] + VIEW_TOP_PX));
        vram_w((uint16_t)(((p[2] - 1) << 10) | ((p[3] - 1) << 8) | (i + 1 < weap_npieces ? i + 1 : 0)));
        vram_w((uint16_t)((1 << 13) | tile));     /* low priority: the high-priority status bar covers the weapon when it bobs down */
        vram_w((uint16_t)(128 + weap_x + p[0]));
    }
    SYS_enableInts();
}

void HUD_Draw(const HudState *st)
{
#ifdef DREAD_GAMEPLAY
    if(weapon_pending<0 && weapon_next>=0){uint16_t f=weapon_next;weapon_next=-1;HUD_WeaponFrame(f);}
#endif
    uint16_t rows[4][32];
    for (int r = 0; r < 4; r++) for (int c = 0; c < 32; c++) rows[r][c] = hudw_bgmap[r][c];
    const uint16_t vals[3] = { st->ammo_cur, st->health, st->armor };
    const uint8_t cols[3] = { HUDW_AMMO_C, HUDW_HEALTH_C, HUDW_ARMOR_C };
    for (int w = 0; w < 3; w++) {
        const uint16_t v = vals[w] > 999 ? 999 : vals[w];
        const uint16_t d[3] = { v / 100, v / 10 % 10, v % 10 };
        const uint8_t lead[3] = { v >= 100, v >= 10, 1 };
        for (int r = 0; r < 3; r++) {
            for (int i = 0; i < 3; i++) if (lead[i]) rows[r][cols[w] + i] = hudw_big[w][i][r][d[i]];
            if (w) rows[r][cols[w] + 3] = hudw_pct[w - 1][r];
        }
    }
    const uint16_t mask = st->arms | (st->keys << 6);
    for (int k = 0; k < HUDW_NWID; k++) {
        const uint16_t v = ((mask >> hudw_wid_b0[k]) & 1) | (hudw_wid_b1[k] != 255 ? ((mask >> hudw_wid_b1[k]) & 1) << 1 : 0);
        rows[hudw_wid_row[k]][hudw_wid_col[k]] = hudw_wid_id[k][v];
    }
    for (int t = 0; t < 4; t++)
        for (int part = 0; part < 2; part++) {
            const uint16_t v = part ? st->maxammo[t] : st->ammo[t];
            const uint16_t d[3] = { v / 100, v / 10 % 10, v % 10 };
            const uint8_t lead[3] = { v >= 100, v >= 10, 1 };
            for (int i = 0; i < 3; i++) if (lead[i]) rows[HUDW_TABLE_R + t][HUDW_TABLE_C + part * 3 + i] = hudw_ysm[t][d[i]];
        }
    /* VRAM writes happen in the VBlank (HUD_VBlank): no interrupt masking during the frame,
       so the per-line scroll interrupt (row-doubled view) never misses a line */
    if (st->face != cur_face) {
#ifdef DREAD_EPISODE
        face_dirty = 0;
        __asm__ volatile ("" ::: "memory");
        unpack_tiles(face_frame, hudw_faces_refs + (uint16_t)st->face * 16, 16);
        __asm__ volatile ("" ::: "memory");
#endif
        cur_face = st->face;
        face_dirty = 1;
    }
    for (int r = 0; r < 4; r++)
        for (int c = 0; c < 32; c++) {
            const int face = r >= HUDW_FACE_R && r < HUDW_FACE_R + 4 && c >= HUDW_FACE_C && c < HUDW_FACE_C + HUDW_FACE_W;
            hud_nt[r][c] = face ? (uint16_t)(0x8000 | (2 << 13) | (TILE_FACE + (r - HUDW_FACE_R) * HUDW_FACE_W + (c - HUDW_FACE_C)))
                                : (uint16_t)(0x8000 | (3 << 13) | (TILE_HUD + rows[r][c]));
        }
    hud_dirty = 1;
}

/* ---- weapon: frame upload is requested here and done by the caller's VBlank (WEAP_VBlank) */
static volatile int16_t weap_req = -1;
void HUD_WeaponFrame(uint16_t f)
{
#ifdef DREAD_EPISODE
#endif
#ifdef DREAD_GAMEPLAY
    if(f>=24)return;
    uint16_t saved_sr;
    __asm__ volatile("move.w %%sr,%0\n\tor.w #0x700,%%sr" : "=d"(saved_sr) :: "cc","memory");
    if(weapon_pending>=0 || weapon_building){weapon_next=f;__asm__ volatile("move.w %0,%%sr" :: "d"(saved_sr) : "cc","memory");return;}
    if((saved_sr&0x700)>=0x400){weapon_next=f;__asm__ volatile("move.w %0,%%sr" :: "d"(saved_sr) : "cc","memory");return;}
    weapon_building=1;
    __asm__ volatile("move.w %0,%%sr" :: "d"(saved_sr) : "cc","memory");
    if(weapon_fuzz!=weapon_fuzz_request){weapon_fuzz=weapon_fuzz_request;weapon_last=-1;for(uint16_t i=0;i<160;i++)weapon_refs[i]=0xffff;}
    if(weapon_last==(int16_t)f){weapon_building=0;return;}
    weapon_unpack(f);weapon_last=f;
    weapon_pos = 0;
    weapon_pending = (int16_t)f;
    weapon_building=0;
#else
    weap_req = (int16_t)f;
#endif
}
void HUD_WeaponBob(int16_t dx, int16_t dy) { bob_x = dx; bob_y = dy; sat_dirty = 1; }

void HUD_Text(uint16_t line, const char *s)      /* line 0/1 = screen rows 25/26 */
{
    for (int i = 0; i < 40; i++) {
        const char ch = *s ? *s++ : ' ';
        txt_nt[line][i] = (uint16_t)((3 << 13) | 0x8000 | (TILE_FONT_INDEX + (ch - 32)));
    }
    txt_dirty |= (uint8_t)(1 << line);
}

/* called from the VBlank interrupt: every VRAM update of the HUD, face, weapon and text */
uint16_t HUD_VBlank(uint16_t max_bytes)    /* returns the bytes sent by DMA (the caller keeps the VBlank DMA budget) */
{
    uint16_t bytes = 0,weapon_dma=0;
#ifdef DREAD_GAMEPLAY
    if(weapon_anim>=0 && !weapon_paused){
        if(weapon_anim_ticks)weapon_anim_ticks--;
        if(!weapon_anim_ticks && !weapon_building && weapon_pending<0){
            const uint16_t w=weapon_anim,k=++weapon_anim_step;
            weapon_next=w*4+anim_frames[w][k];weapon_anim_ticks=anim_ticks[w][k];
            if(!weapon_anim_ticks)weapon_anim=-1;
        }
    }
    if (weapon_pending >= 0) {
        const uint16_t *refs=weap_frame_refs+(uint16_t)weapon_pending*160;
        while(weapon_pos<160){
            const uint16_t start=weapon_pos,n=(160-start)>32?32:160-start;
            uint16_t changed=0;for(uint16_t i=0;i<n;i++)if(weapon_refs[start+i]!=refs[start+i])changed=1;
            if(changed){DMA_doDma(DMA_VRAM,weapon_frame+start*8,(TILE_WEAP+start)*32,n*16,2);bytes+=n*32;weapon_dma=1;}
            for(uint16_t i=0;i<n;i++)weapon_refs[start+i]=refs[start+i];
            weapon_pos+=n;if(changed)break;
        }
        if (weapon_pos==160){weapon_pending=-1;sat_dirty=1;}
    }
#else
    if (weap_req >= 0) {
        const uint16_t f = (uint16_t)weap_req; weap_req = -1;
        DMA_doDma(DMA_VRAM, (void *)(weap_data + (uint32_t)f * weap_tiles * 8), TILE_WEAP * 32, weap_tiles * 16, 2);
        bytes += weap_tiles * 32;
    }
#endif
    if (face_dirty) {
        face_dirty = 0;
        bytes += 512;
#ifdef DREAD_EPISODE
        DMA_doDma(DMA_VRAM, face_frame, TILE_FACE * 32, 16 * 16, 2);
#else
        DMA_doDma(DMA_VRAM, (void *)&hudw_faces[cur_face][0][0], TILE_FACE * 32, 16 * 16, 2);
#endif
    }
    if (hud_dirty) {
        hud_dirty = 0;
        for (int r = 0; r < 4; r++) DMA_doDma(DMA_VRAM, hud_nt[r], BGB + (hud_row0 + r) * 128 + hud_col0 * 2, 32, 2);
        bytes += 256;
    }
    for (int l = 0; l < 2; l++)
        if (txt_dirty & (1 << l)) { txt_dirty &= (uint8_t)~(1 << l); DMA_doDma(DMA_VRAM, txt_nt[l], BGB + (25 + l) * 128, 40, 2); bytes += 80; }
    if (sat_dirty) {
        sat_dirty = 0;
        for (uint16_t i = 0; i < weap_npieces; i++) {
            const uint8_t *p = weap_piece[i];
            vram_addr(SLIST + i * 8);
            vram_w((uint16_t)(128 + weap_y + p[1] + VIEW_TOP_PX + bob_y));
            vram_addr(SLIST + i * 8 + 6);
            vram_w((uint16_t)(128 + weap_x + p[0] + bob_x + weap_dx));
        }
    }
    return weapon_dma?max_bytes:bytes; /* defer scene DMA while a weapon burst uses this blank */
}

/* screen mode change (ints disabled by the caller): bar column, weapon x offset */
void HUD_SetLayout(uint16_t col0, int16_t dx)
{
    hud_col0 = col0; weap_dx = dx;
    for (int r = 0; r < 4; r++) { vram_addr(BGB + (hud_row0 + r) * 128); for (int i = 0; i < 64; i++) vram_w(0); }
    hud_dirty = 1; sat_dirty = 1;
}

#ifdef DREAD_GAMEPLAY
extern const uint16_t ending_old_refs[],ending_start_new[],ending_start_old[],ending_pal[];
extern const uint8_t ending_old_mask[],ending_attr5[];
extern const uint32_t ending_tiles[];
static void static_screen(void)
{
    VDP_setEnable(FALSE);VDP_setScreenWidth320();VDP_setHilightShadow(FALSE);
    *(volatile uint16_t *)0xC00004=0x8200|(BGA>>10);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,0);
    VDP_setVerticalScroll(BG_A,0);VDP_setVerticalScroll(BG_B,0);
    VDP_clearPlane(BG_A,TRUE);VDP_clearPlane(BG_B,TRUE);VDP_clearPlane(WINDOW,TRUE);
    VDP_setAutoInc(2);vram_addr(SLIST);for(uint16_t i=0;i<4;i++)vram_w(0);
}
/* Restore all three existing credit images with lossless packed reference
 * indices and 5-bit tile attributes. New tile IDs are sequential, and the
 * duplicate mask stores only reused IDs. No game graphics are modified. */
void HUD_ShowArt(uint16_t page)
{
    if(page>=3)return;
    SYS_disableInts();static_screen();
    cram_set(0,ending_pal+page*64,64);
    uint16_t nextNew=ending_start_new[page],nextOld=ending_start_old[page];
    for(uint16_t i=0;i<1120;i++){
        const uint16_t g=page*1120+i;
        const uint16_t ref=(ending_old_mask[g>>3]&(0x80>>(g&7)))?ending_old_refs[nextOld++]:nextNew++;
        vram_copy32(TILE_TITLE+i,ending_tiles+(uint32_t)ref*8,1);
    }
    for(uint16_t y=0;y<28;y++){
        vram_addr(BGB+y*128);
        for(uint16_t x=0;x<40;x++){
            const uint16_t g=page*1120+y*40+x;
            const uint16_t b=g*5;
            const uint16_t pair=((uint16_t)ending_attr5[b>>3]<<8)|ending_attr5[(b>>3)+1];
            const uint16_t attr=((pair>>(11-(b&7)))&31)<<11;
            vram_w(attr|(TILE_TITLE+y*40+x));
        }
    }
    VDP_setEnable(TRUE);SYS_enableInts();
}
extern const uint16_t inter_pal[],final_pal[];
extern const uint8_t inter_tilepal2[],inter_data[],final_tilepal2[],final_data[];
/* Static user-approved 320x224 H40 image, four original CRAM palettes.
 * Each original 8x8 tile is expanded from a four-colour local dictionary. */
static void draw_user_h40(const uint16_t *pal,const uint8_t *pals,const uint8_t *data)
{
    static_screen();
    cram_set(0,pal,64);
    for(uint16_t i=0;i<1120;i++){
        const uint8_t *p=data+(uint32_t)i*18;
        const uint16_t color[4]={p[0]>>4,p[0]&15,p[1]>>4,p[1]&15};
        uint32_t tile[8];
        for(uint16_t row=0;row<8;row++){
            uint32_t word=0;
            for(uint16_t col=0;col<8;col++){
                const uint8_t bits=p[2+row*2+(col>>2)];
                word=(word<<4)|color[(bits>>(6-((col&3)<<1)))&3];
            }
            tile[row]=word;
        }
        vram_copy32(TILE_TITLE+i,tile,1);
    }
    for(uint16_t y=0;y<28;y++){
        vram_addr(BGB+y*128);
        for(uint16_t x=0;x<40;x++){
            const uint16_t i=y*40+x;
            const uint16_t palidx=(pals[i>>2]>>(6-((i&3)<<1)))&3;
            vram_w((palidx<<13)|(TILE_TITLE+i));
        }
    }
}
void HUD_ShowIntermission(const char *name,uint16_t kills,uint16_t total,uint16_t items,uint16_t totalitems,uint16_t secrets,uint16_t totalsecrets,uint32_t seconds)
{
    SYS_disableInts();
    draw_user_h40(inter_pal,inter_tilepal2,inter_data);
    /* Only intermission statistics need a live text overlay. */
    const uint16_t white=0xeee;cram_set(63,&white,1);
    VDP_setTextPalette(PAL3);VDP_setTextPriority(TRUE);
    VDP_drawTextBG(BG_A,name,(40-strlen(name))/2,4);VDP_drawTextBG(BG_A,"CONCLUIDO",15,6);
    char text[40];sprintf(text,"MORTES    %3u / %3u",kills,total);VDP_drawTextBG(BG_A,text,9,11);
    sprintf(text,"ITENS     %3u / %3u",items,totalitems);VDP_drawTextBG(BG_A,text,9,14);
    sprintf(text,"SEGREDOS  %3u / %3u",secrets,totalsecrets);VDP_drawTextBG(BG_A,text,9,17);
    sprintf(text,"TEMPO       %u:%02u",(uint16_t)(seconds/60),(uint16_t)(seconds%60));VDP_drawTextBG(BG_A,text,9,20);
    VDP_drawTextBG(BG_A,"APERTE UM BOTAO",12,25);
    VDP_setEnable(TRUE);SYS_enableInts();
}
void HUD_ShowFinaleText(void)
{
    SYS_disableInts();
    draw_user_h40(final_pal,final_tilepal2,final_data);
    /* The user's final artwork already contains the full text. */
    VDP_setEnable(TRUE);SYS_enableInts();
}

#endif
