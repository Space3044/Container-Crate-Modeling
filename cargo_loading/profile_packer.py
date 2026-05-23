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
    SEARCH_MODE_FAST,
    SEARCH_MODE_HIGH_UTILIZATION,
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
MIN_BOTTOM_SUPPORT_RATIO = 0.8
MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION = 0.7
LOCAL_REARRANGE_MAX_PASSES = 3
LOCAL_REARRANGE_TARGETS_PER_PASS = 1


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
    limits = _single_search_limits(problem)
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
            for placement in candidates[: limits.placement_branches]:
                next_placements = [*state.placements, placement]
                candidate_points = [*state.candidate_points, *_extreme_points(placement, next_placements, problem)]
                next_states.append(
                    PackingState(
                        placements=next_placements,
                        candidate_points=_prune_candidate_points(candidate_points, problem, next_placements),
                        unloaded_counter=state.unloaded_counter.copy(),
                    )
                )
        states = _select_beam_states(problem, next_states, limits.beam_width)

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


def _single_search_limits(problem: ProfilePackingInput) -> SearchLimits:
    return _search_limits_for_mode(
        SearchLimits(
            beam_width=DEFAULT_BEAM_WIDTH,
            box_type_candidates=MAX_GLOBAL_BOX_TYPE_CANDIDATES,
            container_candidates=MAX_GLOBAL_CONTAINER_CANDIDATES,
            placement_branches=MAX_PLACEMENT_BRANCHES,
            global_branches_per_state=MAX_GLOBAL_BRANCHES_PER_STATE,
            batch_placements=MAX_BATCH_PLACEMENTS,
            max_steps=MAX_GLOBAL_SEARCH_STEPS,
            candidate_points=80,
        ),
        problem.search_mode,
    )


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


MULTISTART_VARIANTS = (0, 1, 2, 3)


def pack_multi_profile(problem: MultiContainerPackingInput) -> MultiContainerPackingResult:
    if problem.search_mode == SEARCH_MODE_HIGH_UTILIZATION:
        return _pack_multi_profile_multistart(problem)
    return _pack_multi_profile_variant(problem, variant=0)


def _pack_multi_profile_multistart(problem: MultiContainerPackingInput) -> MultiContainerPackingResult:
    best_result: MultiContainerPackingResult | None = None
    best_score: tuple[object, ...] | None = None
    for variant in MULTISTART_VARIANTS:
        result = _pack_multi_profile_variant(problem, variant=variant)
        score = _multi_result_score(result, problem.objective)
        if best_result is None or score > best_score:
            best_result = result
            best_score = score
    return best_result if best_result is not None else _pack_multi_profile_variant(problem, variant=0)


def _multi_result_score(result: MultiContainerPackingResult, objective: str) -> tuple[float, ...]:
    used_container_count = sum(1 for container in result.containers if container.result.placements)
    if objective == "maximize_count":
        return (-result.unloaded_count, -used_container_count, result.loaded_count, result.used_volume)
    return (-result.unloaded_count, -used_container_count, result.used_volume, result.loaded_count)


def _pack_multi_profile_variant(problem: MultiContainerPackingInput, variant: int) -> MultiContainerPackingResult:
    box_by_id = {box.id: box for box in problem.boxes}
    limits = _global_search_limits(problem)
    states = [_initial_global_state(problem)]
    for _ in range(min(sum(box.quantity for box in problem.boxes), limits.max_steps)):
        next_states: list[GlobalPackingState] = []
        expanded_any = False
        for state in states:
            branches = _global_placement_branches(problem, state, box_by_id, limits, variant=variant)
            if branches:
                expanded_any = True
                next_states.extend(branches)
            else:
                next_states.append(state)
        if not expanded_any:
            break
        states = _select_global_beam_states(problem, next_states, limits.beam_width)

    best_state = max(states, key=lambda state: _global_state_score(problem, state))
    best_state = _refill_remaining_boxes_in_used_containers(problem, best_state, box_by_id, limits)
    best_state = _local_rearrange_state(problem, best_state, box_by_id, limits)
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
    return _search_limits_for_mode(_base_global_search_limits(problem), problem.search_mode)


