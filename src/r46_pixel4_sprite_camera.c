/* Native camera-space sprite projection, independently linked beside 8x8.
 * Q16 input and 64-bit intermediate avoid signed multiplication overflow.
 * This path is not active at runtime; performance must be evaluated before
 * a 4x4 dispatcher is enabled.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_camera.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error Native sprite projection requires M2B coexistence
#endif
static int32_t div_scaled(int64_t numerator,int32_t depth)
{
    return (int32_t)(numerator / depth);
}
uint16_t R46_P4_ProjectSpriteRect(int32_t tx,int32_t tz,
    int32_t width,int32_t top_z,int32_t bottom_z,
    uint16_t gameplay,r46_p4_sprite_rect_t *out)
{
    if(!out || tz<(4L<<16) || tz>(1280L<<16) ||
       width<=0 || top_z<bottom_z)return 0;
    /* Calculate unclipped projected edges before testing viewport. */
    int64_t right_world=(int64_t)tx+width;
    int32_t left=38+div_scaled((int64_t)tx*38,tz);
    int32_t right=38+div_scaled(right_world*38,tz)-1;
    int32_t top=22-div_scaled((int64_t)top_z*44,tz);
    int32_t bottom=22-div_scaled((int64_t)bottom_z*44,tz)-1;
    int32_t border=gameplay?2:0;
    if(right<left || bottom<top || right<border || left>75 ||
       bottom<border || top>43)return 0;
    if(left<border)left=border;
    if(right>75)right=75;
    if(top<border)top=border;
    if(bottom>43)bottom=43;
    if(left>right||top>bottom)return 0;
    r46_p4_sprite_rect_t result={
        (int16_t)left,(int16_t)right,(int16_t)top,(int16_t)bottom,
        (uint16_t)(tz>>16)
    };
    *out=result;
    return 1;
}
typedef struct {
    uint16_t (*project)(int32_t,int32_t,int32_t,int32_t,int32_t,
                        uint16_t,r46_p4_sprite_rect_t *);
} r46_p4_sprite_camera_ops_t;
static const r46_p4_sprite_camera_ops_t sprite_ops={R46_P4_ProjectSpriteRect};
__attribute__((noinline))
const r46_p4_sprite_camera_ops_t *R46_P4_SpriteCameraOps(void)
{
    return &sprite_ops;
}
__attribute__((noinline))
uint16_t R46_P4_SpriteCameraValidate(void)
{
    const r46_p4_sprite_camera_ops_t *ops=R46_P4_SpriteCameraOps();
    return (uint16_t)(ops && ops->project && sizeof(r46_p4_sprite_rect_t)==10);
}
#endif
