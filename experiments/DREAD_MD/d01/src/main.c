/* DREAD-MD D01: Dread-style renderer test on Mega Drive, Doom E1M1 (shareware WAD).
 *
 * Screen: H32, view 128x112 logical pixels (each 2x1 screen pixels), 4bpp tiles in RAM,
 * double-buffered: the CPU renders one RAM buffer while the VBlank interrupt DMAs the
 * previous one into the hidden VRAM copy, then flips plane A's name table. */
#include <genesis.h>
#include "render.h"
#include "game_hud.h"
#include "actors.h"
#include "game_sfx.h"
#include "world.h"
#ifdef DREAD_GAMEPLAY
#include "levelmeta.h"
#endif
#ifndef DREAD_NO_MUSIC
#include "music.h"
#ifdef DREAD_EPISODE
static uint16_t selected_map;
static const uint8_t *const episode_music[] = {
    bgm_e1m1, bgm_e1m2, bgm_e1m3, bgm_e1m4, bgm_e1m5,
    bgm_e1m6, bgm_e1m7, bgm_e1m8, bgm_e1m9
};
#define MAP_MUSIC episode_music[selected_map]
#else
#define MAP_MUSIC bgm_e1m1
#endif
#endif
#ifndef START_MUSIC
#define START_MUSIC 1
#endif
static uint16_t music_on = START_MUSIC;

#ifndef ROM_NAME
#define ROM_NAME "DREAD-MD D01 SOM"
#endif
#ifndef DREAD_MAP_LABEL
#define DREAD_MAP_LABEL "E1M1 DOOM"
#endif
#ifndef START_MODE
#define START_MODE 0                           /* 0 H40 linhas, 1 H40 colunas, 2 H32 linhas, 3 H32 colunas */
#endif
/* SGDK 2.x VRAM: plane A name table at 0xE000 (flipped with 0xA000 when double-buffered), plane B 0xC000,
 * window 0xD000, font after the system tiles. Framebuffer tiles from 128 (up to 720 tiles in every mode):
 *   row-doubled: two RAM + two VRAM copies (W/4 x 9 tiles each); column-doubled: one of each (W/4 x 18). */
#define TILE_FB0   128
#define NT0        0xE000
#define VTOP       (VIEW_ROW0 * 8)
static uint16_t dma_chunk = 5632;              /* bytes per VBlank (H40 ~7.7 KB of VBlank DMA, H32 ~6.3 KB, minus the HUD) */
#define DMA_CHUNK  dma_chunk
static uint16_t nbuf, tile_fb1, nt1, view_trows, mode;
#define NBUF       nbuf
#define TCOLS      FB_TCOLS
#define TILE_FB1   tile_fb1
#define NT1        nt1

static uint8_t fbuf[FB_MAX];        /* view name table rows with per-tile palettes */
volatile uint16_t vints;
#ifdef DREAD_GAMEPLAY
static volatile uint16_t joy_edges,joy_previous;
#endif
static const uint8_t *volatile dma_src;   /* buffer being sent, 0 = idle (the POINTER is volatile) */
static volatile uint16_t dma_pos;
#ifdef DREAD_GAMEPLAY
static volatile uint8_t scene_flash, dma_tint;
static uint8_t displayed_tint;
static uint16_t scene_pal[8][32];
void Game_Flash(void) { scene_flash=1; }
extern const uint16_t weap_pal[16];
static void scene_palettes(void)
{
    for(uint16_t i=0;i<32;i++){
        uint16_t c=i<16?md_palette[0][i]:weap_pal[i-16];scene_pal[0][i]=c;
        uint16_t rr=c&14,gg=(c>>4)&14,bb=(c>>8)&14;
        scene_pal[1][i]=i>=16?c:!c?0:((rr>10?14:rr+4)|((gg>10?14:gg+4)<<4)|((bb>10?14:bb+4)<<8));
        scene_pal[3][i]=!c?0:(14-rr)|((14-gg)<<4)|((14-bb)<<8);
        scene_pal[4][i]=!c?0:((rr/2&14)|((gg>8?14:gg+6)<<4)|((bb/2&14)<<8));
        for(uint16_t t=5;t<8;t++){uint16_t add=(8-t)*2;scene_pal[t][i]=!c?0:((rr+add>14?14:rr+add)|(((gg*(8-add)/8)&14)<<4)|(((bb*(8-add)/8)&14)<<8));}
        scene_pal[2][i]=!c?0:(rr>6?14:rr+8)|((gg/2&14)<<4)|((bb/2&14)<<8);
    }
}
#endif
static volatile uint16_t game_video_active;
volatile uint16_t intermission_active;
static volatile uint8_t shown;            /* VRAM copy currently displayed */

/* bench: the test harness (or holding B on the title) drives a fixed input script */
volatile uint16_t bench_req;
volatile uint16_t bench_joy;
volatile uint32_t bench_frames, bench_vints;
volatile uint16_t bench_done;
volatile uint16_t cur_buf;
volatile uint16_t frame_segs, frame_nodes, frame_cols, frame_anchors, frame_subs;

static void vram_cmd(uint16_t addr) { *(volatile uint32_t *)0xC00004 = 0x40000000UL | ((uint32_t)(addr & 0x3FFF) << 16) | (addr >> 14); }

/* rows shown twice: hint.s scrolls plane A up by one row every 2 lines inside the view */
extern void hint_a(void), hint_b(void);
static volatile uint8_t hint_on;
uint16_t hint_r1on;                 /* VDP reg 1 write with the display on (hint_a turns the display back on at the view) */

static void vint_cb(void)
{
    vints++;
#ifdef DREAD_JOY_VBLANK
    /* JOY_update masks interrupts. Poll during vertical blank to preserve row timing. */
    JOY_update();
#ifdef DREAD_GAMEPLAY
    const uint16_t joy=JOY_readJoypad(JOY_1);
    joy_edges|=joy&~joy_previous;joy_previous=joy;
#endif
#endif
    *(volatile uint32_t *)0xC00004 = 0x40000010UL;
    *(volatile uint16_t *)0xC00000 = 0;
    if (hint_on) {
        /* lines 0..15 above the view are black: display off there, so the VBlank DMA keeps the full
           blank-time speed until hint_a turns the display on before the first view line (a DMA that
           ran into the visible area halted the 68000 and the row-doubling H-int: squashed picture band) */
        *(volatile uint16_t *)0xC00004 = hint_r1on & ~0x40;
        SYS_setHIntCallback(hint_a); *(volatile uint16_t *)0xC00004 = 0x8014;
    }
    /* all VRAM traffic must end inside the VBlank: a DMA that runs into the active display halts the
       68000 (frame time) and delays the row-doubling H-int (lines of the wrong rows, the picture jumps) */
    if(!game_video_active)return;
    const uint16_t hud_bytes = HUD_VBlank(DMA_CHUNK);
    if (dma_src && hud_bytes < DMA_CHUNK) {
        const uint16_t budget = (DMA_CHUNK - hud_bytes) & ~1u;
        const uint16_t n = (FB_BYTES - dma_pos) > budget ? budget : (FB_BYTES - dma_pos);
        const uint16_t dst = (shown ? TILE_FB0 : TILE_FB1) * 32 + dma_pos;
        DMA_doDma(DMA_VRAM, (void *)(dma_src + dma_pos), dst, n / 2, 2);
        dma_pos += n;
        if (dma_pos >= FB_BYTES) {
            shown ^= 1;
            *(volatile uint16_t *)0xC00004 = 0x8200 | ((shown ? NT1 : NT0) >> 10);
#ifdef DREAD_GAMEPLAY
            if(displayed_tint!=dma_tint){
                *(volatile uint32_t *)0xC00004=0xC0000000UL;
                for(uint16_t c=0;c<32;c++)*(volatile uint16_t *)0xC00000=scene_pal[dma_tint][c];
                displayed_tint=dma_tint;
            }
#endif
            dma_src = 0;
        }
    }
}

