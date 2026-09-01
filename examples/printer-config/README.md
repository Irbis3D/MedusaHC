# Supplementary printer configuration examples

This folder contains supplementary Duender printer examples such as
`printer.cfg`, Eddy/BLTouch configuration, sensorless homing, ADXL, and an
example saved-variables file. These files are not installed automatically.

The canonical MedusaHC Core configuration installed into
`~/printer_data/config/MedusaHC/` is stored in `config/MedusaHC/` at the
repository root.

The supplied configuration is a **4-tool V-Front Duender example**. It is not a universal drop-in printer configuration. Before use, check all MCU identifiers, pins, axis limits, homing directions, TMC settings, PID values, probe offsets, dock coordinates, and parking positions.

The main MedusaHC files in the repository's `config/MedusaHC/` directory are:

- `MHC_config.cfg` — tool sensors, shared extruder hardware, heaters, fans, servo, and tool commands.
- `MHC_variables.cfg` — tool count, layout orientation, dock coordinates, cleaning/priming settings, and stored offsets.
- `MHC_macros.cfg` — the public macro interface and small compatibility wrappers for the Python controller.
- `medusahc.py` from `klippy/extras/` — pickup, drop, feeder, cleaning, priming, error handling, and offset logic.
- `pin_watch.py` from `klippy/extras/` — real-time tool sensor monitoring.

## Layout selection

Set `variable_tools_direction` in `config/MedusaHC/MHC_variables.cfg`:

- `1` — V-Front;
- `-1` — V-Back.

Then enter the actual X/Y coordinates for the installed docks. Pickup, drop, cleaning, and priming directions are derived automatically from `variable_tools_direction`. Parking coordinates in printer-level macros must still be adjusted separately.

## Probe selection

The example enables native Klipper Eddy support through `eddy_config.cfg`.

`bltouch.cfg` is an alternative backup configuration. Do not enable Eddy and BLTouch probe sections at the same time without resolving duplicate sections and pins. A BLTouch setup also requires manual review of `START_PRINT`, including the Eddy-specific `TAP_BASE_TOOL` call.

Tool-offset auto-calibration is intentionally not bundled into this base
configuration. Install the optional MedusaHC-Calibrate module when automatic
SexBall/contact, Eddy Tap Z, or Eddy Tap + EddySeek XYZ calibration is needed.

## External components

Some example sections depend on software installed separately:

- `pin_watch.py`, which must be copied to the Klipper `klippy/extras` directory;
- `medusahc.py`, which must be copied to the same Klipper `klippy/extras` directory;
- optional klipper-tmc-autotune;
- standard installation-specific files such as `mainsail.cfg` and `timelapse.cfg`.

`pin_watch.py` retains optional, disabled-by-default compatibility
synchronization with `klipper-toolchanger`. MedusaHC does not install or
require that plugin. A minimal optional configuration is documented in the
main project README.

Camera-assisted tool calibration is not currently included. A new native or
adapted implementation may be added later.
