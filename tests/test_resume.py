"""Safety checks for repeated recovery and the path back to the print."""

import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_motion


def print_state():
    return {
        "absolute_coord": True, "allow_absolute_extrude": False,
        "base_position": [0., 0., 0., 0.],
        "last_position": [100., 100., .2, 12.],
        "homing_position": [0., 0., 0., 0.],
        "speed": 25., "speed_factor": 1. / 60., "extrude_factor": 1.,
    }


class ResumeTests(unittest.TestCase):
    def controller(self):
        c = test_motion.MotionTests().controller()
        c.operation = "idle"
        c.sensor_error = True
        c.target_tool = 1
        c.last_error = "earlier failure"
        c._tool_count = lambda: 2
        c._heater_temperature = lambda tool: 205.
        c._global = lambda: {"error_state": 1}
        c.reactor = SimpleNamespace(monotonic=lambda: 0.)
        c.gcode = Mock()
        pause = SimpleNamespace(is_paused=True)
        move = SimpleNamespace(
            saved_states={"PAUSE_STATE": print_state()},
            base_position=[1., 2., .5, 0.],
            get_status=lambda now: {
                "homing_origin": [1., 2., .5, 0.],
                "position": [20., -5., 5.2, 12.],
            },
        )
        toolhead = SimpleNamespace(get_status=lambda now: {
            "axis_maximum": [320., 320., 300., 0.],
        })
        c.printer = SimpleNamespace(lookup_object=lambda name: {
            "pause_resume": pause, "gcode_move": move,
            "toolhead": toolhead,
        }[name])
        gcmd = SimpleNamespace(get_int=lambda key, default=None: 1, error=RuntimeError)
        return c, pause, move, gcmd

    def test_repeated_failed_resume_keeps_original_point_and_pause(self):
        c, pause, move, gcmd = self.controller()
        original = copy.deepcopy(move.saved_states["PAUSE_STATE"])
        calls = []

        def run(script):
            calls.append(script)
            if script == "MHC_SET T=1":
                c.sensor_error = True

        c._run = run
        c._set_tool = Mock(side_effect=lambda tool: setattr(c, "sensor_error", True))
        for _ in range(2):
            c.cmd_MHC_RESUME(gcmd)
            self.assertTrue(pause.is_paused)
            self.assertEqual(move.saved_states["PAUSE_STATE"], original)
        self.assertNotIn("BASE_RESUME VELOCITY=30", calls)
        self.assertFalse(any("G1 Z" in line for line in calls))

    def test_real_set_failure_during_resume_preserves_pause_point(self):
        c, pause, move, gcmd = self.controller()
        original = copy.deepcopy(move.saved_states["PAUSE_STATE"])
        c._is_printing = lambda: False
        c._current_tool = lambda: -1
        c._tool_cfg = lambda: {"tools_direction": 1}
        c._home = Mock()
        c._apply_offset = Mock()
        c._set_compat = Mock()
        c.printer = SimpleNamespace(
            command_error=RuntimeError,
            lookup_object=lambda name, default=None: {
                "pause_resume": pause, "gcode_move": move,
                "toolhead": SimpleNamespace(get_status=lambda now: {
                    "axis_maximum": [320., 320., 300., 0.],
                }),
                "print_stats": SimpleNamespace(state="paused"),
            }[name])
        c._pick = Mock(side_effect=lambda tool: c._fail("pick not confirmed"))
        calls = []
        c._run = calls.append
        for _ in range(2):
            c.cmd_MHC_RESUME(gcmd)
            self.assertTrue(pause.is_paused)
            self.assertEqual(move.saved_states["PAUSE_STATE"], original)
            self.assertTrue(c.sensor_error)
        self.assertEqual(c._pick.call_count, 2)
        self.assertNotIn("BASE_RESUME VELOCITY=30", calls)

    def test_error_recovery_does_not_visit_previous_tool_xy(self):
        c, pause, move, gcmd = self.controller()
        calls = []

        def run(script):
            calls.append(script)
            if script == "MHC_SET T=1":
                c.sensor_error = False
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c._set_tool = Mock(side_effect=lambda tool: setattr(c, "sensor_error", False))
        c._current_tool = lambda: 1
        c.cmd_MHC_RESUME(gcmd)

        saved = move.saved_states["PAUSE_STATE"]
        self.assertEqual(saved["homing_position"][:3], [1., 2., .5])
        self.assertEqual(saved["base_position"][:3], [1., 2., .5])
        self.assertEqual(saved["last_position"][:3], [20., -5., 5.7])
        self.assertEqual(saved["last_position"][3], 12.)
        # The physical Z stays high, while an absolute G1 Z.2 in the file
        # will resolve to the new tool's physical layer height of 0.7 mm.
        self.assertAlmostEqual(saved["last_position"][2] -
                               saved["base_position"][2], 5.2)
        self.assertAlmostEqual(.2 + saved["base_position"][2], .7)
        self.assertEqual(calls[-2:], [
            "G90\nG1 Z5.200000 F3000",
            "BASE_RESUME VELOCITY=30",
        ])
        self.assertFalse(any("G1 X100.000000 Y100.000000" in script
                             for script in calls))
        self.assertFalse(pause.is_paused)

    def test_no_xy_return_when_z_clearance_exceeds_machine_limit(self):
        c, pause, move, gcmd = self.controller()
        c.sensor_error = False
        c._current_tool = lambda: 1
        c._set_tool = Mock()
        c.printer = SimpleNamespace(lookup_object=lambda name: {
            "pause_resume": pause, "gcode_move": move,
            "toolhead": SimpleNamespace(get_status=lambda now: {
                "axis_maximum": [320., 320., 5.5, 0.],
            }),
        }[name])
        calls = []
        c._run = calls.append
        original = copy.deepcopy(move.saved_states["PAUSE_STATE"])
        with self.assertRaisesRegex(RuntimeError, "Z clearance"):
            c.cmd_MHC_RESUME(gcmd)
        self.assertTrue(pause.is_paused)
        self.assertEqual(move.saved_states["PAUSE_STATE"], original)
        self.assertFalse(any("G1 X100" in line for line in calls))
        self.assertNotIn("BASE_RESUME VELOCITY=30", calls)

    def test_fail_during_print_replaces_pause_state_with_prechange_state(self):
        c, pause, move, gcmd = self.controller()
        c._is_printing = lambda: True
        c._current_tool = lambda: -2
        c._tool_cfg = lambda: {"tools_direction": 1}
        c._apply_offset = Mock()
        c._home = Mock()
        c._set_compat = Mock()
        c.printer = SimpleNamespace(
            command_error=RuntimeError,
            lookup_object=lambda name, default=None: (
                move if name == "gcode_move" else
                SimpleNamespace(state="printing") if name == "print_stats"
                else None))
        before = print_state()

        def run(script):
            if script == "SAVE_GCODE_STATE NAME=MHC_CHANGE_STATE":
                move.saved_states["MHC_CHANGE_STATE"] = copy.deepcopy(before)
            if script == "MHC_ERROR":
                move.saved_states["PAUSE_STATE"] = dict(last_position=[0., 220., 5., 12.])

        c._run = run
        c.cmd_MHC_SET(gcmd)
        self.assertEqual(move.saved_states["PAUSE_STATE"], before)
        self.assertIsNone(c._change_state)
        self.assertTrue(c.sensor_error)

    def test_resume_with_cold_tool_does_not_move_or_release_pause(self):
        c, pause, move, gcmd = self.controller()
        c._heater_temperature = lambda tool: 180.
        c._run = Mock()
        with self.assertRaisesRegex(RuntimeError, "heat T1"):
            c.cmd_MHC_RESUME(gcmd)
        self.assertTrue(pause.is_paused)
        c._run.assert_not_called()

    def test_resume_primes_and_cleans_an_already_mounted_tool(self):
        c = test_motion.MotionTests().controller()
        c._resume_preparing = True
        c._is_printing = lambda: False
        c.operation = "idle"
        c.sensor_error = False
        c.last_error = ""
        c._tool_count = lambda: 2
        c._tool_cfg = lambda: {"tools_direction": 1}
        c._set_compat = Mock()
        c._home = Mock()
        c._current_tool = lambda: 0
        c._motion_values = lambda tool: dict(
            x=17., x_prime_shift=12., y_prime=-45., y_brush=-35.,
            y_safe=-5., feed=18000., direction=1, accel=10000.)
        commands = []
        c._run = commands.append
        c.cmd_MHC_SET(SimpleNamespace(get_int=lambda name, default=None: 0))
        script = "\n".join(commands)
        self.assertIn("G1 Y-45.0 F18000.0", script)
        self.assertIn("G1 Y-35.0 F18000.0", script)
        self.assertIn("G1 E2.0", script)
        self.assertIn("G1 X-8.0 Y5.0 F15000.0", script)
        self.assertIn("M106 S255", script)
        self.assertIn("M106 S0", script)

    def test_resume_changes_wrong_mounted_tool_before_returning(self):
        c, pause, move, gcmd = self.controller()
        mounted = [0]
        c._is_printing = lambda: False
        c._current_tool = lambda: mounted[0]
        c._tool_cfg = lambda: {"tools_direction": 1}
        c._home = Mock()
        c._apply_offset = Mock()
        c._set_compat = Mock()
        c._drop_active = Mock(side_effect=lambda: mounted.__setitem__(0, -1))
        c._pick = Mock(side_effect=lambda tool: mounted.__setitem__(0, tool))
        calls = []

        def run(script):
            calls.append(script)
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.printer.lookup_object = lambda name, default=None: {
            "pause_resume": pause, "gcode_move": move,
            "toolhead": SimpleNamespace(get_status=lambda now: {
                "axis_maximum": [320., 320., 300., 0.],
            }),
        }.get(name, default)
        c.cmd_MHC_RESUME(gcmd)
        c._drop_active.assert_called_once_with()
        c._pick.assert_called_once_with(1)
        self.assertEqual(mounted[0], 1)
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_manual_pause_with_same_tool_returns_without_homing_or_cleaning(self):
        c, pause, move, gcmd = self.controller()
        c._global = lambda: {"error_state": 0}
        c._current_tool = lambda: 1
        c._heater_temperature = Mock(side_effect=AssertionError("no heat check"))
        c._set_tool = Mock()
        calls = []

        def run(script):
            calls.append(script)
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.cmd_MHC_RESUME(gcmd)
        c._set_tool.assert_not_called()
        self.assertFalse(any("G28" in script or "CLOSE" in script for script in calls))
        self.assertIn("G90\nG1 X100.000000 Y100.000000 F12000", calls)
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_manual_z_jog_does_not_replace_saved_layer_height(self):
        c, pause, move, gcmd = self.controller()
        c._global = lambda: {"error_state": 0}
        c._current_tool = lambda: 1
        c._set_tool = Mock()
        move.get_status = lambda now: {
            "homing_origin": [1., 2., .5, 0.],
            "position": [20., -5., 15.2, 12.],
        }
        calls = []

        def run(script):
            calls.append(script)
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.cmd_MHC_RESUME(gcmd)
        self.assertFalse(any("G1 Z" in script for script in calls))
        self.assertEqual(move.saved_states["PAUSE_STATE"]["last_position"][2], .7)
        self.assertIn("G90\nG1 X100.000000 Y100.000000 F12000", calls)
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_error_z_jog_stays_lifted_until_print_file_sets_z(self):
        c, pause, move, gcmd = self.controller()
        c._current_tool = lambda: 1
        c._set_tool = Mock(side_effect=lambda tool: setattr(c, "sensor_error", False))
        move.get_status = lambda now: {
            "homing_origin": [1., 2., .5, 0.],
            "position": [20., -5., 15.2, 12.],
        }
        calls = []

        def run(script):
            calls.append(script)
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.cmd_MHC_RESUME(gcmd)
        saved = move.saved_states["PAUSE_STATE"]
        self.assertEqual(saved["last_position"][:3], [20., -5., 15.2])
        self.assertEqual(saved["base_position"][2], .5)
        self.assertFalse(any("G1 Z" in script or "G1 X100" in script
                             for script in calls))
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_lowered_z_is_raised_before_error_recovery_homes_xy(self):
        c, pause, move, gcmd = self.controller()
        c._current_tool = lambda: 1
        c._set_tool = Mock(side_effect=lambda tool: setattr(c, "sensor_error", False))
        position = [20., -5., .2, 12.]
        move.get_status = lambda now: {
            "homing_origin": [1., 2., .5, 0.],
            "position": position,
        }
        calls = []

        def run(script):
            calls.append(script)
            if script.startswith("G90\nG1 Z"):
                position[2] = float(script.split("G1 Z")[1].split()[0]) + move.base_position[2]
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.cmd_MHC_RESUME(gcmd)
        self.assertEqual(calls[0], "G90\nG1 Z4.700000 F3000")
        self.assertEqual(calls[1], "G90\nG28 Y\nG28 X\nCLOSE")
        self.assertEqual(move.saved_states["PAUSE_STATE"]["last_position"][2], 5.7)
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_manual_pause_with_different_tool_uses_full_preparation(self):
        c, pause, move, gcmd = self.controller()
        c._global = lambda: {"error_state": 0}
        mounted = [0]
        c._current_tool = lambda: mounted[0]
        def set_tool(tool):
            mounted[0] = tool
            c.sensor_error = False

        c._set_tool = Mock(side_effect=set_tool)
        calls = []

        def run(script):
            calls.append(script)
            if script == "BASE_RESUME VELOCITY=30":
                pause.is_paused = False

        c._run = run
        c.cmd_MHC_RESUME(gcmd)
        c._set_tool.assert_called_once_with(1)
        self.assertIn("G90\nG28 Y\nG28 X\nCLOSE", calls)
        self.assertEqual(calls[-1], "BASE_RESUME VELOCITY=30")

    def test_error_pause_does_not_move_before_parking_or_repeat_pause(self):
        c, pause, move, gcmd = self.controller()
        state = SimpleNamespace(state="printing")
        c.printer = SimpleNamespace(lookup_object=lambda name, default=None: {
            "print_stats": state,
        }.get(name, default))
        c._set_compat = Mock()
        calls = []
        c._run = calls.append
        c.cmd_MHC_ERROR(None)
        self.assertEqual(calls, ["PAUSE"])
        c._set_compat.assert_called_with("error_state", 1)
        state.state = "paused"
        c.cmd_MHC_ERROR(None)
        self.assertEqual(calls, ["PAUSE"])
