from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from cargo_loading.profile_geometry import polygon_area, rectangle_inside_polygon
from cargo_loading.profile_models import (
    BoxPlacement,
    BoxSpec,
    ContainerPackingResult,
    ContainerSpec,
    LoadedBox,
    MultiContainerPackingInput,
    MultiContainerPackingResult,
    ProfilePackingInput,
    ProfilePackingResult,
    ULDProfile,
    UnloadedBox,
)


Point3D = tuple[float, float, float]
DEFAULT_BEAM_WIDTH = 30
MAX_PLACEMENT_BRANCHES = 20
MAX_GLOBAL_BRANCHES_PER_STATE = 80
MAX_GLOBAL_BOX_TYPE_CANDIDATES = 8
MAX_GLOBAL_CONTAINER_CANDIDATES = 12
MAX_BATCH_PLACEMENTS = 8
MAX_GLOBAL_SEARCH_STEPS = 1000


@dataclass
class PackingState:
    placements: list[BoxPlacement]
    candidate_points: list[Point3D]
    unloaded_counter: Counter[str]


@dataclass
class ContainerState:
    spec: ContainerSpec
    container_id: str
    placements: list[BoxPlacement]
    candidate_points: list[Point3D]


@dataclass
class GlobalPackingState:
    containers: list[ContainerState]
    remaining_counter: Counter[str]


@dataclass(frozen=True)
class SearchLimits:
    beam_width: int
    box_type_candidates: int
    container_candidates: int
    placement_branches: int
    global_branches_per_state: int
    batch_placements: int
    max_steps: int
    candidate_points: int


def pack_packing(problem: ProfilePackingInput | MultiContainerPackingInput) -> ProfilePackingResult | MultiContainerPackingResult:
    if isinstance(problem, MultiContainerPackingInput):
        return pack_multi_profile(problem)
    return pack_profile(problem)


def pack_profile(problem: ProfilePackingInput) -> ProfilePackingResult:
    best_result: ProfilePackingResult | None = None
    for expanded_boxes in _expanded_box_orders(problem.boxes):
        result = _pack_profile_ordered(problem, expanded_boxes)
        if best_result is None or _result_score(result, problem.objective) > _result_score(best_result, problem.objective):
            best_result = result
    if best_result is None:
        return _pack_profile_ordered(problem, [])
    return best_result


def _pack_profile_ordered(
    problem: ProfilePackingInput,
    expanded_boxes: list[tuple[BoxSpec, str]],
) -> ProfilePackingResult:
    states = [PackingState(placements=[], candidate_points=[(0, 0, 0)], unloaded_counter=Counter())]
    for box, instance_id in expanded_boxes:
        next_states: list[PackingState] = []
        for state in states:
            candidates = _placement_candidates(box, instance_id, problem, state.placements, state.candidate_points)
            if not candidates:
                unloaded_counter = state.unloaded_counter.copy()
                unloaded_counter[box.id] += 1
                next_states.append(
                    PackingState(
                        placements=state.placements,
                        candidate_points=state.candidate_points,
                        unloaded_counter=unloaded_counter,
                    )
                )
                continue
            for placement in candidates[:MAX_PLACEMENT_BRANCHES]:
                candidate_points = [*state.candidate_points, *_new_candidate_points(placement)]
                next_states.append(
                    PackingState(
                        placements=[*state.placements, placement],
                        candidate_points=_prune_candidate_points(candidate_points, problem),
                        unloaded_counter=state.unloaded_counter.copy(),
                    )
                )
        states = _select_beam_states(problem, next_states, DEFAULT_BEAM_WIDTH)

    best_state = max(states, key=lambda state: _state_score(problem, state)) if states else PackingState([], [(0, 0, 0)], Counter())
    return _profile_result_from_state(problem, best_state)


