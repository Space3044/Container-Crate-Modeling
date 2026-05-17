import unittest

from cargo_loading.profile_geometry import polygon_area, rectangle_inside_polygon


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


if __name__ == "__main__":
    unittest.main()
