#ifndef R20_DMA_H
#define R20_DMA_H
#if defined(DOOM_R20_VBLANK_VIDEO)
void R20_VBlankVideo(void);
void R20_StopVideo(void);
void R20_AbortVideo(void);
#else
#define R20_VBlankVideo() ((void)0)
#define R20_StopVideo() ((void)0)
#define R20_AbortVideo() ((void)0)
#endif
#endif