def _profile_result_from_state(problem: ProfilePackingInput, state: PackingState) -> ProfilePackingResult:
    placements = state.placements
    unloaded_counter = state.unloaded_counter
    unloaded = [
        UnloadedBox(box_id=box_id, quantity=quantity, reason="no feasible space")
        for box_id, quantity in sorted(unloaded_counter.items())
    ]
    loaded_counter = Counter(placement.box_id for placement in placements)
    loaded = [LoadedBox(box_id=box_id, quantity=quantity) for box_id, quantity in sorted(loaded_counter.items())]
    validation_errors = validate_profile_packing(problem, placements)
    cross_section_area = polygon_area(problem.uld.cross_section)
    uld_volume = problem.uld.length * cross_section_area
    used_volume = sum(placement.volume for placement in placements)
    return ProfilePackingResult(
        uld_id=problem.uld.id,
        loaded_count=len(placements),
        unloaded_count=sum(unloaded_counter.values()),
        used_volume=used_volume,
        cross_section_area=cross_section_area,
        uld_volume=uld_volume,
        volume_utilization=used_volume / uld_volume if uld_volume else 0,
        placements=placements,
        unloaded=unloaded,
        validation_passed=not validation_errors,
        validation_errors=validation_errors,
        loaded=loaded,
    )


def _result_score(result: ProfilePackingResult, objective: str) -> tuple[float, int, float]:
    if objective == "maximize_count":
        return (result.loaded_count, result.used_volume, -result.unloaded_count)
    return (result.used_volume, result.loaded_count, -result.unloaded_count)


def _select_beam_states(
    problem: ProfilePackingInput,
    states: list[PackingState],
    beam_width: int,
) -> list[PackingState]:
    unique_states = {}
    for state in states:
        unique_states[_state_signature(state)] = state
    return sorted(
        unique_states.values(),
        key=lambda state: _state_score(problem, state),
        reverse=True,
    )[:beam_width]


def _state_score(problem: ProfilePackingInput, state: PackingState) -> tuple[float, int, float, float, float, float, float]:
    used_volume = sum(placement.volume for placement in state.placements)
    loaded_count = len(state.placements)
    unloaded_count = sum(state.unloaded_counter.values())
    max_x, max_y, max_z = _bounding_extents(state.placements)
    bounding_volume = max_x * max_y * max_z
    if problem.objective == "maximize_count":
        return (loaded_count, used_volume, -unloaded_count, -bounding_volume, -max_z, -max_y, -max_x)
    return (used_volume, loaded_count, -unloaded_count, -bounding_volume, -max_z, -max_y, -max_x)


def _state_signature(state: PackingState) -> tuple[object, ...]:
    placements = tuple(
        (
            placement.box_id,
            placement.instance_id,
            placement.x,
            placement.y,
            placement.z,
            placement.length,
            placement.width,
            placement.height,
        )
        for placement in state.placements
    )
    return placements + tuple(sorted(state.unloaded_counter.items()))


def pack_multi_profile(problem: MultiContainerPackingInput) -> MultiContainerPackingResult:
    box_by_id = {box.id: box for box in problem.boxes}
    limits = _global_search_limits(problem)
    states = [_initial_global_state(problem)]
    for _ in range(min(sum(box.quantity for box in problem.boxes), limits.max_steps)):
        next_states: list[GlobalPackingState] = []
        expanded_any = False
        for state in states:
            branches = _global_placement_branches(problem, state, box_by_id, limits)
            if branches:
                expanded_any = True
                next_states.extend(branches)
            else:
                next_states.append(state)
        if not expanded_any:
            break
        states = _select_global_beam_states(problem, next_states, limits.beam_width)

    best_state = max(states, key=lambda state: _global_state_score(problem, state))
    return _multi_result_from_global_state(problem, best_state)


def _initial_global_state(problem: MultiContainerPackingInput) -> GlobalPackingState:
    return GlobalPackingState(
        containers=[
            ContainerState(
                spec=container,
                container_id=container_id,
                placements=[],
                candidate_points=[(0, 0, 0)],
            )
            for container, container_id in _expand_containers(problem.containers)
        ],
        remaining_counter=Counter({box.id: box.quantity for box in problem.boxes}),
    )