/* switch the screen mode (detail level): resolution H40/H32, row- or column-doubled view */
#ifndef START_CROP
#define START_CROP 0
#endif
static uint16_t crop = START_CROP;                         /* side crop: tiles removed on each side (0, 2, 4) */
static void set_mode(uint16_t m)
{
    while (dma_src) {}
    SYS_disableInts();
#ifdef DREAD_ROW_ONLY
    m &= ~1u;
#endif
    mode = m;
    const uint16_t h40 = !(m & 2), colb = (m & 1) ? 2 : 1;
    r_fullheight = (m & 4) != 0;
    r_rowdup=(m&8)!=0;
    R_SetMode(colb, h40 ? 40 : 32, crop);
    if (h40) VDP_setScreenWidth320(); else VDP_setScreenWidth256();
    *(volatile uint16_t *)0xC00004 = 0x8F02;      /* auto-increment 2 */
    view_trows = VIEW_H / 8;
    nbuf = r_vh==72?2:1;
    tile_fb1 = nbuf == 2 ? TILE_FB0 + TCOLS * view_trows : TILE_FB0;
    nt1 = nbuf == 2 ? 0xA000 : 0xE000;
#ifdef DREAD_GAMEPLAY
    scene_palettes();displayed_tint=0;
#endif
    /* palette 0: the view */
    *(volatile uint32_t *)0xC00004 = 0xC0000000UL;
    #ifdef DREAD_GAMEPLAY
    for(int i=0;i<32;i++)*(volatile uint16_t *)0xC00000=scene_pal[0][i];
#else
    for (int i = 0; i < 16; i++) *(volatile uint16_t *)0xC00000 = md_palette[0][i];
#endif
    /* name tables: view rows point at the framebuffer tiles, column-major */
    for (int b = 0; b < 2; b++) {
        const uint16_t nt = b ? 0xA000 : NT0, base = (b && nbuf == 2) ? TILE_FB1 : TILE_FB0;
        for (int ty = 0; ty < 32; ty++) {
            vram_cmd(nt + ty * 128);
            for (int tx = 0; tx < 64; tx++) {
                uint16_t v = 0;
                const uint16_t r = colb == 2 ? ty - VIEW_ROW0 : ty - VIEW_ROW0;   /* row-doubled: tile rows 0..8 (vscroll repeats lines) */
                if (tx >= crop && tx < crop + TCOLS && ty >= VIEW_ROW0 && r < view_trows) v = base + (tx - crop) * view_trows + r;
                *(volatile uint16_t *)0xC00000 = v;
            }
        }
    }
    *(volatile uint32_t *)0xC00004 = 0x40000010UL;   /* VSRAM 0 */
    *(volatile uint16_t *)0xC00000 = 0;
    *(volatile uint16_t *)0xC00004 = 0x8200 | (NT0 >> 10);
    shown = 0; cur_buf = 0;
    hint_r1on = 0x8100 | VDP_getReg(1) | 0x40;
    *(volatile uint16_t *)0xC00004 = hint_r1on;      /* display on (column mode never runs hint_a) */
    hint_on = r_vh==72;
    VDP_setHIntCounter(1);
    *(volatile uint16_t *)0xC00004 = hint_on ? 0x8014 : 0x8004;
    HUD_SetLayout(h40 ? 4 : 0, h40 ? 0 : -32);
    dma_chunk = h40 ? 6144 : 4864;
#ifdef DREAD_JOY_VBLANK
    dma_chunk -= 512;                         /* leave time for controller polling before the view */
#endif                 /* whole VBlank DMA budget (HUD + framebuffer) */
    SYS_enableInts();
}

/* ---- doors: B (or C+B) opens the door line in front; manual doors close again after ~4 s */
static int16_t door_target[64];
static uint16_t door_wait[64];
static uint8_t door_manual[64];
static uint16_t prev_joy;
#ifdef DREAD_GAMEPLAY
static uint16_t owned_weapons=3, current_weapon=1, player_keys;
#ifdef DREAD_GAMEPLAY
uint16_t cheat_god,cheat_kfa;
static HudState *active_hud;
static HudState saved_inventory;
static uint16_t saved_owned,saved_weapon;
static void toggle_kfa(void){
    if(!active_hud)return;
    cheat_kfa^=1;
    if(cheat_kfa){saved_inventory=*active_hud;saved_owned=owned_weapons;saved_weapon=current_weapon;owned_weapons=63;player_keys=63;active_hud->keys=63;active_hud->arms=15;active_hud->armor=200;
        for(uint16_t i=0;i<4;i++)active_hud->ammo[i]=active_hud->maxammo[i];
    }else{owned_weapons=saved_owned;current_weapon=saved_weapon;player_keys=saved_inventory.keys;active_hud->keys=player_keys;active_hud->arms=saved_inventory.arms;active_hud->armor=saved_inventory.armor;for(uint16_t i=0;i<4;i++)active_hud->ammo[i]=saved_inventory.ammo[i];HUD_WeaponFrame(current_weapon*4);}
    HUD_Draw(active_hud);
}
static void cheats_menu(void){
    uint16_t sel=0,pj=JOY_readJoypad(JOY_1);
    for(;;){
        SYS_disableInts();VDP_clearPlane(WINDOW,TRUE);
        VDP_drawTextBG(WINDOW,"CHEATS",3,4);char t[32];
        sprintf(t,"%c IDDQD: %s",sel==0?'>':' ',cheat_god?"LIGADO":"DESLIGADO");VDP_drawTextBG(WINDOW,t,3,6);
        sprintf(t,"%c IDKFA: %s",sel==1?'>':' ',cheat_kfa?"LIGADO":"DESLIGADO");VDP_drawTextBG(WINDOW,t,3,7);
        VDP_drawTextBG(WINDOW,sel==2?"> VOLTAR":"  VOLTAR",3,9);SYS_enableInts();
        uint16_t e=0;while(!e){uint16_t t0=vints;while(t0==vints){}uint16_t j=JOY_readJoypad(JOY_1);e=j&~pj;pj=j;}
        if(e&(BUTTON_START|BUTTON_B))break;
        if(e&BUTTON_UP)sel=(sel+2)%3;if(e&BUTTON_DOWN)sel=(sel+1)%3;
        if(e&(BUTTON_A|BUTTON_C|BUTTON_LEFT|BUTTON_RIGHT)){if(sel==2)break;if(sel==0)cheat_god^=1;else toggle_kfa();}
    }
}
#endif
static const uint8_t weapon_ammo[6]={255,0,1,0,2,255};
static const uint8_t weapon_delay[6]={26,24,63,7,34,7};
static const uint8_t weapon_sound[6]={2,0,1,0,4,3};
#endif
static int door_index(uint16_t sector)
{
    for (int d = 0; d < map_ndoors && d < 64; d++) if (map_doors[d].sector == sector) return d;
    return -1;
}
static void door_open(int d, int manual)
{
#ifdef DREAD_GAMEPLAY
    World_Door(map_doors[d].sector,manual);return;
#endif
    Game_Sound(8);
    door_target[d] = map_doors[d].open_ceil;
    door_wait[d] = manual ? 4 * 60 : 0xFFFF;
    door_manual[d] = (uint8_t)manual;
}

static View view;
static int16_t cur_floor;

static int blocked_from(int16_t x, int16_t y,int16_t ox,int16_t oy)
{
    const int16_t R = 16;
    const MapSector *here = &map_sectors[map_subs[R_PointInSub(ox, oy)].sector];
    const int16_t gx = (int16_t)((x - map_bm[0]) >> 7), gy = (int16_t)((y - map_bm[1]) >> 7);
    if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return 1;
    const uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
    for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
        const MapLine *l = &map_lines[map_bm_list[k]];
        const int16_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1];
        const int16_t bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        if ((ax < bx ? ax : bx) > x + R || (ax > bx ? ax : bx) < x - R) continue;
        if ((ay < by ? ay : by) > y + R || (ay > by ? ay : by) < y - R) continue;
        int solid = (l->back == NO_MAP_SECTOR) || (l->flags & 1);
        if (!solid) {
            const MapSector *f = &map_sectors[l->front], *b = &map_sectors[l->back];
            const int16_t hi = f->floor > b->floor ? f->floor : b->floor;
            const int16_t lo = sec_ceil[l->front] < sec_ceil[l->back] ? sec_ceil[l->front] : sec_ceil[l->back];
            if(lo-hi<56)solid=1;
            else if(hi-here->floor>24){
                const int32_t dx=(int32_t)bx-ax,dy=(int32_t)by-ay;
                const int32_t before=dx*(oy-ay)-dy*(ox-ax),after=dx*(y-ay)-dy*(x-ax);
                /* A lowered lift can leave our radius over the old ledge.
                 * Permit escape on the same side, never crossing a high step. */
                if(!((before<0)==(after<0) && (after<0?-after:after)>=(before<0?-before:before)))solid=1;
            }
        }
        if (!solid) continue;
        /* distance^2 from (x,y) to segment ab */
        const int32_t dx = bx - ax, dy = by - ay, px = x - ax, py = y - ay;
        const int32_t len2 = dx * dx + dy * dy;
        if (!len2) continue;
        int32_t t = px * dx + py * dy;
        int32_t cx, cy;
        if (t <= 0) { cx = ax; cy = ay; }
        else if (t >= len2) { cx = bx; cy = by; }
        else { cx = ax + (int32_t)((int64_t)dx * t / len2); cy = ay + (int32_t)((int64_t)dy * t / len2); }
        const int32_t ex = x - cx, ey = y - cy;
        if (ex * ex + ey * ey < (int32_t)R * R) return 1;
    }
    return 0;
}

