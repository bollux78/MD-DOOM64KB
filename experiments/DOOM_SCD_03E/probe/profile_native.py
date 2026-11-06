"""Profile the native renderer in the shipping 03E ROM without adding ROM hooks."""

from collections import Counter
import json

import r94_pcprofile as r94
import r117_profile as r117


def classify(function):
    name = function.split(".")[0]
    if name.startswith(("R60_WallColumn", "R113_WallColumn")):
        return "wall_kernels"
    if name.startswith(("R_DrawColumnFlat", "R95_Fill", "R_DrawPlanes", "R_DrawSpan")):
        return "flats_out_of_line"
    group = r117.category(function)
    if group.startswith("L_"):
        return "logic"
    return {
        "R_WALL_COLUMNS": "wall_setup_and_other_columns",
        "R_BSP_SEGS_FLATS": "bsp_segs_and_inline_flats",
        "R_SETUP": "render_setup",
        "R_SPRITES_MASKED": "sprites_and_masked",
        "PRESENT_HUD_VDP": "presentation_hud_vdp",
    }.get(group, group.lower())


class Sampler:
    def __init__(self, rom, elf):
        with rom.open("rb") as file:
            file.seek(0x78)
            self.vector = int.from_bytes(file.read(4), "big") & 0xffffff
        self.symbols = r94.text_symbols(elf)
        self.addresses = [address for address, _ in self.symbols]
        self.returns = r94.return_sites(elf)
        self.reset()

    def reset(self):
        self.categories = Counter()
        self.functions = Counter()

    def sample(self, debugger, registers):
        sp = int(registers[15 * 8:16 * 8], 16) & 0xffffff
        frame = debugger.readmem(sp, 70)
        pc = int.from_bytes(frame[2:6], "big") & 0xffffff
        fn = r94.find(self.symbols, self.addresses, pc)
        self.functions[fn] += 1
        if r117.is_helper(fn):
            for offset in range(6, len(frame), 4):
                address = int.from_bytes(frame[offset:offset + 4], "big") & 0xffffff
                if address in self.returns:
                    fn = r94.find(self.symbols, self.addresses, address)
                    break
        self.categories[classify(fn)] += 1

    def report(self, label, frames, vblanks):
        samples = self.categories.total()
        assert samples >= 100 and frames > 0 and vblanks > 0, (label, samples, frames, vblanks)
        print("NATIVE_PROFILE " + json.dumps({
            "window": label,
            "frames": frames,
            "vblanks": vblanks,
            "fps_ntsc": round(frames * 60 / vblanks, 3),
            "samples": samples,
            "categories": dict(self.categories.most_common()),
            "top_functions": dict(self.functions.most_common(20)),
        }), flush=True)


def registers_at_stop(debugger):
    debugger.cont()
    regs = debugger.req("g")
    return int(regs[17 * 8:18 * 8], 16) & 0xffffff, regs


def spawn(game, sampler, frames):
    game.breakpoint(game.frame)
    while game.next(game.frame, game.poll) == game.poll:
        game.pad(0)
    start = game.number("ticcount", 4)
    position = game.position()
    game.breakpoint(sampler.vector)
    for _ in range(frames):
        while True:
            pc, regs = registers_at_stop(game.g)
            if pc == game.frame:
                break
            if pc == sampler.vector:
                sampler.sample(game.g, regs)
            elif pc == game.poll:
                game.pad(0)
            else:
                assert pc == game.sound, f"unexpected spawn stop at {pc:06x}"
    end = game.number("ticcount", 4)
    assert game.position() == position and game.number("scd_available", 1) == 0
    sampler.report("E1M1 spawn", frames, end - start)
    game.breakpoint(sampler.vector, False)
    game.breakpoint(game.frame, False)
    game.next(game.poll)


def demo(game, sampler):
    """Use the same DEMO1 gametic range as the 03D capture script."""
    sampler.reset()
    ticker, finish = game.sym("G_Ticker"), game.frame
    game.g.req("qSupported")
    game.breakpoint(ticker)
    game.breakpoint(finish)
    game.breakpoint(game.error)
    game.breakpoint(game.sym("R116_End"))
    armed = False
    sampling = False
    frames = 0
    start = None
    while True:
        pc, regs = registers_at_stop(game.g)
        if pc == sampler.vector and sampling:
            sampler.sample(game.g, regs)
            continue
        if pc == ticker:
            if not armed:
                for name, value in (("scd_available", 0), ("r116_sel", 1), ("r116_norender", 1)):
                    assert game.g.req(f"M{game.sym(name):x},1:{value:02x}") == "OK"
                armed = True
            if game.number("_g_gametic", 4) >= 190:
                assert game.g.req(f"M{game.sym('r116_norender'):x},1:00") == "OK"
                game.breakpoint(ticker, False)
            continue
        assert pc == finish, f"demo stopped at {pc:06x} before profile completed"
        tic = game.number("_g_gametic", 4)
        if tic < 200:
            continue
        if start is None:
            assert tic == 200 and game.number("_g_gamemap") == 1, tic
            start = game.number("ticcount", 4)
            game.breakpoint(sampler.vector)
            sampling = True
            continue
        frames += 1
        if tic >= 260:
            assert tic == 260 and game.number("_g_gamemap") == 1, tic
            assert game.number("scd_available", 1) == 0
            sampler.report("DEMO1 gametics 200-260", frames, game.number("ticcount", 4) - start)
            break