def _global_search_limits(problem: MultiContainerPackingInput) -> SearchLimits:
    total_quantity = sum(box.quantity for box in problem.boxes)
    container_count = sum(container.quantity for container in problem.containers)
    box_type_count = len(problem.boxes)
    if total_quantity >= 200 or container_count >= 12 or box_type_count >= 20:
        return SearchLimits(
            beam_width=3,
            box_type_candidates=2,
            container_candidates=2,
            placement_branches=1,
            global_branches_per_state=8,
            batch_placements=30,
            max_steps=200,
            candidate_points=12,
        )
    if total_quantity >= 30 or container_count >= 8 or box_type_count >= 10:
        return SearchLimits(
            beam_width=6,
            box_type_candidates=3,
            container_candidates=3,
            placement_branches=2,
            global_branches_per_state=16,
            batch_placements=16,
            max_steps=300,
            candidate_points=20,
        )
    return SearchLimits(
        beam_width=DEFAULT_BEAM_WIDTH,
        box_type_candidates=MAX_GLOBAL_BOX_TYPE_CANDIDATES,
        container_candidates=MAX_GLOBAL_CONTAINER_CANDIDATES,
        placement_branches=MAX_PLACEMENT_BRANCHES,
        global_branches_per_state=MAX_GLOBAL_BRANCHES_PER_STATE,
        batch_placements=MAX_BATCH_PLACEMENTS,
        max_steps=MAX_GLOBAL_SEARCH_STEPS,
        candidate_points=80,
    )


def _global_placement_branches(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits | None = None,
) -> list[GlobalPackingState]:
    limits = limits or _global_search_limits(problem)
    branches: list[GlobalPackingState] = []
    tried_box_types = 0
    for box in _ranked_candidate_box_types(problem, state, box_by_id):
        if tried_box_types >= limits.box_type_candidates and branches:
            break
        tried_box_types += 1
        for container_index, container_state, profile_input, candidates in _container_candidate_options(problem, state, box, limits):
            quantity = state.remaining_counter[box.id]
            instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
            for placement_index, placement in enumerate(candidates[: limits.placement_branches]):
                single_branch = _place_box_in_global_state(
                    state,
                    container_index,
                    container_state,
                    profile_input,
                    box,
                    placement,
                    limits,
                )
                branches.append(single_branch)
                if placement_index == 0:
                    repeated_branch = _repeat_box_in_container(problem, single_branch, container_index, box, limits)
                    if len(repeated_branch.containers[container_index].placements) > len(single_branch.containers[container_index].placements):
                        branches.append(repeated_branch)
    return sorted(
        branches,
        key=lambda branch: _global_state_score(problem, branch),
        reverse=True,
    )[: limits.global_branches_per_state]


def _container_candidate_options(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box: BoxSpec,
    limits: SearchLimits | None = None,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
    limits = limits or _global_search_limits(problem)
    options: list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]] = []
    container_pool = _candidate_container_pool(state.containers, box, limits)
    quantity = state.remaining_counter[box.id]
    instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
    for container_index, container_state in container_pool:
        profile_input = _profile_input_for_container(problem, container_state)
        candidates = _placement_candidates(
            box,
            instance_id,
            profile_input,
            container_state.placements,
            container_state.candidate_points,
        )
        if candidates:
            options.append((container_index, container_state, profile_input, candidates[: limits.placement_branches]))
    return sorted(
        options,
        key=lambda option: _container_option_score(option[1], option[3][0]),
        reverse=True,
    )[: limits.container_candidates]


def _candidate_container_pool(
    containers: list[ContainerState],
    box: BoxSpec,
    limits: SearchLimits,
) -> list[tuple[int, ContainerState]]:
    indexed = [
        (index, container)
        for index, container in enumerate(containers)
        if _box_can_fit_container(box, container.spec) and _container_remaining_volume(container) >= box.volume
    ]
    if len(indexed) <= limits.container_candidates * 2:
        return indexed
    compact_candidates = sorted(
        indexed,
        key=lambda item: _container_pool_score(item[1], box),
        reverse=True,
    )[: limits.container_candidates]
    fresh_candidates = sorted(
        indexed,
        key=lambda item: (sum(placement.volume for placement in item[1].placements), item[0]),
    )[: limits.container_candidates]
    return _unique_container_options([*compact_candidates, *fresh_candidates])


