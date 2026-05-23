import unittest

from cargo_loading.profile_models import BoxSpec, ContainerSpec, MultiContainerPackingInput
from cargo_loading.profile_packer import (
    MAX_BATCH_PLACEMENTS,
    MAX_GLOBAL_BOX_TYPE_CANDIDATES,
    MAX_GLOBAL_CONTAINER_CANDIDATES,
    _candidate_box_types,
    _container_candidate_options,
    _global_placement_branches,
    _global_search_limits,
    _initial_global_state,
    _local_rearrange_state,
    _ruin_and_recreate,
    _worst_container_indices,
    pack_multi_profile,
)


class MultiContainerPackerTests(unittest.TestCase):
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
        self.assertGreater(high_limits.candidate_points, balanced_limits.candidate_points)

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


if __name__ == "__main__":
    unittest.main()
