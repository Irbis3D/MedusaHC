# PAUSE/RESUME migration for the Python controller

This release changes recovery after a failed tool change. Updating Core copies
the new `klippy/extras/medusahc.py`, but **does not edit your active Klipper
macros or restart Klipper**. Before using the new recovery path, update the
`PAUSE` and `RESUME` sections that your printer actually includes. Keep your
own parking coordinates, messages and other printer-specific actions.

## What to change in your macros

1. Back up your active `PAUSE` and `RESUME` sections. Confirm they use
   `rename_existing: BASE_PAUSE` and `rename_existing: BASE_RESUME`, respectively.
2. In `PAUSE`, first check `printer.pause_resume.is_paused`. If it is already
   true, return without moving, calling `BASE_PAUSE`, or changing
   `target_tool`. A second failed recovery must keep the original saved point.
3. For the first pause during a print, check the existing `error_state`. On a
   **manual** pause (`error_state == 0`), save
   `printer.medusahc.current_tool` to the existing `GLOBAL_STATE.target_tool`.
   On a **tool-change failure**, leave `target_tool` alone: `SET` or `DROP`
   already set it to the intended tool. Do not add a new `resume_tool` variable.
4. Call `BASE_PAUSE` **before** the printer-specific Z lift and XY parking
   moves. That saves the real print position for a manual pause. Core replaces
   this saved state with the pre-change state if a tool change failed.
5. In `RESUME`, while `printer.pause_resume.is_paused` is true, read the saved
   `target_tool` and call only `MHC_RESUME T={target_tool}`. Remove the old
   inline `G28`, `CLOSE`, `SET`, E moves, `BASE_RESUME` and tool-offset call from
   this branch; `MHC_RESUME` owns that sequence and calls `BASE_RESUME` only
   after successful preparation. Do not clear `error_state` before it runs.
6. Preserve your existing notification and non-print behavior as appropriate.
   Use the exact macro name on **your** printer: some configs use
   `GLOBAL_STATE`, others `_GLOBAL_STATE`. The `printer["gcode_macro ..."]`
   lookup and `SET_GCODE_VARIABLE MACRO=...` must refer to the same one.

The [complete PAUSE/RESUME example](../config/MedusaHC/macros_examples.cfg)
uses the standard Duender layout: `_GLOBAL_STATE` and parking at Y220/X0.
Adapt the steps above to your own macros if your printer uses different
coordinates or macro names.

After editing, restart Klipper while the printer is idle so the new Python
module and macros load together. An installer update alone leaves the active
macros unchanged; mixing the old `RESUME` macro with the new controller keeps
the old recovery behavior.

## Recovery behavior

The controller records the print's G-code state before normal SET/DROP motion.
An error during a print sets `GLOBAL_STATE.error_state`, latches
`medusahc.sensor_error` and `medusahc.last_error`, then invokes `PAUSE` once.
It no longer adds a Y move before the printer's park. Another failure while
already paused does not invoke `PAUSE` again or overwrite the saved point.
Manual sensor movement outside SET/DROP leaves `sensor_error` false;
`current_tool = -2` alone means the physical state is undetermined.

On a manual pause, `MHC_RESUME` compares the mounted tool with the saved
`target_tool`. If they match, it returns to the print position without XY
homing or priming. If they differ, or the pause followed a failed tool change,
it raises Z if necessary, homes XY, closes the feeder and runs the normal SET
path. The target tool is primed and brush-cleaned during this path even while
Klipper reports the print as paused, including when that tool is already
mounted. Preparation requires the target tool to be above 190 C. A failed SET
leaves the printer paused; it cannot reach `BASE_RESUME`.

For failed-change recovery, Core restores G-code modes, E position and tool
offset while keeping the head at the safe exit position after cleaning. It
does not return to the old tool's last print XY. The next commands in the
print file move the new tool to its destination. **The slicer's G-code must
set the correct Z before the first extrusion after a tool change.** The
multi-tool sample files checked for this release do so; check other slicer
profiles before relying on this path. For a manual pause, the head travels
above the saved print XY, then `BASE_RESUME VELOCITY=30` lowers it to the saved
layer. A Z jog through the printer menu does not overwrite that saved layer;
recovery raises a lowered Z before any XY homing.

Core currently copies Klipper's `gcode_move.saved_states["PAUSE_STATE"]` to
preserve the pre-change G-code and E context. This uses Klipper's internal
saved-state representation and should be checked when updating Klipper.

## Printer checks

With the actual slicer profile, verify in this order: manual PAUSE/RESUME with
the same tool; manual pause after changing the mounted tool; a failed pickup;
one more failed RESUME while still paused; then a successful recovery. Check
that repeat failure does not move away from the park, the recovered tool primes
and cleans, the next file move goes to the new tool's location without visiting
the old tool's print XY, and Z reaches the intended layer before extrusion.