def _unique_container_options(options: list[tuple[int, ContainerState]]) -> list[tuple[int, ContainerState]]:
    unique_options: list[tuple[int, ContainerState]] = []
    seen: set[str] = set()
    for option in options:
        container_id = option[1].container_id
        if container_id not in seen:
            seen.add(container_id)
            unique_options.append(option)
    return unique_options


def _container_pool_score(container: ContainerState, box: BoxSpec) -> tuple[float, float]:
    used_volume = sum(placement.volume for placement in container.placements)
    remaining_after_box = _container_remaining_volume(container) - box.volume
    return (used_volume, -remaining_after_box)


def _container_remaining_volume(container: ContainerState) -> float:
    container_volume = container.spec.length * polygon_area(container.spec.cross_section)
    used_volume = sum(placement.volume for placement in container.placements)
    return container_volume - used_volume


def _container_option_score(container: ContainerState, first_candidate: BoxPlacement) -> tuple[float, float]:
    used_volume = sum(placement.volume for placement in container.placements)
    container_volume = container.spec.length * polygon_area(container.spec.cross_section)
    slack_after_placement = container_volume - used_volume - first_candidate.volume
    return (used_volume, -slack_after_placement)


def _candidate_box_types(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits | None = None,
) -> list[BoxSpec]:
    limits = limits or _global_search_limits(problem)
    return _ranked_candidate_box_types(problem, state, box_by_id)[: limits.box_type_candidates]


def _ranked_candidate_box_types(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
) -> list[BoxSpec]:
    boxes = [
        box_by_id[box_id]
        for box_id, quantity in state.remaining_counter.items()
        if quantity > 0 and _box_can_fit_any_container(box_by_id[box_id], state.containers)
    ]
    return sorted(
        boxes,
        key=lambda box: _box_type_score(problem, state, box),
        reverse=True,
    )


def _box_type_score(problem: MultiContainerPackingInput, state: GlobalPackingState, box: BoxSpec) -> tuple[float, float, int, float]:
    fit_count = sum(1 for container in state.containers if _box_can_fit_container(box, container.spec))
    remaining_quantity = state.remaining_counter[box.id]
    longest_edge = max(box.length, box.width, box.height)
    if problem.objective == "maximize_count":
        return (-fit_count, remaining_quantity, box.volume, longest_edge)
    return (-fit_count, box.volume, remaining_quantity, longest_edge)


def _box_can_fit_any_container(box: BoxSpec, containers: list[ContainerState]) -> bool:
    return any(_box_can_fit_container(box, container.spec) for container in containers)


def _box_can_fit_container(box: BoxSpec, container: ContainerSpec) -> bool:
    max_y = max(y for y, _ in container.cross_section)
    max_z = max(z for _, z in container.cross_section)
    for length, width, height in _orientation_options(box):
        if length <= container.length and width <= max_y and height <= max_z:
            return True
    return False


def _repeat_box_in_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box: BoxSpec,
    limits: SearchLimits | None = None,
) -> GlobalPackingState:
    limits = limits or _global_search_limits(problem)
    current_state = state
    repeated = 1
    while repeated < limits.batch_placements and current_state.remaining_counter[box.id] > 0:
        container_state = current_state.containers[container_index]
        profile_input = _profile_input_for_container(problem, container_state)
        quantity = current_state.remaining_counter[box.id]
        instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
        candidates = _placement_candidates(
            box,
            instance_id,
            profile_input,
            container_state.placements,
            container_state.candidate_points,
        )
        if not candidates:
            break
        current_state = _place_box_in_global_state(
            current_state,
            container_index,
            container_state,
            profile_input,
            box,
            candidates[0],
            limits,
        )
        repeated += 1
    return current_state


