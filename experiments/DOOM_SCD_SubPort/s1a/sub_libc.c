/* Minimal libc for the sub-CPU, with the SGDK signatures the engine headers declare. No includes. */
void memset(void *to, unsigned char value, unsigned short len) { unsigned char *p = to; while (len--) *p++ = value; }
void memcpy(void *to, const void *from, unsigned short len) { unsigned char *p = to; const unsigned char *q = from; while (len--) *p++ = *q++; }