static int blocked(int16_t x,int16_t y){return blocked_from(x,y,x,y);}
#ifdef DREAD_COMBAT
int ActorBlockedFrom(int16_t x,int16_t y,int16_t ox,int16_t oy){return blocked_from(x,y,ox,oy);}
int ActorBlocked(int16_t x, int16_t y) { return blocked(x, y); }
#endif

static volatile uint16_t exit_req;              /* 1 = exit, 2 = secret exit */
static void use_line(void)
{
    /* A use ray stops at its first physical line: never operate a switch through a wall. */
    const uint16_t a=view.angle>>6;
    const int32_t px=view.x>>16,py=view.y>>16;
    const int32_t dx=((64L*sintab[(a+256)&1023])>>14),dy=((64L*sintab[a])>>14);
    int best=-1; uint32_t nearest=65537;
    for (uint16_t i=0;i<map_counts[5];i++) {
        const MapLine *ln=&map_lines[i];
        const int32_t ax=map_verts[ln->v1][0],ay=map_verts[ln->v1][1];
        const int32_t lx=map_verts[ln->v2][0]-ax,ly=map_verts[ln->v2][1]-ay;
        int32_t den=dx*ly-dy*lx,tn=(ax-px)*ly-(ay-py)*lx,un=(ax-px)*dy-(ay-py)*dx;
        if (den<0) { den=-den;tn=-tn;un=-un; }
        if (!den || tn<0 || tn>den || un<0 || un>den) continue;
        /* Ignore ordinary open portals, but not the first solid wall. */
        if (!ln->special && ln->back!=NO_MAP_SECTOR && !(ln->flags&1)) {
            const int16_t lo=map_sectors[ln->front].floor>map_sectors[ln->back].floor?map_sectors[ln->front].floor:map_sectors[ln->back].floor;
            const int16_t hi=sec_ceil[ln->front]<sec_ceil[ln->back]?sec_ceil[ln->front]:sec_ceil[ln->back];
            if(view.z>lo && view.z<hi)continue;
        }
        const uint32_t t=(uint32_t)(((int64_t)tn<<16)/den);
        if(t<nearest){nearest=t;best=i;}
    }
    if(best<0)return;
    const MapLine *l = &map_lines[best];
    const uint16_t sp = l->special;
#ifdef DREAD_GAMEPLAY
    uint16_t required=0;
    if(sp==26 || sp==32)required=(1u<<0)|(1u<<3);
    if(sp==27 || sp==34)required=(1u<<1)|(1u<<4);
    if(sp==28 || sp==33)required=(1u<<2)|(1u<<5);
    if(required && !(player_keys&required)){HUD_Text(1,"PRECISA DA CHAVE");Game_Sound(11);return;}
#endif
    Game_Sound(10);
    if (sp == 11) { exit_req = 1; return; }          /* exit switch */
    if (sp == 51) { exit_req = 2; return; }          /* secret exit switch */
#ifdef DREAD_GAMEPLAY
    if(sp!=1 && sp!=26 && sp!=27 && sp!=28 && sp!=31 && sp!=32 && sp!=33 && sp!=34 && sp!=117 && sp!=118){World_Activate(best,0,&view);return;}
#endif
    if ((sp == 1 || (sp >= 26 && sp <= 28) || (sp >= 31 && sp <= 34) || sp == 117 || sp == 118) && l->back != NO_MAP_SECTOR) {
        const int d = door_index(l->back);
        if (d >= 0) door_open(d, sp == 1 || (sp >= 26 && sp <= 28) || sp == 117);
    } else if (l->tag) {
        for (int d = 0; d < map_ndoors && d < 64; d++)
            if (map_sector_tag[map_doors[d].sector] == (int16_t)l->tag) door_open(d, 0);
    }
}

static void doors_tick(uint16_t dt)
{
    const int16_t psec = (int16_t)map_subs[R_PointInSub(view.x >> 16, view.y >> 16)].sector;
    for (int d = 0; d < map_ndoors && d < 64; d++) {
        const MapSector *s = &map_sectors[map_doors[d].sector];
        int16_t *const sc = &sec_ceil[map_doors[d].sector];
        const int16_t tgt = door_target[d];
        if (*sc < tgt) { *sc += 2 * dt; if (*sc > tgt) *sc = tgt; }
        else if (*sc > tgt) {
            if (psec == (int16_t)map_doors[d].sector) { door_target[d] = map_doors[d].open_ceil; continue; }   /* never close on the player */
            *sc -= 2 * dt; if (*sc < tgt) *sc = tgt;
        } else if (door_manual[d] && door_wait[d] != 0xFFFF) {
            if (door_wait[d] > dt) door_wait[d] -= dt;
            else { door_wait[d] = 0xFFFF; door_target[d] = s->floor; }
        }
    }
}

/* walk-over exit lines (52 exit, 124 secret exit) crossed by the move (x0,y0) -> (x1,y1) */
static void check_walk_exits(int16_t x0, int16_t y0, int16_t x1, int16_t y1)
{
    const int16_t gx = (int16_t)((x1 - map_bm[0]) >> 7), gy = (int16_t)((y1 - map_bm[1]) >> 7);
    if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return;
    const uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
    for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
        const MapLine *l = &map_lines[map_bm_list[k]];
#ifndef DREAD_GAMEPLAY
        if (l->special != 52 && l->special != 124) continue;
#endif
        const int32_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1], bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        const int32_t s0 = (bx - ax) * (y0 - ay) - (by - ay) * (x0 - ax), s1 = (bx - ax) * (y1 - ay) - (by - ay) * (x1 - ax);
        if ((s0 < 0) == (s1 < 0)) continue;
        const int32_t t0 = (x1 - x0) * (ay - y0) - (y1 - y0) * (ax - x0), t1 = (x1 - x0) * (by - y0) - (y1 - y0) * (bx - x0);
        if ((t0 < 0) == (t1 < 0)) continue;
        if(l->special==52 || l->special==124)exit_req=l->special==124?2:1;
#ifdef DREAD_GAMEPLAY
        else if(l->special!=97 || s0<0)World_Activate(map_bm_list[k],1,&view);
#endif
    }
}

static int player_blocked(int16_t x,int16_t y)
{
#ifdef DREAD_COMBAT
    if(Actors_PlayerBlocked(x,y,view.z))return 1;
#endif
    return blocked_from(x,y,view.x>>16,view.y>>16);
}
static void try_move(int32_t mx, int32_t my)
{
    const int32_t ox = view.x, oy = view.y;
    const int32_t nx = view.x + mx, ny = view.y + my;
    if (!player_blocked(nx >> 16, ny >> 16)) { view.x = nx; view.y = ny; }
    else if (!player_blocked(nx >> 16, view.y >> 16)) { view.x = nx; }
    else if (!player_blocked(view.x >> 16, ny >> 16)) { view.y = ny; }
    if (view.x != ox || view.y != oy) check_walk_exits((int16_t)(ox >> 16), (int16_t)(oy >> 16), (int16_t)(view.x >> 16), (int16_t)(view.y >> 16));
}

/* bench route: (vblanks, buttons) */
static const uint16_t bench_script[][2] = {
    {60, 0}, {120, BUTTON_UP}, {60, BUTTON_LEFT}, {150, BUTTON_UP}, {90, BUTTON_RIGHT}, {180, BUTTON_UP},
    {120, BUTTON_RIGHT | BUTTON_UP}, {120, BUTTON_UP}, {200, BUTTON_LEFT}, {150, BUTTON_UP}, {0, 0}
};

