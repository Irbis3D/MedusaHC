# Configuration files

This folder contains the Klipper configuration example and the macros used by MedusaHC V0.2.

The supplied configuration is a **4-tool V-Front Duender example**. It is not a universal drop-in printer configuration. Before use, check all MCU identifiers, pins, axis limits, homing directions, TMC settings, PID values, probe offsets, dock coordinates, and parking positions.

The main MedusaHC files are:

- `MHC_config.cfg` — tool sensors, shared extruder hardware, heaters, fans, servo, and tool commands.
- `MHC_variables.cfg` — tool count, layout orientation, dock coordinates, cleaning/priming settings, and stored offsets.
- `MHC_macros.cfg` — pickup, drop, feeder, cleaning, priming, error handling, and offset logic.
- `pin_watch.py` from the `Scripts` folder — real-time tool sensor monitoring.

## Layout selection

Set `variable_tools_direction` in `MHC_variables.cfg`:

- `1` — V-Front;
- `-1` — V-Back.

Then enter the actual X/Y coordinates for the installed docks. Pickup, drop, cleaning, and priming directions are derived automatically from `variable_tools_direction`. Parking coordinates in printer-level macros must still be adjusted separately.

## Probe selection

The example enables native Klipper Eddy support through `eddy_config.cfg` and `eddy_features.cfg`.

`bltouch.cfg` is an alternative backup configuration. Do not enable Eddy and BLTouch probe sections at the same time without resolving duplicate sections and pins. A BLTouch setup also requires manual review of `START_PRINT`, including the Eddy-specific `TAP_BASE_TOOL` call.

## External components

Some active sections depend on software installed separately:

- klipper-toolchanger and its stock `tools_calibrate.py` for full X/Y/Z calibration;
- `pin_watch.py`, which must be copied to the Klipper `klippy/extras` directory;
- optional klipper-tmc-autotune;
- standard installation-specific files such as `mainsail.cfg` and `timelapse.cfg`.

`axiscope.cfg` is experimental. Its current macros have not been adapted to the V0.2 configuration structure and may not work without changes.
