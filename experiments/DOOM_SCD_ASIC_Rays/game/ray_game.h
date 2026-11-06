#ifndef SCD_RAY_GAME_H
#define SCD_RAY_GAME_H
#include <stdint.h>
extern const volatile uint8_t scd_ray_mode;
extern volatile uint8_t scd_ray_available, scd_ray_profile;
void SCD_RayBoot(void);
void SCD_RayBegin(uint16_t tic, uint16_t map);
void SCD_RayEnd(void);
int SCD_RayQuery(uint32_t actor, int32_t x1, int32_t y1, int32_t x2, int32_t y2);
uint16_t SCD_RayClock(void);
void SCD_RayProfile(uint16_t start);
#endif