/* in-game menu (START): detail levels switch at once, the renderer adapts */
/* frame cap: minimum VBlanks per rendered frame (steady pacing, the spare time goes to the game) */
static uint16_t fcap = 6;
static const uint8_t fcap_v[4] = { 0, 5, 6, 8 };
static const char *const fcap_s[4] = { "LIVRE   ", "12 FPS  ", "10 FPS  ", "7.5 FPS " };
static uint16_t fcap_i = 2;
static void menu_draw(uint16_t sel)
{
    static const char *const res[2]={"H40 (320)","H32 (256)"};
    static const char *const crp[3]={"LARGURA TOTAL ","-2 TILES/LADO ","-4 TILES/LADO "};
    char l[7][36];
    sprintf(l[0],"%c TELA: %s",sel==0?'>':' ',res[(mode>>1)&1]);
    sprintf(l[1],"%c RESOLUCAO: %uX%u",sel==1?'>':' ',r_vw,r_vh);
    sprintf(l[2], "%c RECORTE: %s", sel == 2 ? '>' : ' ', crp[crop >> 1]);
    sprintf(l[3], "%c MUSICA:  %s", sel == 3 ? '>' : ' ', music_on ? "LIGADA   " : "DESLIGADA");
    sprintf(l[4], "%c LIMITE:  %s", sel == 4 ? '>' : ' ', fcap_s[fcap_i]);
    sprintf(l[5], "%c CHEATS",sel==5?'>':' ');
    sprintf(l[6], "%c VOLTAR A ABERTURA",sel==6?'>':' ');
    SYS_disableInts();
    VDP_clearPlane(WINDOW, TRUE);
    VDP_drawTextBG(WINDOW, "MODOS DE VIDEO", 1, 3);
    for (int i = 0; i < 7; i++) VDP_drawTextBG(WINDOW, l[i], 1, 5 + i);
    VDP_drawTextBG(WINDOW, "A:TIRO B:USO/CORRER C+A:ARMA", 1, 13);
    VDP_drawTextBG(WINDOW, "lados troca, START sai", 1, 14);
    SYS_enableInts();
}
static void menu(void)
{
    uint16_t sel = 0, pj = BUTTON_START;
#ifdef DREAD_GAMEPLAY
    uint16_t go_title=0;HUD_WeaponPause(1);
#endif
    while (dma_src) {}
    SYS_disableInts();
    VDP_setTextPalette(PAL3);
    VDP_setTextPriority(TRUE);
    PAL_setColor(63,0xeee);
    VDP_setWindowVPos(FALSE, 15);
    SYS_enableInts();
    menu_draw(sel);
    for (;;) {
        { const uint16_t v0 = vints; while (vints == v0) {} }
#ifndef DREAD_JOY_VBLANK
        JOY_update();
#endif
        const uint16_t j = JOY_readJoypad(JOY_1), e = j & ~pj;
        pj = j;
        if (e & BUTTON_START) break;
        if (e & BUTTON_UP) { sel = (sel + 6) % 7; menu_draw(sel); }
        if (e & BUTTON_DOWN) { sel = (sel + 1) % 7; menu_draw(sel); }
        if (e & (BUTTON_LEFT | BUTTON_RIGHT | BUTTON_A | BUTTON_C)) {
            if (sel == 6){
#ifdef DREAD_GAMEPLAY
                go_title=1;
#endif
                break;
            }
#ifdef DREAD_GAMEPLAY
            if(sel==5){cheats_menu();menu_draw(sel);pj=JOY_readJoypad(JOY_1);continue;}
#endif
            if (sel == 4) {
                fcap_i = (uint16_t)((fcap_i + ((e & BUTTON_LEFT) ? 3 : 1)) & 3);
                fcap = fcap_v[fcap_i];
                menu_draw(sel);
                continue;
            }
            if (sel == 3) {
#ifndef DREAD_NO_MUSIC
                music_on ^= 1;
                if (music_on) XGM2_play(MAP_MUSIC); else XGM2_stop();
#endif
                menu_draw(sel);
                continue;
            }
            if (sel == 2) { crop = (uint16_t)((crop + ((e & BUTTON_LEFT) ? 4 : 2)) % 6); set_mode(mode); }
            else if (sel == 0) set_mode(mode ^ 2);
            else {
                static const uint16_t choices[4]={0,1,9,4};
                uint16_t index=0;for(uint16_t i=0;i<4;i++)if((mode&~2u)==choices[i])index=i;
                index=(index+((e&BUTTON_LEFT)?3:1))&3;
                set_mode((mode&2)|choices[index]);
            }
            SYS_disableInts(); VDP_setWindowVPos(FALSE, 15); SYS_enableInts();
            menu_draw(sel);
        }
    }
    SYS_disableInts();
    VDP_clearPlane(WINDOW, TRUE);
    VDP_setWindowVPos(FALSE, 0);
#ifdef DREAD_GAMEPLAY
    HUD_RestoreTextColor();HUD_WeaponPause(0);
#endif
    SYS_enableInts();
#ifdef DREAD_GAMEPLAY
    if(go_title)SYS_hardReset();
#endif
    prev_joy = BUTTON_START;
#ifdef DREAD_GAMEPLAY
    joy_edges=0;
#endif
}

#ifdef DREAD_EPISODE
#ifdef DREAD_NO_MUSIC
static uint16_t selected_map;
#endif

enum TitleScreen { TITLE_ART, TITLE_MENU, TITLE_LEVELS };
enum TitleChoice { TITLE_NEW_GAME, TITLE_SELECT_LEVEL, TITLE_BENCHMARK, TITLE_CREDITS };

static const char *const title_items[] = { "NEW GAME", "SELECT LEVEL", "BENCHMARK"
#ifdef DREAD_GAMEPLAY
    ,"CREDITS"
#endif
};
#ifdef DREAD_GAMEPLAY
static void wait_any_button(void)
{
    uint16_t released=0;
    for(;;){JOY_update();uint16_t j=JOY_readJoypad(JOY_1);if(!j)released=1;else if(released)return;SYS_doVBlankProcess();}
}
static void credits_sequence(void)
{
    for(uint16_t page=0;page<3;page++){HUD_ShowArt(page);wait_any_button();}
}
#endif
static const char *const title_levels[] = {
    "E1M1  HANGAR", "E1M2  NUCLEAR PLANT", "E1M3  TOXIN REFINERY",
    "E1M4  COMMAND CONTROL", "E1M5  PHOBOS LAB", "E1M6  CENTRAL PROCESSING",
    "E1M7  COMPUTER STATION", "E1M8  PHOBOS ANOMALY", "E1M9  MILITARY BASE"
};

static void draw_title_menu(enum TitleScreen screen, uint16_t cursor)
{
    SYS_disableInts();
    VDP_clearPlane(BG_A, TRUE);
    VDP_setAutoInc(2);
    extern const uint16_t title_mapb[1120];
    for(uint16_t y=0;y<28;y++){
        vram_cmd(0xc000+y*128);
        for(uint16_t x=0;x<40;x++){
            const uint16_t a=title_mapb[y*40+x];
            const uint16_t inside=screen!=TITLE_ART && x>=6 && x<=35 && y>=7 && y<=24;
            *(volatile uint16_t *)0xc00000=(a&0x6000)|(112+(a&2047))|(inside?0:0x8000);
        }
    }
    VDP_setHilightShadow(screen != TITLE_ART);
    PAL_setColor(63,0xeee);
    VDP_setTextPalette(PAL3);
    VDP_setTextPriority(TRUE);
    if (screen == TITLE_ART) {
#ifdef DREAD_VALIDATION_TEST
        VDP_drawTextBG(BG_A, ROM_NAME, 5, 20);
        VDP_drawTextBG(BG_A, "APERTE START OU AGUARDE 15 SEGUNDOS", 3, 23);
#else
        VDP_drawTextBG(BG_A, "PRESS START", 14, 23);
#endif
    } else {
        const bool levels = screen == TITLE_LEVELS;
        const char *const *items = levels ? title_levels : title_items;
        const uint16_t count = levels ? sizeof(title_levels) / sizeof(*title_levels)
                                      : sizeof(title_items) / sizeof(*title_items);
        const uint16_t x = levels ? 8 : 14, y = levels ? 10 : 13;
        if (levels) VDP_drawTextBG(BG_A, "SELECT LEVEL", 14, 8);
        for (uint16_t i = 0; i < count; i++)
            VDP_drawTextBG(BG_A, items[i], x, y + i);
        VDP_drawTextBG(BG_A, ">", x - 2, y + cursor);
        VDP_drawTextBG(BG_A, "A / START: OK    B: BACK", 8, 22);
    }
    SYS_enableInts();
}

