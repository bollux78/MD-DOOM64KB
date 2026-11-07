/* Sega CD geometry-local BSP globals.
 * Renderer code is never linked on sub: P_LoadNodes assigns these actual
 * nonvisual map pointers, with identical types to the original R128.
 */
#include "r_main.h"
int16_t numnodes;
const mapnode_t __far* nodes;
