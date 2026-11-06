#ifndef SCD_PROBE_H
#define SCD_PROBE_H

#include <stdint.h>

extern volatile unsigned char scd_available;
void SCD_Probe(void);
void SCD_BeginWorld(void);
int SCD_EndWorld(void);
void SCD_Flush(void);
int SCD_Column(uint8_t *fb, uint8_t *dst, const uint8_t *source,
               const uint8_t *lut, uint16_t phase, uint16_t step,
               uint16_t rows, uint16_t odd);
uint8_t *SCD_DrawBuffer(void);

#endif
