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

        self.assertEqual(result.used_volume, 1500)
        self.assertEqual(result.loaded_count, 2)
        self.assertEqual(result.unloaded_count, 1)
        self.assertEqual([(item.box_id, item.quantity) for item in result.loaded], [("LONG", 1), ("SHORT", 1)])
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


if __name__ == "__main__":
    unittest.main()