def _place_box_in_global_state(
    state: GlobalPackingState,
    container_index: int,
    container_state: ContainerState,
    profile_input: ProfilePackingInput,
    box: BoxSpec,
    placement: BoxPlacement,
    limits: SearchLimits,
) -> GlobalPackingState:
    next_remaining = state.remaining_counter.copy()
    next_remaining[box.id] -= 1
    next_candidate_points = _prune_candidate_points(
        [*container_state.candidate_points, *_new_candidate_points(placement)],
        profile_input,
        max_points=limits.candidate_points,
    )
    next_container = ContainerState(
        spec=container_state.spec,
        container_id=container_state.container_id,
        placements=[*container_state.placements, placement],
        candidate_points=next_candidate_points,
    )
    next_containers = [*state.containers]
    next_containers[container_index] = next_container
    return GlobalPackingState(containers=next_containers, remaining_counter=next_remaining)


def _select_global_beam_states(
    problem: MultiContainerPackingInput,
    states: list[GlobalPackingState],
    beam_width: int,
) -> list[GlobalPackingState]:
    unique_states = {}
    for state in states:
        unique_states[_global_state_signature(state)] = state
    return sorted(
        unique_states.values(),
        key=lambda state: _global_state_score(problem, state),
        reverse=True,
    )[:beam_width]


def _global_state_score(problem: MultiContainerPackingInput, state: GlobalPackingState) -> tuple[float, int, float, float, float]:
    used_volume = sum(placement.volume for container in state.containers for placement in container.placements)
    loaded_count = sum(len(container.placements) for container in state.containers)
    unloaded_count = sum(quantity for quantity in state.remaining_counter.values() if quantity > 0)
    compactness = sum(_container_bounding_volume(container) for container in state.containers)
    utilization_spread = _utilization_spread(state.containers)
    if problem.objective == "maximize_count":
        return (loaded_count, used_volume, -unloaded_count, -compactness, -utilization_spread)
    return (used_volume, loaded_count, -unloaded_count, -compactness, -utilization_spread)


def _global_state_signature(state: GlobalPackingState) -> tuple[object, ...]:
    remaining = tuple((box_id, quantity) for box_id, quantity in sorted(state.remaining_counter.items()) if quantity > 0)
    containers = tuple(
        (
            container.container_id,
            tuple(
                (
                    placement.box_id,
                    placement.instance_id,
                    placement.x,
                    placement.y,
                    placement.z,
                    placement.length,
                    placement.width,
                    placement.height,
                )
                for placement in container.placements
            ),
        )
        for container in state.containers
    )
    return remaining + containers


def _multi_result_from_global_state(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
) -> MultiContainerPackingResult:
    container_results: list[ContainerPackingResult] = []

    for container_state in state.containers:
        single_result = _profile_result_from_state(
            _profile_input_for_container(problem, container_state),
            PackingState(
                placements=container_state.placements,
                candidate_points=container_state.candidate_points,
                unloaded_counter=Counter(),
            ),
        )
        container_results.append(
            ContainerPackingResult(
                container_id=container_state.container_id,
                container_type=container_state.spec.id,
                result=single_result,
            )
        )

    unloaded = [
        UnloadedBox(box_id=box_id, quantity=quantity, reason="no feasible space across containers")
        for box_id, quantity in sorted(state.remaining_counter.items())
        if quantity > 0
    ]
    loaded_counter = Counter(placement.box_id for container in state.containers for placement in container.placements)
    loaded = [
        LoadedBox(box_id=box_id, quantity=quantity)
        for box_id, quantity in sorted(loaded_counter.items())
        if quantity > 0
    ]
    validation_errors = [
        f"{container.container_id}: {error}"
        for container in container_results
        for error in container.result.validation_errors
    ]
    used_volume = sum(container.result.used_volume for container in container_results)
    container_volume = sum(container.result.uld_volume for container in container_results)
    return MultiContainerPackingResult(
        loaded_count=sum(item.quantity for item in loaded),
        unloaded_count=sum(item.quantity for item in unloaded),
        used_volume=used_volume,
        container_volume=container_volume,
        volume_utilization=used_volume / container_volume if container_volume else 0,
        containers=container_results,
        loaded=loaded,
        unloaded=unloaded,
        validation_passed=not validation_errors,
        validation_errors=validation_errors,
    )


