#ifndef SCD_LOGIC_PACKET_H
#define SCD_LOGIC_PACKET_H
#include <stdint.h>

enum { SCD_SIGHT = 1, SCD_SOUND = 2, SCD_RAYS = 4 };
enum { LOAD_NODES = 1, SIGHT_BSP, LOAD_PORTALS, SOUND_FLOOD, SORT_INTERCEPTS };
enum { MAX_NODES = 8192, MAX_LEAVES = 512, MAX_SECTORS = 512,
       MAX_PORTALS = 8192, MAX_INTERCEPTS = 64 };

typedef struct { int16_t x, y, dx, dy; uint16_t child[2]; } LogicNode;
typedef struct { uint16_t a, b, blocks; } LogicPortal;
typedef struct { int32_t floor, ceiling; } LogicHeight;
typedef struct {
    uint16_t sequence, command, count, result, origin;
    union {
        LogicNode nodes[MAX_NODES];
        struct { int32_t x1, y1, x2, y2; uint16_t leaf[MAX_LEAVES]; } sight;
        LogicPortal portals[MAX_PORTALS];
        struct { LogicHeight height[MAX_SECTORS]; uint8_t visited[MAX_SECTORS]; } sound;
        struct { int32_t frac[MAX_INTERCEPTS]; uint16_t order[MAX_INTERCEPTS]; } ray;
    } data;
} LogicPacket;

_Static_assert(sizeof(LogicPacket) <= 128UL * 1024, "packet exceeds Word RAM bank");

extern volatile uint8_t scd_available;
extern uint8_t scd_logic_loaded;
extern const volatile uint8_t scd_logic_mode;
volatile LogicPacket *SCD_LogicPacket(void);
int SCD_LogicCall(uint16_t command, uint16_t count);
void SCD_Probe(void);
#endif
