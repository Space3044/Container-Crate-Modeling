import unittest
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

        self.assertEqual(result.used_volume, 1000)
        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("SHORT", 2)])
        self.assertEqual(
            {
                container.container_id: [placement.box_id for placement in container.result.placements]
                for container in result.containers
            },
            {"BIG-001": ["SHORT", "SHORT"], "SMALL-001": []},
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
        self.assertGreater(high_limits.beam_width, balanced_limits.beam_width)
        self.assertGreater(high_limits.placement_branches, balanced_limits.placement_branches)
        self.assertGreater(high_limits.max_free_spaces, balanced_limits.max_free_spaces)

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

    def test_min_support_ratio_relaxes_in_high_utilization_mode(self):
        self.assertEqual(_min_support_ratio_for_mode("fast"), MIN_BOTTOM_SUPPORT_RATIO)
        self.assertEqual(_min_support_ratio_for_mode("balanced"), MIN_BOTTOM_SUPPORT_RATIO)
        self.assertEqual(_min_support_ratio_for_mode("high_utilization"), MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION)
        self.assertLess(MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION, MIN_BOTTOM_SUPPORT_RATIO)

    def test_pack_multi_profile_multistart_runs_variants_only_in_high_utilization(self):
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

        self.assertEqual(len(rounds), 3)
        self.assertEqual(actual, expected)

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

        combo = _max_volume_combo([(box_d, 190, 98, 2), (box_j, 108, 108, 1)], 290)

        counts = {spec.id: count for spec, _, _, count in combo}
        self.assertEqual(counts, {"BOX-D": 2, "BOX-J": 1})

    def test_column_building_improves_q5_height_band_case(self):
        # 现场反例：6 个 Q5 装 12 种箱型共 73 箱。矮箱 A 整层会占满
        # 截面全高带，高箱无处可叠。立柱墙分支让矮箱让出全高带后，
        # fast 档从 62 箱提升到 67 箱。
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
            search_mode="fast",
        )

        result = pack_multi_profile(problem)

        self.assertGreaterEqual(result.loaded_count, 67)
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


if __name__ == "__main__":
    unittest.main()
