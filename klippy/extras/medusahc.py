"""MedusaHC tool-change controller for Klipper.

The module replaces the long SET/DROP Jinja chains while retaining the normal
MedusaHC G-code names through ``MHC_macros.cfg``. It deliberately reads the
existing macro variables, so printer-specific geometry stays in
``MHC_variables.cfg`` instead of being hard-coded here.

Code map for maintainers
------------------------
* Configuration/status helpers read TOOL_CFG, GLOBAL_STATE, TOOL_STATE_n and
  TOOL_OFFSET.
* Sensor helpers read the existing ``pin_watch io`` Klipper object.
* Feeder and offset helpers contain the small reusable physical operations.
* ``_drop_active`` and ``_pick`` contain the dock motion paths.
* ``_after_pick`` contains printing-only prime and brush-cleaning behavior.
* ``cmd_MHC_*`` methods are the public Klipper G-code command handlers.

Normal tuning should be done in ``MHC_variables.cfg``. Edit motion formulas in
this file only when adapting MedusaHC to geometry that cannot be represented by
the existing coordinates, direction and speed variables. Motion strings use
Klipper feedrates in mm/min; user-facing speed variables are in mm/s and are
multiplied by 60 where needed.
"""

import logging


class _OperationPaused(Exception):
    """Internal control-flow signal after an active print was safely paused."""


