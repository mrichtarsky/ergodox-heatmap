# ergodox-heatmap

**Generate heatmap and statistics for your ErgoDox EZ typing. This is useful when getting started, both for finding issues with your keymap, and for motivation when you see your key counts ;)**

## Usage

- Works on Windows and macOS. But only `hid_listen` and the browser launching is OS-specific and can also be made to work on e.g. Linux.
- Requires keycode tracing added to your firmware:
```
patch keymap.c trace_codes.patch
```
- Enabling the debug console in `rules.mk`:
```
CONSOLE_ENABLE = yes
```
- Compiling and flashing your firmware
- Run [`launch.py`](https://github.com/mrichtarsky/ergodox-heatmap/blob/main/launch.py). This will log keycodes to `logs` directory and should be kept running.
- In `gen_heatmap.py`, adjust `LAYER_NAMES` for your map and change `BROWSER`
- At any time, run [`gen-heatmap.py`](https://github.com/mrichtarsky/ergodox-heatmap/blob/main/gen-heatmap.py) to see the current heat maps and statistics in the browser. For each layer, two heatmaps are shown:
  - Relative to all key presses
  - Relative to all key presses within the layer

- [`build.sh`](https://github.com/mrichtarsky/ergodox-heatmap/blob/main/build.sh) contains an example build script that automatically applies the patch, uses [ergodox-compress-keymap](https://github.com/mrichtarsky/ergodox-compress-keymap) for reducing the firmware size, compiles the firmware and runs Wally. Adjust paths for your setup.

- Thanks to [naps62 for the ErgoDox EZ svg](https://github.com/naps62/ergodox-heatmap-generator)!
- Note that this is not a key logger, since only key codes are logged. **That said, together with your keymap it becomes a key logger. So treat with the appropriate care.**
