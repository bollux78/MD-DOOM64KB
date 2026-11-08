/* SGDK string ABI helpers for the original demo decoder/texture-name lookup.
 * memcpy/memset continue to come from the proven sub libc object. */
char *strncpy(char *d,const char *s,unsigned short n)
{char *r=d;while(n--){*d=*s;if(*s)s++;d++;}return r;}
char *strcpy(char *d,const char *s)
{char *r=d;while((*d++=*s++));return r;}
int strcmp(const char *a,const char *b)
{while(*a && *a==*b){a++;b++;}return (unsigned char)*a-(unsigned char)*b;}
int toupper(int c){return c>='a' && c<='z'?c-'a'+'A':c;}
extern void I_Error(const char *,...);
void exit(int code){(void)code;I_Error("SCD EXIT BEFORE BUDGET");for(;;){}}
