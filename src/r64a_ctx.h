/* R64A per-frame view context; EXPERIMENTAL, off by default. */
#ifndef R64A_CTX_H
#define R64A_CTX_H
#if defined(DOOM_R64A_PROLOGUE)
void R64A_FrameBegin(void);
void R64A_FrameEnd(void);
#define R64A_FRAME_BEGIN() R64A_FrameBegin()
#define R64A_FRAME_END() R64A_FrameEnd()
#else
#define R64A_FRAME_BEGIN() ((void)0)
#define R64A_FRAME_END() ((void)0)
#endif
#endif
