#!/bin/bash
set -euxo pipefail

SCRIPT_PATH=$(dirname "$0")
SCRIPT_PATH=$(cd "$SCRIPT_PATH" && pwd)

# Run from QMK MSYS shell
# Location of keymap.c downloaded from Oryx
# Supposed to be under version control
KEYMAP=c:/projects/qmk_firmware/keyboards/ergodox_ez/keymaps/martin_colemak

if [ $(cd $KEYMAP; git status --porcelain keymap.c | grep ' M' | wc -l) -ne "0" ]; then
  echo "Unstaged changes, quitting"
  exit 1
fi

patch -N $KEYMAP/keymap.c $SCRIPT_PATH/trace_codes.patch

trap cleanup EXIT

function cleanup()
{
    pushd $KEYMAP
    git checkout keymap.c
    popd
}

python c:/projects/ergodox-compress-keymap/ergodox_compress_keymap.py
cd c:/projects/qmk_firmware
qmk compile -j 10 -kb ergodox_ez/glow -km martin_colemak
"C:/Program Files (x86)/Wally/Wally.exe" c:/projects/qmk_firmware/.build/ergodox_ez_glow_martin_colemak.hex