static void title(void)
{
    enum TitleScreen screen = TITLE_ART;
    uint16_t cursor = 0, previous = 0;
    HUD_ShowOpening();
    draw_title_menu(screen, cursor);
#ifdef DREAD_VALIDATION_TEST
    const uint16_t title_start = vints;
#endif
    while (!bench_req) {
        const uint16_t frame = vints;
        while (vints == frame && !bench_req) {}
#ifndef DREAD_JOY_VBLANK
        JOY_update();
#endif
        const uint16_t joy = JOY_readJoypad(JOY_1);
        const uint16_t pressed = joy & ~previous;
        previous = joy;
        if (screen == TITLE_ART) {
#ifdef DREAD_VALIDATION_TEST
            if ((uint16_t)(vints - title_start) >= 15 * 60) break;
#endif
            if (!(pressed & (BUTTON_START | BUTTON_A | BUTTON_B | BUTTON_C))) continue;
            screen = TITLE_MENU;
        } else if (pressed & BUTTON_B) {
            cursor = screen == TITLE_LEVELS ? TITLE_SELECT_LEVEL : 0;
            screen = screen == TITLE_LEVELS ? TITLE_MENU : TITLE_ART;
        } else if (pressed & (BUTTON_START | BUTTON_A | BUTTON_C)) {
            if (screen == TITLE_LEVELS) {
                selected_map = cursor;
                break;
            }
#ifdef DREAD_GAMEPLAY
            if(cursor==TITLE_CREDITS){credits_sequence();HUD_ShowOpening();screen=TITLE_ART;cursor=0;draw_title_menu(screen,cursor);continue;}
#endif
            if (cursor != TITLE_SELECT_LEVEL) {
                selected_map = 0;
                bench_req = cursor == TITLE_BENCHMARK;
                break;
            }
            screen = TITLE_LEVELS;
            cursor = 0;
        } else if (pressed & (BUTTON_UP | BUTTON_DOWN)) {
            const uint16_t count = screen == TITLE_LEVELS
                ? sizeof(title_levels) / sizeof(*title_levels)
                : sizeof(title_items) / sizeof(*title_items);
            cursor = (cursor + ((pressed & BUTTON_UP) ? count - 1 : 1)) % count;
        } else continue;
        draw_title_menu(screen, cursor);
    }
    while (!bench_req) {
#ifndef DREAD_JOY_VBLANK
        JOY_update();
#endif
        if (!(JOY_readJoypad(JOY_1) & (BUTTON_START | BUTTON_A | BUTTON_C))) break;
    }
    HUD_ClearOpening();
}
#else
static void title(void)
{
    VDP_clearPlane(BG_B, TRUE);
    VDP_drawText(ROM_NAME, 4, 6);
    VDP_drawText("Renderer estilo Dread:", 4, 9);
    VDP_drawText("paredes por coluna, chao/teto", 4, 10);
    VDP_drawText("MAPA: " DREAD_MAP_LABEL, 4, 11);
#ifdef DREAD_COMBAT
    VDP_drawText("Teste de IA e tiros da pistola.", 4, 12);
#else
    VDP_drawText("Objetos e monstros estaticos.", 4, 12);
#endif
    VDP_drawText("Mede FPS. START no jogo: menu", 4, 13);
    VDP_drawText("de modos (H40/H32, linhas ou", 4, 14);
    VDP_drawText("colunas duplicadas).", 4, 15);
    VDP_drawText("Cima/baixo anda, lados gira,", 4, 16);
    VDP_drawText("C+lados anda de lado,", 4, 17);
    VDP_drawText("A atira, B abre portas.", 4, 18);
    VDP_drawText("aperte START ou aguarde", 4, 20);
    VDP_drawText("15 segundos", 4, 21);
    const uint16_t t0 = vints;
    while ((uint16_t)(vints - t0) < 15 * 60) {
#ifndef DREAD_JOY_VBLANK
        JOY_update();
#endif
        const uint16_t j = JOY_readJoypad(JOY_1);
        if (j & BUTTON_START) break;
        if (j & BUTTON_B) { bench_req = 1; break; }
        if (bench_req) break;
    }
    VDP_clearPlane(BG_B, TRUE);
}
#endif

static void place_player(void)
{
    view.x = (int32_t)map_start[0] << 16; view.y = (int32_t)map_start[1] << 16;
    view.angle = (uint16_t)((int32_t)map_start[2] * 65536 / 360);
    cur_floor = map_sectors[map_subs[R_PointInSub(map_start[0], map_start[1])].sector].floor;
    view.z = cur_floor + 41;
}

/* (re)load the selected map: geometry state, doors, monsters, items */
static void start_level(void)
{
#ifdef DREAD_EPISODE
#ifdef DREAD_SSF
    extern const uint8_t ssf_map_banks[9];
    /* Fixed code/music stay below2MiB. The four upper512KiB slots hold one map. */
    SYS_disableInts();
    for(uint16_t slot=4;slot<8;slot++)*(volatile uint8_t*)(0xa130f1UL+slot*2)=ssf_map_banks[selected_map]+slot-4;
    SYS_enableInts();
#endif
    dread_map = &episode_maps[selected_map];
#endif
    R_Init();
#ifdef DREAD_COMBAT
    Actors_Init();
#endif
    for (int d = 0; d < map_ndoors && d < 64; d++) { door_target[d] = sec_ceil[map_doors[d].sector]; door_wait[d] = 0xFFFF; door_manual[d] = 0; }
    exit_req = 0;
#ifdef DREAD_GAMEPLAY
    extern const uint8_t *const *r_mask_table;
    r_mask_table=level_meta[selected_map].masks;
    World_Init(selected_map);joy_edges=0;
    if(game_video_active)set_mode(mode);
#ifdef DREAD_SSF
    if(game_video_active){SYS_disableInts();scene_palettes();displayed_tint=255;SYS_enableInts();}
#endif
#endif
}

#ifdef DREAD_COMBAT
/* item pickups in the player's subsector (flags bits 8-15 = item code from conv.py) */
static void pickups(HudState *hud, uint16_t psub)
{
    const int16_t px = (int16_t)(view.x >> 16), py = (int16_t)(view.y >> 16);
    for (uint16_t ti = map_sub_things[psub]; ti < map_sub_things[psub + 1]; ti++) {
        const MapThing *t = &map_things[ti];
        const uint16_t code = t->flags >> 8;
        if ((t->flags & THING_MONSTER) || !code || code>=80 || Thing_Taken(ti)) continue;
        if ((px - t->x) * (px - t->x) + (py - t->y) * (py - t->y) > 24 * 24) continue;
        uint16_t *hp = &hud->health, *ar = &hud->armor, *am = &hud->ammo[0];
        switch (code) {
        case 1: if (*am >= 200) continue; *am = *am + 10 > 200 ? 200 : *am + 10; break;          /* clip */
        case 2: if (*am >= 200) continue; *am = *am + 50 > 200 ? 200 : *am + 50; break;          /* box of bullets */
        case 3: if (*hp >= 100) continue; *hp = *hp + 10 > 100 ? 100 : *hp + 10; break;          /* stimpack */
        case 4: if (*hp >= 100) continue; *hp = *hp + 25 > 100 ? 100 : *hp + 25; break;          /* medikit */
        case 5: *hp = *hp + 1 > 200 ? 200 : *hp + 1; break;                                      /* health bonus */
        case 6: *ar = *ar + 1 > 200 ? 200 : *ar + 1; break;                                      /* armor bonus */
        case 7: if (*ar >= 100) continue; *ar = 100; break;                                      /* green armor */
        case 8: if (*ar >= 200) continue; *ar = 200; break;                                      /* blue armor */
        case 9: *hp = *hp + 100 > 200 ? 200 : *hp + 100; break;                                  /* soulsphere */
        case 10: *am = *am + 10 > 200 ? 200 : *am + 10; break;                                   /* backpack */
#ifdef DREAD_GAMEPLAY
        case 20: case 21: case 22: case 23: case 24: case 25: {
            static const uint8_t bit[6]={0,1,2,5,4,3};
            hud->keys|=1u<<bit[code-20];player_keys=hud->keys;break;
        }
        case 30: case 31: case 32: case 33: {
            const uint16_t w=code==33?5:code-28;
            owned_weapons|=1u<<w;hud->arms=(owned_weapons>>1)&15;
            current_weapon=w;HUD_WeaponFrame(w*4);
            if(w==2)hud->ammo[1]+=8;else if(w==3)hud->ammo[0]+=20;else if(w==4)hud->ammo[2]+=2;
            Game_Sound(7);break;
        }
        case 70: case 71: case 72: case 73: case 74: case 75:
            World_Power(code);if(code==71){if(hud->health<100)hud->health=100;current_weapon=0;HUD_WeaponFrame(0);}break;
        case 40: case 41:
            if(hud->ammo[1]>=hud->maxammo[1])continue;
            hud->ammo[1]+=code==40?4:20;break;
        case 42: case 43:
            if(hud->ammo[2]>=hud->maxammo[2])continue;
            hud->ammo[2]+=code==42?1:5;break;
#endif
        default: continue;
        }
#ifdef DREAD_GAMEPLAY
        for(uint16_t a=0;a<4;a++)if(hud->ammo[a]>hud->maxammo[a])hud->ammo[a]=hud->maxammo[a];
        hud->ammo_cur=weapon_ammo[current_weapon]==255?0:hud->ammo[weapon_ammo[current_weapon]];
        Game_Sound(6);
#else
        hud->ammo_cur = hud->ammo[0];
#endif
        Thing_Take(ti);
        HUD_Draw(hud);
    }
}
#endif

