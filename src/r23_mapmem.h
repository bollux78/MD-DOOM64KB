#ifndef R23_MAPMEM_H
#define R23_MAPMEM_H
#include <stddef.h>
#include <stdint.h>
#if defined(DOOM_R23_MAPMEM)
void R23_MapMemoryInit(uint16_t lines,uint16_t sides,uint16_t cells);
void *R23_NodeAlloc(void);
void R23_NodeFree(void *p);
uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size);
void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value);
#define R23_GET(p,f) ((__typeof__((p)->f))R23_MapRead((p),offsetof(__typeof__(*(p)),f),sizeof((p)->f)))
#define R23_SET(p,f,v) R23_MapWrite((p),offsetof(__typeof__(*(p)),f),sizeof((p)->f),(uint32_t)(v))
extern const uint16_t *r23_sector_offsets,*r23_sector_lines;
#define SECTOR_LINE(s,i) (&_g_maplines[r23_sector_lines[r23_sector_offsets[(s)->sector_index]+(i)]])
#define SECTOR_LINECOUNT(s) (r23_sector_offsets[(s)->sector_index+1]-r23_sector_offsets[(s)->sector_index])
#else
#define R23_GET(p,f) ((p)->f)
#define R23_SET(p,f,v) ((p)->f=(v))
#define SECTOR_LINE(s,i) ((s)->lines[i])
#define SECTOR_LINECOUNT(s) ((s)->linecount)
#endif
#endif
