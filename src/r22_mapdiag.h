#ifndef R22_MAPDIAG_H
#define R22_MAPDIAG_H
#include <stdint.h>
#if defined(DOOM_R22_MAP_DIAG)
typedef struct {uint16_t map,stage;uint32_t free,largest;} r22_map_entry;
extern r22_map_entry r22_map_trace[16];
extern uint16_t r22_map_head,r22_map_count,r22_map_current,r22_map_stage;
extern uint16_t r22_map_request,r22_map_tag,r22_map_failed_stage;
extern uint32_t r22_map_need;
void R22_MapMark(uint16_t map,uint16_t stage);
void R22_MapReport(void);
#else
#define R22_MapMark(map,stage) ((void)0)
#endif
#endif