def _base_global_search_limits(problem: MultiContainerPackingInput) -> SearchLimits:
    total_quantity = sum(box.quantity for box in problem.boxes)
    container_count = sum(container.quantity for container in problem.containers)
    box_type_count = len(problem.boxes)
    if container_count >= 12 or box_type_count >= 20:
        return SearchLimits(
            beam_width=3,
            box_type_candidates=2,
            container_candidates=2,
            placement_branches=1,
            global_branches_per_state=8,
            batch_placements=30,
            max_steps=200,
            candidate_points=30,
        )
    if container_count >= 8 or box_type_count >= 10:
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
    if total_quantity >= 30:
        return SearchLimits(
            beam_width=6,
            box_type_candidates=MAX_GLOBAL_BOX_TYPE_CANDIDATES,
            container_candidates=MAX_GLOBAL_CONTAINER_CANDIDATES,
            placement_branches=2,
            global_branches_per_state=16,
            batch_placements=16,
            max_steps=300,
            candidate_points=80,
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


def _search_limits_for_mode(limits: SearchLimits, search_mode: str) -> SearchLimits:
    if search_mode == SEARCH_MODE_FAST:
        return SearchLimits(
            beam_width=max(2, limits.beam_width // 2),
            box_type_candidates=max(2, min(limits.box_type_candidates, (limits.box_type_candidates + 1) // 2)),
            container_candidates=max(2, min(limits.container_candidates, (limits.container_candidates + 1) // 2)),
            placement_branches=max(1, (limits.placement_branches + 1) // 2),
            global_branches_per_state=max(8, limits.global_branches_per_state // 2),
            batch_placements=max(limits.batch_placements, 12),
            max_steps=max(100, limits.max_steps // 2),
            candidate_points=max(40, limits.candidate_points // 2),
        )
    if search_mode == SEARCH_MODE_HIGH_UTILIZATION:
        return SearchLimits(
            beam_width=max(limits.beam_width + 1, round(limits.beam_width * 1.6)),
            box_type_candidates=max(limits.box_type_candidates + 1, round(limits.box_type_candidates * 1.5)),
            container_candidates=max(limits.container_candidates + 1, round(limits.container_candidates * 1.5)),
            placement_branches=max(limits.placement_branches + 1, round(limits.placement_branches * 1.5)),
            global_branches_per_state=max(limits.global_branches_per_state + 1, round(limits.global_branches_per_state * 1.6)),
            batch_placements=limits.batch_placements,
            max_steps=max(limits.max_steps + 1, round(limits.max_steps * 1.5)),
            candidate_points=max(240, round(limits.candidate_points * 1.8)),
        )
    return limits


def _global_placement_branches(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits | None = None,
    active_only: bool = False,
    variant: int = 0,
) -> list[GlobalPackingState]:
    limits = limits or _global_search_limits(problem)
    branches: list[GlobalPackingState] = []
    tried_box_types = 0
    for box in _ranked_candidate_box_types(problem, state, box_by_id, variant):
        if tried_box_types >= limits.box_type_candidates and branches:
            break
        tried_box_types += 1
        for container_index, container_state, profile_input, candidates in _container_candidate_options(problem, state, box, limits, active_only=active_only):
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
    active_only: bool = False,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
    limits = limits or _global_search_limits(problem)
    quantity = state.remaining_counter[box.id]
    instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"

    active_pool = [
        (index, container)
        for index, container in enumerate(state.containers)
        if container.placements and _box_can_fit_container(box, container.spec) and _container_remaining_volume(container) >= box.volume
    ]
    active_options = _container_options_from_pool(problem, active_pool, box, instance_id, limits)
    if active_options:
        return _sort_container_options(active_options, limits)
    if active_only:
        return []

    container_pool = _candidate_container_pool(state.containers, box, limits)
    return _sort_container_options(
        _container_options_from_pool(problem, container_pool, box, instance_id, limits),
        limits,
    )


def _container_options_from_pool(
    problem: MultiContainerPackingInput,
    container_pool: list[tuple[int, ContainerState]],
    box: BoxSpec,
    instance_id: str,
    limits: SearchLimits,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
    options: list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]] = []
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
    return options


def _sort_container_options(
    options: list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]],
    limits: SearchLimits,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
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
    variant: int = 0,
) -> list[BoxSpec]:
    limits = limits or _global_search_limits(problem)
    return _ranked_candidate_box_types(problem, state, box_by_id, variant)[: limits.box_type_candidates]


def _ranked_candidate_box_types(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    variant: int = 0,
) -> list[BoxSpec]:
    boxes = [
        box_by_id[box_id]
        for box_id, quantity in state.remaining_counter.items()
        if quantity > 0 and _box_can_fit_any_container(box_by_id[box_id], state.containers)
    ]
    return sorted(
        boxes,
        key=lambda box: _box_type_score(problem, state, box, variant),
        reverse=True,
    )


def _box_type_score(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box: BoxSpec,
    variant: int = 0,
) -> tuple[float, ...]:
    fit_count = sum(1 for container in state.containers if _box_can_fit_container(box, container.spec))
    remaining_quantity = state.remaining_counter[box.id]
    longest_edge = max(box.length, box.width, box.height)
    if variant == 1:
        return (-fit_count, box.volume, remaining_quantity, longest_edge)
    if variant == 2:
        return (-fit_count, longest_edge, box.volume, remaining_quantity)
    if variant == 3:
        return (-fit_count, box.volume * remaining_quantity, longest_edge, remaining_quantity)
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


def _refill_remaining_boxes_in_used_containers(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState:
    current_state = state
    while True:
        next_state = _next_refill_state(problem, current_state, box_by_id, limits)
        if next_state is None:
            return current_state
        current_state = next_state


def _local_rearrange_state(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState:
    if problem.search_mode != SEARCH_MODE_HIGH_UTILIZATION:
        return state
    if not any(container.placements for container in state.containers):
        return state

    best_state = state
    best_score = _global_state_score(problem, best_state)
    tried_signatures: set[tuple[object, ...]] = {_global_state_signature(best_state)}

    best_state, best_score = _run_rearrange_strategy(
        problem,
        best_state,
        best_score,
        box_by_id,
        limits,
        tried_signatures,
        _evacuate_and_refill,
        targets_per_pass=1,
    )
    best_state, best_score = _run_rearrange_strategy(
        problem,
        best_state,
        best_score,
        box_by_id,
        limits,
        tried_signatures,
        _ruin_and_recreate,
        targets_per_pass=LOCAL_REARRANGE_TARGETS_PER_PASS,
    )
    return best_state


def _run_rearrange_strategy(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    score: tuple[object, ...],
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    tried_signatures: set[tuple[object, ...]],
    strategy,
    targets_per_pass: int,
) -> tuple[GlobalPackingState, tuple[object, ...]]:
    best_state = state
    best_score = score
    skip_indices: set[int] = set()
    for _ in range(LOCAL_REARRANGE_MAX_PASSES):
        target_indices = _worst_container_indices(best_state, targets_per_pass, skip_indices)
        if not target_indices:
            break
        candidate = strategy(problem, best_state, box_by_id, limits, target_indices)
        if candidate is best_state:
            skip_indices.update(target_indices)
            continue
        signature = _global_state_signature(candidate)
        if signature in tried_signatures:
            skip_indices.update(target_indices)
            continue
        tried_signatures.add(signature)
        candidate_score = _global_state_score(problem, candidate)
        if candidate_score > best_score:
            best_state = candidate
            best_score = candidate_score
            skip_indices.clear()
        else:
            skip_indices.update(target_indices)
    return best_state, best_score


def _worst_container_indices(
    state: GlobalPackingState,
    count: int,
    skip_indices: set[int],
) -> list[int]:
    scored: list[tuple[float, int]] = []
    for index, container in enumerate(state.containers):
        if index in skip_indices or not container.placements:
            continue
        container_volume = container.spec.length * polygon_area(container.spec.cross_section)
        used_volume = sum(placement.volume for placement in container.placements)
        utilization = used_volume / container_volume if container_volume else 0
        scored.append((utilization, index))
    scored.sort()
    return [index for _, index in scored[:count]]


def _evacuate_and_refill(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    target_indices: list[int],
) -> GlobalPackingState:
    evacuated = _evacuate_containers(state, target_indices)
    if evacuated is state:
        return state
    refilled = _refill_remaining_boxes_in_used_containers(problem, evacuated, box_by_id, limits)
    resolved = _resolve_active_only_beam(problem, refilled, box_by_id, limits)
    return resolved


def _evacuate_containers(
    state: GlobalPackingState,
    target_indices: list[int],
) -> GlobalPackingState:
    target_set = set(target_indices)
    next_remaining = state.remaining_counter.copy()
    next_containers: list[ContainerState] = []
    changed = False
    for index, container in enumerate(state.containers):
        if index not in target_set or not container.placements:
            next_containers.append(container)
            continue
        for placement in container.placements:
            next_remaining[placement.box_id] += 1
        next_containers.append(
            ContainerState(
                spec=container.spec,
                container_id=container.container_id,
                placements=[],
                candidate_points=[(0, 0, 0)],
            )
        )
        changed = True
    if not changed:
        return state
    return GlobalPackingState(containers=next_containers, remaining_counter=next_remaining)


def _resolve_active_only_beam(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState:
    remaining_count = sum(quantity for quantity in state.remaining_counter.values() if quantity > 0)
    if remaining_count == 0:
        return state
    states = [state]
    for _ in range(min(remaining_count, limits.max_steps)):
        next_states: list[GlobalPackingState] = []
        expanded_any = False
        for current in states:
            branches = _global_placement_branches(problem, current, box_by_id, limits, active_only=True)
            if branches:
                expanded_any = True
                next_states.extend(branches)
            else:
                next_states.append(current)
        if not expanded_any:
            break
        states = _select_global_beam_states(problem, next_states, limits.beam_width)
    return max(states, key=lambda candidate: _global_state_score(problem, candidate))


def _ruin_and_recreate(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    target_indices: list[int],
) -> GlobalPackingState:
    target_set = set(target_indices)
    next_remaining = state.remaining_counter.copy()
    next_containers: list[ContainerState] = []
    changed = False
    for index, container in enumerate(state.containers):
        if index not in target_set or not container.placements:
            next_containers.append(container)
            continue
        top_z = max(placement.z for placement in container.placements)
        if top_z <= 0:
            next_containers.append(container)
            continue
        kept = [placement for placement in container.placements if placement.z < top_z]
        removed = [placement for placement in container.placements if placement.z >= top_z]
        if not kept or not removed:
            next_containers.append(container)
            continue
        for placement in removed:
            next_remaining[placement.box_id] += 1
        profile_input = _profile_input_for_container(problem, container)
        new_points = _refill_candidate_points(profile_input, kept, limits)
        next_containers.append(
            ContainerState(
                spec=container.spec,
                container_id=container.container_id,
                placements=kept,
                candidate_points=new_points,
            )
        )
        changed = True
    if not changed:
        return state
    ruined_state = GlobalPackingState(containers=next_containers, remaining_counter=next_remaining)
    return _refill_remaining_boxes_in_used_containers(problem, ruined_state, box_by_id, limits)


def _next_refill_state(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState | None:
    for box in _refill_candidate_box_types(state, box_by_id):
        option = _best_refill_option(problem, state, box, limits)
        if option is None:
            continue
        container_index, container_state, profile_input, placement = option
        next_state = _place_box_in_global_state(
            state,
            container_index,
            container_state,
            profile_input,
            box,
            placement,
            limits,
        )
        return _repeat_box_in_container(problem, next_state, container_index, box, limits)
    return None


def _refill_candidate_box_types(state: GlobalPackingState, box_by_id: dict[str, BoxSpec]) -> list[BoxSpec]:
    return sorted(
        (box_by_id[box_id] for box_id, quantity in state.remaining_counter.items() if quantity > 0),
        key=lambda box: (box.volume, -state.remaining_counter[box.id], max(box.length, box.width, box.height)),
    )


def _best_refill_option(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box: BoxSpec,
    limits: SearchLimits,
) -> tuple[int, ContainerState, ProfilePackingInput, BoxPlacement] | None:
    options: list[tuple[int, ContainerState, ProfilePackingInput, BoxPlacement]] = []
    quantity = state.remaining_counter[box.id]
    instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
    for container_index, container_state in enumerate(state.containers):
        if not container_state.placements:
            continue
        if not _box_can_fit_container(box, container_state.spec) or _container_remaining_volume(container_state) < box.volume:
            continue
        profile_input = _profile_input_for_container(problem, container_state)
        candidate_points = _refill_candidate_points(profile_input, container_state.placements, limits=limits)
        candidates = _placement_candidates(
            box,
            instance_id,
            profile_input,
            container_state.placements,
            candidate_points,
        )
        if candidates:
            options.append((container_index, container_state, profile_input, candidates[0]))
    if not options:
        return None
    return max(options, key=lambda option: _container_option_score(option[1], option[3]))


def _refill_candidate_points(
    problem: ProfilePackingInput,
    placements: list[BoxPlacement],
    limits: SearchLimits | None,
) -> list[Point3D]:
    points = [(0, 0, 0)]
    for placement in placements:
        points.extend(_extreme_points(placement, placements, problem))
    max_points = _candidate_point_limit(limits) if limits else 160
    return _prune_candidate_points(points, problem, placements, max_points=max_points)


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
    next_placements = [*container_state.placements, placement]
    next_candidate_points = _prune_candidate_points(
        [*container_state.candidate_points, *_extreme_points(placement, next_placements, profile_input)],
        profile_input,
        next_placements,
        max_points=_candidate_point_limit(limits),
    )
    next_container = ContainerState(
        spec=container_state.spec,
        container_id=container_state.container_id,
        placements=next_placements,
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


def _global_state_score(problem: MultiContainerPackingInput, state: GlobalPackingState) -> tuple[float, int, float, int, float, float]:
    used_volume = sum(placement.volume for container in state.containers for placement in container.placements)
    loaded_count = sum(len(container.placements) for container in state.containers)
    unloaded_count = sum(quantity for quantity in state.remaining_counter.values() if quantity > 0)
    compactness = sum(_container_bounding_volume(container) for container in state.containers)
    used_container_count = _used_container_count(state.containers)
    active_container_utilization = _active_container_utilization(state.containers)
    if problem.objective == "maximize_count":
        return (-unloaded_count, -used_container_count, loaded_count, used_volume, active_container_utilization, -compactness)
    return (-unloaded_count, -used_container_count, used_volume, loaded_count, active_container_utilization, -compactness)


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
        search_mode=problem.search_mode,
    )


def _container_bounding_volume(container: ContainerState) -> float:
    max_x, max_y, max_z = _bounding_extents(container.placements)
    return max_x * max_y * max_z


def _used_container_count(containers: list[ContainerState]) -> int:
    return sum(1 for container in containers if container.placements)


def _active_container_utilization(containers: list[ContainerState]) -> float:
    used_volume = 0
    active_volume = 0
    for container in containers:
        if not container.placements:
            continue
        volume = container.spec.length * polygon_area(container.spec.cross_section)
        active_volume += volume
        used_volume += sum(placement.volume for placement in container.placements)
    return used_volume / active_volume if active_volume else 0


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
        supporters = [existing for existing in placements if existing is not placement]
        if not _placement_has_enough_support(placement, supporters, _min_support_ratio_for_mode(problem.search_mode)):
            errors.append(f"{placement.instance_id} has insufficient bottom support")

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
) -> tuple[float, float, float, float, float, float, int, float, float, float]:
    max_x, max_y, max_z = _bounding_extents([*placements, placement])
    bounding_volume = max_x * max_y * max_z
    return (
        bounding_volume,
        max_z,
        max_y,
        max_x,
        -_support_ratio(placement, placements),
        -_dominant_support_ratio(placement, placements),
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
    if any(placements_overlap(placement, existing) for existing in placements):
        return False
    return _placement_has_enough_support(placement, placements, _min_support_ratio_for_mode(problem.search_mode))


def _new_candidate_points(placement: BoxPlacement) -> list[Point3D]:
    return [
        (placement.x + placement.length, placement.y, placement.z),
        (placement.x, placement.y + placement.width, placement.z),
        (placement.x, placement.y, placement.z + placement.height),
    ]


def _extreme_points(
    placement: BoxPlacement,
    placements: list[BoxPlacement],
    problem: ProfilePackingInput,
) -> list[Point3D]:
    x, y, z = placement.x, placement.y, placement.z
    length, width, height = placement.length, placement.width, placement.height
    raw_points: list[Point3D] = [
        (x + length, y, z),
        (x, y + width, z),
        (x, y, z + height),
        (x + length, y + width, z),
        (x + length, y, z + height),
        (x, y + width, z + height),
    ]
    others = [other for other in placements if other is not placement]
    seen: set[Point3D] = set()
    points: list[Point3D] = []
    for point in raw_points:
        for projected in _project_extreme_point(point, others, problem):
            if projected in seen:
                continue
            seen.add(projected)
            points.append(projected)
    return points


def _project_extreme_point(
    point: Point3D,
    others: list[BoxPlacement],
    problem: ProfilePackingInput,
) -> list[Point3D]:
    projections: list[Point3D] = [point]
    x, y, z = point
    pushed_x = _push_negative_x(x, y, z, others)
    if pushed_x != x:
        projections.append((pushed_x, y, z))
    pushed_y = _push_negative_y(x, y, z, others)
    if pushed_y != y:
        projections.append((x, pushed_y, z))
    pushed_z = _push_negative_z(x, y, z, others)
    if pushed_z != z:
        projections.append((x, y, pushed_z))
    return projections


def _push_negative_x(x: float, y: float, z: float, placements: list[BoxPlacement]) -> float:
    best = 0.0
    for other in placements:
        right_face = other.x + other.length
        if right_face > x:
            continue
        if not (other.y <= y < other.y + other.width):
            continue
        if not (other.z <= z < other.z + other.height):
            continue
        if right_face > best:
            best = right_face
    return best


def _push_negative_y(x: float, y: float, z: float, placements: list[BoxPlacement]) -> float:
    best = 0.0
    for other in placements:
        back_face = other.y + other.width
        if back_face > y:
            continue
        if not (other.x <= x < other.x + other.length):
            continue
        if not (other.z <= z < other.z + other.height):
            continue
        if back_face > best:
            best = back_face
    return best


def _push_negative_z(x: float, y: float, z: float, placements: list[BoxPlacement]) -> float:
    best = 0.0
    for other in placements:
        top_face = other.z + other.height
        if top_face > z:
            continue
        if not (other.x <= x < other.x + other.length):
            continue
        if not (other.y <= y < other.y + other.width):
            continue
        if top_face > best:
            best = top_face
    return best


def _prune_candidate_points(
    candidate_points: list[Point3D],
    problem: ProfilePackingInput,
    placements: list[BoxPlacement] | None = None,
    max_points: int | None = None,
) -> list[Point3D]:
    points = []
    placements = placements or []
    for point in set(candidate_points):
        x, y, z = point
        if any(_point_inside_placement(point, placement) for placement in placements):
            continue
        if x <= problem.uld.length and rectangle_inside_polygon(
            y=y,
            z=z,
            width=0,
            height=0,
            polygon=problem.uld.cross_section,
        ):
            points.append(point)
    sorted_points = sorted(points, key=_candidate_point_sort_key)
    if max_points is None or len(sorted_points) <= max_points:
        return sorted_points
    return _select_diverse_candidate_points(sorted_points, max_points)


def _candidate_point_sort_key(point: Point3D) -> tuple[float, float, float]:
    return (point[2], point[1], point[0])


def _select_diverse_candidate_points(sorted_points: list[Point3D], max_points: int) -> list[Point3D]:
    if max_points <= 0:
        return []

    selected: list[Point3D] = []
    seen: set[Point3D] = set()

    floor_quota = max(1, max_points // 3)
    for point in sorted_points[:floor_quota]:
        selected.append(point)
        seen.add(point)

    layers: dict[float, list[Point3D]] = {}
    for point in sorted_points:
        layers.setdefault(point[2], []).append(point)

    layer_index = 0
    layer_heights = sorted(layers)
    while len(selected) < max_points:
        progressed = False
        for height in layer_heights:
            layer = layers[height]
            if layer_index >= len(layer):
                continue
            progressed = True
            point = layer[layer_index]
            if point in seen:
                continue
            selected.append(point)
            seen.add(point)
            if len(selected) >= max_points:
                break
        if not progressed:
            break
        layer_index += 1

    return sorted(selected, key=_candidate_point_sort_key)


def _candidate_point_limit(limits: SearchLimits) -> int:
    return max(160, limits.candidate_points)


def _point_inside_placement(point: Point3D, placement: BoxPlacement) -> bool:
    x, y, z = point
    return (
        placement.x <= x < placement.x + placement.length
        and placement.y <= y < placement.y + placement.width
        and placement.z <= z < placement.z + placement.height
    )


def _placement_has_enough_support(
    placement: BoxPlacement,
    placements: list[BoxPlacement],
    min_ratio: float = MIN_BOTTOM_SUPPORT_RATIO,
) -> bool:
    return _support_ratio(placement, placements) >= min_ratio


def _min_support_ratio_for_mode(search_mode: str) -> float:
    if search_mode == SEARCH_MODE_HIGH_UTILIZATION:
        return MIN_BOTTOM_SUPPORT_RATIO_HIGH_UTILIZATION
    return MIN_BOTTOM_SUPPORT_RATIO


def _support_ratio(placement: BoxPlacement, placements: list[BoxPlacement]) -> float:
    if placement.z == 0:
        return 1
    support_area = sum(_support_overlap_area(placement, existing) for existing in placements)
    bottom_area = placement.length * placement.width
    return support_area / bottom_area if bottom_area else 0


def _dominant_support_ratio(placement: BoxPlacement, placements: list[BoxPlacement]) -> float:
    if placement.z == 0:
        return 1
    bottom_area = placement.length * placement.width
    if not bottom_area:
        return 0
    return max((_support_overlap_area(placement, existing) for existing in placements), default=0) / bottom_area


def _support_overlap_area(placement: BoxPlacement, supporter: BoxPlacement) -> float:
    if abs((supporter.z + supporter.height) - placement.z) > 1e-9:
        return 0
    overlap_length = _axis_overlap(placement.x, placement.x + placement.length, supporter.x, supporter.x + supporter.length)
    overlap_width = _axis_overlap(placement.y, placement.y + placement.width, supporter.y, supporter.y + supporter.width)
    return overlap_length * overlap_width


def _axis_overlap(first_start: float, first_end: float, second_start: float, second_end: float) -> float:
    return max(0, min(first_end, second_end) - max(first_start, second_start))
