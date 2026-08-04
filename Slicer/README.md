# Slicer files

This folder contains OrcaSlicer examples for the supplied **4-tool** MedusaHC configuration.

- `Printer presets.zip` — 4-tool Duender/MedusaHC printer preset.
- `4rcaCube.3mf` — Generic 3mf 4-tool test project.
- `4rcaCube_orca_project.3mf` — OrcaSlicer project version of the test.

Open a 3MF as a **project** to inspect its printer, filament, and process settings.

Before printing:

- verify the bed size, printable height, tool count, start/end G-code, and all printer limits;
- configure the post-processing script path for the current computer;
- verify that the start G-code contains temperature parameters only for the configured tools;
- check that the selected parking positions are safe for V-Front or V-Back;
- confirm that the slicer tool order matches the physical `T0`, `T1`, `T2`, and `T3` assignments.

These files are examples and must be adapted to the actual printer, firmware, filament, and hotends.
