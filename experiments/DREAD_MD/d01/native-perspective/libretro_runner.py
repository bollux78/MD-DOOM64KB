"""Run the R128 menu benchmark on Genesis Plus GX and save the real result screen."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from PIL import Image, ImageDraw


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                ("size", C.c_size_t), ("meta", C.c_char_p)]


ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class Emulator:
    def __init__(self, core, rom):
        self.pad = set()
        self.pixel_format = 0
        self.capture = False
        self.screen = None
        self.core = C.CDLL(str(core.resolve()))
        callbacks = (
            ("environment", ENV, self.environment),
            ("video_refresh", VIDEO, self.video),
            ("audio_sample", AUDIO, lambda left, right: None),
            ("audio_sample_batch", BATCH, lambda data, frames: frames),
            ("input_poll", POLL, lambda: None),
            ("input_state", INPUT, lambda port, device, index, button:
             int(port == 0 and device == 1 and button in self.pad)),
        )
        self.callbacks = []
        for name, cb_type, fn in callbacks:
            cb = cb_type(fn)
            self.callbacks.append(cb)
            getattr(self.core, "retro_set_" + name)(cb)
        self.core.retro_init()
        self.core.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        self.rom_bytes = C.create_string_buffer(rom.read_bytes())
        game = GameInfo(str(rom.resolve()).encode(), C.cast(self.rom_bytes, C.c_void_p),
                        C.sizeof(self.rom_bytes) - 1, None)
        if not self.core.retro_load_game(C.byref(game)):
            raise RuntimeError(f"Could not load {rom}")
        if self.core.retro_get_region() != 0:
            raise RuntimeError("Expected NTSC")
        self.core.retro_set_controller_port_device(0, 1)
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.restype = C.c_size_t
        if self.core.retro_get_memory_size(2) != 65536:
            raise RuntimeError("Expected 64 KiB of Mega Drive work RAM")
        self.ram = self.core.retro_get_memory_data(2)
        if not self.ram:
            raise RuntimeError("Missing work RAM pointer")

    def environment(self, command, data):
        if command == 10:  # RETRO_ENVIRONMENT_SET_PIXEL_FORMAT
            self.pixel_format = C.cast(data, C.POINTER(C.c_int))[0]
            return self.pixel_format in (0, 1, 2)
        if command == 3:  # RETRO_ENVIRONMENT_GET_CAN_DUPE
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        return False

    def video(self, data, width, height, pitch):
        if self.capture and data:
            self.screen = (C.string_at(data, height * pitch), width, height, pitch,
                           self.pixel_format)

    def step(self, count, button=None, capture=False):
        self.pad = {button} if button is not None else set()
        self.capture = capture
        for _ in range(count):
            self.core.retro_run()
        self.capture = False

    def screenshot(self):
        raw, width, height, pitch, fmt = self.screen
        dtype = np.uint32 if fmt == 1 else np.uint16
        pixels = np.frombuffer(raw, dtype=dtype).reshape(height, pitch // np.dtype(dtype).itemsize)
        pixels = pixels[:, :width].astype(np.uint32)
        if fmt == 1:
            channels = ((pixels >> 16) & 255, (pixels >> 8) & 255, pixels & 255)
        elif fmt == 2:
            channels = ((pixels >> 11) * 255 // 31, ((pixels >> 5) & 63) * 255 // 63,
                        (pixels & 31) * 255 // 31)
        else:
            channels = (((pixels >> 10) & 31) * 255 // 31, ((pixels >> 5) & 31) * 255 // 31,
                        (pixels & 31) * 255 // 31)
        return Image.fromarray(np.stack(channels, axis=2).astype(np.uint8))

    def result(self, offset, raw_bg=False):
        raw = C.string_at(self.ram + offset, 32 if raw_bg else 24)
        marker = b"RAB2" if raw_bg else b"RAB1"
        swapped = marker[1::-1] + marker[3:1:-1]
        if raw[:4] == swapped:
            words = bytearray(raw)
            words[::2], words[1::2] = raw[1::2], raw[::2]
            raw = words
        if raw[:4] != marker:
            return None
        _, frames, vblanks, min_fps_x10, max_fps_x10, level = struct.unpack_from(">6I", raw)
        if level != 1 or not frames or not vblanks:
            raise RuntimeError(f"Invalid E1M1 result: {frames}, {vblanks}, map {level}")
        result = {"frames": frames, "vblanks": vblanks, "seconds": vblanks / 60,
                "fps": frames * 60 / vblanks, "min_fps_1s": min_fps_x10 / 10,
                "max_fps_1s": max_fps_x10 / 10}
        if raw_bg:
            uploads, raw_frames = struct.unpack_from(">2I", raw, 24)
            if not raw_frames or not uploads or uploads > 377 * raw_frames:
                raise RuntimeError(f"Invalid raw BG totals: {uploads} uploads / {raw_frames} frames")
            result.update(tile_uploads=uploads, raw_frames=raw_frames,
                          tile_uploads_per_frame=uploads / raw_frames)
        return result

    def close(self):
        self.core.retro_unload_game()
        self.core.retro_deinit()

