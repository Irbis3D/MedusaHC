import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import test_motion


class SensorErrorTests(unittest.TestCase):
    def controller(self, tool=-2, printing=False):
        c = test_motion.MotionTests().controller()
        c.operation = "idle"
        c.target_tool = -1
        c.last_error = ""
        c.sensor_error = False
        c.feeder_open = False
        c.layer = 0
        c._current_tool = lambda: tool
        c._is_printing = lambda: printing
        c._tool_count = lambda: 2
        c._sensor_source = lambda: SimpleNamespace(state={"e": 0, "t0": 0})
        c._set_compat = Mock()
        c._run = Mock()
        c.gcode = Mock()
        c.pause = Mock()
        c.move = SimpleNamespace(saved_states={})
        c.printer = Mock()
        c.printer.command_error = RuntimeError
        c.printer.lookup_object = lambda name, default=None: (
            c.pause if name == "pause_resume" else
            c.move if name == "gcode_move" else
            SimpleNamespace(state="printing" if printing else "standby"))
        c._run.side_effect = lambda script: (
            c.move.saved_states.update(MHC_CHANGE_STATE={})
            if script == "SAVE_GCODE_STATE NAME=MHC_CHANGE_STATE" else None)
        return c

    def test_unknown_and_manual_changes_do_not_report_errors(self):
        c = self.controller()
        for operation in ("idle", "picking", "dropping"):
            c.operation = operation
            for tool in (-2, -1, 0, 1, -2):
                c._current_tool = lambda: tool
                status = c.get_status(0)
                self.assertEqual(status["current_tool"], tool)
                self.assertFalse(status["sensor_error"])
                self.assertEqual(status["last_error"], "")

    def test_invalid_state_keeps_existing_error_recovery(self):
        for printing in (False, True):
            for name in ("cmd_MHC_SET", "cmd_MHC_DROP"):
                with self.subTest(printing=printing, command=name):
                    c = self.controller(printing=printing)
                    cmd = Mock()
                    cmd.get_int.return_value = 0
                    c._tool_cfg = lambda: {"tools_direction": 1}
                    if printing:
                        getattr(c, name)(cmd)
                    else:
                        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                            getattr(c, name)(cmd)
                    c._home.assert_called_once_with()
                    c._run.assert_any_call("MHC_ERROR")
                    c.pause.send_pause_command.assert_not_called()
                    self.assertTrue(c.get_status(0)["sensor_error"])
                    self.assertEqual(c.operation, "idle")

    def test_post_motion_failures_latch_and_next_command_clears(self):
        for action in ("_pick", "_drop_active"):
            c = self.controller(tool=0)
            c._motion_values = lambda tool: dict(
                direction=1, accel=1000, y_safe=0, x=20, feed=6000,
                y_brush=-10, x_prime_shift=2, y_latch=-20,
                x_shift=4, slow_feed=600)
            c._open = Mock()
            c._close = Mock()
            c._after_pick = Mock()
            c._wait_moves = Mock()
            c._wait_for_tool = Mock(return_value=False)
            c._begin("picking" if action == "_pick" else "dropping")
            with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                if action == "_pick":
                    c._pick(0)
                else:
                    c._drop_active()
            self.assertTrue(c.get_status(0)["sensor_error"])
            c._run.assert_any_call("MHC_ERROR")
            c._close.assert_not_called()
            c._after_pick.assert_not_called()
            c._current_tool = lambda: -1
            self.assertTrue(c.get_status(0)["sensor_error"])
            c._begin("changing", 0)
            self.assertFalse(c.get_status(0)["sensor_error"])
            self.assertEqual(c.last_error, "")
