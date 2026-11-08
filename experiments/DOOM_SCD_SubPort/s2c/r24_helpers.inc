/* Included at end of original r24_romthings.c on both CPUs. */
uint16_t S2C_RomCount(void){return count;}
uint16_t S2C_RomDead(uint16_t i){if(i>=count)I_Error("S2C ROM INDEX");return !!dead(i);}
uint16_t S2C_RomDelay(uint16_t i){if(i>=count)I_Error("S2C ROM INDEX");return delays[i];}
void S2C_RomApply(uint16_t i,uint16_t d,uint16_t delay){
    if(i>=count || d>1)I_Error("S2C ROM APPLY");
    if(d)removed[i>>3]|=1u<<(i&7);else removed[i>>3]&=~(1u<<(i&7));delays[i]=delay;
}
