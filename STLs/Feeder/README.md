# Feeder parts

This folder contains the printable parts for the hotend-side feeder and its servo-assisted opening mechanism.

## Lever-driven opener update

The servo opener now uses two linked levers with two 693-2RS bearings at the joints instead of an eccentric cam. Removing this sliding contact makes the mechanism move more freely and gives it a more positive, repeatable opening action. The revised servo position also keeps it from protruding above the feeder, reducing its influence on system resonances.

Use the small servo horn supplied with the servo—the one with the short rounded arm and mounting holes. Cut away the rest of the horn, glue the remaining section into the printed lever, and optionally secure it with the original servo screw.

The new linkage makes the servo rotate in the opposite direction. Reconfigure and verify the open and closed servo angles before operating the feeder. Move the mechanism slowly during initial setup and make sure it reaches both positions without binding or over-travel.

Some parts received major mechanical changes, while others only gained minor improvements such as rounded edges. Reprinting the complete feeder set is recommended: there are relatively few parts, and the feeder must be disassembled for the upgrade anyway.

The mechanism must move freely without excessive play. Print quality, bearing and pin alignment, spring selection, and surface finishing directly affect reliable opening and closing. Refer to [`MedusaHC_Feeder_Lever_MOD.step`](../../STEP/MedusaHC_Feeder_Lever_MOD.step) to confirm orientation and hardware placement. This separate assembly documents the experimental feeder; it has not yet been incorporated into the main MedusaHC STEP assembly.
