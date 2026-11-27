/* ROM ordered-list interpreter. Generated streams trusted after offline
 * validation. Fixed sequences require no BSP or visibility-mask decisions.
 * Preserve group boundaries for renderer's early termination checks. */
#include <stdint.h>
#include <stddef.h>
#define FRL_STACK 128
typedef struct {
    const uint16_t *cursor,*stack[FRL_STACK];
    uint16_t sp;
    int16_t x,y;
    uint32_t tests,groups;
} FRListIter;
static void frl_begin(FRListIter *it,unsigned cell,int16_t x,int16_t y){
    it->cursor=sc_list_words+sc_list_offsets[sc_list_roots[cell]];
    it->sp=0;it->x=x;it->y=y;it->tests=it->groups=0;
}
static int frl_next(FRListIter *it,const uint16_t **ids,unsigned *count){
    const uint16_t *p=it->cursor;
    for(;;){
        unsigned cmd=*p++;
        if(cmd==0){
            if(!it->sp)return 0;
            p=it->stack[--it->sp];continue;
        }
        if(cmd==65535u){
            unsigned plane=*p++,a=*p++,b=*p++;
            const int16_t *q=sc_planes+4u*plane;
            int32_t sa=(int32_t)q[2]*((int32_t)it->y-q[1]);
            int32_t sb=(int32_t)q[3]*((int32_t)it->x-q[0]);
            if(sa>=sb){unsigned t=a;a=b;b=t;}
            if(it->sp>FRL_STACK-2)return -1;
            it->stack[it->sp++]=p;
            it->stack[it->sp++]=sc_list_words+sc_list_offsets[b];
            p=sc_list_words+sc_list_offsets[a];
            it->tests++;continue;
        }
        *count=cmd-1u;*ids=p;
        it->cursor=p+*count;it->groups++;
        return 1;
    }
}
