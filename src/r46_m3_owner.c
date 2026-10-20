/* R46 M3A handoff PRECONDITION tracker. It never touches VDP or _s_screen. */
#if defined(DOOM_R46_M2C)
#include "r46_m3_owner.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error M3A handoff requires R39f 8x8 control plus staged pixel4 support
#endif
void R46_M3_OwnerInit(r46_m3_owner_t *s)
{
    if(!s)return;
    s->owner=R46_M3_CELL;
    s->desired=R46_M3_CELL;
    s->phase=R46_M3_ACTIVE;
    s->acknowledged=0;
    s->epoch=0;
}
uint16_t R46_M3_Request(r46_m3_owner_t *s,uint16_t next)
{
    if(!s||s->phase!=R46_M3_ACTIVE||next>R46_M3_PIXEL4||
       next==s->owner)return 0;
    s->desired=next;
    s->phase=R46_M3_QUIESCE;
    s->acknowledged=0;
    s->epoch=(uint16_t)(s->epoch+1u);
    return 1;
}
uint16_t R46_M3_AckQuiesce(r46_m3_owner_t *s,uint16_t flags)
{
    if(!s||s->phase!=R46_M3_QUIESCE||!flags||
       (flags&~R46_M3_QUIESCE_ALL))return 0;
    s->acknowledged=(uint16_t)(s->acknowledged|flags);
    if((s->acknowledged&R46_M3_QUIESCE_ALL)==R46_M3_QUIESCE_ALL)
        s->phase=R46_M3_RECONFIGURE;
    return 1;
}
uint16_t R46_M3_AckReconfigure(r46_m3_owner_t *s,uint16_t flags)
{
    if(!s||s->phase!=R46_M3_RECONFIGURE||!flags||
       (flags&~R46_M3_RECONFIG_ALL) ||
       (s->acknowledged&R46_M3_QUIESCE_ALL)!=R46_M3_QUIESCE_ALL)
        return 0;
    s->acknowledged=(uint16_t)(s->acknowledged|flags);
    return 1;
}
uint16_t R46_M3_Commit(r46_m3_owner_t *s)
{
    if(!s||s->phase!=R46_M3_RECONFIGURE||
       (s->acknowledged&(R46_M3_QUIESCE_ALL|R46_M3_RECONFIG_ALL))!=
                       (R46_M3_QUIESCE_ALL|R46_M3_RECONFIG_ALL))
        return 0;
    s->owner=s->desired;
    s->phase=R46_M3_ACTIVE;
    s->acknowledged=0;
    return 1;
}
uint16_t R46_M3_AbortQuiesce(r46_m3_owner_t *s)
{
    if(!s||s->phase!=R46_M3_QUIESCE)return 0;
    s->desired=s->owner;
    s->phase=R46_M3_ACTIVE;
    s->acknowledged=0;
    return 1;
}
uint16_t R46_M3_MayWrite(const r46_m3_owner_t *s,uint16_t owner)
{
    return (uint16_t)(s && owner<=R46_M3_PIXEL4 &&
                       s->phase==R46_M3_ACTIVE && s->owner==owner);
}
typedef struct {
    void (*init)(r46_m3_owner_t *);
    uint16_t (*request)(r46_m3_owner_t *,uint16_t);
    uint16_t (*quiesce)(r46_m3_owner_t *,uint16_t);
    uint16_t (*reconfigure)(r46_m3_owner_t *,uint16_t);
    uint16_t (*commit)(r46_m3_owner_t *);
    uint16_t (*abort)(r46_m3_owner_t *);
    uint16_t (*may_write)(const r46_m3_owner_t *,uint16_t);
} r46_m3_owner_ops_t;
static const r46_m3_owner_ops_t owner_ops={
    R46_M3_OwnerInit,R46_M3_Request,R46_M3_AckQuiesce,
    R46_M3_AckReconfigure,R46_M3_Commit,R46_M3_AbortQuiesce,
    R46_M3_MayWrite
};
__attribute__((noinline))
const r46_m3_owner_ops_t *R46_M3_OwnerOps(void){return &owner_ops;}
__attribute__((noinline))
uint16_t R46_M3_OwnerValidate(void)
{
    const r46_m3_owner_ops_t *p=R46_M3_OwnerOps();
    return (uint16_t)(p && p->init && p->request && p->quiesce &&
        p->reconfigure && p->commit && p->abort && p->may_write &&
        sizeof(r46_m3_owner_t)==10);
}
#endif
