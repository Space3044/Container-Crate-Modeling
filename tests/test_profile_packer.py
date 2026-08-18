import unittest

import cargo_loading.profile_packer as profile_packer
from cargo_loading.profile_packer import pack_profile, validate_profile_packing
from cargo_loading.profile_models import BoxPlacement, BoxSpec, ProfilePackingInput, ULDProfile


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

    def test_validate_profile_packing_rejects_stacked_box_with_insufficient_support(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=160,
                cross_section=[(0, 0), (60, 0), (60, 80), (0, 80)],
            ),
            boxes=[],
        )
        placements = [
            BoxPlacement("BASE-L", "BASE-L-001", 0, 0, 0, 50, 50, 30),
            BoxPlacement("BASE-R", "BASE-R-001", 100, 0, 0, 50, 50, 30),
            BoxPlacement("TOP", "TOP-001", 0, 0, 30, 150, 50, 20),
        ]

        errors = validate_profile_packing(problem, placements)

        self.assertIn("TOP-001 has insufficient bottom support", errors)

    def test_validate_profile_packing_uses_only_boxes_touching_the_same_support_height(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=220,
                cross_section=[(0, 0), (120, 0), (120, 90), (0, 90)],
            ),
            boxes=[],
        )
        placements = [
            BoxPlacement("LOW", "LOW-001", 0, 0, 0, 100, 100, 30),
            BoxPlacement("TALL", "TALL-001", 100, 0, 0, 100, 100, 50),
            BoxPlacement("TOP", "TOP-001", 0, 0, 50, 200, 100, 20),
        ]

        errors = validate_profile_packing(problem, placements)

        self.assertIn("TOP-001 has insufficient bottom support", errors)

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

    def test_free_spaces_keep_stacking_space_above_placed_box(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=100,
                cross_section=[(0, 0), (60, 0), (60, 50), (0, 50)],
            ),
            boxes=[],
        )
        base = BoxPlacement("BASE", "BASE-001", 0, 0, 0, 40, 40, 20)

        spaces = profile_packer._subtract_placement_from_spaces(
            profile_packer._initial_free_spaces(problem), base, max_spaces=160
        )

        self.assertIn(profile_packer.FreeSpace(0, 0, 20, 100, 60, 30), spaces)
        self.assertIn(profile_packer.FreeSpace(40, 0, 0, 60, 60, 50), spaces)
        self.assertIn(profile_packer.FreeSpace(0, 40, 0, 100, 20, 50), spaces)

    def test_free_spaces_expose_cavity_above_lower_neighbor(self):
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="ULD-001",
                length=100,
                cross_section=[(0, 0), (60, 0), (60, 50), (0, 50)],
            ),
            boxes=[],
        )
        base = BoxPlacement("BASE", "BASE-001", 0, 0, 0, 40, 40, 20)
        neighbor = BoxPlacement("NEI", "NEI-001", 40, 0, 0, 30, 40, 10)

        spaces = profile_packer._initial_free_spaces(problem)
        for placement in (base, neighbor):
            spaces = profile_packer._subtract_placement_from_spaces(spaces, placement, max_spaces=160)

        self.assertIn(profile_packer.FreeSpace(40, 0, 10, 60, 60, 40), spaces)
        self.assertIn(profile_packer.FreeSpace(70, 0, 0, 30, 60, 50), spaces)
        for first in spaces:
            for second in spaces:
                if first is not second:
                    self.assertFalse(profile_packer._space_contains_space(first, second))

    def test_beam_diversity_keeps_spread_layout_in_sloped_q7(self):
        # 与多容器路径同一现场反例：装载量相同时 beam 只比包围盒体积，
        # 沿长度方向铺开的布局被整批淘汰，单 ULD 路径同样只能装 11 箱。
        problem = ProfilePackingInput(
            uld=ULDProfile(
                id="Q7",
                length=306,
                cross_section=[(0, 0), (240, 0), (240, 240), (120, 291), (0, 291)],
            ),
            boxes=[
                BoxSpec(id="BOX-A", length=109, width=109, height=95, quantity=4),
                BoxSpec(id="BOX-B", length=106, width=69, height=99, quantity=3),
                BoxSpec(id="BOX-C", length=120, width=100, height=145, quantity=2),
                BoxSpec(id="BOX-D", length=112, width=112, height=123, quantity=1),
                BoxSpec(id="BOX-E", length=110, width=110, height=146, quantity=1),
                BoxSpec(id="BOX-F", length=124, width=100, height=154, quantity=1),
            ],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 12)
        self.assertEqual(result.unloaded_count, 0)
        self.assertTrue(result.validation_passed)


    def test_full_rotatable_allows_upright_orientation(self):
        # 截面 100×100 装不下高 150 的箱子，只有把 150 转到 x 方向才装得进
        problem = ProfilePackingInput(
            uld=ULDProfile(id="T", length=200, cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)]),
            boxes=[BoxSpec(id="BOX-A", length=50, width=50, height=150, quantity=2, full_rotatable=True)],
        )

        result = pack_profile(problem)

        self.assertEqual(result.loaded_count, 2)
        self.assertTrue(result.validation_passed)
        for placement in result.placements:
            self.assertEqual((placement.length, placement.width, placement.height), (150, 50, 50))

    def test_full_rotatable_defaults_to_disabled(self):
        # 不勾选时维持原规约：高度方向保持输入值，该箱型装不进去
        box = BoxSpec(id="BOX-A", length=50, width=50, height=150, quantity=2)
        problem = ProfilePackingInput(
            uld=ULDProfile(id="T", length=200, cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)]),
            boxes=[box],
        )

        self.assertFalse(box.full_rotatable)
        self.assertEqual(pack_profile(problem).loaded_count, 0)

    def test_orientation_options_cover_all_six_permutations_when_full_rotatable(self):
        rotatable = BoxSpec(id="B", length=2, width=3, height=5, quantity=1)
        fixed = BoxSpec(id="B", length=2, width=3, height=5, quantity=1, rotatable=False)
        full = BoxSpec(id="B", length=2, width=3, height=5, quantity=1, full_rotatable=True)

        self.assertEqual(profile_packer._orientation_options(fixed), [(2, 3, 5)])
        self.assertEqual(profile_packer._orientation_options(rotatable), [(2, 3, 5), (3, 2, 5)])
        self.assertEqual(
            profile_packer._orientation_options(full),
            [(2, 3, 5), (2, 5, 3), (3, 2, 5), (3, 5, 2), (5, 2, 3), (5, 3, 2)],
        )

    def test_validate_rejects_height_swap_without_full_rotatable(self):
        uld = ULDProfile(id="T", length=300, cross_section=[(0, 0), (200, 0), (200, 200), (0, 200)])
        upright = BoxPlacement(box_id="B", instance_id="B#1", x=0, y=0, z=0, length=100, width=40, height=60)

        rotatable_only = ProfilePackingInput(
            uld=uld,
            boxes=[BoxSpec(id="B", length=60, width=40, height=100, quantity=1)],
        )
        full_rotatable = ProfilePackingInput(
            uld=uld,
            boxes=[BoxSpec(id="B", length=60, width=40, height=100, quantity=1, full_rotatable=True)],
        )

        self.assertEqual(
            validate_profile_packing(rotatable_only, [upright]),
            ["B#1 uses a disallowed orientation"],
        )
        self.assertEqual(validate_profile_packing(full_rotatable, [upright]), [])


    def test_height_swapped_marks_only_placements_that_changed_height(self):
        # FLIP 只有立起来才装得下，PLAIN 维持录入高度；标记只应落在前者
        problem = ProfilePackingInput(
            uld=ULDProfile(id="T", length=400, cross_section=[(0, 0), (200, 0), (200, 200), (0, 200)]),
            boxes=[
                BoxSpec(id="FLIP", length=50, width=50, height=300, quantity=1, full_rotatable=True),
                BoxSpec(id="PLAIN", length=60, width=40, height=80, quantity=1),
            ],
        )

        result = pack_profile(problem)
        by_id = {placement.box_id: placement for placement in result.placements}

        self.assertEqual(result.loaded_count, 2)
        self.assertTrue(by_id["FLIP"].height_swapped)
        self.assertNotEqual(by_id["FLIP"].height, 300)
        self.assertFalse(by_id["PLAIN"].height_swapped)

    def test_height_swapped_stays_false_when_full_rotatable_box_keeps_input_height(self):
        # 勾选了长宽高互换，但算法选用原始高度时不应标注
        problem = ProfilePackingInput(
            uld=ULDProfile(id="T", length=400, cross_section=[(0, 0), (200, 0), (200, 200), (0, 200)]),
            boxes=[BoxSpec(id="BOX-A", length=60, width=40, height=80, quantity=3, full_rotatable=True)],
        )

        result = pack_profile(problem)

        for placement in result.placements:
            self.assertEqual(placement.height_swapped, placement.height != 80)


if __name__ == "__main__":
    unittest.main()
