#!/usr/bin/env python3
"""Small host-only unit tests for the static RAM symbol parser."""
from ram_symbols import ram_symbols

SAMPLE = """
00020000 00000020 T rom_func
E0FF0000 0000AC00 b heap.0
E0FFAC00 00000410 B columnCache
E0FFB010 00000020 d local_data
E1000000 00000004 B outside_ram
E0FFB030 00000000 b zero
"""

def main():
    found = ram_symbols(SAMPLE)
    assert len(found) == 3, found
    assert found[0] == (0xAC00, 0xE0FF0000, "b", "heap.0"), found
    assert found[1] == (0x410, 0xE0FFAC00, "B", "columnCache"), found
    assert found[2] == (0x20, 0xE0FFB010, "d", "local_data"), found
    print("RAM symbol parser unit test: OK")

if __name__ == "__main__":
    main()
