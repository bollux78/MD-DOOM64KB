#include "../scene.h"

/* The ray is forward + a multiple of the perpendicular camera plane.
 * The DDA parameter is therefore already the perpendicular wall depth. */
static unsigned divide(unsigned numerator, unsigned denominator)
{
    __asm__ ("divu.w %1,%0" : "+d" (numerator) : "d" (denominator) : "cc");
    return (unsigned short)numerator;
}

static unsigned wall_color(char material, unsigned u, unsigned v, unsigned side)
{
    switch (material)
    {
        case '1':
            if ((v & 7u) == 0 || ((u + ((v & 8u) ? 8u : 0u)) & 15u) == 0)
                return 3;
            return (v & 7u) == 1 ? 6 - side : 5 - side;
        case '2':
            if (u < 2 || v < 2 || u >= 30 || v >= 30)
                return 7;
            return ((u ^ v) & 4u) == 0 ? 10 - side : 9 - side;
        default:
            if (u < 2 || u >= 30 || (v & 15u) == 0)
                return 3;
            if (v >= 12 && v < 17)
                return (u & 4u) ? 15 : 13;
            return 12 - side;
    }
}

void scd_render(unsigned char *tiles, int camera_x, int camera_y, unsigned heading)
{
    const int forward_x = cosine[heading];
    const int forward_y = cosine[(heading + 48u) & 63u];
    unsigned short row[VIEW_HEIGHT];

    for (unsigned y = 0; y < VIEW_HEIGHT; ++y)
        row[y] = (y / 4u) * TILES_W * 32u + (y % 4u) * 8u;

    for (int x = 0; x < VIEW_WIDTH; ++x)
    {
        const int plane = (x * 2 + 1 - VIEW_WIDTH) * 2;
        const int dx = forward_x - ((forward_y * plane) >> 8);
        const int dy = forward_y + ((forward_x * plane) >> 8);
        const int step_x = dx < 0 ? -1 : 1;
        const int step_y = dy < 0 ? -1 : 1;
        const unsigned delta_x = dx ? divide(65535u, dx * step_x) : 65535u;
        const unsigned delta_y = dy ? divide(65535u, dy * step_y) : 65535u;
        const unsigned frac_x = camera_x & 255;
        const unsigned frac_y = camera_y & 255;
        unsigned next_x = dx ? ((dx < 0 ? frac_x : 256u - frac_x) * delta_x) >> 8 : 65535u;
        unsigned next_y = dy ? ((dy < 0 ? frac_y : 256u - frac_y) * delta_y) >> 8 : 65535u;
        int cell_x = camera_x >> 8, cell_y = camera_y >> 8;
        unsigned depth, side;
        char material;

        do
        {
            side = next_y < next_x;
            if (side)
            {
                cell_y += step_y;
                depth = next_y;
                next_y += delta_y;
            }
            else
            {
                cell_x += step_x;
                depth = next_x;
                next_x += delta_x;
            }
            material = scene[cell_y][cell_x];
        } while (material == '0');

        if (depth < 16u)
            depth = 16u;
        const int height = divide(VIEW_HEIGHT * 256u, depth);
        const int top = (VIEW_HEIGHT - height) >> 1;
        const int bottom = top + height;
        const unsigned u = ((side ? camera_x + (((int)depth * dx) >> 8)
                                  : camera_y + (((int)depth * dy) >> 8)) >> 3) & 31u;
        const unsigned texture_step = divide(32u * 256u, height);
        unsigned texture_v = top < 0 ? -top * texture_step : 0;
        unsigned char *column = tiles + (x / 4) * 32 + (x & 3);

        for (int y = 0; y < VIEW_HEIGHT; ++y)
        {
            unsigned color;
            if (y < top)
                color = y < 12 ? 2 : 1;
            else if (y >= bottom)
                color = y >= 45 ? 8 : (y >= 35 ? 7 : 3);
            else
            {
                color = wall_color(material, u, texture_v >> 8, side);
                texture_v += texture_step;
            }
            const unsigned char pair = color * 17u;
            unsigned char *pixel = column + row[y];
            pixel[0] = pair;
            pixel[4] = pair;
        }
    }
}