#ifdef DREAD_CELLSTREAM_REPORT
/* Dedicated fullscreen summary at the end of the 312-frame route.
 * Kept behind an experimental flag; normal gameplay/menu are unchanged. */
#ifdef DREAD_CELL_STREAM
extern volatile uint32_t cell_stream_rebuilds, cell_stream_hits, cell_stream_fallbacks;
extern volatile uint16_t cell_stream_last_len;
#endif
static void benchmark_report_screen(uint16_t f100)
{
    char line[40];
    while (dma_src) {}                 /* do not cut a pending framebuffer DMA */
    SYS_disableInts();
    hint_on = 0;
    VDP_setHInterrupt(FALSE);
    SYS_setHIntCallback(NULL);
    SYS_setVIntCallback(NULL);         /* do not let HUD VBlank repaint the report */
    /* Gameplay writes reg 1/2 and VSRAM directly, bypassing SGDK's cache.
     * The last VBlank may have disabled display pending hint_a; that callback
     * no longer runs here. Explicitly restore a static, unscrolled text screen.
     * Also select the SDK's BG_A table, not the last double-buffered table. */
    VDP_setEnable(FALSE);
    *(volatile uint16_t *)0xC00004 = 0x8200 | (NT0 >> 10);
    VDP_setWindowHPos(FALSE, 0);
    VDP_setWindowVPos(FALSE, 0);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setVerticalScroll(BG_A, 0);
    VDP_setVerticalScroll(BG_B, 0);
    /* Hide the weapon's hardware sprite chain on the report. */
    VDP_setAutoInc(2);
    vram_cmd(0xF400);
    for (uint16_t i = 0; i < 4; i++)
        *(volatile uint16_t *)0xC00000 = 0;
    VDP_setHilightShadow(FALSE);
    VDP_setTextPalette(PAL3);
    VDP_setTextPriority(TRUE);
    VDP_clearPlane(WINDOW, TRUE);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_drawTextBG(BG_A, "DOOM MD  RENDER BENCHMARK", 2, 1);
    VDP_drawTextBG(BG_A, "E1M1 / ROTA FIXA / NTSC", 2, 3);
#ifdef DREAD_NATIVE_PERSPECTIVE
    VDP_drawTextBG(BG_A, "MODO: NATIVE PERSPECTIVE", 2, 5);
#elif defined(DREAD_CELL_STREAM)
    VDP_drawTextBG(BG_A, "MODO: CELLSTREAM B1", 2, 5);
#else
    VDP_drawTextBG(BG_A, "MODO: CONTROL BSP", 2, 5);
#endif
    sprintf(line, "FPS DA ROTA: %u.%02u", f100 / 100, f100 % 100);
    VDP_drawTextBG(BG_A, line, 2, 7);
    sprintf(line, "QUADROS: %lu", (unsigned long)bench_frames);
    VDP_drawTextBG(BG_A, line, 2, 9);
    sprintf(line, "VBLANKS: %lu", (unsigned long)bench_vints);
    VDP_drawTextBG(BG_A, line, 2, 10);
    sprintf(line, "SEGS: %u  NODES: %u", frame_segs, frame_nodes);
    VDP_drawTextBG(BG_A, line, 2, 12);
    sprintf(line, "SUBS: %u  SEG VISITS: %u", frame_subs, frame_cols);
    VDP_drawTextBG(BG_A, line, 2, 13);
    sprintf(line, "ANCORAS: %u", frame_anchors);
    VDP_drawTextBG(BG_A, line, 2, 14);
#ifdef DREAD_CELL_STREAM
    sprintf(line, "REBUILDS: %lu", (unsigned long)cell_stream_rebuilds);
    VDP_drawTextBG(BG_A, line, 2, 16);
    sprintf(line, "CACHE HITS: %lu", (unsigned long)cell_stream_hits);
    VDP_drawTextBG(BG_A, line, 2, 17);
    sprintf(line, "FALLBACKS: %lu", (unsigned long)cell_stream_fallbacks);
    VDP_drawTextBG(BG_A, line, 2, 18);
    sprintf(line, "LEAVES: %u", cell_stream_last_len);
    VDP_drawTextBG(BG_A, line, 2, 19);
#endif
    VDP_drawTextBG(BG_A, "PIXELS: NAO VALIDADOS", 2, 22);
    VDP_drawTextBG(BG_A, "CENAS: TESTAR NO HARDWARE", 2, 23);
    VDP_drawTextBG(BG_A, "START: REINICIAR", 2, 26);
    /* Never rely on hint_a to turn the report on. */
    VDP_setEnable(TRUE);
    SYS_enableInts();
    for (;;) {
        JOY_update();
        if (JOY_readJoypad(JOY_1) & BUTTON_START) SYS_hardReset();
        SYS_doVBlankProcess();
    }
}
#endif


#ifdef DREAD_GAMEPLAY
static void episode_end(void)
{
    while(dma_src){} SYS_disableInts();hint_on=0;
    VDP_setHInterrupt(FALSE);SYS_setHIntCallback(NULL);SYS_setVIntCallback(NULL);
    SYS_enableInts();
#ifndef DREAD_NO_MUSIC
    if(music_on)XGM2_play(bgm_end);
#endif
    HUD_ShowFinaleText();wait_any_button();
    credits_sequence();
    for(;;){JOY_update();if(!JOY_readJoypad(JOY_1))break;SYS_doVBlankProcess();}
    SYS_hardReset();
}
#endif

