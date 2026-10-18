#!/usr/bin/env python3
"""Exercise production heap audit against valid and corrupted allocator chains."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/i_genesisv.c').read_text();body=s.split('static void R28_VideoAudit(void)\n{',1)[1].split('\n#endif\n#else\nstatic uint16_t r20_video_copy',1)[0]
body=body.replace('    extern uint16_t _bend;','')
c='''#include <stdint.h>
#include <sys/mman.h>
#include <assert.h>
#define VIEWWINDOWWIDTH 38
#define VDP_DISPLAY_ROWS 28
#define _bend (*(uint16_t*)0xE0FFE400u)
static uint16_t r28_ptr,r28_header,r28_raw_free,r28_errors,r28_allocs,r28_before,r28_after,r28_copies,r28_uploads,r21_heap_at_end_free;
static uint16_t *r20_video_copy;
static void R28_VideoAudit(void) {
'''+body+'''
static void init(void) {
 *(uint16_t*)0xE0FFE400u=1283;
 *(uint16_t*)0xE0FFE902u=2131;
 *(uint16_t*)0xE0FFF154u=1194;
 *(uint16_t*)0xE0FFF5FEu=0;
 r20_video_copy=(uint16_t*)0xE0FFE904u;
 r28_allocs=1;r28_copies=2134;r28_uploads=2133;
 r28_before=3324;r28_after=1194;r21_heap_at_end_free=1194;
}
int main(void) {
 assert(mmap((void*)0xE0FFE000u,8192,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)-1);
 init();R28_VideoAudit();assert(r28_errors==0&&r28_header==2131&&r28_raw_free==1194);
 init();*(uint16_t*)0xE0FFE902u=2130;R28_VideoAudit();assert(r28_errors==(2|8));
 init();*(uint16_t*)0xE0FFE400u=1;R28_VideoAudit();assert(r28_errors==(1|4|8));
 init();r20_video_copy++;R28_VideoAudit();assert(r28_errors==4);
 init();r28_allocs=0;R28_VideoAudit();assert(r28_errors==16);
 init();r28_uploads=0;R28_VideoAudit();assert(r28_errors==32);
 init();r21_heap_at_end_free++;R28_VideoAudit();assert(r28_errors==8);
 init();*(uint16_t*)0xE0FFF154u=65534;R28_VideoAudit();assert(r28_errors==(1|8));
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(c)
 subprocess.run(['cc','-O2','-Wno-pointer-to-int-cast',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS production R28 audit: valid heap, free/used header, invalid size/bounds, missing pointer, allocation count, inactive upload and SDK mismatch')
