# MedusaHC changelog

This file summarizes the major public changes between MedusaHC releases. The project is still in beta, so every configuration must be reviewed and adapted to the actual printer before use.

## V0.2 Beta — 2026-08-04

V0.2 is a major mechanical, configuration, calibration, and repository update. It adds two supported dock orientations, refreshes the common tool hardware, replaces Eddy-ng with native Klipper Eddy tap support, and provides a new four-tool Duender example configuration.

### Mechanical layouts

- Added **V-Front** and **V-Back** dock layouts.
- V-Front places the docks in front of the print area. It provides more available space for tools and is generally easier to adapt to Voron-style and other CoreXY printers.
- V-Back places the docks behind the print area, closer to the XY motors. The shorter effective belt path reduces the influence of belt elasticity during docking and keeps the front of the printer open and easy to observe.
- Both layouts use the same main MedusaHC macros and common Base, Feeder, Hotend, and Toolhead parts.
- The full STEP assembly demonstrates five tools in the V-Front layout and four tools in the V-Back layout. The supplied Klipper configuration and OrcaSlicer files are configured for four tools.

### Duender mounting compatibility

- Current layout-specific mounts are designed for a Duender with **MGN9H rails on the XY axes**.
- MGN12H installations require the MedusaHC mounting system to be raised and the final geometry to be checked on the actual printer.
- V-Front can use adapters with the standard Duender front mounts or the included GN500 front mounts with a profile opening.
- For V-Back, the standard Duender front mounts remain installed while the docks attach to the rear profile with new mounting parts.
- V-Back requires the complete X axis to face rearward, the X rail to move to the opposite side of the profile, and the belts to run behind the X profile.
- The current V-Back toolhead belt clamp may require several belt teeth to be removed in the clamped section so the carriage can seat fully. A small amount of cyanoacrylate can be used to reduce the risk of slipping. This is a temporary assembly solution.
- Depending on the available rear clearance, the complete Z axis and bed may need to be shifted forward.

### Printable parts and reference files

- Added separate `V-Front Mounts` and `V-Back Mounts` folders.
- Added new front and rear dock mounts and reversed MGN9H X-axis mounts.
- Retained the left and right glue-on adapters for installing MedusaHC on the standard Duender front mounts.
- Added separate V-Front and V-Back main bin parts.
- Updated the common dock base, bin, mounting plate, feeder, toolhead, and carriage parts.
- Added updated nozzle-cleaning, PTFE-cleaning, priming, PTFE-routing, and wire-management parts.
- Added Bambu-style and TZ hotend body variants.
- Added an Eddy and ADXL-compatible MGN9H toolhead mount.
- Moved the servo and MG90S opening mechanism parts to the Feeder folder.
- Retained the SexBall mounting parts for contact-sensor calibration.
- Replaced the separate V0.1 STEP component files with one complete V0.2 reference assembly.
- Added V-Front and V-Back reference renders.

### Four-tool configuration

- Reworked the example configuration for a standard Duender with four front-mounted tools.
- Tools are numbered normally from `T0` through `T3` in both configuration variables and klipper-toolchanger definitions.
- Updated the example X dock positions and side clearances for the four-tool Duender layout.
- Added `variable_tools_direction` to select the dock orientation:
  - `1` for V-Front;
  - `-1` for V-Back.
- Pickup, drop, cleaning, and priming movement directions are derived automatically from `variable_tools_direction`.
- Users still need to enter the actual dock coordinates and separately configure all printer-level parking positions for the selected layout.
- Updated `printer.cfg`, sensorless homing, axis limits, and parking examples for the four-tool front layout.
- Retained BLTouch as an optional backup configuration. BLTouch users must manually review duplicate probe sections, pins, and the Eddy-specific `TAP_BASE_TOOL` call in `START_PRINT`.

### Feeder, cleaning, and priming behavior

- Updated the feeder `OPEN` and `CLOSE` movements to match the current mechanism.
- Updated extruder-current handling for the current feeder and motor arrangement.
- Reworked the cleaning and priming movement variables and macros for the new base system.
- Cleaning and priming positions now follow the same layout-relative geometry as the latch position.
- Updated per-tool priming, cleaning, retract, and first-use priming variables.
- Updated pause, resume, cancellation, tool-change recovery, and safe-movement behavior.

### Eddy probing and Z calibration

- Removed the Eddy-ng configuration and the modified `probe_eddy_ng.py` Klipper module.
- Added `eddy_config.cfg` for native Klipper Eddy current probe and tap support.
- Renamed and reworked the old Eddy feature macros as `eddy_features.cfg`.
- Added `TOOL_Z_CALIBRATION` for automatic Z-only calibration of `T0` through `T3` with native Eddy tap probing.
- T0 is used as the Z reference. Calculated tool Z offsets are saved to `saved_vars.cfg` and restored during initialization.
- The new Eddy mount position differs from the previous version. Probe installation height and all probing movements must be verified before automatic calibration.

### Full X/Y/Z tool calibration

- Full automatic tool-offset calibration now uses the stock **klipper-toolchanger** calibration system.
- SexBall, Nudge, and similar contact sensors supported by klipper-toolchanger can be used for X, Y, and Z calibration.
- The stock `tools_calibrate.py` is used without modification, allowing klipper-toolchanger to be updated normally.
- Added automatic transfer of the latest klipper-toolchanger calibration results into MedusaHC tool-offset variables and `saved_vars.cfg`.
- Updated `CALIBRATE_AND_SAVE_OFFSETS` to select each tool, reset the selected tool offset at the correct point in the loop, run calibration, and save the results.
- Without a contact calibration sensor, native Eddy tap can calibrate Z only. X and Y must be calibrated manually or by another suitable method.

### Axiscope status

- Retained `axiscope.cfg` as an experimental reference for camera-assisted XY calibration.
- The concept should still be usable, but the current Axiscope macros have not been adapted to the V0.2 configuration structure and are not verified for this release.

### OrcaSlicer and post-processing

- Added two updated four-tool OrcaSlicer 3MF projects.
- Added a separate four-tool Duender/MedusaHC printer preset.
- Removed the unused `EXTRUDER4_TEMP` and `EXTRUDER5_TEMP` parameters from the supplied start G-code.
- Removed computer-specific post-processing paths from the public 3MF projects.
- Retained `SET_FINISH.py` and added `SET_FINISH_Snapmaker_Orca.py`.
- Post-processing script paths must be configured locally by each user.

### Documentation and repository organization

- Expanded the main README with V-Front/V-Back selection, Duender mounting requirements, probe choices, calibration procedures, and known limitations.
- Added a short English README to every public project folder.
- Reorganized `Config` as `Macros` and replaced the old `3MF` folder with `Slicer`.
- Added dedicated `Images` and `STEP` folders.
- Marked STL, STEP, 3MF, PNG, and ZIP files as binary in Git attributes.
- Preserved the existing manual, BOM links, GPLv3 license, and affiliate purchasing links.

### Removed legacy files

- Removed the V0.1 OrcaSlicer projects from the current branch.
- Removed the separate V0.1 STEP component files from the current branch.
- Removed obsolete base, brush, nozzle-close, feeder, and toolhead models that were replaced by V0.2 parts.
- Removed `eddy_ng.cfg`, `eddy_ng_features.cfg`, and `probe_eddy_ng.py`.
- Removed the old optional `KlipperScreen.conf` example.

The V0.1 files remain available through the Git history at commit `0136d07`.