def _profile_input_for_container(problem: MultiContainerPackingInput, container_state: ContainerState) -> ProfilePackingInput:
    return ProfilePackingInput(
        uld=ULDProfile(
            id=container_state.container_id,
            length=container_state.spec.length,
            cross_section=container_state.spec.cross_section,
        ),
        boxes=problem.boxes,
        objective=problem.objective,
    )


def _container_bounding_volume(container: ContainerState) -> float:
    max_x, max_y, max_z = _bounding_extents(container.placements)
    return max_x * max_y * max_z


def _utilization_spread(containers: list[ContainerState]) -> float:
    utilizations = []
    for container in containers:
        volume = container.spec.length * polygon_area(container.spec.cross_section)
        used_volume = sum(placement.volume for placement in container.placements)
        utilizations.append(used_volume / volume if volume else 0)
    return max(utilizations, default=0) - min(utilizations, default=0)


def validate_profile_packing(problem: ProfilePackingInput, placements: list[BoxPlacement]) -> list[str]:
    errors: list[str] = []
    for placement in placements:
        if placement.x < 0 or placement.y < 0 or placement.z < 0:
            errors.append(f"{placement.instance_id} has negative coordinate")
        if placement.x + placement.length > problem.uld.length:
            errors.append(f"{placement.instance_id} exceeds ULD length")
        if not rectangle_inside_polygon(
            y=placement.y,
            z=placement.z,
            width=placement.width,
            height=placement.height,
            polygon=problem.uld.cross_section,
        ):
            errors.append(f"{placement.instance_id} exceeds ULD cross_section")

    for index, first in enumerate(placements):
        for second in placements[index + 1 :]:
            if placements_overlap(first, second):
                errors.append(f"{first.instance_id} overlaps {second.instance_id}")
    return errors


def _expand_containers(containers: list[ContainerSpec]) -> list[tuple[ContainerSpec, str]]:
    expanded: list[tuple[ContainerSpec, str]] = []
    counters: Counter[str] = Counter()
    for container in containers:
        for _ in range(container.quantity):
            counters[container.id] += 1
            expanded.append((container, f"{container.id}-{counters[container.id]:03d}"))
    return expanded


def placements_overlap(first: BoxPlacement, second: BoxPlacement) -> bool:
    return (
        first.x < second.x + second.length
        and first.x + first.length > second.x
        and first.y < second.y + second.width
        and first.y + first.width > second.y
        and first.z < second.z + second.height
        and first.z + first.height > second.z
    )


def _expanded_box_orders(boxes: list[BoxSpec]) -> list[list[tuple[BoxSpec, str]]]:
    order_keys = [
        lambda item: (-item.volume, item.id),
        lambda item: (item.volume, item.id),
        lambda item: (-item.length, -item.volume, item.id),
        lambda item: (item.length, -item.volume, item.id),
        lambda item: (-(item.width * item.height), -item.volume, item.id),
        lambda item: (-item.height, -item.volume, item.id),
    ]
    orders: list[list[tuple[BoxSpec, str]]] = []
    seen: set[tuple[str, ...]] = set()
    for order_key in order_keys:
        expanded: list[tuple[BoxSpec, str]] = []
        for box in sorted(boxes, key=order_key):
            for index in range(1, box.quantity + 1):
                expanded.append((box, f"{box.id}-{index:03d}"))
        signature = tuple(instance_id for _, instance_id in expanded)
        if signature not in seen:
            seen.add(signature)
            orders.append(expanded)
    return orders


def _placement_candidates(
    box: BoxSpec,
    instance_id: str,
    problem: ProfilePackingInput,
    placements: list[BoxPlacement],
    candidate_points: list[Point3D],
) -> list[BoxPlacement]:
    candidates: list[BoxPlacement] = []
    for x, y, z in set(candidate_points):
        for length, width, height in _orientation_options(box):
            placement = BoxPlacement(
                box_id=box.id,
                instance_id=instance_id,
                x=x,
                y=y,
                z=z,
                length=length,
                width=width,
                height=height,
            )
            if _placement_is_valid(problem, placement, placements):
                candidates.append(placement)
    return sorted(candidates, key=lambda placement: _placement_score(problem, placements, placement))


