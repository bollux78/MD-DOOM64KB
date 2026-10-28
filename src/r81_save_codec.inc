/* Included in g_game.c: bounded streaming codec, no permanent scratch buffer.
 * Integer coding removes trailing zero bytes before zigzag/varint encoding.
 * Zero bytes are RLE encoded; all limits and CRC refer to compressed bytes. */
#include "r81_save_io.h"
static uint16_t R81_Crc(uint16_t crc,uint8_t byte){
    crc^=(uint16_t)byte<<8;
    for(uint16_t i=0;i<8u;i++)crc=(uint16_t)((crc<<1)^((crc&0x8000u)?0x1021u:0));
    return crc;
}
#ifndef R81_SAVE_HOST_TEST
uint8_t R81_SramRead(uint16_t logical){
    uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");
    R22_SRAM_ENABLE();
    uint8_t v=R22_SRAM_BYTE(R22_SRAM_BASE+1u+2UL*logical);
#if !defined(DOOM_R27_SRAM_FIXED)
    *(volatile uint8_t*)0x00A130F1UL=0;
#endif
    __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");return v;
}
void R81_SramWrite(uint16_t logical,uint8_t value){
    uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");
    R22_SRAM_ENABLE();R22_SRAM_BYTE(R22_SRAM_BASE+1u+2UL*logical)=value;
#if !defined(DOOM_R27_SRAM_FIXED)
    *(volatile uint8_t*)0x00A130F1UL=0;
#endif
    __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");
}
#endif
static void R81_Emit(r81_io_t *io,uint8_t value){
    if(io->error)return;
    if(io->pos>=io->limit){io->error=1;return;}
    if(io->mode==R81_WRITE)R81_SramWrite((uint16_t)(R81_SAVE_BASE+16u+io->pos),value);
    io->pos++;io->crc=R81_Crc(io->crc,value);
}
static uint8_t R81_Take(r81_io_t *io){
    if(io->error || io->pos>=io->limit){io->error=1;return 0;}
    uint8_t v=R81_SramRead((uint16_t)(R81_SAVE_BASE+16u+io->pos++));
    io->crc=R81_Crc(io->crc,v);return v;
}
static void R81_Flush(r81_io_t *io){
    if(io->zero_run){R81_Emit(io,0);R81_Emit(io,io->zero_run);io->zero_run=0;}
}
static uint8_t R81_Byte(r81_io_t *io,uint8_t value){
    if(io->mode>=R81_LOAD){
        if(io->zero_run){io->zero_run--;return 0;}
        value=R81_Take(io);
        if(!value){uint8_t count=R81_Take(io);if(!count)io->error=1;else io->zero_run=(uint8_t)(count-1u);}
        return value;
    }
    if(!value){if(++io->zero_run==255u)R81_Flush(io);}
    else{R81_Flush(io);R81_Emit(io,value);}
    return value;
}
uint32_t R81_U(r81_io_t *io,uint32_t value){
    if(io->mode<R81_LOAD){
        uint32_t original=value;
        do{uint8_t b=(uint8_t)(value&127u);value>>=7;if(value)b|=128u;R81_Byte(io,b);}while(value&&!io->error);
        return original;
    }
    value=0;
    for(uint16_t n=0;n<5u;n++){
        uint8_t b=R81_Byte(io,0);if(n==4u && (b&0xf0u)){io->error=1;return 0;}
        value|=(uint32_t)(b&127u)<<(n*7u);if(!(b&128u))return value;
    }
    io->error=1;return 0;
}
int32_t R81_N(r81_io_t *io,int32_t value){
    if(io->mode<R81_LOAD){
        int32_t original=value;
        uint16_t n=0;uint32_t u=(uint32_t)value;
        if(u)while(n<3u && !(u&255u)){value>>=8;u=(uint32_t)value;n++;}
        uint32_t z=((uint32_t)value<<1)^(uint32_t)(value>>31);
        uint8_t first=(uint8_t)((z&31u)<<2)|n;
        z>>=5;if(z)first|=128u;R81_Byte(io,first);if(z)R81_U(io,z);return original;
    }
    uint8_t first=R81_Byte(io,0);uint16_t n=first&3u;
    uint32_t z=(first>>2)&31u;
    if(first&128u){uint32_t high=R81_U(io,0);if(high>0x07ffffffUL)io->error=1;z|=high<<5;}
    int32_t q=(int32_t)((z>>1)^(0u-(z&1u)));
    value=(int32_t)((uint32_t)q<<(8u*n));
    if((value>>(8u*n))!=q)io->error=1;
    return value;
}
int32_t R81_GetField(const void *object,const r81_field_t *f){
    const uint8_t *p=(const uint8_t*)object+f->offset;
    if(f->size==1u){int8_t v;memcpy(&v,p,1);return v;}
    if(f->size==2u){int16_t v;memcpy(&v,p,2);return v;}
    int32_t v;memcpy(&v,p,4);return v;
}
static void R81_PutField(void *object,const r81_field_t *f,int32_t v){
    uint8_t *p=(uint8_t*)object+f->offset;
    if(f->size==1u){int8_t x=(int8_t)v;memcpy(p,&x,1);}
    else if(f->size==2u){int16_t x=(int16_t)v;memcpy(p,&x,2);}
    else memcpy(p,&v,4);
}
void R81_Fields(r81_io_t *io,void *object,const r81_field_t *fields,uint16_t count){
    for(uint16_t k=0;k<count;k++)for(uint16_t j=0;j<fields[k].count;j++){
        r81_field_t f=fields[k];f.offset=(uint16_t)(f.offset+j*f.size);
        if(f.size!=1u && f.size!=2u && f.size!=4u){io->error=1;return;}
        int32_t v=R81_N(io,io->mode<R81_LOAD?R81_GetField(object,&f):0);
        if(io->mode>=R81_LOAD){
            if((f.size==1u && (v< -128 || v>127)) || (f.size==2u && (v< -32768L || v>32767L))){io->error=1;return;}
            R81_PutField(object,&f,v);
        }
    }
}
uint16_t R81_ObjectId(r81_io_t *io,const mobj_t *object){
    if(!object)return 0;
    for(uint16_t i=0;i<io->object_count;i++)if(io->objects[i]==object)return (uint16_t)(i+1u);
    /* Removed/untracked objects are deliberately not persisted as pointers. */
    return 0;
}
uint16_t R81_SectorId(r81_io_t *io,const sector_t *sector){
    if(!sector)return 0;
    int32_t n=sector-_g_sectors;
    if(n<0 || n>=io->sectors){io->error=1;return 0;}return (uint16_t)(n+1);
}
