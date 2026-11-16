#include <stddef.h>

int memcmp(const void *left, const void *right, size_t count)
{
    const unsigned char *a = left;
    const unsigned char *b = right;

    while (count-- != 0) {
        if (*a != *b)
            return (int)*a - (int)*b;
        ++a;
        ++b;
    }

    return 0;
}
