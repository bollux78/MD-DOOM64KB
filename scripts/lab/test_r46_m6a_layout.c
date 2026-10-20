/* R46 M6A host executable (not a Genesis ROM).
 * The pure contract is intentionally compiled with the host compiler
 * before any experimental SGDK recompilation or VDP programming.
 */
#include <stdint.h>
#include <stdio.h>
#include "r46_m6a_layout.h"
int main(void)
{
    uint8_t used[2048]={0};
    uint16_t count=0;
    if(!R46_M6A_LayoutValidate())return 1;
    for(uint16_t bank=0;bank<2;bank++){
        for(uint16_t row=1;row<=21;row++){
            for(uint16_t col=0;col<38;col++){
                uint16_t index=R46_M6A_DynamicTile(bank,col,row);
                if(index<112u||index>=1792u||used[index])return 2;
                used[index]=1;count++;
            }
        }
    }
    if(count!=1596u)return 3;
    for(uint16_t i=16;i<112;i++)if(used[i])return 4;
    for(uint16_t i=1792;i<2048;i++)if(used[i])return 5;
    printf("R46 M6A PASS: %u distinct dynamic tiles, font 16..111, bank0 150..947, bank1 986..1783, map E000\n",count);
    return 0;
}
