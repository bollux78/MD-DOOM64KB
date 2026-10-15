#!/usr/bin/env bash
set -euo pipefail
# Experimental, isolated toolchain build. Does NOT use the user's PC or runner.
# Marsdev upstream documents MARS_BUILD_DIR, make sgdk, and local (non-sudo) builds.
mkdir -p "$HOME/mars"
git clone --depth=1 https://github.com/andwn/marsdev.git "$RUNNER_TEMP/marsdev-src"
cd "$RUNNER_TEMP/marsdev-src"
export MARS_BUILD_DIR="$HOME/mars"
echo "Building m68k GCC and SGDK; cold cache may take a long time."
make m68k-toolchain -j2
make sgdk -j2
test -x "$HOME/mars/m68k-elf/bin/m68k-elf-gcc"
test -f "$HOME/mars/m68k-elf/lib/libmd.a"
test -f "$HOME/mars/m68k-elf/makefile.gen"