class MedusaHC:
    """Own one MedusaHC operation at a time and expose Klipper commands."""

    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object("gcode")
        self.pin_watch_name = config.get("pin_watch", "pin_watch io")
        self.sensor_timeout = config.getfloat(
            "sensor_timeout", 0.50, minval=0.0, maxval=5.0
        )
        self.sensor_poll_interval = config.getfloat(
            "sensor_poll_interval", 0.01, above=0.0, maxval=0.25
        )
        self.pin_watch = None
        self.operation = "idle"
        self.target_tool = -1
        self.last_error = ""
        self.feeder_open = False
        self.layer = 0
        self.printer.register_event_handler("klippy:ready", self._handle_ready)
        self._init_timer = self.reactor.register_timer(self._initialize_timer)
        self._register_commands()

    def _register_commands(self):
        """Register internal MHC_* commands; legacy names live in the CFG."""
        commands = {
            "MHC_SET": (self.cmd_MHC_SET, "Pick or change to a MedusaHC tool"),
            "MHC_DROP": (self.cmd_MHC_DROP, "Park the active MedusaHC tool"),
            "MHC_OPEN": (self.cmd_MHC_OPEN, "Open the MedusaHC feeder"),
            "MHC_CLOSE": (self.cmd_MHC_CLOSE, "Close the MedusaHC feeder"),
            "MHC_CLEAN": (self.cmd_MHC_CLEAN, "Clean the active MedusaHC tool"),
            "MHC_ERROR": (self.cmd_MHC_ERROR, "Run MedusaHC error recovery"),
            "MHC_TOOL_OFFSET": (self.cmd_MHC_TOOL_OFFSET, "Apply a tool offset"),
            "MHC_ASSIGN_TOOL": (self.cmd_MHC_ASSIGN_TOOL, "Sync klipper-toolchanger"),
            "MHC_LAYER_SET": (self.cmd_MHC_LAYER_SET, "Update the current layer"),
            # Invisible compatibility commands for existing slicer and common
            # macro files. Unlike [gcode_macro] wrappers, these do not create
            # buttons in the Mainsail macro panel.
            "DROP": (self.cmd_MHC_DROP, "Park the active MedusaHC tool"),
            "TOOL_OFFSET_T": (
                self.cmd_MHC_TOOL_OFFSET, "Apply a MedusaHC tool offset"
            ),
            "LAYER_SET": (self.cmd_MHC_LAYER_SET, "Update the current layer"),
            "PRIME_FLAGS_SET": (
                self.cmd_PRIME_FLAGS_SET, "Mark first prime complete for all tools"
            ),
        }
        for name, (handler, description) in commands.items():
            self.gcode.register_command(name, handler, desc=description)

    def _handle_ready(self):
        """Resolve runtime objects and put the feeder servo in a known state."""
        self.pin_watch = self.printer.lookup_object(self.pin_watch_name, None)
        if self.pin_watch is None:
            raise self.printer.config_error(
                "[medusahc] could not find [%s]" % self.pin_watch_name
            )
        self.feeder_open = bool(int(self._global().get("feeder_open", 0)))
        # Keep the servo output disabled during MCU/config startup, then move it
        # directly to the configured closed position as soon as Klipper is
        # ready.  This avoids a hard-coded initial_angle briefly opening the
        # feeder before TOOL_CFG is available.
        close_angle = float(self._tool_cfg().get("servo_close_angle", 180.0))
        self._run("SET_SERVO SERVO=my_servo ANGLE=%s" % close_angle)
        self.reactor.update_timer(self._init_timer, self.reactor.monotonic() + 2.0)

    def _initialize_timer(self, eventtime):
        """Populate derived runtime values after all Klipper objects are ready."""
        try:
            cfg = self._tool_cfg()
            for name, multiplier in (
                ("fast_feedrate", float(cfg["fast_speed"]) * 60.0),
                ("slow_feedrate", float(cfg.get("slow_speed", 40.0)) * 60.0),
                ("clean_feedrate", float(cfg.get("clean_speed", 50.0)) * 60.0),
            ):
                self._set_compat(name, multiplier)
            tmc = self.printer.lookup_object("tmc2209 extruder", None)
            if tmc is not None:
                status = tmc.get_status(eventtime)
                current = float(status.get("run_current", 0.0))
                self._set_compat("e_cur", current)
                self._set_compat(
                    "e_cur_high", current * float(cfg.get("e_cur_high_mult", 1.7))
                )
            self._restore_saved_offsets()
            self._close()
            self.gcode.respond_info("MedusaHC controller initialized")
        except Exception:
            logging.exception("MedusaHC initialization failed")
            self.last_error = "Initialization failed; see klippy.log"
        return self.reactor.NEVER

    def _restore_saved_offsets(self):
        """Restore per-tool XYZ offsets previously stored by SAVE_VARIABLE."""
        saved = self.printer.lookup_object("save_variables", None)
        values = getattr(saved, "allVariables", {}) if saved is not None else {}
        offset_macro = self._macro_name("TOOL_OFFSET")
        for tool in range(self._tool_count()):
            for axis in ("x", "y", "z"):
                saved_name = "t%d_gcode_%s_offset" % (tool, axis)
                if saved_name not in values:
                    continue
                self._run(
                    "SET_GCODE_VARIABLE MACRO=%s VARIABLE=t%d_off_%s VALUE=%s"
                    % (offset_macro, tool, axis, float(values[saved_name]))
                )

    def get_status(self, eventtime):
        """Return a compact status dictionary for Klipper API consumers."""
        source = self._sensor_source()
        raw_state = getattr(source, "state", {}) or {}
        sensors = {}
        for name, value in raw_state.items():
            try:
                sensors[str(name)] = int(value)
            except (TypeError, ValueError):
                pass
        return {
            "operation": self.operation,
            "current_tool": self._current_tool(),
            "target_tool": self.target_tool,
            "last_error": self.last_error,
            "feeder_open": self.feeder_open,
            "layer": self.layer,
            "sensor_error": self._current_tool() == -2,
            "tool_count": self._tool_count(),
            "sensors": sensors,
        }

    # ---------------------------------------------------------------------
    # Existing MedusaHC configuration and sensor access
    # ---------------------------------------------------------------------

    def _macro_name(self, name):
        """Prefer the future hidden macro name while accepting legacy config."""
        candidates = (name,) if name.startswith("_") else ("_" + name, name)
        for candidate in candidates:
            if self.printer.lookup_object("gcode_macro %s" % candidate, None) is not None:
                return candidate
        raise self.printer.command_error(
            "MedusaHC requires [gcode_macro %s] or [gcode_macro _%s]"
            % (name, name)
        )

    def _macro(self, name):
        resolved = self._macro_name(name)
        obj = self.printer.lookup_object("gcode_macro %s" % resolved, None)
        if obj is None:
            raise self.printer.command_error(
                "MedusaHC requires [gcode_macro %s]" % resolved
            )
        return obj.variables

    def _tool_cfg(self):
        return self._macro("TOOL_CFG")

    def _global(self):
        return self._macro("GLOBAL_STATE")

    def _offsets(self):
        return self._macro("TOOL_OFFSET")

    def _sensor_source(self):
        if self.pin_watch is None:
            self.pin_watch = self.printer.lookup_object(self.pin_watch_name, None)
        return self.pin_watch

    def _current_tool(self):
        source = self._sensor_source()
        return int(getattr(source, "current_tool", -2)) if source else -2

    def _tool_count(self):
        return int(self._global().get("max_tool", 0))

    def _validate_tool(self, gcmd, tool):
        count = self._tool_count()
        if tool < 0 or tool >= count:
            raise gcmd.error("Tool T%d is outside configured range T0..T%d" % (tool, count - 1))

    def _run(self, script):
        self.gcode.run_script_from_command(script)

    def _set_compat(self, variable, value):
        global_macro = self._macro_name("GLOBAL_STATE")
        self._run(
            "SET_GCODE_VARIABLE MACRO=%s VARIABLE=%s VALUE=%s"
            % (global_macro, variable, value)
        )

    def _wait_moves(self):
        # M400 waits via Klipper's reactor, so button callbacks continue to run.
        self._run("M400")

    def _wait_for_tool(self, expected):
        if self._current_tool() == expected:
            return True
        deadline = self.reactor.monotonic() + self.sensor_timeout
        while self.reactor.monotonic() < deadline:
            wake = min(deadline, self.reactor.monotonic() + self.sensor_poll_interval)
            self.reactor.pause(wake)
            if self._current_tool() == expected:
                return True
        return self._current_tool() == expected

    def _begin(self, operation, target=-1):
        if self.operation != "idle":
            raise self.printer.command_error(
                "MedusaHC is busy: %s" % self.operation
            )
        self.operation = operation
        self.target_tool = target
        self.last_error = ""

    def _finish(self):
        self.operation = "idle"

    def _fail(self, message):
        self.last_error = message
        logging.error("MedusaHC: %s", message)
        stats = self.printer.lookup_object("print_stats", None)
        print_was_active = getattr(stats, "state", "") in ("printing", "paused")
        try:
            self._run("MHC_ERROR")
        finally:
            self._finish()
        if print_was_active:
            raise _OperationPaused(message)
        raise self.printer.command_error(message)

    def _is_printing(self):
        stats = self.printer.lookup_object("print_stats", None)
        return getattr(stats, "state", "") == "printing"

    def _heater_temperature(self, tool):
        name = "extruder" if tool == 0 else "extruder%d" % tool
        heater = self.printer.lookup_object(name, None)
        if heater is None:
            return 0.0
        status = heater.get_status(self.reactor.monotonic())
        return float(status.get("temperature", 0.0))

    def _motion_values(self, tool):
        """Resolve one tool's geometry and convert configured speeds."""
        cfg = self._tool_cfg()
        direction = int(cfg.get("tools_direction", 1))
        if direction not in (-1, 1):
            raise self.printer.command_error("TOOL_CFG.tools_direction must be 1 or -1")
        return {
            "x": float(cfg["x_t%d" % tool]),
            "y_safe": float(cfg["y_safe"]),
            "y_latch": float(cfg["y_latch"]),
            "y_prime": float(cfg["y_prime"]),
            "y_brush": float(cfg["y_brush"]),
            "x_shift": float(cfg["x_shift"]),
            "x_prime_shift": float(cfg["x_prime_shift"]),
            "accel": float(cfg["fast_accel"]),
            "feed": float(cfg["fast_speed"]) * 60.0,
            "slow_feed": float(cfg.get("slow_speed", 40.0)) * 60.0,
            "clean_feed": float(cfg.get("clean_speed", 50.0)) * 60.0,
            "direction": direction,
        }

    # ---------------------------------------------------------------------
    # Reusable physical operations
    # ---------------------------------------------------------------------

    def _old_accel(self):
        toolhead = self.printer.lookup_object("toolhead")
        return float(toolhead.get_status(self.reactor.monotonic())["max_accel"])

    def _home(self):
        self._run(self._macro_name("HOME_REQUEST"))

    def _open(self):
        """Release the feeder latch using its servo and extruder movement."""
        if self.feeder_open:
            return
        state = self._global()
        cfg = self._tool_cfg()
        high = float(state.get("e_cur_high", 0.0))
        base = float(state.get("e_cur", 0.0))
        accel = float(cfg["fast_accel"])
        old_accel = self._old_accel()
        e_open = float(cfg.get("e_open", -5.0))
        servo_angle = float(cfg.get("servo_open_angle", 90.0))
        self._run("""SET_STEPPER_ENABLE STEPPER=extruder ENABLE=1
SET_VELOCITY_LIMIT ACCEL={accel}
SET_SERVO SERVO=my_servo ANGLE={servo_angle}
G91
SET_TMC_CURRENT STEPPER=extruder CURRENT={high}
G1 E-0.3 F1000
G1 E0.3 F1000
G1 E-0.3 F1000
G1 E0.3 F1000
G1 E{e_open} F2500
G90
SET_VELOCITY_LIMIT ACCEL={old}
SET_TMC_CURRENT STEPPER=extruder CURRENT={base}""".format(
            high=high, accel=accel, servo_angle=servo_angle,
            e_open=e_open, old=old_accel, base=base
        ))
        self.feeder_open = True
        self._set_compat("feeder_open", 1)

    def _close(self):
        """Engage the feeder latch and restore its logical state."""
        cfg = self._tool_cfg()
        e_close = float(cfg.get("e_close", 3.0))
        servo_angle = float(cfg.get("servo_close_angle", 180.0))
        self._run("""SET_SERVO SERVO=my_servo ANGLE={servo_angle}
G91
G1 E{e_close} F6000
G90""".format(servo_angle=servo_angle, e_close=e_close))
        self.feeder_open = False
        self._set_compat("feeder_open", 0)

    def _apply_offset(self, tool, move=1):
        """Apply the stored XYZ correction for a selected hotend."""
        offsets = self._offsets()
        state = self._global()
        x = float(offsets.get("t%d_off_x" % tool, 0.0))
        y = float(offsets.get("t%d_off_y" % tool, 0.0))
        z = float(offsets.get("t%d_off_z" % tool, 0.0))
        self._run("SET_GCODE_OFFSET X=%s Y=%s Z=%s MOVE=%d" % (x, y, z, move))
        self.gcode.respond_info(
            "MHC_TOOL_OFFSET T%d: X=%s Y=%s Z=%s MOVE=%d" % (tool, x, y, z, move)
        )

    # ---------------------------------------------------------------------
    # Dock motion paths
    #
    # All X/Y formulas are expressed from the configured dock center. The
    # ``tools_direction`` multiplier mirrors the path for front/back layouts.
    # Keep the safety move before any latch movement when adapting this code.
    # ---------------------------------------------------------------------

    def _drop_active(self):
        """Move the currently attached hotend into its dock and verify it."""
        tool = self._current_tool()
        if tool == -1:
            self.gcode.respond_info("MHC_DROP: nothing installed")
            return
        if tool < 0 or tool >= self._tool_count():
            self._fail("MHC_DROP: ambiguous sensor state")
        v = self._motion_values(tool)
        d = v["direction"]
        old_accel = self._old_accel()
        # Change the coordinate transform without compensating motion over the
        # print. The active offset is applied again only after reaching safety.
        self._apply_offset(0, move=0)
        self._run("SET_GCODE_OFFSET X=0 Y=0 MOVE=0")
        self._run("""SET_VELOCITY_LIMIT ACCEL={accel}
G90
G1 Y{safe} X{xapproach} F{feed}""".format(
            accel=v["accel"], safe=v["y_safe"], xapproach=v["x"] + 10*d,
            feed=v["feed"]
        ))
        if not self.feeder_open:
            self._open()
        self._run("""M106 S255
G1 Y{brushapproach} F{feed}
G1 X{xprime} F{feed}
G1 Y{latchapproach} F{feed}
G1 X{xshift} F{feed}
G1 Y{latch} F{feed}
G1 X{x} F{slow}
G1 Y{safe} F{feed}
SET_VELOCITY_LIMIT ACCEL={old}""".format(
            safe=v["y_safe"], brushapproach=v["y_brush"] + 3*d,
            xprime=v["x"] - v["x_prime_shift"]*d,
            feed=v["feed"], latchapproach=v["y_latch"] + 8*d,
            xshift=v["x"] - v["x_shift"]*d, latch=v["y_latch"], x=v["x"],
            slow=v["slow_feed"], old=old_accel
        ))
        self._wait_moves()
        if not self._wait_for_tool(-1):
            self._fail("MHC_DROP: dock sensors did not confirm an empty toolhead")
        self.gcode.respond_info("MHC_DROP OK: T%d parked" % tool)

    def _pick(self, tool):
        """Collect one hotend from its dock and verify the sensor result."""
        v = self._motion_values(tool)
        d = v["direction"]
        old_accel = self._old_accel()
        self._apply_offset(0, move=0)
        self._run("SET_GCODE_OFFSET X=0 Y=0 MOVE=0")
        self._run("""SET_VELOCITY_LIMIT ACCEL={accel}
G90
G1 Y{safe} X{x} F{feed}""".format(
            accel=v["accel"], safe=v["y_safe"], x=v["x"], feed=v["feed"]
        ))
        if not self.feeder_open:
            self._open()
        self._run("""G1 Y{latch3} F{feed}
G1 Y{latch} F{slow}
G1 Y{latch03} F{slow}
G1 Y{latch} F{slow}
G1 X{xshift2} F{feed}
G1 X{xshift} F{slow}
G1 Y{latch5} F{slow}
G1 X{xshift_more} F{slow}
M106 S255""".format(
            feed=v["feed"],
            latch3=v["y_latch"] + 20*d, latch=v["y_latch"], latch03=v["y_latch"] - .1*d,
            slow=v["slow_feed"], xshift2=v["x"] - (v["x_shift"] - 4)*d,
            xshift=v["x"] - v["x_shift"]*d, latch5=v["y_latch"] + 5*d,
            xshift_more=v["x"] - (v["x_shift"] + 2)*d
        ))
        self._wait_moves()
        if not self._wait_for_tool(tool):
            self._fail("MHC_SET: sensors did not confirm T%d" % tool)
        self._close()
        self._after_pick(tool, v)
        self._run("SET_VELOCITY_LIMIT ACCEL=%s" % old_accel)
        self._run("M106 S0")
        self.gcode.respond_info("MHC_SET OK: T%d installed" % tool)

    def _after_pick(self, tool, v):
        """Prime, brush-clean and apply offsets after a successful pickup.

        Extrusion values come from TOOL_STATE_n. On a tool's first use during
        a print, the two dedicated short retracts replace the normal prime and
        cleaning retracts because the slicer has no matching unretract yet.
        """
        state = self._macro("TOOL_STATE_%d" % tool)
        first_prime_executed = False
        if self._is_printing() and self._heater_temperature(tool) > 190.0:
            self._run("G90\nG1 X%s F%s\nG1 Y%s F%s" % (
                v["x"] - v["x_prime_shift"] * v["direction"], v["feed"],
                v["y_prime"], v["feed"]))
            first_prime_enabled = int(state.get("first_prime_enabled", 1)) != 0
            if first_prime_enabled and int(state.get("first_prime_flag", 1)) == 0:
                amount = float(state.get("first_prime_amount", 0.0))
                speed = float(state.get("first_prime_speed", 1.0)) * 60.0
                self._run("G91\nG1 E%s F%s\nG90" % (amount, speed))
                state_macro = self._macro_name("TOOL_STATE_%d" % tool)
                self._run(
                    "SET_GCODE_VARIABLE MACRO=%s VARIABLE=first_prime_flag VALUE=1"
                    % state_macro
                )
                first_prime_executed = True
            amount = float(state.get("prime_amount", 0.0))
            speed = float(state.get("prime_speed", 1.0))
            retract = float(state.get(
                "first_prime_prime_retract", 0.2
            )) if first_prime_executed else float(state.get("prime_retract", 0.0))
            retract_speed = float(state.get("prime_retract_speed", 1.0))
            self._run("""G91
G1 E{e1} F{f1}
G1 E{e2} F{f2}
G1 E{e3} F{f3}
G1 E-{retract} F{rf}
G90""".format(
                e1=amount * .2, e2=amount * .3, e3=amount * .5,
                f1=speed * .5 * 60., f2=speed * .75 * 60., f3=speed * 60.,
                retract=retract, rf=retract_speed * 60.
            ))
        if self._is_printing() and int(state.get("clean_move", 1)) != 0:
            cmx = float(state.get("x_clean_move", 0.0))
            cmy = float(state.get("y_clean_move", 0.0))
            cmf = v["clean_feed"]
            # On a tool's first use the slicer has no matching tool-change
            # unretract queued. Use dedicated short retracts after both prime
            # and cleaning; later changes retain the normal retract values.
            retract = float(state.get(
                "first_prime_clean_retract", 0.1
            )) if first_prime_executed else float(state.get("clean_retract", 0.0))
            rf = float(state.get("clean_retract_speed", 1.0)) * 60.0
            d = v["direction"]
            ptfe = float(state.get("ptfe_clean_slow_speed", 12.5)) * 60.0
            self._run("""G90
G1 X{xprime} F{feed}
G1 Y{prime} F{feed}
G91
G1 X{xptfe} F{ptfe}
G1 Y{yptfe} F{feed}
G1 X{xptfe_back} F{feed}
G1 X{xptfe} F{ptfe}
G1 X{xbrush} F{feed}
G1 Y{ybrush} F{feed}
G1 X{cmx1} Y{cmy1} F{cmf}
G1 Y{cmy2} F{cmf}
G1 X{cmx2} Y{cmy1} F{cmf}
G1 Y{cmy2} F{cmf}
G1 X{cmx1} Y{cmy1} F{cmf}
G1 E-{retract} F{rf}
G90
G1 Y{safe} F{feed}""".format(
                xprime=v["x"]-v["x_prime_shift"]*d, prime=v["y_prime"], feed=v["feed"],
                xptfe=10*d, ptfe=ptfe, yptfe=6*d, xptfe_back=-10*d, xbrush=10*d,
                ybrush=v["y_brush"]-v["y_prime"]-8*d,
                cmx1=-cmx*d, cmy1=cmy*d, cmy2=-cmy*d, cmx2=cmx*d,
                cmf=cmf, retract=retract, rf=rf, safe=v["y_safe"]
            ))
            self._apply_offset(tool)
        else:
            self._run("G1 Y%s F%s" % (v["y_safe"], v["feed"]))
            self._apply_offset(tool)

    # ---------------------------------------------------------------------
    # Public MHC_* G-code handlers
    # ---------------------------------------------------------------------

    def cmd_MHC_SET(self, gcmd):
        """Pick T, parking another attached tool first when necessary."""
        tool = gcmd.get_int("T", None)
        if tool is None:
            raise gcmd.error("MHC_SET requires T=<number>")
        self._validate_tool(gcmd, tool)
        self._begin("changing", tool)
        try:
            self._set_compat("error_state", 0)
            self._set_compat("target_tool", tool)
            self._home()
            self._apply_offset(tool, move=0)
            direction = int(self._tool_cfg().get("tools_direction", 1))
            self._run("G91\nG1 %s F14000\nG90" % (("Y%s Z3" % (-2*direction)) if self._is_printing() else "Z1"))
            current = self._current_tool()
            if current == -2:
                self._fail("MHC_SET: ambiguous sensor state")
            if current == tool:
                self._apply_offset(tool)
                self.gcode.respond_info("MHC_SET: T%d already installed" % tool)
                return
            if current >= 0:
                self.operation = "dropping"
                self._drop_active()
            self.operation = "picking"
            self._pick(tool)
        except _OperationPaused as exc:
            self.gcode.respond_info("MedusaHC paused: %s" % exc)
        finally:
            if self.operation != "idle":
                self._finish()

    def cmd_MHC_DROP(self, gcmd):
        """Park the attached hotend, if any."""
        self._begin("dropping")
        try:
            self._home()
            self._drop_active()
        except _OperationPaused as exc:
            self.gcode.respond_info("MedusaHC paused: %s" % exc)
        finally:
            if self.operation != "idle":
                self._finish()

    def cmd_MHC_OPEN(self, gcmd):
        self._open()

    def cmd_MHC_CLOSE(self, gcmd):
        self._close()

    def cmd_MHC_CLEAN(self, gcmd):
        tool = self._current_tool()
        if tool < 0:
            self.gcode.respond_info("MHC_CLEAN: no tool installed")
            return
        self._home()
        v = self._motion_values(tool)
        state = self._macro("TOOL_STATE_%d" % tool)
        old_accel = self._old_accel()
        cmx = float(state.get("x_clean_move", 0.0))
        cmy = float(state.get("y_clean_move", 0.0))
        cmf = v["clean_feed"]
        ptfe = float(state.get("ptfe_clean_slow_speed", 12.5)) * 60.0
        d = v["direction"]
        self._run("""SET_VELOCITY_LIMIT ACCEL={accel}
G90
G1 Y{safe} F{feed}
G1 X{xprime} F{feed}
G1 Y{prime} F{feed}
G91
G1 X{xptfe} F{ptfe}
G1 Y{yptfe} F{feed}
G1 X{xptfe_back} F{feed}
G1 X{xptfe} F{ptfe}
G1 X{xbrush} F{feed}
G1 Y{ybrush} F{feed}
G1 X{cmx1} Y{cmy1} F{cmf}
G1 Y{cmy2} F{cmf}
G1 X{cmx2} Y{cmy1} F{cmf}
G1 Y{cmy2} F{cmf}
G1 X{cmx1} Y{cmy1} F{cmf}
G90
G1 Y{safe} F{feed}
SET_VELOCITY_LIMIT ACCEL={old}""".format(
            accel=v["accel"], safe=v["y_safe"], feed=v["feed"],
            xprime=v["x"] - v["x_prime_shift"]*d, prime=v["y_prime"],
            xptfe=10*d, ptfe=ptfe, yptfe=6*d, xptfe_back=-10*d,
            xbrush=10*d, ybrush=v["y_brush"]-v["y_prime"]-8*d,
            cmx1=-cmx*d, cmy1=cmy*d,
            cmy2=-cmy*d, cmx2=cmx*d, cmf=cmf, old=old_accel
        ))

    def cmd_MHC_ERROR(self, gcmd):
        """Move away from the docks and pause only when a print is active."""
        stats = self.printer.lookup_object("print_stats", None)
        state = getattr(stats, "state", "")
        if state in ("printing", "paused"):
            self._set_compat("error_state", 1)
            cfg = self._tool_cfg()
            safe = float(cfg["y_safe"]) + 50.0 * int(cfg.get("tools_direction", 1))
            self._run("G90\nG1 Y%s F6000\nPAUSE" % safe)
        else:
            self.gcode.respond_info("MHC_ERROR: no active print; printer was not paused")

    def cmd_MHC_TOOL_OFFSET(self, gcmd):
        tool = gcmd.get_int("T", None)
        if tool is None:
            raise gcmd.error("MHC_TOOL_OFFSET requires T=<number>")
        self._validate_tool(gcmd, tool)
        self._apply_offset(tool, gcmd.get_int("MOVE", 1, minval=0, maxval=1))

    def cmd_MHC_ASSIGN_TOOL(self, gcmd):
        tool = self._current_tool()
        if tool >= 0:
            self._run("INITIALIZE_TOOLCHANGER T=%d" % tool)
        else:
            self.gcode.respond_info("No tool installed; initialization deferred")

    def cmd_MHC_LAYER_SET(self, gcmd):
        layer = gcmd.get_int("L", None)
        if layer is None:
            return
        self.layer = layer
        self._set_compat("layer", layer)

    def cmd_PRIME_FLAGS_SET(self, gcmd):
        for tool in range(self._tool_count()):
            state_macro = self._macro_name("TOOL_STATE_%d" % tool)
            self._run(
                "SET_GCODE_VARIABLE MACRO=%s VARIABLE=first_prime_flag VALUE=1"
                % state_macro
            )


def load_config(config):
    """Klipper entry point for the ``[medusahc]`` config section."""
    return MedusaHC(config)
