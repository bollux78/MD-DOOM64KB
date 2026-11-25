/* Desktop correctness probe; no Mega Drive timing claims. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "render.h"
extern int r_pvs_off;
static uint8_t fb[FB_MAX];
int main(int argc,char **argv){
    unsigned total=0;
    r_pvs_off=1;
    for(int map=0;map<episode_map_count;map++){
    dread_map=&episode_maps[map];R_Init();
    for(int detail=0;detail<2;detail++){
        R_SetMode(detail?2:1,40,0);
        for(int i=0;i<32;i++){
            View v;v.x=(int32_t)map_start[0]*65536;v.y=(int32_t)map_start[1]*65536;
            if(i>=8){const MapSub *sub=&map_subs[(i*19)%map_counts[2]];const MapSeg *seg=&map_segs[sub->first];v.x=(int32_t)map_verts[seg->v1][0]*65536;v.y=(int32_t)map_verts[seg->v1][1]*65536;}
            v.z=map_sectors[map_subs[R_PointInSub(v.x>>16,v.y>>16)].sector].floor+41;
            v.angle=(uint16_t)(i*8192);
            memset(fb,0,sizeof fb);R_RenderView(&v,fb);total+=rstats.segs_drawn;
            if(i==0 && detail==0 && argc>1){
                char path[512];snprintf(path,sizeof path,"%s-E1M%d.ppm",argv[1],map+1);FILE *f=fopen(path,"wb");if(!f)return 2;
                fprintf(f,"P6 320 144 255\n");
                for(int y=0;y<144;y++)for(int x=0;x<320;x++){
                    uint8_t byte=FB_COL(fb,x/2)[(y/2)*4];int index=(x&1)?byte&15:byte>>4;
                    fwrite(pal_rgb_all[0][index],1,3,f);
                }fclose(f);
            }
        }
    }
    printf("E1M%d ",map+1);
    }
    printf("views=576 segs=%u source_columns=%d\n",total,map_sprites[0].w2);
    return total?0:3;
}
