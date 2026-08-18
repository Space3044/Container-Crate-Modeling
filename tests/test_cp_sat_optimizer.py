import unittest

import cargo_loading.profile_packer as profile_packer
from cargo_loading.cp_sat_optimizer import is_available, optimize_single_container
from cargo_loading.profile_models import BoxPlacement, BoxSpec, ContainerSpec, MultiContainerPackingInput


@unittest.skipUnless(is_available(), "OR-Tools is not installed")
class CpSatOptimizerTests(unittest.TestCase):
    def test_optimizer_rearranges_container_and_loads_remaining_box(self):
        box = BoxSpec(id="BOX", length=5, width=10, height=10, quantity=2)
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="RECT",
                    length=10,
                    cross_section=[(0, 0), (10, 0), (10, 10), (0, 10)],
                    quantity=1,
                )
            ],
            boxes=[box],
            search_mode="high_utilization",
        )
        state = profile_packer._initial_global_state(problem)
        container = state.containers[0]
        profile_input = profile_packer._profile_input_for_container(problem, container)
        state = profile_packer._place_box_in_global_state(
            state,
            0,
            container,
            profile_input,
            box,
            BoxPlacement("BOX", "BOX-001", 0, 0, 0, 5, 10, 10),
            profile_packer._global_search_limits(problem),
        )

        optimized = optimize_single_container(
            problem,
            state,
            0,
            {box.id: box},
            profile_packer._global_search_limits(problem),
        )

        self.assertIsNotNone(optimized)
        self.assertEqual(optimized.remaining_counter[box.id], 0)
        placements = optimized.containers[0].placements
        self.assertEqual(len(placements), 2)
        self.assertEqual(
            profile_packer.validate_profile_packing(
                profile_packer._profile_input_for_container(problem, optimized.containers[0]),
                placements,
            ),
            [],
        )

    def test_optimizer_models_supported_stacking_inside_sloped_profile(self):
        box = BoxSpec(id="BOX", length=100, width=100, height=100, quantity=2)
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec(
                    id="Q5",
                    length=100,
                    cross_section=[(0, 0), (240, 0), (240, 190), (120, 290), (0, 290)],
                    quantity=1,
                )
            ],
            boxes=[box],
            search_mode="high_utilization",
        )
        state = profile_packer._initial_global_state(problem)
        container = state.containers[0]
        profile_input = profile_packer._profile_input_for_container(problem, container)
        state = profile_packer._place_box_in_global_state(
            state,
            0,
            container,
            profile_input,
            box,
            BoxPlacement("BOX", "BOX-001", 0, 0, 0, 100, 100, 100),
            profile_packer._global_search_limits(problem),
        )

        optimized = optimize_single_container(
            problem,
            state,
            0,
            {box.id: box},
            profile_packer._global_search_limits(problem),
        )

        self.assertIsNotNone(optimized)
        placements = optimized.containers[0].placements
        self.assertEqual(len(placements), 2)
        self.assertEqual(sorted(placement.z for placement in placements), [0, 100])
        self.assertEqual(
            profile_packer.validate_profile_packing(
                profile_packer._profile_input_for_container(problem, optimized.containers[0]),
                placements,
            ),
            [],
        )

    def test_optimizer_does_not_move_required_box_into_disallowed_container(self):
        normal = BoxSpec(id="NORMAL", length=5, width=10, height=10, quantity=1)
        required = BoxSpec(
            id="REQUIRED",
            length=5,
            width=10,
            height=10,
            quantity=1,
            required_container_types=("TARGET",),
        )
        problem = MultiContainerPackingInput(
            containers=[
                ContainerSpec("FLEX", 10, [(0, 0), (10, 0), (10, 10), (0, 10)], 1),
                ContainerSpec("TARGET", 10, [(0, 0), (10, 0), (10, 10), (0, 10)], 1),
            ],
            boxes=[normal, required],
            search_mode="high_utilization",
        )
        state = profile_packer._initial_global_state(problem)
        container = state.containers[0]
        state = profile_packer._place_box_in_global_state(
            state,
            0,
            container,
            profile_packer._profile_input_for_container(problem, container),
            normal,
            BoxPlacement("NORMAL", "NORMAL-001", 0, 0, 0, 5, 10, 10),
            profile_packer._global_search_limits(problem),
        )

        optimized = optimize_single_container(
            problem,
            state,
            0,
            {box.id: box for box in problem.boxes},
            profile_packer._global_search_limits(problem),
        )

        self.assertIsNotNone(optimized)
        self.assertEqual([placement.box_id for placement in optimized.containers[0].placements], ["NORMAL"])
        self.assertEqual(optimized.remaining_counter["REQUIRED"], 1)


if __name__ == "__main__":
    unittest.main()
