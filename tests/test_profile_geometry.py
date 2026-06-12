import unittest

from cargo_loading.profile_geometry import convex_y_interval, is_convex_polygon, polygon_area, rectangle_inside_polygon
from cargo_loading.profile_models import PackingInputError, ULDProfile


class ProfileGeometryTests(unittest.TestCase):
    def test_polygon_area_for_right_top_cut_profile(self):
        profile = [(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)]

        self.assertEqual(polygon_area(profile), 33950)

    def test_rectangle_inside_polygon_accepts_rectangle_under_slant(self):
        profile = [(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)]

        self.assertTrue(rectangle_inside_polygon(y=0, z=0, width=60, height=40, polygon=profile))

    def test_rectangle_inside_polygon_rejects_rectangle_cut_by_slant(self):
        profile = [(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)]

        self.assertFalse(rectangle_inside_polygon(y=180, z=120, width=30, height=30, polygon=profile))

    def test_is_convex_polygon_accepts_field_profiles_and_rejects_concave(self):
        self.assertTrue(is_convex_polygon([(0, 0), (240, 0), (240, 240), (120, 290), (0, 290)]))
        self.assertTrue(is_convex_polygon([(0, 0), (100, 0), (100, 100), (0, 100)]))
        self.assertFalse(is_convex_polygon([(0, 0), (240, 0), (240, 240), (120, 240), (0, 290)]))
        self.assertFalse(is_convex_polygon([(0, 0), (100, 0)]))

    def test_uld_profile_rejects_concave_cross_section(self):
        with self.assertRaises(PackingInputError):
            ULDProfile(id="BAD", length=100, cross_section=[(0, 0), (240, 0), (240, 240), (120, 240), (0, 290)])

    def test_convex_y_interval_narrows_under_slant(self):
        profile = [(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)]

        self.assertEqual(convex_y_interval(profile, 0, 110), (0, 220))
        self.assertEqual(convex_y_interval(profile, 110, 160), (0, 170))
        self.assertIsNone(convex_y_interval(profile, 0, 200))


if __name__ == "__main__":
    unittest.main()
