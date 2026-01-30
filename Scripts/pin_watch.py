# klippy/extras/pin_watch.py
#
# - Computes tool state from pin events (e, t0..tN) and exposes it as:
#     printer["pin_watch <name>"].current_tool
# - Does NOT write GLOBAL_STATE.
# - Optional toolchanger sync:
#     * While printing: only INITIALIZE_TOOLCHANGER when ct >= 0 (never UNSELECT)
#     * While not printing: ct >= 0 -> INITIALIZE_TOOLCHANGER, else -> UNSELECT_TOOL
# - All gcode executed only via gcode.run_script_from_command(...)
# - All exceptions inside callbacks/timers are caught (won't shutdown Klipper)

import logging

_BUSY_STATUSES = ("changing", "initializing")


class PinWatch:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.name = config.get_name().split(" ", 1)[-1]

        self.gcode = self.printer.lookup_object("gcode")
        self.buttons = self.printer.load_object(config, "buttons")

        self.toolchanger_name = config.get("toolchanger", "toolchanger")
        self.sync_toolchanger = int(config.get("sync_toolchanger", 1)) != 0
        self.verbose = int(config.get("verbose", 0)) != 0

        # Collapse bursts: schedule compute after assign_delay seconds from last edge.
        # Use 0.0 for immediate.
        self.assign_delay = float(config.get("assign_delay", 0.0))

        # Internal pin states (0/1). Labels: e, t0, t1, ...
        self.state = {}
        self.pin_by_label = {}
        self.t_indices = set()

        # Exposed status field
        self.current_tool = -2  # -2 unknown/error, -1 unmounted, >=0 tool index

        # One-shot compute timer (re-armed on each edge)
        self._compute_timer = None
        self._pending_reason = "startup"

        # Toolchanger sync deferral timer
        self._pending_tc_ct = None
        self._tc_timer = None

        opts = list(config.get_prefix_options("pin_"))
        if not opts:
            raise config.error("pin_watch: no pins found. Add pin_<name>: <pin> options.")

        for opt in opts:
            label = opt[len("pin_"):]  # pin_t0 -> t0
            pin_str = str(config.get(opt)).strip()
            self.pin_by_label[label] = pin_str

            if label not in self.state:
                self.state[label] = 0

            ti = self._parse_t_index(label)
            if ti is not None:
                self.t_indices.add(ti)

            self.buttons.register_debounce_button(pin_str, self._make_callback(label), config)

        if self.verbose:
            self._info(
                "pin_watch %s: configured %d pin(s): %s"
                % (
                    self.name,
                    len(opts),
                    ", ".join(["%s=%s" % (l, self.pin_by_label[l]) for l in sorted(self.pin_by_label)]),
                )
            )

        # Initial compute
        self._schedule_compute("startup", 0.0)

    # --- status export for Jinja ---
    def get_status(self, eventtime):
        return {"current_tool": int(self.current_tool)}

    def _parse_t_index(self, label):
        if not label.startswith("t"):
            return None
        try:
            return int(label[1:])
        except Exception:
            return None

    def _tool_count(self):
        if not self.t_indices:
            return 0
        return max(self.t_indices) + 1

    def _make_callback(self, label):
        def _cb(eventtime, state):
            try:
                s = int(state)
                if self.state.get(label, None) == s:
                    return
                self.state[label] = s
                if self.verbose:
                    self._info("pin_watch %s: %s -> %d (t=%.6f)" % (self.name, label, s, eventtime))
                self._schedule_compute(label, self.assign_delay)
            except Exception:
                logging.exception("pin_watch %s: exception in pin callback (%s)", self.name, label)
                try:
                    self._info("pin_watch %s: ERROR in callback (%s) - see klippy.log" % (self.name, label))
                except Exception:
                    pass

        return _cb

    # --- compute algo (same as your macro) ---
    def _compute_current_tool(self):
        N = self._tool_count()
        if N < 1:
            return -2, (N, None, None, None, 1)

        ex = int(self.state.get("e", 0))
        bad = 0
        if ex not in (0, 1):
            bad = 1

        S = 0
        empties = 0
        empty_idx = -1

        for i in range(N):
            occ = int(self.state.get("t%d" % i, 0))
            if occ not in (0, 1):
                bad = 1
            S += occ
            if occ == 0:
                empties += 1
                empty_idx = i

        if bad == 1:
            ct = -2
        elif ex == 0 and S == N:
            ct = -1
        elif ex == 1 and S == (N - 1) and empties == 1:
            ct = empty_idx
        else:
            ct = -2

        return ct, (N, ex, S, empties, bad)

    # --- scheduling compute (simple, reliable) ---
    def _schedule_compute(self, reason, delay):
        self._pending_reason = reason

        # cancel previous timer and arm a new one (collapse bursts)
        if self._compute_timer is not None:
            try:
                self.reactor.unregister_timer(self._compute_timer)
            except Exception:
                pass
            self._compute_timer = None

        when = self.reactor.monotonic() + max(0.0, float(delay))
        self._compute_timer = self.reactor.register_timer(self._compute_timer_cb, when)

    def _compute_timer_cb(self, eventtime):
        self._compute_timer = None
        try:
            ct, dbg = self._compute_current_tool()
            self.current_tool = int(ct)

            N, ex, S, empties, bad = dbg
            self._info(
                "pin_watch %s: APPLY current_tool=%d (reason=%s N=%s ex=%s S=%s empties=%s bad=%s)"
                % (
                    self.name,
                    self.current_tool,
                    str(self._pending_reason),
                    str(N),
                    str(ex),
                    str(S),
                    str(empties),
                    str(bad),
                )
            )
            if self.sync_toolchanger:
                self._request_toolchanger_sync(self.current_tool)
        except Exception:
            logging.exception("pin_watch %s: exception in compute/apply", self.name)
            try:
                self._info("pin_watch %s: ERROR in compute/apply - see klippy.log" % self.name)
            except Exception:
                pass
        return self.reactor.NEVER

    # --- toolchanger sync ---
    def _get_toolchanger(self):
        try:
            return self.printer.lookup_object(self.toolchanger_name, None)
        except Exception:
            return None

    def _toolchanger_busy(self):
        tc = self._get_toolchanger()
        st = getattr(tc, "status", None) if tc else None
        return st in _BUSY_STATUSES

    def _is_printing(self):
        ps = self.printer.lookup_object("print_stats", None)
        st = getattr(ps, "state", "") if ps else ""
        return st == "printing"

    def _run_cmd(self, line):
        # your rule: ONLY this way
        self.gcode.run_script_from_command(line)

    def _request_toolchanger_sync(self, ct):
        # Printing: only initialize for ct>=0, never unselect
        if self._is_printing():
            if ct >= 0:
                self._sync_toolchanger_or_defer(ct)
            else:
                if self.verbose:
                    self._info("pin_watch %s: PRINTING -> skip UNSELECT (ct=%d)" % (self.name, int(ct)))
            return

        # Not printing: full mirror
        self._sync_toolchanger_or_defer(ct)

    def _sync_toolchanger_or_defer(self, ct):
        # If busy, defer with a timer (no gcode spam)
        if self._toolchanger_busy():
            self._pending_tc_ct = int(ct)
            if self._tc_timer is None:
                when = self.reactor.monotonic() + 0.1
                self._tc_timer = self.reactor.register_timer(self._tc_timer_cb, when)
            if self.verbose:
                tc = self._get_toolchanger()
                st = getattr(tc, "status", None) if tc else None
                self._info("pin_watch %s: toolchanger busy (status=%s) -> defer" % (self.name, str(st)))
            return
        self._do_toolchanger_sync(int(ct))

    def _tc_timer_cb(self, eventtime):
        self._tc_timer = None
        try:
            if self._pending_tc_ct is None:
                return self.reactor.NEVER

            # Still busy? re-arm timer (still no gcode spam)
            if self._toolchanger_busy():
                when = self.reactor.monotonic() + 0.1
                self._tc_timer = self.reactor.register_timer(self._tc_timer_cb, when)
                return self.reactor.NEVER

            ct = int(self._pending_tc_ct)
            self._pending_tc_ct = None
            self._do_toolchanger_sync(ct)
        except Exception:
            logging.exception("pin_watch %s: exception in tc timer", self.name)
            try:
                self._info("pin_watch %s: ERROR in toolchanger sync - see klippy.log" % self.name)
            except Exception:
                pass
        return self.reactor.NEVER

    def _do_toolchanger_sync(self, ct):
        # IMPORTANT: this runs only when toolchanger not busy (or when user forces it)
        if ct >= 0:
            self._run_cmd("INITIALIZE_TOOLCHANGER T=%d" % ct)
            if self.verbose:
                self._info("pin_watch %s: ASSIGN_TOOL -> INITIALIZE_TOOLCHANGER T=%d" % (self.name, ct))
        else:
            self._run_cmd("UNSELECT_TOOL")
            if self.verbose:
                self._info("pin_watch %s: ASSIGN_TOOL -> UNSELECT_TOOL (ct=%d)" % (self.name, ct))

    def _info(self, msg):
        if not self.verbose:
            return
        try:
            self.gcode.respond_info(msg)
        except Exception:
            logging.info(msg)


def load_config_prefix(config):
    return PinWatch(config)
