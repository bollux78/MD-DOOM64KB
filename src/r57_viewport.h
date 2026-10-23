/* R57 experimental crop. GPL-2.0-or-later.
 * Original visible raster: x=[2,76), y=[2,44), samples of 4x4 pixels.
 * Remove 4 samples (16 physical pixels) from EACH visible edge.
 * Keep projection, center, sample size and packed framebuffer strides.
 */
#ifndef R57_VIEWPORT_H
#define R57_VIEWPORT_H
#if !defined(DOOM_R57_CROP16)
#define R57_CROP_ACTIVE 1
#endif
#if defined(DOOM_R57_CROP16)
#if !defined(DOOM_R22_PIXEL4) || !defined(DOOM_R48_PAIR_V) || !defined(DOOM_R47_PLANE_PAIR)
#error R57 crop16 requires the native pixel4 Pair-V backend
#endif
#if defined(DOOM_R57_VIEW_MENU)
#ifndef DOOM_R57_VIEW_MODE
#define DOOM_R57_VIEW_MODE 0
#endif
#ifndef DOOM_R57_VIEW_HCROP
#define DOOM_R57_VIEW_HCROP 16
#endif
#ifndef DOOM_R57_VIEW_VCROP
#define DOOM_R57_VIEW_VCROP 16
#endif
typedef struct {uint8_t mode,hcrop,vcrop,xmin,xend,ymin,yend;} R57ViewConfig;
extern R57ViewConfig r57_view;
/* Pure geometry helper: all coordinates are 4px samples, tile-aligned. */
static inline R57ViewConfig R57_ViewMake(uint8_t mode,uint8_t h,uint8_t v){
    R57ViewConfig result;
    result.mode=(mode!=0);h=(h>32)?32:(h&~7u);v=(v>32)?32:(v&~7u);
    result.hcrop=h;result.vcrop=v;
    result.xmin=(result.mode?6:2)+h/4;
    result.xend=(result.mode?70:76)-h/4;
    result.ymin=2+v/4;result.yend=44-v/4;
    return result;
}
void R57_ChangeView(uint16_t field,uint16_t forward);
#define R57_XMIN (r57_view.xmin)
#define R57_XEND (r57_view.xend)
#define R57_YMIN (r57_view.ymin)
#define R57_YEND (r57_view.yend)
#define R57_CROP_ACTIVE 1
#else
#define R57_XMIN 6
#if defined(DOOM_R57_NARROW256)
#define R57_XEND 70
#else
#define R57_XEND 72
#endif
#if defined(DOOM_R57_SIZE_MENU)
extern uint8_t r57_crop_enabled;
void R57_SetCrop(uint8_t enabled);
#define R57_CROP_ACTIVE (r57_crop_enabled != 0)
#else
#define R57_CROP_ACTIVE 1
#endif
#define R57_YMIN 6
#define R57_YEND 40
#endif /* VIEW_MENU vs fixed/legacy crop */
#define R57_TILE_XMIN (R57_XMIN / 2)
#define R57_TILE_XEND (R57_XEND / 2)
#define R57_TILE_YMIN (R57_YMIN / 2)
#define R57_TILE_YEND (R57_YEND / 2)
#define R57_DMA_WORDS (R57_TILE_XEND - R57_TILE_XMIN)
#endif
#endif
