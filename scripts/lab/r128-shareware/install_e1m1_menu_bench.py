"""Expose the existing E1M1 timedemo and mirror its final counters for the emulator."""
from pathlib import Path


def replace(source, before, after):
    if source.count(before) != 1:
        raise SystemExit(f"E1M1 benchmark anchor changed: {before!r}")
    return source.replace(before, after)


menu = Path("src/m_text.c")
source = replace(menu.read_text(), "  newgame = 0,",
                 "  benchmark_e1m1 = 0,\n  newgame,")
source = replace(source, "static const menuitem_t MainMenu[]=",
                 """static void M_R128BenchmarkE1M1(int16_t choice)
{
    UNUSED(choice);
    D_R88_SelectBenchmarkMap(0);
    M_ClearMenus();
    D_R50_BenchmarkStart();
}
static const menuitem_t MainMenu[]=""")
source = replace(source, '  {1,"New Game",  M_NewGame},',
                 '  {1,"Benchmark E1M1", M_R128BenchmarkE1M1},\n'
                 '  {1,"New Game",  M_NewGame},')
menu.write_text(source)

benchmark = Path("src/r22_benchmark.inc")
source = replace(benchmark.read_text(), "void I_BenchmarkShowResults(void)",
                 """/* Read by the emulator after the final measurement only. */
volatile uint32_t r128_ab_result[6]
    __attribute__((used, externally_visible, section(".data"))) = {0};

void I_BenchmarkShowResults(void)""")
source = replace(source, "    R21_PROBE_HEAP();",
                 """    extern int16_t _g_gamemap;
    r128_ab_result[1] = bench_frames;
    r128_ab_result[2] = elapsed;
    r128_ab_result[3] = bench_min_x10;
    r128_ab_result[4] = bench_max_x10;
    r128_ab_result[5] = (uint16_t)_g_gamemap;
    r128_ab_result[0] = 0x52414231u;
    R21_PROBE_HEAP();""")
benchmark.write_text(source)
