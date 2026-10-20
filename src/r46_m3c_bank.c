/* M3C host-testable staging barrier. Never writes to VRAM or global RAM. */
#if defined(DOOM_R46_M2C)
#include "r46_m3c_bank.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error M3C staging only valid alongside the R39f 8x8 backend
#endif
#define R46_M3C_COMPLETE_ROWS ((uint32_t)0x001fffffu)
_Static_assert(R46_M3C_COLUMNS*R46_M3C_ROWS==R46_M3C_DYNAMIC_TILES,
               "M3C expected 798 visible tile patterns");
void R46_M3C_BankInit(r46_m3c_bank_t *s)
{
    if(!s)return;
    s->visible_bank=R46_M3C_NO_BANK;
    s->pending_bank=R46_M3C_NO_BANK;
    s->uploaded=0;
    s->mapped_rows=0;
    s->commits=0;
}
uint16_t R46_M3C_StageBank(r46_m3c_bank_t *s,uint16_t bank)
{
    if(!s || bank>1u || s->pending_bank!=R46_M3C_NO_BANK ||
       s->visible_bank==bank)return 0;
    s->pending_bank=bank;
    s->uploaded=0;
    s->mapped_rows=0;
    return 1;
}
uint16_t R46_M3C_BankWritable(const r46_m3c_bank_t *s,uint16_t bank)
{
    return (uint16_t)(s && bank<=1u && s->pending_bank==bank &&
        s->visible_bank!=bank && s->mapped_rows==0);
}
uint16_t R46_M3C_TilesUploaded(r46_m3c_bank_t *s,uint16_t count)
{
    if(!s||s->pending_bank==R46_M3C_NO_BANK||
       s->mapped_rows || !count ||
       (uint32_t)s->uploaded+count>R46_M3C_DYNAMIC_TILES)return 0;
    s->uploaded=(uint16_t)(s->uploaded+count);
    return 1;
}
uint16_t R46_M3C_MapRowWritten(r46_m3c_bank_t *s,uint16_t row)
{
    if(!s||s->pending_bank==R46_M3C_NO_BANK||
       s->uploaded!=R46_M3C_DYNAMIC_TILES||
       row<1u||row>R46_M3C_ROWS)return 0;
    const uint32_t bit=(uint32_t)1u<<(row-1u);
    if(s->mapped_rows&bit)return 0;
    s->mapped_rows|=bit;
    return 1;
}
uint16_t R46_M3C_CommitBank(r46_m3c_bank_t *s,
                           uint16_t blanked_vblank)
{
    if(!s||blanked_vblank!=1u||
       s->pending_bank==R46_M3C_NO_BANK||
       s->uploaded!=R46_M3C_DYNAMIC_TILES||
       s->mapped_rows!=R46_M3C_COMPLETE_ROWS)return 0;
    s->visible_bank=s->pending_bank;
    s->pending_bank=R46_M3C_NO_BANK;
    s->commits++;
    s->uploaded=0;
    s->mapped_rows=0;
    return 1;
}
typedef struct {
    void (*init)(r46_m3c_bank_t*);
    uint16_t (*stage)(r46_m3c_bank_t*,uint16_t);
    uint16_t (*writable)(const r46_m3c_bank_t*,uint16_t);
    uint16_t (*uploaded)(r46_m3c_bank_t*,uint16_t);
    uint16_t (*mapped)(r46_m3c_bank_t*,uint16_t);
    uint16_t (*commit)(r46_m3c_bank_t*,uint16_t);
} r46_m3c_bank_ops_t;
static const r46_m3c_bank_ops_t bank_ops={
    R46_M3C_BankInit,R46_M3C_StageBank,R46_M3C_BankWritable,
    R46_M3C_TilesUploaded,R46_M3C_MapRowWritten,R46_M3C_CommitBank
};
__attribute__((noinline))
const r46_m3c_bank_ops_t *R46_M3C_BankOps(void){return &bank_ops;}
__attribute__((noinline))
uint16_t R46_M3C_BankValidate(void)
{
    const r46_m3c_bank_ops_t *o=R46_M3C_BankOps();
    return (uint16_t)(o&&o->init&&o->stage&&o->writable&&o->uploaded&&
                      o->mapped&&o->commit&&R46_M3C_DYNAMIC_TILES==798);
}
#endif
