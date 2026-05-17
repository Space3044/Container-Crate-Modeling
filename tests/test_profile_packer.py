import unittest

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


if __name__ == "__main__":
    unittest.main()
