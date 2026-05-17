import unittest

from cargo_loading.profile_models import BoxPlacement, ProfilePackingInput, ProfilePackingResult, ULDProfile
from cargo_loading.profile_visualizer import render_cross_section_svg, render_x_slice_svg


class ProfileVisualizerTests(unittest.TestCase):
    def test_render_cross_section_svg_contains_profile_and_placement(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 60), (70, 90), (0, 90)],
            ),
            boxes=[],
        )
        result = ProfilePackingResult(
            uld_id="ULD-001",
            loaded_count=1,
            unloaded_count=0,
            used_volume=90000,
            cross_section_area=8550,
            uld_volume=1026000,
            volume_utilization=0.0877,
            placements=[
                BoxPlacement(
                    box_id="BOX-A",
                    instance_id="BOX-A-001",
                    x=0,
                    y=0,
                    z=0,
                    length=60,
                    width=50,
                    height=30,
                )
            ],
            unloaded=[],
            validation_passed=True,
        )

        svg = render_cross_section_svg(problem, result)

        self.assertIn("<svg", svg)
        self.assertIn("<polygon", svg)
        self.assertIn("BOX-A-001", svg)
        self.assertIn("<rect", svg)

    def test_render_x_slice_svg_separates_x_layers(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 60), (70, 90), (0, 90)],
            ),
            boxes=[],
        )
        result = ProfilePackingResult(
            uld_id="ULD-001",
            loaded_count=2,
            unloaded_count=0,
            used_volume=180000,
            cross_section_area=8550,
            uld_volume=1026000,
            volume_utilization=0.1754,
            placements=[
                BoxPlacement("BOX-A", "BOX-A-001", 0, 0, 0, 60, 50, 30),
                BoxPlacement("BOX-A", "BOX-A-002", 60, 0, 0, 60, 50, 30),
            ],
            unloaded=[],
            validation_passed=True,
        )

        svg = render_x_slice_svg(problem, result)

        self.assertIn("x = 0", svg)
        self.assertIn("x = 60", svg)
        self.assertIn("BOX-A-001", svg)
        self.assertIn("BOX-A-002", svg)


if __name__ == "__main__":
    unittest.main()
