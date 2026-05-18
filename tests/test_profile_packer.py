import unittest

import cargo_loading.profile_packer as profile_packer
from cargo_loading.profile_packer import pack_profile
from cargo_loading.profile_models import BoxSpec, ProfilePackingInput, ULDProfile


class ProfilePackerTests(unittest.TestCase):
    def test_pack_profile_places_boxes_inside_five_sided_cross_section(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 60), (70, 90), (0, 90)],
            ),
            boxes=[
                BoxSpec(id="BOX-A", length=60, width=50, height=30, quantity=2, rotatable=False),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 0)
        self.assertTrue(result.validation_passed)
        self.assertEqual(result.validation_errors, [])
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("BOX-A", 2)])
        self.assertEqual([placement.x for placement in result.placements], [0, 60])

    def test_pack_profile_reports_unloaded_quantity_when_space_runs_out(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=100,
                cross_section=[(0, 0), (50, 0), (50, 30), (0, 30)],
            ),
            boxes=[
                BoxSpec(id="BOX-A", length=60, width=50, height=30, quantity=2, rotatable=False),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 1)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual(result.unloaded[0].box_id, "BOX-A")
        self.assertEqual(result.unloaded[0].quantity, 1)

    def test_pack_profile_tries_multiple_box_orders_to_improve_used_volume(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=9,
                cross_section=[(0, 0), (5, 0), (5, 7), (0, 7)],
            ),
            boxes=[
                BoxSpec(id="A", length=4, width=3, height=6, quantity=3, rotatable=False),
                BoxSpec(id="B", length=7, width=3, height=5, quantity=2, rotatable=False),
                BoxSpec(id="C", length=7, width=4, height=4, quantity=2, rotatable=False),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.used_volume, 144)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("A", 2)])
        self.assertTrue(result.validation_passed)

    def test_pack_profile_scores_candidate_positions_and_orientations(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=9,
                cross_section=[(0, 0), (9, 0), (9, 6), (0, 6)],
            ),
            boxes=[
                BoxSpec(id="A", length=8, width=9, height=3, quantity=1, rotatable=True),
                BoxSpec(id="B", length=3, width=2, height=5, quantity=3, rotatable=True),
                BoxSpec(id="C", length=2, width=5, height=6, quantity=3, rotatable=True),
                BoxSpec(id="D", length=6, width=4, height=2, quantity=3, rotatable=True),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 9)
        self.assertEqual(result.used_volume, 414)
        self.assertEqual(
            [(item.box_id, item.quantity) for item in result.loaded],
            [("B", 3), ("C", 3), ("D", 3)],
        )
        self.assertTrue(result.validation_passed)

    def test_pack_profile_rotates_only_length_and_width_while_height_stays_fixed(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=100,
                cross_section=[(0, 0), (60, 0), (60, 40), (0, 40)],
            ),
            boxes=[
                BoxSpec(id="BOX-A", length=50, width=35, height=45, quantity=1, rotatable=True),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 0)
        self.assertEqual(result.unloaded_count, 1)

    def test_pack_profile_keeps_multiple_partial_layouts_with_beam_search(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=14,
                cross_section=[(0, 0), (10, 0), (10, 8), (0, 8)],
            ),
            boxes=[
                BoxSpec(id="A", length=10, width=6, height=9, quantity=1, rotatable=True),
                BoxSpec(id="B", length=8, width=7, height=5, quantity=3, rotatable=True),
                BoxSpec(id="C", length=4, width=5, height=4, quantity=1, rotatable=True),
                BoxSpec(id="D", length=6, width=9, height=3, quantity=1, rotatable=True),
            ],
        )

        original_beam_width = profile_packer.DEFAULT_BEAM_WIDTH
        try:
            profile_packer.DEFAULT_BEAM_WIDTH = 1
            narrow_result = pack_profile(problem)
        finally:
            profile_packer.DEFAULT_BEAM_WIDTH = original_beam_width

        result = pack_profile(problem)

        self.assertEqual(narrow_result.used_volume, 522)
        self.assertEqual(result.used_volume, 722)
        self.assertGreater(result.used_volume, narrow_result.used_volume)
        self.assertEqual(result.loaded_count, 3)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("B", 2), ("D", 1)])
        self.assertTrue(result.validation_passed)


if __name__ == "__main__":
    unittest.main()
