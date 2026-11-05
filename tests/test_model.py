import json
import tempfile
import unittest
from pathlib import Path

from model import CrosshairProfile, arm_rectangles, circle_geometry, dot_rectangle, shapes


class ProfileTests(unittest.TestCase):
    def test_default_arms_and_dot(self):
        p = CrosshairProfile()
        self.assertEqual(len(shapes(p, 128, 128)), 5)
        self.assertEqual(arm_rectangles(p, 128, 128)[0], (126.5, 111, 3, 12))
        self.assertEqual(dot_rectangle(p, 128, 128), (126.5, 126.5, 3, 3))
        self.assertIsNone(circle_geometry(p))

    def test_axes_are_independent(self):
        p = CrosshairProfile(horizontal_length=40, horizontal_gap=9,
                             horizontal_thickness=7,
                             vertical_length=18, vertical_gap=4,
                             vertical_thickness=2, dot=False)
        arms = arm_rectangles(p, 100, 100)
        self.assertEqual(arms, [(99, 78, 2, 18), (99, 104, 2, 18),
                                (51, 96.5, 40, 7), (109, 96.5, 40, 7)])

    def test_circle_only(self):
        p = CrosshairProfile(circle=True, vertical=False, horizontal=False,
                             dot=False, circle_radius_x=35,
                             circle_radius_y=17, circle_thickness=5,
                             circle_offset_x=4, circle_offset_y=-3)
        self.assertEqual(shapes(p), [])
        self.assertEqual(circle_geometry(p, 100, 120), (104, 117, 35, 17, 5))

    def test_zero_arms_preserves_dot(self):
        self.assertEqual(len(shapes(CrosshairProfile(horizontal_length=0,
                                                     vertical_length=0))), 1)

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            original = CrosshairProfile(name='リング', circle=True,
                                        horizontal_length=61,
                                        vertical_length=7,
                                        circle_radius_x=42,
                                        circle_radius_y=42, monitor=2)
            original.save(path)
            self.assertEqual(original, CrosshairProfile.load(path))

    def test_v01_migration(self):
        original = {'version': 1, 'name': 'v0.1', 'arm_length': 24,
                    'gap': 11, 'thickness': 4, 'dot': False,
                    'color': '#ff0000', 'offset_y': -9}
        p = CrosshairProfile.from_dict(original)
        self.assertEqual(p.version, 2)
        self.assertEqual((p.horizontal_length, p.vertical_length), (24, 24))
        self.assertEqual((p.horizontal_gap, p.vertical_gap), (11, 11))
        self.assertEqual((p.horizontal_thickness, p.vertical_thickness), (4, 4))
        self.assertFalse(p.circle)
        self.assertFalse(p.dot)
        self.assertEqual(p.color, '#ff0000')
        self.assertEqual(p.offset_y, -9)
        self.assertEqual(original['version'], 1)  # Input must not be mutated.

    def test_invalid_values_rejected(self):
        for value in ({'version': True}, {'version': 3}, {'horizontal_length': 131},
                      {'vertical_gap': -1}, {'circle_radius_y': 0},
                      {'circle_thickness': 25}, {'opacity': True},
                      {'color': 'red'}, {'circle': 'true'},
                      {'name': 'a' * 101}, {'monitor': -1}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CrosshairProfile.from_dict(value)

    def test_unexpected_json_fields_do_not_override(self):
        p = CrosshairProfile.from_dict({'version': 2, '__class__': 'ignored'})
        self.assertIsInstance(p, CrosshairProfile)

    def test_file_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            path.write_text(json.dumps({'version': 2, 'circle_radius_x': -1}), encoding='utf-8')
            with self.assertRaises(ValueError):
                CrosshairProfile.load(path)


if __name__ == '__main__':
    unittest.main()
