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
                                              "clean_move_speed": 250})
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
                                      y_safe=-5, feed=18000, clean_feed=3000, direction=direction, accel=10000)
                        controller._motion_values = lambda tool: values
                        scripts = []
                        controller._run = scripts.append
                        if manual:
                            controller.cmd_MHC_CLEAN(None)
                        else:
                            controller._after_pick(0, values)
                        absolute = True
                        position = dict(X=0., Y=0.)
                        primes, crossings = [], []
                        for line in "\n".join(scripts).splitlines():
                            if line == "G90":
                                absolute = True
                            elif line == "G91":
                                absolute = False
                            elif line.startswith("G1 "):
                                fields = {token[0]: float(token[1:]) for token in line.split()[1:]}
                                before = position.copy()
                                for axis in position:
                                    if axis in fields:
                                        position[axis] = fields[axis] if absolute else position[axis] + fields[axis]
                                if fields.get("E", 0) > 0:
                                    primes.append(position.copy())
                                if "X" in fields and "Y" in fields:
                                    crossings.append((before, fields["F"]))
                        self.assertEqual(len(crossings), 3)
                        self.assertEqual(crossings[0][0]["Y"], brush - 2 * direction)
                        self.assertTrue(all(speed == 3000 for _, speed in crossings))
                        self.assertEqual(position["Y"], -5)
                        if manual:
                            self.assertEqual(primes, [])
                        else:
                            self.assertEqual(len(primes), 3)
                            self.assertTrue(all(point == {"X": 17-12*direction, "Y": -45} for point in primes))