int main(bool hard)
{
    (void)hard;
    SYS_disableInts();
    hint_on=0;game_video_active=0;dma_src=0;dma_pos=0;shown=cur_buf=0;
    VDP_setHInterrupt(FALSE);SYS_setHIntCallback(0);
#ifdef DREAD_GAMEPLAY
    owned_weapons=3;current_weapon=1;player_keys=0;cheat_god=cheat_kfa=0;joy_edges=joy_previous=0;
#endif
    SYS_enableInts();
#ifdef DREAD_JOY_VBLANK
    /* The game reads JOY_1 only. Avoid polling an unused second port every VBlank. */
    JOY_setSupport(PORT_2, JOY_SUPPORT_OFF);
#endif
    SYS_disableInts();
    SYS_setVIntCallback(vint_cb);
    SYS_setHIntCallback(hint_a);
    SYS_enableInts();
#ifndef DREAD_NO_MUSIC
    XGM2_loadDriver(TRUE);
    if (music_on) XGM2_play(bgm_intro);
#endif
    title();
    start_level();
#if !defined(DREAD_EPISODE) && !defined(DREAD_TEXT_TITLE)
    HUD_Opening();
#endif
#ifndef DREAD_NO_MUSIC
    if (music_on) XGM2_play(MAP_MUSIC);
#endif
    HUD_Init(HUD_ROW0);
    VDP_setHInterrupt(TRUE);
    set_mode(START_MODE);
    game_video_active=1;
    static HudState hud = { 100, 0, 50, {50, 0, 0, 0}, {200, 50, 50, 300}, 1, 0, 0 };
    hud=(HudState){100,0,50,{50,0,0,0},{200,50,50,300},1,0,0};
    HUD_Draw(&hud);
#ifdef DREAD_GAMEPLAY
    active_hud=&hud;
#endif
    uint16_t face_t = 0, weap_t = 0, weap_step = 0, bob = 0;
#ifdef DREAD_GAMEPLAY
    uint16_t prev_weapon_joy=0;
    uint16_t death_t=0,death_released=0;
#endif
    static const uint8_t weap_seq[4][2] = { {1, 10}, {2, 7}, {3, 8}, {0, 0} };   /* frame, vblanks (Doom 6/4/5 tics) */

    place_player();
#ifdef COMBAT_TEST
    {   /* test builds: start 160 units in front of the first monster, facing it */
        for (uint16_t i = 0; i < map_nthings; i++) if (map_things[i].flags & THING_MONSTER) {
            const MapThing *t = &map_things[i];
            static const int16_t ox[4] = {1, 0, -1, 0}, oy[4] = {0, 1, 0, -1};
            const uint16_t msec = map_subs[t->sub].sector;
            int found = 0;
            for (int16_t dist = 192; dist >= 64 && !found; dist -= 32)
            for (int k = 0; k < 4 && !found; k++) {
                const int16_t x = t->x + ox[k] * dist, y = t->y + oy[k] * dist;
                if (blocked(x, y) || map_subs[R_PointInSub(x, y)].sector != msec) continue;
                found = 1;
                view.x = (int32_t)x << 16; view.y = (int32_t)y << 16;
                view.angle = (uint16_t)(((k + 2) & 3) * 16384);
                view.z = map_sectors[map_subs[R_PointInSub(x, y)].sector].floor + 41;
            }
            if (found) break;
        }
    }
#endif

    uint16_t last = vints, fps_v0 = vints, fps_n = 0;
    uint16_t script_i = 0, script_t = 0;
    uint32_t bench_v0 = 0;
    char txt[40];
    if (bench_req) bench_v0 = vints;
    for (;;) {
        uint16_t now = vints;
        uint16_t dt = now - last; last = now;
#ifdef DREAD_GAMEPLAY
        if(dt>30)dt=30; /* keep game time near real time; movement/projectiles substep */
#else
        if (dt > 8) dt = 8;
#endif
        if (bench_req && !bench_done) dt = 4;    /* bench: same camera path at any speed (frames are comparable) */
#ifndef DREAD_JOY_VBLANK
        JOY_update();
#endif
        uint16_t j = JOY_readJoypad(JOY_1);
#ifdef DREAD_GAMEPLAY
        /* Latch short action presses at VBlank: a slow full-height frame must
         * not swallow START/use/fire between two main-loop polls. */
        const uint16_t edges=joy_edges;
        __asm__ volatile("and.w %1,%0" : "+m"(joy_edges) : "d"((uint16_t)~edges) : "cc","memory");
        j|=edges&(BUTTON_START|BUTTON_A|BUTTON_B|BUTTON_C);
#endif
#ifdef FREEZE_AT
        if (bench_frames >= FREEZE_AT) { dt = 0; bench_done = 3; }   /* test builds: keep rendering one fixed view */
#endif
        if (bench_req && !bench_done) {
            script_t += dt;
            while (bench_script[script_i][0] && script_t >= bench_script[script_i][0]) { script_t -= bench_script[script_i][0]; script_i++; }
            j = bench_script[script_i][1];
            bench_joy = j;
            if (!bench_script[script_i][0]) {
                bench_done = 1; bench_vints = vints - bench_v0;
            }
        }
#ifdef DREAD_GAMEPLAY
        if(!hud.health){
            if(!death_t){death_t=1;death_released=0;Game_Sound(20);HUD_WeaponBob(0,256);HUD_Text(1,"VOCE MORREU - APERTE UM BOTAO");HUD_Draw(&hud);}
            death_t+=dt;
            cur_floor=map_sectors[map_subs[R_PointInSub(view.x>>16,view.y>>16)].sector].floor;
            if(view.z>cur_floor+6){view.z-=dt;if(view.z<cur_floor+6)view.z=cur_floor+6;}
            if(!(j&(BUTTON_A|BUTTON_B|BUTTON_C|BUTTON_START)))death_released=1;
            if(death_t>=60 && death_released && (j&(BUTTON_A|BUTTON_B|BUTTON_C|BUTTON_START))){
                start_level();place_player();owned_weapons=3;current_weapon=1;player_keys=0;hud.keys=0;hud.arms=1;weap_step=weap_t=0;
                hud.health=100;hud.armor=0;hud.ammo[0]=50;hud.ammo[1]=hud.ammo[2]=hud.ammo[3]=0;hud.ammo_cur=50;hud.face=0;
                HUD_WeaponBob(0,0);HUD_WeaponFrame(4);HUD_Text(1,"");HUD_Draw(&hud);death_t=0;scene_flash=0;joy_edges=0;prev_joy=j;last=vints;
                continue;
            }
            goto render_frame;
        }
#endif
        if ((j & BUTTON_START) && !(prev_joy & BUTTON_START) && !bench_req) { prev_joy = j; menu(); last = vints; continue; }
        if ((j & BUTTON_B) && !(prev_joy & BUTTON_B)) use_line();
        prev_joy = j;
#ifdef DREAD_GAMEPLAY
        if(World_Tick(dt,&view,&hud))exit_req=1;
#else
        doors_tick(dt);
#endif
        /* turn / move (per vblank speeds, Doom-like) */
        const int strafe = (j & BUTTON_C) != 0;
        const int32_t speed = (j&BUTTON_B)?0x60000:0x30000;     /* map units per vblank, 16.16 */
        /* pistol: A fires (Doom timing), the status bar counts the bullets */
        if (bench_req == 2 && !bench_done && (bench_frames & 3) == 0) j |= BUTTON_A;   /* combat bench: keeps shooting */
        if (bench_req == 2 && hud.ammo[0] < 5) hud.ammo[0] = 50;
#ifdef DREAD_GAMEPLAY
        if ((j&(BUTTON_C|BUTTON_A))==(BUTTON_C|BUTTON_A) && !(prev_weapon_joy&BUTTON_A)) {
            do { current_weapon=(current_weapon+1)%6; } while(!(owned_weapons&(1u<<current_weapon)));
            weap_step=0;weap_t=0;HUD_WeaponFrame(current_weapon*4);
        }
        const uint8_t ammo=weapon_ammo[current_weapon];
        if(weap_t>dt)weap_t-=dt;else weap_t=0;
        if(weap_step && !weap_t){weap_step=0;HUD_WeaponFrame(current_weapon*4);}
        if(!weap_t && (j&BUTTON_A) && !(j&BUTTON_C) && (ammo==255 || hud.ammo[ammo])) {
            if(ammo!=255 && !cheat_kfa)hud.ammo[ammo]--;
            weap_step=1;weap_t=weapon_delay[current_weapon];
            HUD_WeaponFire(current_weapon);Game_Sound(weapon_sound[current_weapon]);
            if(current_weapon>=1 && current_weapon<=4)Game_Flash();
            Actors_FireWeapon(&view,current_weapon);
        }
        prev_weapon_joy=j;
        hud.ammo_cur=ammo==255?0:hud.ammo[ammo];HUD_Draw(&hud);
#else
        if (weap_step == 0 && (j & BUTTON_A) && hud.ammo[0]) {
            weap_step = 1; weap_t = weap_seq[0][1]; HUD_WeaponFrame(weap_seq[0][0]);
#ifdef DREAD_COMBAT
            Actors_Fire(&view, 1, 5);              /* pistol: 5 x (1..3) */
#endif
            hud.ammo[0]--; hud.ammo_cur = hud.ammo[0]; HUD_Draw(&hud);
        } else if (weap_step) {
            if (weap_t > dt) weap_t -= dt;
            else { HUD_WeaponFrame(weap_seq[weap_step][0]); weap_t = weap_seq[weap_step][1]; weap_step = weap_seq[weap_step][1] ? weap_step + 1 : 0; }
        }
#endif
        /* face looks around */
        face_t += dt;
        if (face_t > 90) { face_t = 0; hud.face = (int16_t)((hud.face + 1 + (vints & 1)) % 3); HUD_Draw(&hud); }
        if (!strafe) {
            if (j & BUTTON_LEFT) view.angle += 400 * dt;
            if (j & BUTTON_RIGHT) view.angle -= 400 * dt;
        }
        const uint16_t a = view.angle >> 6;
        const int32_t cs = sintab[(a + 256) & 1023], sn = sintab[a];
        int32_t fwd = 0, side = 0;
        if (j & BUTTON_UP) fwd = speed * dt;
        if (j & BUTTON_DOWN) fwd = -speed * dt;
        if (strafe && (j & BUTTON_LEFT)) side = -speed * dt;
        if (strafe && (j & BUTTON_RIGHT)) side = speed * dt;
        if (fwd || side) {
            bob += dt;
            const int16_t sx = sintab[(bob * 12) & 1023] >> 11, sy = sintab[(bob * 24) & 1023] >> 12;
            HUD_WeaponBob(sx, sy < 0 ? sy : -sy);
        }
        else HUD_WeaponBob(0,0);
        if (fwd || side) {
            const int32_t mx = ((fwd >> 8) * cs + (side >> 8) * sn) >> 6;
            const int32_t my = ((fwd >> 8) * sn - (side >> 8) * cs) >> 6;
#ifdef DREAD_GAMEPLAY
            const uint16_t steps=(dt+3)/4;
            for(uint16_t step=0;step<steps;step++)try_move(mx/steps,my/steps);
#else
            try_move(mx, my);
#endif
        }
        cur_floor = map_sectors[map_subs[R_PointInSub(view.x >> 16, view.y >> 16)].sector].floor;
        view.z = cur_floor + 41;

#ifdef DREAD_COMBAT
        {
            static ActorPlayer pl;
            const uint16_t health = hud.health, armor = hud.armor;
            pl.x = (int16_t)(view.x >> 16); pl.y = (int16_t)(view.y >> 16); pl.z = view.z;
            pl.sub = (uint16_t)R_PointInSub(pl.x, pl.y);
            pl.health = &hud.health; pl.armor = &hud.armor;
            if (!bench_req || bench_req == 2) Actors_Tick(&pl, dt);   /* bench 2: same route with live monsters */
#ifdef DREAD_GAMEPLAY
            if(combat_drop_ammo || combat_drop_shotgun){
                hud.ammo[0]+=combat_drop_ammo;combat_drop_ammo=0;if(hud.ammo[0]>hud.maxammo[0])hud.ammo[0]=hud.maxammo[0];
                if(combat_drop_shotgun){if(!(owned_weapons&4)){owned_weapons|=4;current_weapon=2;weap_step=weap_t=0;HUD_WeaponFrame(8);}hud.ammo[1]+=combat_drop_shotgun*4;combat_drop_shotgun=0;if(hud.ammo[1]>hud.maxammo[1])hud.ammo[1]=hud.maxammo[1];hud.arms=(owned_weapons>>1)&15;}
                HUD_Draw(&hud);
            }
#endif
            if (bench_req == 2 && hud.health < 30) hud.health = 100;   /* the combat bench never dies */
            pickups(&hud, pl.sub);
#ifdef DREAD_GAMEPLAY
            if(!hud.health)continue;
#else
            if (!hud.health) {                          /* dead: message, then the map starts again */
                HUD_Text(1, "VOCE MORREU");
                const uint16_t t0 = vints;
                while ((uint16_t)(vints - t0) < 120) {}
                HUD_Text(1, "");
                start_level(); place_player();
#ifdef DREAD_GAMEPLAY
                owned_weapons=3;current_weapon=1;player_keys=0;hud.keys=0;hud.arms=1;weap_step=weap_t=0;HUD_WeaponFrame(4);
#endif
                hud.health = 100; hud.armor = 0; hud.ammo[0] = 50; hud.ammo[1]=hud.ammo[2]=hud.ammo[3]=0; hud.ammo_cur = 50;
                HUD_Draw(&hud);
                last = vints;
                continue;
            }
#endif
            if (health != hud.health || armor != hud.armor) HUD_Draw(&hud);
#ifdef COMBAT_TEST
            if ((vints & 31) == 0) {
                char t[40];
                sprintf(t, "W%u H%u K%u A%u HP%u", combat_wakes, combat_hits, combat_kills, combat_attacks, hud.health);
                HUD_Text(1, t);
            }
#endif
        }
#endif
        if (exit_req) {                                 /* level done: next map (E1M8 ends the episode) */
#ifdef DREAD_EPISODE
            const uint16_t secret = exit_req == 2;
#ifdef DREAD_GAMEPLAY
            while(dma_src){}SYS_disableInts();hint_on=0;game_video_active=0;
            VDP_setHInterrupt(FALSE);SYS_setHIntCallback(NULL);SYS_enableInts();
            uint16_t total=0,items=0,totalitems=0;
            for(uint16_t i=0;i<map_nthings;i++){
                const MapThing *t=&map_things[i];const uint16_t code=t->flags>>8;
                if(t->flags&THING_MONSTER){if(THING_KIND(t->flags)!=5)total++;continue;}
                if(code==5 || code==6 || code==9 || code==70 || code==71 || code==72 || code==74 || code==75){totalitems++;if(Thing_Taken(i))items++;}
            }
#ifndef DREAD_NO_MUSIC
            if(music_on)XGM2_play(bgm_inter);
#endif
            intermission_active=1;
            HUD_ShowIntermission(title_levels[selected_map]+6,combat_kills,total,items,totalitems,level_secrets,level_total_secrets,level_time/60);
            wait_any_button();intermission_active=0;
#else
            char msg[32];
            sprintf(msg, "E1M%u CONCLUIDA", selected_map + 1);
            HUD_Text(1, msg);
            const uint16_t t0 = vints;
            while ((uint16_t)(vints - t0) < 120) {}
            HUD_Text(1, "");
#endif
            if (selected_map == 7) {
#ifdef DREAD_GAMEPLAY
                episode_end();
#else
                SYS_hardReset();
#endif
            }     /* end of the episode: back to the title */
            selected_map = secret ? 8 : (selected_map == 8 ? 3 : selected_map + 1);
#ifdef DREAD_GAMEPLAY
            hud.keys=0;player_keys=0;weap_step=weap_t=0;HUD_WeaponFrame(current_weapon*4);
#endif
#ifdef DREAD_GAMEPLAY
            HUD_ClearOpening();HUD_Init(HUD_ROW0);set_mode(mode);game_video_active=1;HUD_WeaponFrame(current_weapon*4);HUD_Draw(&hud);
#endif
            start_level(); place_player();
#ifndef DREAD_NO_MUSIC
            if (music_on) XGM2_play(MAP_MUSIC);
#endif
            last = vints;
            continue;
#else
            exit_req = 0;
#endif
        }
#ifdef DREAD_GAMEPLAY
render_frame:
#endif
        /* render into the free RAM buffer, then hand it to the VBlank DMA */
        if (NBUF == 1) while (dma_src) {}   /* one buffer: the previous frame must be out first */
        uint8_t *const fb = fbuf + (cur_buf ? FB_BYTES : 0);
        R_RenderView(&view, fb);
        if (!bench_req) while ((uint16_t)(vints - now) < fcap) {}   /* frame cap (off in the benches) */
        frame_segs = rstats.segs_drawn; frame_nodes = rstats.nodes_visited; frame_cols = rstats.col_visits; frame_anchors = rstats.anchors; frame_subs = rstats.subs_visited;
        while (dma_src) {}
#ifdef DREAD_GAMEPLAY
        dma_tint=!hud.health?2:World_Tint();if(!dma_tint && scene_flash)dma_tint=1;scene_flash=0;
#endif
        dma_pos = 0; dma_src = fb;
        cur_buf ^= (NBUF - 1);
        if (bench_req && !bench_done) bench_frames++;

        if (++fps_n == 16) {
            const uint16_t dv = vints - fps_v0; fps_v0 = vints; fps_n = 0;
            const uint16_t f10 = dv ? (uint16_t)(16UL * 600 / dv) : 0;
            sprintf(txt, "FPS %2u.%u  SEGS %3u ", f10 / 10, f10 % 10, frame_segs);
            HUD_Text(0, txt);
        }
        if (bench_done == 1) {
            const uint16_t f100 = (uint16_t)(bench_frames * 6000UL / (bench_vints ? bench_vints : 1));
            sprintf(txt, "BENCH %u quadros %u.%u%u FPS", (uint16_t)bench_frames, f100 / 100, (f100 / 10) % 10, f100 % 10);
            HUD_Text(1, txt);
            bench_done = 2;
#ifdef DREAD_CELLSTREAM_REPORT
            benchmark_report_screen(f100);
#endif
        }
    }
    return 0;
}
