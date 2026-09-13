# Sensor status for interface integrations

Read `medusahc.sensor_error` to display sensor validation failures, and
`medusahc.last_error` for the explanation. The flag is latched when SET/DROP
rejects an ambiguous initial state, or when sensors do not confirm the result
of pick/drop within the configured timeout. It clears when the next valid
SET/DROP request is accepted (or Klipper restarts), alongside `last_error`.
Changing sensors by hand does not clear a recorded operation failure.

`current_tool` is live sensor information: -1 means all tools are parked,
0 and above identify the attached tool, and -2 means undetermined. An
undetermined state alone is not an error, either during a swap or while
manually rearranging hotends. `operation` describes the current procedure.
The `pin_watch` status and tool identification algorithm remain unchanged.

Sensor status does not diagnose electrical pin faults. PAUSE/RESUME recovery
uses the same flag to prevent a failed tool change from continuing the print;
see `recovery.md` for the printer-check sequence.
