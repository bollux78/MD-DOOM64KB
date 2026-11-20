/* mdhost: headless Mega Drive runner on the Genesis Plus GX core (libretro objects linked in).
 * Scripted: run frames with buttons held, save screenshots (PPM), dump VRAM/CRAM/VSRAM/regs/68k RAM.
 * usage: mdhost ROM SCRIPT OUTDIR
 * script lines:  run N [buttons]   buttons: letters of U D L R A B C S (start)
 *                shot NAME          dump NAME          # comment
 * Also prints the frame time per frame of the game if asked: "fps" measures nothing (emulator speed is irrelevant). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "libretro.h"
extern unsigned char vram[0x10000], cram[0x80], vsram[0x80], reg[0x20];
extern unsigned char work_ram[0x10000];
static unsigned frame_w, frame_h, mask;
static uint16_t fb[512 * 512];
static void video_cb(const void *data, unsigned w, unsigned h, size_t pitch)
{
    if (!data) return;
    frame_w = w; frame_h = h;
    for (unsigned y = 0; y < h; y++) memcpy(fb + y * w, (const uint8_t *)data + y * pitch, w * 2);
}
static void audio_cb(int16_t l, int16_t r) { (void)l; (void)r; }
static size_t audio_batch_cb(const int16_t *d, size_t n) { (void)d; return n; }
static void poll_cb(void) {}
static int16_t input_cb(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
    (void)dev; (void)idx;
    if (port) return 0;
    if (id == RETRO_DEVICE_ID_JOYPAD_MASK) return (int16_t)mask;
    return (mask >> id) & 1;
}
static void log_cb(enum retro_log_level l, const char *fmt, ...) { (void)l; (void)fmt; }
static bool env_cb(unsigned cmd, void *data)
{
    switch (cmd) {
    case RETRO_ENVIRONMENT_GET_LOG_INTERFACE: ((struct retro_log_callback *)data)->log = log_cb; return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_RGB565;
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY: case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY: *(const char **)data = "."; return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        struct retro_variable *v = data;
        if (!strcmp(v->key, "genesis_plus_gx_system_hw")) { v->value = "mega drive / genesis"; return true; }
        v->value = NULL; return false;
    }
    case RETRO_ENVIRONMENT_GET_INPUT_BITMASKS: return true;
    default: return false;
    }
}
static void shot(const char *path)
{
    FILE *f = fopen(path, "wb");
    fprintf(f, "P6 %u %u 255\n", frame_w, frame_h);
    for (unsigned i = 0; i < frame_w * frame_h; i++) {
        const uint16_t p = fb[i];
        const uint8_t c[3] = { (uint8_t)((p >> 11) << 3), (uint8_t)(((p >> 5) & 63) << 2), (uint8_t)((p & 31) << 3) };
        fwrite(c, 1, 3, f);
    }
    fclose(f);
}
static void dump(const char *path)
{
    FILE *f = fopen(path, "wb");
    fwrite(vram, 1, sizeof vram, f); fwrite(cram, 1, sizeof cram, f); fwrite(vsram, 1, sizeof vsram, f);
    fwrite(reg, 1, sizeof reg, f); fwrite(work_ram, 1, sizeof work_ram, f);
    fclose(f);
}
int main(int argc, char **argv)
{
    if (argc < 4) { fprintf(stderr, "usage: mdhost ROM SCRIPT OUTDIR\n"); return 1; }
    retro_set_environment(env_cb);
    retro_set_video_refresh(video_cb);
    retro_set_audio_sample(audio_cb);
    retro_set_audio_sample_batch(audio_batch_cb);
    retro_set_input_poll(poll_cb);
    retro_set_input_state(input_cb);
    retro_init();
    struct retro_game_info gi = { argv[1], NULL, 0, NULL };
    FILE *rf = fopen(argv[1], "rb"); fseek(rf, 0, SEEK_END); gi.size = ftell(rf); fseek(rf, 0, SEEK_SET);
    void *rom = malloc(gi.size); fread(rom, 1, gi.size, rf); fclose(rf); gi.data = rom;
    if (!retro_load_game(&gi)) { fprintf(stderr, "load failed\n"); return 1; }
    retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);
    FILE *sf = strcmp(argv[2], "-") ? fopen(argv[2], "r") : stdin;
    char line[256]; unsigned long frame = 0;
    while (fgets(line, sizeof line, sf)) {
        char cmd[32] = "", arg[200] = "";
        int n = 0;
        if (sscanf(line, "%31s %d %199s", cmd, &n, arg) < 1 || cmd[0] == '#') continue;
        if (!strcmp(cmd, "run")) {
            mask = 0;
            for (char *p = arg; *p; p++) switch (*p) {
                case 'U': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_UP; break;
                case 'D': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_DOWN; break;
                case 'L': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_LEFT; break;
                case 'R': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_RIGHT; break;
                case 'A': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_Y; break;
                case 'B': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_B; break;
                case 'C': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_A; break;
                case 'S': mask |= 1 << RETRO_DEVICE_ID_JOYPAD_START; break;
            }
            for (int i = 0; i < n; i++, frame++) retro_run();
        } else {
            char path[512]; sscanf(line, "%31s %199s", cmd, arg);
            snprintf(path, sizeof path, "%s/%s", argv[3], arg);
            if (!strcmp(cmd, "shot")) shot(path);
            else if (!strcmp(cmd, "dump")) dump(path);
        }
    }
    printf("mdhost: %lu frames\n", frame);
    return 0;
}
