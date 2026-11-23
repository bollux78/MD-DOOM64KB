/* Link stubs so the renderer can be built on the host for geometry A/B checks.
 * Actors are not drawn and no pickup is hidden: only walls, flats, sky and static things are compared. */
#include <stdint.h>
void Actors_Draw(uint16_t sub) { (void)sub; }
void Actors_FrameBegin(void) {}
int  Thing_Taken(uint16_t index) { (void)index; return 0; }