def _placement_score(
    problem: ProfilePackingInput,
    placements: list[BoxPlacement],
    placement: BoxPlacement,
) -> tuple[float, float, float, float, int, float, float, float]:
    max_x, max_y, max_z = _bounding_extents([*placements, placement])
    bounding_volume = max_x * max_y * max_z
    return (
        bounding_volume,
        max_z,
        max_y,
        max_x,
        -_contact_count(problem, placements, placement),
        placement.z,
        placement.y,
        placement.x,
    )


def _bounding_extents(placements: list[BoxPlacement]) -> Point3D:
    return (
        max((placement.x + placement.length for placement in placements), default=0),
        max((placement.y + placement.width for placement in placements), default=0),
        max((placement.z + placement.height for placement in placements), default=0),
    )


def _contact_count(problem: ProfilePackingInput, placements: list[BoxPlacement], placement: BoxPlacement) -> int:
    contacts = 0
    max_y = max(y for y, _ in problem.uld.cross_section)
    max_z = max(z for _, z in problem.uld.cross_section)
    if placement.x == 0:
        contacts += 1
    if placement.y == 0:
        contacts += 1
    if placement.z == 0:
        contacts += 1
    if placement.x + placement.length == problem.uld.length:
        contacts += 1
    if placement.y + placement.width == max_y:
        contacts += 1
    if placement.z + placement.height == max_z:
        contacts += 1

    for existing in placements:
        contacts += _face_contact_count(placement, existing)
    return contacts


def _face_contact_count(first: BoxPlacement, second: BoxPlacement) -> int:
    contacts = 0
    x_faces_touch = first.x == second.x + second.length or second.x == first.x + first.length
    y_faces_touch = first.y == second.y + second.width or second.y == first.y + first.width
    z_faces_touch = first.z == second.z + second.height or second.z == first.z + first.height
    x_ranges_overlap = _ranges_overlap(first.x, first.x + first.length, second.x, second.x + second.length)
    y_ranges_overlap = _ranges_overlap(first.y, first.y + first.width, second.y, second.y + second.width)
    z_ranges_overlap = _ranges_overlap(first.z, first.z + first.height, second.z, second.z + second.height)

    if x_faces_touch and y_ranges_overlap and z_ranges_overlap:
        contacts += 1
    if y_faces_touch and x_ranges_overlap and z_ranges_overlap:
        contacts += 1
    if z_faces_touch and x_ranges_overlap and y_ranges_overlap:
        contacts += 1
    return contacts


def _ranges_overlap(first_start: float, first_end: float, second_start: float, second_end: float) -> bool:
    return first_start < second_end and first_end > second_start


def _orientation_options(box: BoxSpec) -> list[tuple[float, float, float]]:
    if not box.rotatable:
        return [(box.length, box.width, box.height)]
    return sorted({(box.length, box.width, box.height), (box.width, box.length, box.height)})


def _placement_is_valid(problem: ProfilePackingInput, placement: BoxPlacement, placements: list[BoxPlacement]) -> bool:
    if placement.x + placement.length > problem.uld.length:
        return False
    if not rectangle_inside_polygon(
        y=placement.y,
        z=placement.z,
        width=placement.width,
        height=placement.height,
        polygon=problem.uld.cross_section,
    ):
        return False
    return not any(placements_overlap(placement, existing) for existing in placements)


def _new_candidate_points(placement: BoxPlacement) -> list[Point3D]:
    return [
        (placement.x + placement.length, placement.y, placement.z),
        (placement.x, placement.y + placement.width, placement.z),
        (placement.x, placement.y, placement.z + placement.height),
    ]


def _prune_candidate_points(
    candidate_points: list[Point3D],
    problem: ProfilePackingInput,
    max_points: int | None = None,
) -> list[Point3D]:
    points = []
    for point in set(candidate_points):
        x, y, z = point
        if x <= problem.uld.length and rectangle_inside_polygon(
            y=y,
            z=z,
            width=0,
            height=0,
            polygon=problem.uld.cross_section,
        ):
            points.append(point)
    sorted_points = sorted(points, key=lambda item: (item[2], item[1], item[0]))
    return sorted_points[:max_points] if max_points is not None else sorted_points
