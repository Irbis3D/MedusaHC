import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("medusahc", Path(__file__).parents[1] / "klippy/extras/medusahc.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MotionTests(unittest.TestCase):
    def controller(self):
        controller = object.__new__(module.MedusaHC)
        controller._macro = Mock(return_value={"prime_amount": 10, "prime_speed": 5,
                                              "x_clean_move": 8, "y_clean_move": 5,
                                              "clean_move_speed": 250,
                                              "prime_retract": .8, "clean_retract": .7})
        controller._is_printing = lambda: True
        controller._heater_temperature = lambda tool: 210
        controller._apply_offset = Mock()
        controller._current_tool = lambda: 0
        controller._home = Mock()
        controller._old_accel = lambda: 1000
        return controller

    def test_prime_position_and_brush_speed_for_both_dock_directions(self):
        for direction in (1, -1):
            for brush in (-45, -35):
                for manual in (False, True):
                    with self.subTest(direction=direction, brush=brush, manual=manual):
                        controller = self.controller()
                        values = dict(x=17, x_prime_shift=12, y_prime=-45, y_brush=brush,
                                      y_safe=-5, feed=18000, direction=direction, accel=10000)
                        controller._motion_values = lambda tool: values
                        scripts = []
                        controller._run = scripts.append
                        if manual:
                            controller.cmd_MHC_CLEAN(None)
                        else:
                            controller._after_pick(0, values)
                        absolute = True
                        position = dict(X=0., Y=0.)
                        primes, crossings, moves, slow_passes = [], [], [], []
                        for line in "\n".join(scripts).splitlines():
                            if line == "G90":
                                absolute = True
                            elif line == "G91":
                                absolute = False
                            elif line.startswith("G1 "):
                                fields = {token[0]: float(token[1:]) for token in line.split()[1:]}
                                before = position.copy()
                                moves.append((before, fields))
                                for axis in position:
                                    if axis in fields:
                                        position[axis] = fields[axis] if absolute else position[axis] + fields[axis]
                                if fields.get("E", 0) > 0:
                                    primes.append(position.copy())
                                if "X" in fields and "Y" in fields:
                                    crossings.append((before, fields["F"]))
                                if "X" in fields and fields.get("F") == 750:
                                    slow_passes.append(before)
                        self.assertEqual(len(crossings), 3)
                        self.assertEqual(crossings[0][0]["Y"], brush - 2 * direction)
                        self.assertTrue(all(speed == 15000 for _, speed in crossings))
                        self.assertEqual(position["Y"], -5)
                        self.assertEqual(slow_passes[0], {"X": 17-12*direction, "Y": brush})
                        self.assertEqual(slow_passes[1]["Y"], brush + 6*direction)
                        if manual:
                            self.assertEqual(primes, [])
                        else:
                            self.assertEqual(len(primes), 3)
                            self.assertTrue(all(point == {"X": 17-12*direction, "Y": -45} for point in primes))
                            prime_retract = next(i for i, (_, fields) in enumerate(moves) if fields.get("E") == -.8)
                            self.assertEqual(moves[prime_retract + 1][1], {"Y": brush, "F": 18000})
                            self.assertEqual(moves[-2][1]["E"], -.7)
                            self.assertEqual(moves[-1][1], {"Y": -5, "F": 18000})

    def test_each_tool_uses_its_own_speed_and_reads_runtime_changes(self):
        controller = self.controller()
        states = {0: {"clean_move_speed": 80}, 1: {"clean_move_speed": 250}}
        controller._macro = lambda name: states[int(name.rsplit("_", 1)[1])]
        values = dict(x=17, x_prime_shift=12, y_prime=-45, y_brush=-45,
                      y_safe=-5, feed=18000, direction=1, accel=10000)
        controller._motion_values = lambda tool: values
        for tool, speed in ((0, 80), (1, 250), (0, 120)):
            states[tool]["clean_move_speed"] = speed
            controller._current_tool = lambda: tool
            for manual in (True, False):
                scripts = []
                controller._run = scripts.append
                if manual:
                    controller.cmd_MHC_CLEAN(None)
                else:
                    controller._after_pick(tool, values)
                crossings = [line for line in "\n".join(scripts).splitlines()
                             if line.startswith("G1 X") and " Y" in line]
                self.assertEqual(len(crossings), 3)
                self.assertTrue(all(float(line.split(" F")[1]) == speed * 60 for line in crossings))
