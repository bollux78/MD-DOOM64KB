#ifndef LEVEL_META_H
#define LEVEL_META_H
#include "render.h"
typedef struct { const uint16_t *specials; const uint16_t *floorflat; const int16_t (*teleports)[3]; uint16_t nteleports; const uint8_t *const *masks; } LevelMeta;
extern const LevelMeta level_meta[9];
#endif
