/* R57 experimental crop. GPL-2.0-or-later.
 * Original visible raster: x=[2,76), y=[2,44), samples of 4x4 pixels.
 * Remove 4 samples (16 physical pixels) from EACH visible edge.
 * Keep projection, center, sample size and packed framebuffer strides.
 */
#ifndef R57_VIEWPORT_H
#define R57_VIEWPORT_H
#if defined(DOOM_R57_CROP16)
#if !defined(DOOM_R22_PIXEL4) || !defined(DOOM_R48_PAIR_V) || !defined(DOOM_R47_PLANE_PAIR)
#error R57 crop16 requires the native pixel4 Pair-V backend
#endif
#define R57_XMIN 6
#define R57_XEND 72
#define R57_YMIN 6
#define R57_YEND 40
#define R57_TILE_XMIN (R57_XMIN / 2)
#define R57_TILE_XEND (R57_XEND / 2)
#define R57_TILE_YMIN (R57_YMIN / 2)
#define R57_TILE_YEND (R57_YEND / 2)
#define R57_DMA_WORDS (R57_TILE_XEND - R57_TILE_XMIN)
#endif
#endif
