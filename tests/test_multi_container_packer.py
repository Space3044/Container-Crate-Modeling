import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cargo_loading.profile_packer as profile_packer
from cargo_loading.profile_models import BoxPlacement, BoxSpec, ContainerSpec, MultiContainerPackingInput, PackingInputError
from cargo_loading.profile_packer import (
    MAX_BATCH_PLACEMENTS,
    MAX_GLOBAL_BOX_TYPE_CANDIDATES,
    MAX_GLOBAL_CONTAINER_CANDIDATES,
    MIN_BOTTOM_SUPPORT_RATIO,
    MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION,
    _candidate_box_types,
    _container_candidate_options,
    _global_placement_branches,
    _global_search_limits,
    _initial_global_state,
    _local_rearrange_state,
    _max_volume_combo,
    _min_support_ratio_for_mode,
    _pack_multi_profile_variant,
    _ruin_and_recreate,
    _worst_container_indices,
    pack_multi_profile,
)


class MultiContainerPackerTests(unittest.TestCase):
    def test_multi_result_score_follows_selected_objective(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[],
            objective="maximize_volume",
        )
        higher_volume = SimpleNamespace(
            containers=[],
            unloaded=[],
            loaded_count=1,
            unloaded_count=2,
            used_volume=100,
        )
        higher_count = SimpleNamespace(
            containers=[],
            unloaded=[],
            loaded_count=2,
            unloaded_count=1,
            used_volume=90,
        )

        self.assertGreater(
            profile_packer._multi_result_score(problem, higher_volume),
            profile_packer._multi_result_score(problem, higher_count),
        )
        count_problem = replace(problem, objective="maximize_count")
        self.assertGreater(
            profile_packer._multi_result_score(count_problem, higher_count),
            profile_packer._multi_result_score(count_problem, higher_volume),
        )

    def test_volume_objective_prefers_more_volume_over_more_boxes_in_all_modes(self):
        containers = [
            ContainerSpec(
                id="LINE",
                length=110,
                cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                quantity=3,
            )
        ]
        boxes = [
            BoxSpec(
                id=f"B{index:02d}",
                length=length,
                width=10,
                height=10,
                quantity=1,
                rotatable=False,
            )
            for index, length in enumerate((28, 44, 43, 37, 70, 62, 65, 31))
        ]

        for search_mode in ("fast", "balanced", "high_utilization"):
            result = pack_multi_profile(
                MultiContainerPackingInput(
                    containers=containers,
                    boxes=boxes,
                    objective="maximize_volume",
                    search_mode=search_mode,
                )
            )
            self.assertEqual((result.loaded_count, result.used_volume), (6, 32100))
            self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_merges_equivalent_rows_before_calculation(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=40,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                )
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=10, width=10, height=10, quantity=2, rotatable=False),
                BoxSpec(id="BOX-B", length=10, width=10, height=10, quantity=2, rotatable=False),
            ],
            search_mode="fast",
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 4)
        self.assertEqual(result.unloaded_count, 0)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("BOX-A", 4)])
        self.assertTrue(
            all(
                placement.box_id == "BOX-A"
                for container in result.containers
                for placement in container.result.placements
            )
        )

    def test_equivalent_row_split_and_order_do_not_change_high_volume_result(self):
        containers = [
            ContainerSpec(
                id="R",
                length=180,
                cross_section=[(0, 0), (120, 0), (120, 100), (0, 100)],
                quantity=2,
            ),
            ContainerSpec(
                id="S",
                length=220,
                cross_section=[(0, 0), (100, 0), (100, 80), (0, 80)],
                quantity=1,
            ),
        ]
        common_boxes = [
            BoxSpec(id="B", length=55, width=45, height=35, quantity=10),
            BoxSpec(id="C", length=80, width=40, height=60, quantity=6),
            BoxSpec(id="D", length=35, width=35, height=25, quantity=18),
            BoxSpec(id="E", length=90, width=60, height=75, quantity=3, required_container_types=("S",)),
        ]
        merged_problem = MultiContainerPackingInput(
            containers=containers,
            boxes=[BoxSpec(id="A", length=60, width=50, height=40, quantity=12), *common_boxes],
            objective="maximize_volume",
            search_mode="high_utilization",
        )
        split_and_reordered_problem = MultiContainerPackingInput(
            containers=containers,
            boxes=[
                *common_boxes,
                BoxSpec(id="A", length=60, width=50, height=40, quantity=4),
                BoxSpec(id="A2", length=50, width=60, height=40, quantity=8),
            ],
            objective="maximize_volume",
            search_mode="high_utilization",
        )

        merged_result = pack_multi_profile(merged_problem)
        split_result = pack_multi_profile(split_and_reordered_problem)

        self.assertEqual(
            (split_result.loaded_count, split_result.unloaded_count, split_result.used_volume),
            (merged_result.loaded_count, merged_result.unloaded_count, merged_result.used_volume),
        )
        self.assertEqual(
            (merged_result.loaded_count, merged_result.unloaded_count, merged_result.used_volume),
            (47, 2, 5051250),
        )
        self.assertTrue(merged_result.validation_passed)
        self.assertTrue(split_result.validation_passed)

    def test_balanced_large_history_case_keeps_all_boxes_for_both_objectives(self):
        """大规模历史输入不能因箱型归并和候选裁剪漏掉可行的 214 箱布局。"""
        containers = [
            ContainerSpec(
                id="Q7",
                length=306,
                cross_section=[(0, 0), (240, 0), (240, 240), (120, 290), (0, 290)],
                quantity=14,
            ),
            ContainerSpec(
                id="Q6",
                length=306,
                cross_section=[(0, 0), (240, 0), (240, 240), (0, 240)],
                quantity=2,
            ),
            ContainerSpec(
                id="L",
                length=346,
                cross_section=[(0, 0), (240, 0), (240, 160), (0, 160)],
                quantity=6,
            ),
        ]
        boxes = [
            BoxSpec(id="BOX-A", length=128, width=116, height=146, quantity=7),
            BoxSpec(id="BOX-B", length=189, width=96, height=115, quantity=8),
            BoxSpec(id="BOX-C", length=124, width=116, height=106, quantity=14),
            BoxSpec(id="BOX-D", length=124, width=124, height=109, quantity=12),
            BoxSpec(id="BOX-E", length=108, width=107, height=106, quantity=7),
            BoxSpec(id="BOX-F", length=107, width=107, height=104, quantity=7),
            BoxSpec(id="BOX-G", length=107, width=107, height=105, quantity=29),
            BoxSpec(id="BOX-H", length=226, width=150, height=179, quantity=2),
            BoxSpec(id="BOX-I", length=107, width=107, height=68, quantity=1),
            BoxSpec(id="BOX-J", length=107, width=107, height=86, quantity=1),
            BoxSpec(id="BOX-L", length=107, width=107, height=87, quantity=1),
            BoxSpec(id="BOX-M", length=120, width=100, height=119, quantity=1),
            BoxSpec(id="BOX-N", length=120, width=100, height=148, quantity=1),
            BoxSpec(id="BOX-O", length=41, width=41, height=14, quantity=2),
            BoxSpec(id="BOX-Q", length=107, width=107, height=51, quantity=1),
            BoxSpec(id="BOX-R", length=52, width=52, height=18, quantity=7),
            BoxSpec(id="BOX-S", length=122, width=102, height=108, quantity=6),
            BoxSpec(id="BOX-T", length=102, width=100, height=109, quantity=1),
            BoxSpec(id="BOX-U", length=67, width=58, height=42, quantity=48),
            BoxSpec(id="BOX-V", length=122, width=104, height=143, quantity=31),
            BoxSpec(id="BOX-W", length=120, width=112, height=159, quantity=7),
            BoxSpec(id="BOX-X", length=140, width=110, height=105, quantity=10),
            BoxSpec(id="BOX-Y", length=190, width=98, height=107, quantity=7),
            BoxSpec(id="BOX-Z", length=116, width=79, height=64, quantity=3),
        ]

        for search_mode in ("balanced", "high_utilization"):
            for objective in ("maximize_count", "maximize_volume"):
                problem = MultiContainerPackingInput(
                    containers=containers,
                    boxes=boxes,
                    objective=objective,
                    search_mode=search_mode,
                )
                if search_mode == "balanced":
                    self.assertEqual(_global_search_limits(problem).box_type_candidates, 3)
                result = pack_multi_profile(problem)
                self.assertEqual(result.loaded_count, 214)
                self.assertEqual(result.unloaded_count, 0)
                self.assertEqual(result.used_volume, 264257689)
                self.assertTrue(result.validation_passed)

        # 还原历史中拆开的等价行，确保输入表示变化不会改变均衡模式结果。
        split_boxes = [box for box in boxes if box.id != "BOX-G"] + [
            BoxSpec(id="BOX-G", length=107, width=107, height=105, quantity=6),
            BoxSpec(id="BOX-K", length=107, width=107, height=105, quantity=16),
            BoxSpec(id="BOX-P", length=107, width=107, height=105, quantity=7),
        ]
        split_result = pack_multi_profile(
            MultiContainerPackingInput(
                containers=containers,
                boxes=split_boxes,
                objective="maximize_count",
                search_mode="balanced",
            )
        )
        self.assertEqual((split_result.loaded_count, split_result.unloaded_count), (214, 0))

    def test_pack_multi_profile_obeys_required_container_types(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="ULD-B",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(
                    id="VIP",
                    length=10,
                    width=10,
                    height=10,
                    quantity=1,
                    rotatable=False,
                    required_container_types=("ULD-B",),
                )
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 1)
        self.assertEqual(result.unloaded_count, 0)
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"ULD-A-001": [], "ULD-B-001": ["VIP"]},
        )
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_marks_height_swapped_placements(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=200,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=1,
                )
            ],
            boxes=[
                BoxSpec(
                    id="UPRIGHT",
                    length=50,
                    width=50,
                    height=150,
                    quantity=1,
                    full_rotatable=True,
                )
            ],
            search_mode="fast",
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 1)
        self.assertTrue(result.validation_passed)
        placement = result.containers[0].result.placements[0]
        self.assertTrue(placement.height_swapped)
        self.assertEqual((placement.length, placement.width, placement.height), (150, 50, 50))

    def test_pack_multi_profile_prioritizes_required_container_type_boxes(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="TARGET",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="SMALL",
                    length=5,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(
                    id="FLEX",
                    length=10,
                    width=10,
                    height=10,
                    quantity=1,
                    rotatable=False,
                ),
                BoxSpec(
                    id="VIP",
                    length=10,
                    width=10,
                    height=5,
                    quantity=1,
                    rotatable=False,
                    required_container_types=("TARGET",),
                ),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 1)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("VIP", 1)])
        self.assertEqual([(item.box_id, item.quantity) for item in result.unloaded], [("FLEX", 1)])
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"TARGET-001": ["VIP"], "SMALL-001": []},
        )
        self.assertTrue(result.validation_passed)

    def test_multi_container_input_rejects_unknown_required_container_type(self):
        with self.assertRaisesRegex(PackingInputError, "required_container_types"):
            MultiContainerPackingInput(
                containers=[
                    ContainerSpec(
                        id="ULD-A",
                        length=10,
                        cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                        quantity=1,
                    )
                ],
                boxes=[
                    BoxSpec(
                        id="VIP",
                        length=10,
                        width=10,
                        height=10,
                        quantity=1,
                        rotatable=False,
                        required_container_types=("ULD-B",),
                    )
                ],
            )

    def test_pack_multi_profile_distributes_boxes_across_container_instances(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=60,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=2,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=60, width=50, height=30, quantity=2, rotatable=False)],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 0)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("BOX-A", 2)])
        self.assertEqual([container.container_id for container in result.containers], ["RECT-001", "RECT-002"])
        self.assertEqual([container.result.loaded_count for container in result.containers], [1, 1])
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_reports_remaining_boxes_as_unloaded(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=60,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=60, width=50, height=30, quantity=2, rotatable=False)],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 1)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual([(item.box_id, item.quantity, item.reason) for item in result.unloaded], [("BOX-A", 1, "no feasible space across containers")])

    def test_pack_multi_profile_keeps_duplicate_uld_type_instance_ids_unique(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD",
                    length=60,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="ULD",
                    length=60,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=1,
                ),
            ],
            boxes=[BoxSpec(id="BOX-A", length=60, width=50, height=30, quantity=2, rotatable=False)],
        )

        result = pack_multi_profile(problem)

        self.assertEqual([container.container_id for container in result.containers], ["ULD-001", "ULD-002"])
        self.assertEqual([container.result.loaded_count for container in result.containers], [1, 1])

    def test_pack_multi_profile_tries_multiple_uld_orders_to_improve_used_volume(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="BIG",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="SMALL",
                    length=5,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(id="LONG", length=10, width=10, height=10, quantity=1, rotatable=False),
                BoxSpec(id="SHORT", length=5, width=10, height=10, quantity=2, rotatable=False),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.used_volume, 1500)
        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual(
            [(item.box_id, item.quantity) for item in result.loaded],
            [("LONG", 1), ("SHORT", 1)],
        )
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"BIG-001": ["LONG"], "SMALL-001": ["SHORT"]},
        )
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_prioritizes_constrained_uld_before_flexible_uld(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="FLEX",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="LOW",
                    length=10,
                    cross_section=[(0, 0), (20, 0), (20, 5), (0, 5)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(id="ALT", length=10, width=10, height=10, quantity=1, rotatable=False),
                BoxSpec(id="SHARED", length=10, width=10, height=5, quantity=2, rotatable=False),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.used_volume, 2000)
        self.assertEqual(result.loaded_count, 3)
        self.assertEqual(result.unloaded_count, 0)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("ALT", 1), ("SHARED", 2)])
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"FLEX-001": ["ALT"], "LOW-001": ["SHARED", "SHARED"]},
        )
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_uses_global_beam_search_to_keep_non_greedy_assignments(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="C1",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="C2",
                    length=10,
                    cross_section=[(0, 0), (20, 0), (20, 5), (0, 5)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(id="A", length=10, width=10, height=5, quantity=1, rotatable=False),
                BoxSpec(id="B", length=5, width=10, height=10, quantity=1, rotatable=False),
                BoxSpec(id="C", length=6, width=12, height=3, quantity=1, rotatable=False),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.used_volume, 1000)
        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("A", 1), ("B", 1)])
        self.assertEqual([(item.box_id, item.quantity) for item in result.unloaded], [("C", 1)])
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"C1-001": ["B"], "C2-001": ["A"]},
        )
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_handles_field_like_mixed_air_cargo_manifest(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=318,
                    cross_section=[(0, 0), (224, 0), (224, 115), (178, 163), (0, 163)],
                    quantity=1,
                ),
                ContainerSpec(
                    id="ULD-B",
                    length=244,
                    cross_section=[(0, 0), (156, 0), (156, 114), (124, 153), (0, 153)],
                    quantity=1,
                ),
            ],
            boxes=[
                BoxSpec(id="MAIL-TRAY", length=60, width=40, height=35, quantity=12, rotatable=True),
                BoxSpec(id="E-COM-CARTON", length=80, width=60, height=45, quantity=8, rotatable=True),
                BoxSpec(id="SPARE-PART-CASE", length=120, width=80, height=55, quantity=3, rotatable=True),
                BoxSpec(id="TALL-CARTON", length=70, width=50, height=90, quantity=2, rotatable=True),
                BoxSpec(id="OVERSIZE-TALL", length=90, width=60, height=170, quantity=1, rotatable=True),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 25)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual(result.used_volume, 4950000)
        self.assertEqual(
            [(item.box_id, item.quantity) for item in result.loaded],
            [("E-COM-CARTON", 8), ("MAIL-TRAY", 12), ("SPARE-PART-CASE", 3), ("TALL-CARTON", 2)],
        )
        self.assertEqual([(item.box_id, item.quantity) for item in result.unloaded], [("OVERSIZE-TALL", 1)])
        used_containers = [container for container in result.containers if container.result.loaded_count > 0]
        self.assertEqual([container.container_id for container in used_containers], ["ULD-A-001"])
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_keeps_repeated_quantity_results_monotonic_for_default_uld(self):
        def pack_default_quantity(quantity: int):
            return pack_multi_profile(
                MultiContainerPackingInput(
                    containers=[
                        ContainerSpec(
                            id="ULD-A",
                            length=300,
                            cross_section=[(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)],
                            quantity=1,
                        )
                    ],
                    boxes=[
                        BoxSpec(id="BOX-A", length=60, width=40, height=30, quantity=quantity, rotatable=True),
                    ],
                )
            )

        fifty_result = pack_default_quantity(50)
        two_hundred_result = pack_default_quantity(200)

        self.assertEqual(fifty_result.loaded_count, 50)
        self.assertGreaterEqual(two_hundred_result.loaded_count, 99)
        self.assertTrue(fifty_result.validation_passed)
        self.assertTrue(two_hundred_result.validation_passed)

    def test_pack_multi_profile_keeps_usable_candidate_points_for_many_uld_instances(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=300,
                    cross_section=[(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)],
                    quantity=12,
                )
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=60, width=40, height=30, quantity=1200, rotatable=True),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertGreaterEqual(result.loaded_count, 700)
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_packs_repeated_boxes_into_fewer_uld_before_opening_new_ones(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-A",
                    length=300,
                    cross_section=[(0, 0), (220, 0), (220, 110), (170, 160), (0, 160)],
                    quantity=12,
                )
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=60, width=40, height=30, quantity=200, rotatable=True),
            ],
        )

        result = pack_multi_profile(problem)

        used_containers = [container for container in result.containers if container.result.loaded_count > 0]
        self.assertEqual(result.loaded_count, 200)
        self.assertLessEqual(len(used_containers), 3)
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_refills_fragmented_space_with_remaining_small_boxes(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=12,
                )
            ],
            boxes=[
                BoxSpec(id="BIG", length=60, width=50, height=50, quantity=50, rotatable=True),
                BoxSpec(id="SMALL", length=20, width=20, height=20, quantity=800, rotatable=True),
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 850)
        self.assertEqual(result.unloaded_count, 0)
        self.assertTrue(result.validation_passed)

    def test_pack_multi_profile_keeps_layer_candidates_for_many_uld_and_box_types(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="ULD-LARGE",
                    length=318,
                    cross_section=[(0, 0), (224, 0), (224, 115), (178, 163), (0, 163)],
                    quantity=10,
                ),
                ContainerSpec(
                    id="ULD-MEDIUM",
                    length=244,
                    cross_section=[(0, 0), (156, 0), (156, 114), (124, 153), (0, 153)],
                    quantity=10,
                ),
            ],
            boxes=[
                BoxSpec(
                    id=f"BOX-{index:02d}",
                    length=40 + (index % 5) * 10,
                    width=30 + (index % 4) * 10,
                    height=25 + (index % 6) * 5,
                    quantity=40,
                    rotatable=True,
                )
                for index in range(25)
            ],
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 1000)
        self.assertEqual(result.unloaded_count, 0)
        self.assertGreaterEqual(result.volume_utilization, 0.58)
        self.assertTrue(result.validation_passed)

    def test_global_search_limits_candidate_box_types_for_large_type_sets(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=100,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=1,
                )
            ],
            boxes=[
                BoxSpec(id=f"BOX-{index:02d}", length=index + 1, width=10, height=10, quantity=1, rotatable=False)
                for index in range(MAX_GLOBAL_BOX_TYPE_CANDIDATES + 5)
            ],
        )
        box_by_id = {box.id: box for box in problem.boxes}

        candidates = _candidate_box_types(problem, _initial_global_state(problem), box_by_id)

        self.assertEqual(len(candidates), min(MAX_GLOBAL_BOX_TYPE_CANDIDATES, _global_search_limits(problem).box_type_candidates))
        self.assertEqual(candidates[0].id, f"BOX-{MAX_GLOBAL_BOX_TYPE_CANDIDATES + 4:02d}")

    def test_global_search_batches_repeated_box_placements_for_large_quantities(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="LONG",
                    length=100,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=10, width=10, height=10, quantity=20, rotatable=False)],
        )
        box_by_id = {box.id: box for box in problem.boxes}

        branches = _global_placement_branches(problem, _initial_global_state(problem), box_by_id)

        self.assertGreaterEqual(max(len(branch.containers[0].placements) for branch in branches), MAX_BATCH_PLACEMENTS)

    def test_global_search_limits_candidate_containers_for_large_uld_sets(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id=f"ULD-{index:02d}",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                )
                for index in range(MAX_GLOBAL_CONTAINER_CANDIDATES + 5)
            ],
            boxes=[BoxSpec(id="BOX-A", length=10, width=10, height=10, quantity=1, rotatable=False)],
        )

        options = _container_candidate_options(problem, _initial_global_state(problem), problem.boxes[0])

        expected_count = min(MAX_GLOBAL_CONTAINER_CANDIDATES, _global_search_limits(problem).container_candidates)
        self.assertEqual(len(options), expected_count)
        self.assertEqual([option[1].container_id for option in options], [f"ULD-{index:02d}-001" for index in range(expected_count)])

    def test_global_search_limits_follow_search_mode(self):
        containers = [
            ContainerSpec(
                id="RECT",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                quantity=1,
            )
        ]
        boxes = [BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=20)]

        fast_limits = _global_search_limits(MultiContainerPackingInput(containers=containers, boxes=boxes, search_mode="fast"))
        balanced_limits = _global_search_limits(MultiContainerPackingInput(containers=containers, boxes=boxes, search_mode="balanced"))
        high_limits = _global_search_limits(
            MultiContainerPackingInput(containers=containers, boxes=boxes, search_mode="high_utilization")
        )

        self.assertLess(fast_limits.beam_width, balanced_limits.beam_width)
        self.assertLess(fast_limits.global_branches_per_state, balanced_limits.global_branches_per_state)
        self.assertLessEqual(fast_limits.box_type_candidates, balanced_limits.box_type_candidates)
        self.assertLessEqual(fast_limits.container_candidates, balanced_limits.container_candidates)
        self.assertLessEqual(fast_limits.placement_branches, balanced_limits.placement_branches)
        self.assertLessEqual(fast_limits.max_steps, balanced_limits.max_steps)
        self.assertLessEqual(fast_limits.max_free_spaces, balanced_limits.max_free_spaces)
        self.assertGreater(high_limits.beam_width, balanced_limits.beam_width)
        self.assertGreater(high_limits.placement_branches, balanced_limits.placement_branches)
        self.assertGreater(high_limits.max_free_spaces, balanced_limits.max_free_spaces)

        large_containers = [replace(containers[0], quantity=12)]
        large_fast = _global_search_limits(
            MultiContainerPackingInput(containers=large_containers, boxes=boxes, search_mode="fast")
        )
        large_balanced = _global_search_limits(
            MultiContainerPackingInput(containers=large_containers, boxes=boxes, search_mode="balanced")
        )
        large_high = _global_search_limits(
            MultiContainerPackingInput(containers=large_containers, boxes=boxes, search_mode="high_utilization")
        )
        self.assertEqual(large_fast.beam_width, 2)
        self.assertEqual(large_balanced.beam_width, 4)
        self.assertEqual(large_high.beam_width, 10)

    def test_extra_large_search_uses_bounded_but_stronger_mode_budgets(self):
        containers = [
            ContainerSpec(
                id="RECT",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                quantity=12,
            )
        ]
        boxes = [BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=500)]

        problems = {
            mode: MultiContainerPackingInput(containers=containers, boxes=boxes, search_mode=mode)
            for mode in ("fast", "balanced", "high_utilization")
        }
        fast = _global_search_limits(problems["fast"])
        balanced = _global_search_limits(problems["balanced"])
        high = _global_search_limits(problems["high_utilization"])

        self.assertTrue(profile_packer._is_extra_large_problem(problems["balanced"]))
        self.assertLess(fast.beam_width, balanced.beam_width)
        self.assertLess(balanced.beam_width, high.beam_width)
        self.assertLessEqual(fast.max_steps, balanced.max_steps)
        self.assertLess(balanced.max_steps, high.max_steps)
        self.assertLess(balanced.max_free_spaces, high.max_free_spaces)
        self.assertEqual((fast.max_steps, balanced.max_steps, high.max_steps), (80, 80, 120))

    def test_extra_large_round_plan_keeps_representative_independent_frontiers(self):
        base = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=12,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=500)],
        )

        balanced = profile_packer._round_plan(replace(base, search_mode="balanced"))
        high = profile_packer._round_plan(replace(base, search_mode="high_utilization"))

        self.assertEqual(
            balanced,
            [(0, None), (4, None), (profile_packer.FAST_COMPATIBLE_VARIANT_OFFSET, None), (100, None)],
        )
        for round_spec in (
            (profile_packer.BALANCED_COMPATIBLE_VARIANT_OFFSET, None),
            (profile_packer.BALANCED_COMPATIBLE_VARIANT_OFFSET + 4, None),
            (profile_packer.FAST_COMPATIBLE_VARIANT_OFFSET, None),
            (
                profile_packer.ALTERNATE_OBJECTIVE_VARIANT_OFFSET
                + profile_packer.BALANCED_COMPATIBLE_VARIANT_OFFSET,
                None,
            ),
        ):
            self.assertIn(round_spec, high)
        self.assertEqual(len(high), 6)

    def test_large_uld_count_with_214_boxes_keeps_full_round_plan(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=22,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=214)],
            search_mode="balanced",
        )

        self.assertFalse(profile_packer._is_extra_large_problem(problem))
        self.assertEqual(len(profile_packer._round_plan(problem)), 10)

    def test_container_geometry_helpers_are_reused_for_the_same_state(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=2)],
        )
        state = _initial_global_state(problem).containers[0]

        self.assertIs(state.get_scan_index(), state.get_scan_index())
        self.assertIs(
            profile_packer._profile_input_for_container(problem, state),
            profile_packer._profile_input_for_container(problem, state),
        )

    def test_bounded_active_container_scan_expands_when_first_batch_is_infeasible(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=12,
                )
            ],
            boxes=[BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=500)],
            search_mode="balanced",
        )
        state = _initial_global_state(problem)
        pool = list(enumerate(state.containers[:6]))
        limits = _global_search_limits(problem)
        expected = [(pool[4][0], pool[4][1], MagicMock(), [MagicMock()])]

        with patch.object(
            profile_packer,
            "_container_options_from_pool",
            side_effect=[[], expected],
        ) as scan:
            actual = profile_packer._bounded_active_container_options(
                problem,
                pool,
                problem.boxes[0],
                "BOX-A-001",
                limits,
                None,
            )

        self.assertEqual(actual, expected)
        self.assertEqual(scan.call_count, 2)
        self.assertTrue(all(len(call.args[1]) <= limits.container_candidates * 2 for call in scan.call_args_list))

    def test_extra_large_rescue_bounds_box_and_container_attempts(self):
        boxes = [
            BoxSpec(id=f"BOX-{index:02d}", length=10 + index, width=10, height=10, quantity=50)
            for index in range(10)
        ]
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=120,
                    cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                    quantity=12,
                )
            ],
            boxes=boxes,
            search_mode="fast",
        )
        state = _initial_global_state(problem)
        active_containers = []
        for index, container in enumerate(state.containers):
            placement = BoxPlacement(
                box_id=boxes[0].id,
                instance_id=f"SEED-{index}",
                x=0,
                y=0,
                z=0,
                length=1,
                width=1,
                height=1,
            )
            active_containers.append(
                replace(container, placements=[placement], used_volume=index + 1)
            )
        state = replace(state, containers=active_containers)

        with patch.object(profile_packer, "_rescue_box_into_container", return_value=None) as rescue:
            actual = profile_packer._rescue_unloaded_boxes(
                problem,
                state,
                {box.id: box for box in boxes},
                _global_search_limits(problem),
            )

        self.assertIs(actual, state)
        self.assertEqual(
            rescue.call_count,
            profile_packer.EXTRA_LARGE_RESCUE_BOX_TYPES
            * profile_packer.EXTRA_LARGE_RESCUE_CONTAINERS,
        )
        self.assertEqual(profile_packer._extra_large_rescue_limits("fast"), (6, 3))
        self.assertEqual(profile_packer._extra_large_rescue_limits("balanced"), (48, 6))
        self.assertEqual(profile_packer._extra_large_rescue_limits("high_utilization"), (64, 8))

    def test_high_beam_keeps_better_volume_path_when_extra_candidates_expand(self):
        containers = [
            ContainerSpec(
                id="R",
                length=169,
                cross_section=[(0, 0), (110, 0), (110, 90), (0, 90)],
                quantity=2,
            ),
            ContainerSpec(
                id="Q",
                length=145,
                cross_section=[(0, 0), (120, 0), (120, 75), (70, 110), (0, 110)],
                quantity=2,
            ),
        ]
        boxes = [
            BoxSpec(id="B0", length=76, width=70, height=53, quantity=5, rotatable=False),
            BoxSpec(id="B1", length=70, width=57, height=42, quantity=6, full_rotatable=True),
            BoxSpec(id="B2", length=42, width=38, height=32, quantity=8, required_container_types=("Q",)),
            BoxSpec(id="B3", length=37, width=59, height=47, quantity=6, rotatable=False),
            BoxSpec(id="B4", length=43, width=39, height=27, quantity=7),
            BoxSpec(id="B5", length=34, width=74, height=57, quantity=5),
            BoxSpec(id="B6", length=37, width=42, height=70, quantity=4, rotatable=False),
        ]
        balanced = pack_multi_profile(
            MultiContainerPackingInput(
                containers=containers,
                boxes=boxes,
                objective="maximize_volume",
                search_mode="balanced",
            )
        )
        high = pack_multi_profile(
            MultiContainerPackingInput(
                containers=containers,
                boxes=boxes,
                objective="maximize_volume",
                search_mode="high_utilization",
            )
        )

        self.assertEqual((balanced.loaded_count, balanced.used_volume), (38, 4235895))
        self.assertEqual((high.loaded_count, high.used_volume), (39, 4524034))
        self.assertGreaterEqual(high.loaded_count, balanced.loaded_count)
        self.assertGreaterEqual(high.used_volume, balanced.used_volume)
        self.assertTrue(high.validation_passed)

    def test_local_rearrange_is_noop_outside_high_utilization_mode(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=100,
                    cross_section=[(0, 0), (60, 0), (60, 50), (0, 50)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=20, width=20, height=20, quantity=4)],
            search_mode="balanced",
        )
        box_by_id = {box.id: box for box in problem.boxes}
        limits = _global_search_limits(problem)
        initial_state = _initial_global_state(problem)

        result_state = _local_rearrange_state(problem, initial_state, box_by_id, limits)

        self.assertIs(result_state, initial_state)

    def test_worst_container_indices_picks_lowest_utilization_and_skips_empties(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=100,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=3,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=50, width=50, height=50, quantity=1)],
        )
        state = _initial_global_state(problem)
        big_box = BoxSpec(id="BIG", length=50, width=50, height=50, quantity=1)
        small_box = BoxSpec(id="SMALL", length=10, width=10, height=10, quantity=1)
        from cargo_loading.profile_models import BoxPlacement

        state.containers[0].placements.append(
            BoxPlacement("BIG", "BIG-001", 0, 0, 0, big_box.length, big_box.width, big_box.height)
        )
        state.containers[1].placements.append(
            BoxPlacement("SMALL", "SMALL-001", 0, 0, 0, small_box.length, small_box.width, small_box.height)
        )

        indices = _worst_container_indices(state, count=2, skip_indices=set())

        self.assertEqual(indices, [1, 0])

    def test_ruin_and_recreate_strips_top_layer_and_keeps_bottom(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=100,
                    cross_section=[(0, 0), (50, 0), (50, 50), (0, 50)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=50, width=50, height=20, quantity=2)],
            search_mode="high_utilization",
        )
        box_by_id = {box.id: box for box in problem.boxes}
        limits = _global_search_limits(problem)
        state = _initial_global_state(problem)
        from cargo_loading.profile_models import BoxPlacement

        bottom = BoxPlacement("BOX", "BOX-001", 0, 0, 0, 50, 50, 20)
        top = BoxPlacement("BOX", "BOX-002", 0, 0, 20, 50, 50, 20)
        state.containers[0].placements.extend([bottom, top])
        state.remaining_counter["BOX"] = 0

        new_state = _ruin_and_recreate(problem, state, box_by_id, limits, [0])

        placements = new_state.containers[0].placements
        self.assertGreaterEqual(len(placements), 1)
        self.assertTrue(any(placement.z == 0 for placement in placements))
        self.assertEqual(new_state.remaining_counter["BOX"], 2 - len(placements))

    def test_pack_multi_profile_high_utilization_does_not_regress(self):
        problem_balanced = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=100,
                    cross_section=[(0, 0), (60, 0), (60, 50), (0, 50)],
                    quantity=2,
                )
            ],
            boxes=[
                BoxSpec(id="BIG", length=60, width=50, height=30, quantity=2),
                BoxSpec(id="MID", length=30, width=30, height=20, quantity=4),
            ],
            search_mode="balanced",
        )
        problem_high = MultiContainerPackingInput(
            containers=problem_balanced.containers,
            boxes=problem_balanced.boxes,
            search_mode="high_utilization",
        )

        balanced_result = pack_multi_profile(problem_balanced)
        high_result = pack_multi_profile(problem_high)

        self.assertGreaterEqual(high_result.used_volume, balanced_result.used_volume)
        self.assertLessEqual(high_result.unloaded_count, balanced_result.unloaded_count)
        self.assertTrue(high_result.validation_passed)

    def test_top_and_partitioned_layer_rearrange_improve_field_layout_and_keep_ids_unique(self):
        # 两个连续现场反例：Q5-001 需要旋转顶层 BOX-E；Q5-002 需要把底层
        # 从 2x3 整行网格改成左侧 1x3、右侧 2x2 的分块混排。
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="Q5",
                    length=306,
                    cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)],
                    quantity=2,
                ),
                ContainerSpec(
                    id="Q4",
                    length=306,
                    cross_section=[(0, 0), (240, 0), (240, 130), (120, 290), (0, 290)],
                    quantity=2,
                ),
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=102, width=90, height=168, quantity=1),
                BoxSpec(id="BOX-B", length=102, width=90, height=156, quantity=18),
                BoxSpec(id="BOX-C", length=102, width=90, height=113, quantity=1),
                BoxSpec(id="BOX-D", length=102, width=90, height=137, quantity=1),
                BoxSpec(id="BOX-E", length=120, width=80, height=121, quantity=20),
                BoxSpec(id="BOX-G", length=80, width=80, height=32, quantity=1),
            ],
            search_mode="high_utilization",
        )

        result = _pack_multi_profile_variant(problem, 0)

        self.assertEqual(result.loaded_count, 41)
        self.assertEqual(result.used_volume, 52014140)
        self.assertEqual(
            [(item.box_id, item.quantity) for item in result.unloaded],
            [("BOX-C", 1)],
        )
        q5_001 = next(container for container in result.containers if container.container_id == "Q5-001")
        top_box_e = sorted(
            (
                placement.x,
                placement.y,
                placement.z,
                placement.length,
                placement.width,
                placement.height,
            )
            for placement in q5_001.result.placements
            if placement.box_id == "BOX-E" and placement.z == 156
        )
        self.assertIn((120, 0, 156, 80, 120, 121), top_box_e)
        q5_002 = next(container for container in result.containers if container.container_id == "Q5-002")
        floor_box_e = sorted(
            (placement.x, placement.y, placement.length, placement.width)
            for placement in q5_002.result.placements
            if placement.box_id == "BOX-E" and placement.z == 0
        )
        self.assertEqual(
            floor_box_e,
            [
                (0, 0, 120, 80),
                (0, 80, 120, 80),
                (0, 160, 120, 80),
                (120, 0, 80, 120),
                (120, 120, 80, 120),
                (200, 0, 80, 120),
                (200, 120, 80, 120),
            ],
        )
        instance_ids = [
            placement.instance_id
            for container in result.containers
            for placement in container.result.placements
        ]
        self.assertEqual(len(instance_ids), len(set(instance_ids)))
        self.assertTrue(result.validation_passed)

    def test_partitioned_layer_layout_packs_seven_rotatable_boxes(self):
        box = BoxSpec(id="BOX-E", length=120, width=80, height=121, quantity=7)
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="Q5",
                    length=306,
                    cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)],
                    quantity=1,
                )
            ],
            boxes=[box],
            search_mode="high_utilization",
        )
        state = _initial_global_state(problem)
        container = state.containers[0]
        profile_input = profile_packer._profile_input_for_container(problem, container)

        row_layout = profile_packer._layer_layout_in_space(
            box,
            container.free_spaces[0],
            profile_input,
            max_count=7,
        )
        partitioned_layout = profile_packer._layer_layout_in_space(
            box,
            container.free_spaces[0],
            profile_input,
            max_count=7,
            include_x_partitions=True,
        )

        self.assertEqual(len(row_layout), 6)
        self.assertEqual(len(partitioned_layout), 7)
        self.assertEqual(profile_packer.validate_profile_packing(profile_input, partitioned_layout), [])

    def test_min_support_ratio_relaxes_in_high_utilization_mode(self):
        self.assertEqual(_min_support_ratio_for_mode("fast"), MIN_BOTTOM_SUPPORT_RATIO)
        self.assertEqual(_min_support_ratio_for_mode("balanced"), MIN_BOTTOM_SUPPORT_RATIO)
        self.assertEqual(_min_support_ratio_for_mode("high_utilization"), MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION)
        self.assertLess(MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION, MIN_BOTTOM_SUPPORT_RATIO)

    def test_high_utilization_still_has_stronger_budget_than_balanced(self):
        containers = [
            ContainerSpec(
                id="RECT",
                length=120,
                cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
                quantity=2,
            )
        ]
        boxes = [BoxSpec(id="BOX-A", length=40, width=40, height=40, quantity=10)]

        balanced_problem = MultiContainerPackingInput(
            containers=containers, boxes=boxes, search_mode="balanced"
        )
        high_problem = MultiContainerPackingInput(
            containers=containers, boxes=boxes, search_mode="high_utilization"
        )

        balanced_result = pack_multi_profile(balanced_problem)
        high_result = pack_multi_profile(high_problem)
        variant_0_result = _pack_multi_profile_variant(high_problem, 0)

        self.assertGreaterEqual(high_result.loaded_count, balanced_result.loaded_count)
        self.assertGreaterEqual(high_result.used_volume, variant_0_result.used_volume)

    def test_balanced_parallel_rounds_match_serial_round_selection(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=10, width=10, height=10, quantity=4)],
            search_mode="balanced",
        )
        rounds = profile_packer._round_plan(problem)
        serial_results = [
            profile_packer._pack_multi_profile_round(problem, variant, seed)
            for variant, seed in rounds
        ]
        expected = max(serial_results, key=lambda result: profile_packer._multi_result_score(problem, result))

        actual = pack_multi_profile(problem)

        self.assertEqual(len(rounds), 10)
        self.assertEqual(actual, expected)

    def test_round_plans_independently_include_lower_budget_frontiers(self):
        base = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=10, width=10, height=10, quantity=4)],
        )
        balanced_rounds = profile_packer._round_plan(replace(base, search_mode="balanced"))
        high_rounds = profile_packer._round_plan(replace(base, search_mode="high_utilization"))

        self.assertIn((profile_packer.FAST_COMPATIBLE_VARIANT_OFFSET, None), balanced_rounds)
        self.assertIn((profile_packer.FAST_COMPATIBLE_VARIANT_OFFSET, None), high_rounds)
        for variant, seed in ((0, None), (4, None), (0, 1), (0, 2)):
            self.assertIn(
                (profile_packer.BALANCED_COMPATIBLE_VARIANT_OFFSET + variant, seed),
                high_rounds,
            )
        for variant, seed in balanced_rounds[:5]:
            self.assertIn(
                (profile_packer.ALTERNATE_OBJECTIVE_VARIANT_OFFSET + variant, seed),
                balanced_rounds,
            )

    def test_parallel_rounds_use_at_most_three_spawn_workers(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=10, width=10, height=10, quantity=1)],
            search_mode="high_utilization",
        )
        rounds = profile_packer._round_plan(problem)
        round_result = _pack_multi_profile_variant(problem, 0)
        futures = [MagicMock() for _ in rounds]
        for future in futures:
            future.result.return_value = round_result

        with patch.object(profile_packer, "ProcessPoolExecutor") as executor_class:
            executor = executor_class.return_value.__enter__.return_value
            executor.submit.side_effect = futures

            result = profile_packer._best_of_rounds(problem, rounds)

        self.assertEqual(result, round_result)
        self.assertGreater(len(rounds), profile_packer.MAX_PARALLEL_SEARCH_PROCESSES)
        self.assertEqual(executor_class.call_args.kwargs["max_workers"], 3)
        self.assertEqual(executor_class.call_args.kwargs["mp_context"].get_start_method(), "spawn")
        self.assertEqual(executor.submit.call_count, len(rounds))

    def test_fast_mode_does_not_start_process_pool(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=10, width=10, height=10, quantity=1)],
            search_mode="fast",
        )

        with patch.object(profile_packer, "ProcessPoolExecutor") as executor_class:
            result = pack_multi_profile(problem)

        executor_class.assert_not_called()
        self.assertEqual(result.loaded_count, 1)

    def test_parallel_round_failure_is_not_silently_ignored(self):
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=20,
                    cross_section=[(0, 0), (20, 0), (20, 20), (0, 20)],
                    quantity=1,
                )
            ],
            boxes=[BoxSpec(id="BOX", length=10, width=10, height=10, quantity=1)],
            search_mode="balanced",
        )
        failed_future = MagicMock()
        failed_future.result.side_effect = RuntimeError("worker failed")

        with patch.object(profile_packer, "ProcessPoolExecutor") as executor_class:
            executor = executor_class.return_value.__enter__.return_value
            executor.submit.return_value = failed_future

            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                profile_packer._best_of_rounds(problem, profile_packer._round_plan(problem))

    def test_volume_progress_path_uses_separate_frontier_from_standard_beam(self):
        container = ContainerSpec(
            id="RECT",
            length=100,
            cross_section=[(0, 0), (100, 0), (100, 100), (0, 100)],
            quantity=1,
        )
        problem = MultiContainerPackingInput(
            containers=[container],
            boxes=[BoxSpec(id="BOX", length=1, width=1, height=1, quantity=10)],
        )

        def state(name: str, remaining: int, used_volume: float):
            placement = BoxPlacement(
                box_id="BOX",
                instance_id=name,
                x=0,
                y=0,
                z=0,
                length=used_volume,
                width=1,
                height=1,
            )
            return profile_packer.GlobalPackingState(
                containers=[
                    profile_packer.ContainerState(
                        spec=container,
                        container_id="RECT-001",
                        placements=[placement],
                        free_spaces=[],
                    )
                ],
                remaining_counter=profile_packer.Counter({"BOX": remaining}),
            )

        count_leader = state("COUNT-LEADER", remaining=1, used_volume=10)
        count_runner_up = state("COUNT-RUNNER-UP", remaining=2, used_volume=20)
        volume_leader = state("VOLUME-LEADER", remaining=3, used_volume=90)

        selected = profile_packer._select_global_beam_states(
            problem,
            [count_leader, count_runner_up, volume_leader],
            beam_width=2,
        )
        supplemental = profile_packer._supplemental_volume_progress_state(
            problem,
            [count_leader, count_runner_up, volume_leader],
            selected,
            beam_width=2,
        )

        self.assertEqual(selected, [count_leader, count_runner_up])
        self.assertIs(supplemental, volume_leader)

    def test_layer_building_reaches_hand_verified_pga_optimum(self):
        # 现场反例：PGA 五边形截面 + 27 个可旋转 BOX-A。手算最优是
        # 第一层 12 个（两行 95x114）、第二层 11 个（6+5 混排）、顶层 B 和 C。
        # 逐箱贪心只能到每层 10 个；层构建必须一步给出混合朝向行组合。
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="PGA",
                    length=600,
                    cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)],
                    quantity=1,
                )
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=114, width=95, height=102, quantity=27),
                BoxSpec(id="BOX-B", length=431, width=41, height=33, quantity=1),
                BoxSpec(id="BOX-C", length=325, width=83, height=42, quantity=1),
            ],
            search_mode="fast",
        )

        result = pack_multi_profile(problem)

        loaded_by_id = {item.box_id: item.quantity for item in result.loaded}
        self.assertEqual(loaded_by_id, {"BOX-A": 23, "BOX-B": 1, "BOX-C": 1})
        self.assertEqual(result.unloaded_count, 4)
        self.assertTrue(result.validation_passed)

    def test_rescue_pass_recovers_constrained_long_box(self):
        # BOX-B 长 431，只有 PGA 装得下。beam 中途大批量分支会把先装 B 的
        # 状态挤掉，收尾腾挪必须把 B 救回来，所有箱子全部装载。
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(id="Q7", length=306, cross_section=[(0, 0), (240, 0), (240, 240), (120, 290), (0, 290)], quantity=1),
                ContainerSpec(id="Q6", length=306, cross_section=[(0, 0), (240, 0), (240, 240), (0, 240)], quantity=1),
                ContainerSpec(id="L", length=346, cross_section=[(0, 0), (240, 0), (240, 160), (0, 160)], quantity=1),
                ContainerSpec(id="PGA", length=600, cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)], quantity=1),
                ContainerSpec(id="Q5", length=306, cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)], quantity=1),
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=114, width=95, height=102, quantity=27),
                BoxSpec(id="BOX-B", length=431, width=41, height=33, quantity=1),
                BoxSpec(id="BOX-C", length=325, width=83, height=42, quantity=1),
                BoxSpec(id="BOX-D", length=133, width=100, height=174, quantity=1),
                BoxSpec(id="BOX-E", length=125, width=105, height=103, quantity=1),
            ],
            search_mode="balanced",
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.unloaded_count, 0)
        used_containers = [container for container in result.containers if container.result.placements]
        self.assertLessEqual(len(used_containers), 2)
        self.assertTrue(result.validation_passed)

    def test_max_volume_combo_fills_column_height_exactly(self):
        # D+D+J 总高 101+101+88 = 290，正好顶满 Q5 截面左侧全高带
        box_d = BoxSpec(id="BOX-D", length=190, width=98, height=101, quantity=2)
        box_j = BoxSpec(id="BOX-J", length=108, width=108, height=88, quantity=1)

        combo = _max_volume_combo([(box_d, 190, 98, 101, 2), (box_j, 108, 108, 88, 1)], 290)

        counts = {spec.id: count for spec, _, _, _, count in combo}
        self.assertEqual(counts, {"BOX-D": 2, "BOX-J": 1})

    def test_column_building_improves_q5_height_band_case(self):
        # 现场反例：6 个 Q5 装 12 种箱型共 73 箱。矮箱 A 整层会占满
        # 截面全高带，高箱无处可叠。立柱墙分支让矮箱让出全高带后，
        # 立柱墙最初让 fast 从 62 提升到 67 箱；严格按体积目标评分后，
        # 当前方案选择 66 个更大的箱子，并获得更高装载体积。
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(id="Q5", length=306, cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)], quantity=6),
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=132, width=114, height=63, quantity=32),
                BoxSpec(id="BOX-B", length=118, width=98, height=75, quantity=1),
                BoxSpec(id="BOX-C", length=110, width=120, height=130, quantity=3),
                BoxSpec(id="BOX-D", length=190, width=98, height=101, quantity=8),
                BoxSpec(id="BOX-E", length=120, width=100, height=132, quantity=5),
                BoxSpec(id="BOX-F", length=120, width=84, height=148, quantity=1),
                BoxSpec(id="BOX-G", length=120, width=80, height=50, quantity=1),
                BoxSpec(id="BOX-H", length=74, width=64, height=47, quantity=1),
                BoxSpec(id="BOX-I", length=108, width=108, height=71, quantity=1),
                BoxSpec(id="BOX-J", length=108, width=108, height=88, quantity=10),
                BoxSpec(id="BOX-K", length=108, width=108, height=106, quantity=7),
                BoxSpec(id="BOX-L", length=108, width=108, height=122, quantity=3),
            ],
            objective="maximize_volume",
            search_mode="fast",
        )

        result = pack_multi_profile(problem)

        self.assertEqual((result.loaded_count, result.used_volume), (66, 77431884))
        self.assertTrue(result.validation_passed)

    def test_beam_keeps_large_box_path_when_small_column_branch_advances_more_boxes(self):
        container = ContainerSpec(
            id="Q7",
            length=306,
            cross_section=[(0, 0), (240, 0), (240, 240), (120, 290), (0, 290)],
            quantity=1,
        )
        dimensions = [
            (118, 80, 225, 1),
            (118, 80, 225, 1),
            (118, 80, 225, 1),
            (118, 80, 225, 1),
            (118, 80, 225, 1),
            (40, 37, 19, 1),
            (48, 46, 17, 1),
            (118, 80, 225, 1),
            (59, 49, 46, 3),
            (118, 80, 225, 1),
        ]

        def solve(require_q7: bool):
            boxes = [
                BoxSpec(
                    id=f"BOX-{index:02d}",
                    length=length,
                    width=width,
                    height=height,
                    quantity=quantity,
                    required_container_types=("Q7",) if require_q7 and (length, width, height) == (118, 80, 225) else (),
                )
                for index, (length, width, height, quantity) in enumerate(dimensions)
            ]
            return pack_multi_profile(
                MultiContainerPackingInput(
                    containers=[container],
                    boxes=boxes,
                    search_mode="balanced",
                )
            )

        automatic_result = solve(require_q7=False)
        constrained_result = solve(require_q7=True)

        self.assertEqual(automatic_result.loaded_count, 12)
        self.assertEqual(automatic_result.unloaded_count, 0)
        self.assertEqual(constrained_result.loaded_count, 12)
        self.assertEqual(constrained_result.unloaded_count, 0)
        self.assertEqual(automatic_result.used_volume, constrained_result.used_volume)
        self.assertTrue(automatic_result.validation_passed)
        self.assertTrue(constrained_result.validation_passed)

    def test_beam_diversity_keeps_spread_layout_in_sloped_q7(self):
        # 现场反例：单个 Q7（斜边截面）装 12 箱，人工可行方案要求高箱沿长度方向
        # 铺满 306，矮箱双层退到斜边下的矮带。原 beam 在装载量相同时只比包围盒
        # 体积，把铺开布局整批淘汰，三种模式都只能装 11 箱。
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(id="Q7", length=306, cross_section=[(0, 0), (240, 0), (240, 240), (120, 291), (0, 291)], quantity=1),
            ],
            boxes=[
                BoxSpec(id="BOX-A", length=109, width=109, height=95, quantity=4),
                BoxSpec(id="BOX-B", length=106, width=69, height=99, quantity=3),
                BoxSpec(id="BOX-C", length=120, width=100, height=145, quantity=2),
                BoxSpec(id="BOX-D", length=112, width=112, height=123, quantity=1),
                BoxSpec(id="BOX-E", length=110, width=110, height=146, quantity=1),
                BoxSpec(id="BOX-F", length=124, width=100, height=154, quantity=1),
            ],
            search_mode="balanced",
        )

        result = pack_multi_profile(problem)

        self.assertEqual(result.loaded_count, 12)
        self.assertEqual(result.unloaded_count, 0)
        self.assertTrue(result.validation_passed)


if __name__ == "__main__":
    unittest.main()
