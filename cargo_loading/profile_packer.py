from __future__ import annotations

from bisect import bisect_left, bisect_right
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
import multiprocessing
import random
from collections import Counter, defaultdict

from cargo_loading.profile_geometry import convex_y_interval, polygon_area, rectangle_inside_polygon
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
    SEARCH_MODE_BALANCED,
    SEARCH_MODE_FAST,
    SEARCH_MODE_HIGH_UTILIZATION,
    ULDProfile,
    UnloadedBox,
    merge_box_specs,
)


Point3D = tuple[float, float, float]
PlacementScore = tuple[float, float, float, float, float, float, int, float, float, float]
EPSILON = 1e-9
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
LAYER_BUILD_MIN_QUANTITY = 4
COLUMN_BUILD_MIN_BOXES = 2
COLUMN_TOPPER_CANDIDATES = 5
COLUMN_BUILD_MAX_SPACES = 16
GRASP_ROUNDS_BALANCED = 2
GRASP_ROUNDS_HIGH_UTILIZATION = 3
GRASP_RCL_WINDOW = 3
MAX_PARALLEL_SEARCH_PROCESSES = 3


@dataclass(frozen=True)
class FreeSpace:
    """容器内一块极大空闲长方体（Empty Maximal Space）。"""

    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class PackingState:
    placements: list[BoxPlacement]
    free_spaces: list[FreeSpace]
    unloaded_counter: Counter[str]


@dataclass
class ContainerState:
    spec: ContainerSpec
    container_id: str
    placements: list[BoxPlacement]
    free_spaces: list[FreeSpace]
    container_volume: float = -1.0
    used_volume: float = -1.0
    max_x: float = -1.0
    max_y: float = -1.0
    max_z: float = -1.0

    def __post_init__(self) -> None:
        if self.container_volume < 0:
            self.container_volume = self.spec.length * polygon_area(self.spec.cross_section)
        if self.used_volume < 0:
            self.used_volume = sum(placement.volume for placement in self.placements)
        if self.max_x < 0 or self.max_y < 0 or self.max_z < 0:
            self.max_x, self.max_y, self.max_z = _bounding_extents(self.placements)


@dataclass
class GlobalPackingState:
    containers: list[ContainerState]
    remaining_counter: Counter[str]


@dataclass(frozen=True)
class PlacementScanIndex:
    placements: list[BoxPlacement]
    x_starts: dict[float, tuple[int, ...]]
    x_ends: dict[float, tuple[int, ...]]
    y_starts: dict[float, tuple[int, ...]]
    y_ends: dict[float, tuple[int, ...]]
    z_starts: dict[float, tuple[int, ...]]
    z_ends: dict[float, tuple[int, ...]]
    top_heights: tuple[float, ...]


@dataclass(frozen=True)
class SearchLimits:
    beam_width: int
    box_type_candidates: int
    container_candidates: int
    placement_branches: int
    global_branches_per_state: int
    batch_placements: int
    max_steps: int
    max_free_spaces: int


def pack_packing(problem: ProfilePackingInput | MultiContainerPackingInput) -> ProfilePackingResult | MultiContainerPackingResult:
    if isinstance(problem, MultiContainerPackingInput):
        return pack_multi_profile(problem)
    return pack_profile(problem)


def pack_profile(problem: ProfilePackingInput) -> ProfilePackingResult:
    problem = _normalize_problem_boxes(problem)
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
    states = [PackingState(placements=[], free_spaces=_initial_free_spaces(problem), unloaded_counter=Counter())]
    for box, instance_id in expanded_boxes:
        next_states: list[PackingState] = []
        for state in states:
            candidates = _placement_candidates(box, instance_id, problem, state.placements, state.free_spaces)
            if not candidates:
                unloaded_counter = state.unloaded_counter.copy()
                unloaded_counter[box.id] += 1
                next_states.append(
                    PackingState(
                        placements=state.placements,
                        free_spaces=state.free_spaces,
                        unloaded_counter=unloaded_counter,
                    )
                )
                continue
            for placement in candidates[: limits.placement_branches]:
                next_placements = [*state.placements, placement]
                next_states.append(
                    PackingState(
                        placements=next_placements,
                        free_spaces=_subtract_placement_from_spaces(state.free_spaces, placement, _free_space_limit(limits)),
                        unloaded_counter=state.unloaded_counter.copy(),
                    )
                )
        states = _select_beam_states(problem, next_states, limits.beam_width)

    best_state = (
        max(states, key=lambda state: _state_score(problem, state))
        if states
        else PackingState([], _initial_free_spaces(problem), Counter())
    )
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
            max_free_spaces=80,
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


MULTISTART_VARIANTS = (0, 1, 2, 3, 4)


def pack_multi_profile(problem: MultiContainerPackingInput) -> MultiContainerPackingResult:
    problem = _normalize_problem_boxes(problem)
    return _best_of_rounds(problem, _round_plan(problem))


def _normalize_problem_boxes(
    problem: ProfilePackingInput | MultiContainerPackingInput,
) -> ProfilePackingInput | MultiContainerPackingInput:
    """确保直接调用求解器时也遵守计算前箱型归并规则。"""
    return replace(problem, boxes=merge_box_specs(problem.boxes))


def _round_plan(problem: MultiContainerPackingInput) -> list[tuple[int, int | None]]:
    """每轮 = (box 排序变体, GRASP 种子)。种子为 None 表示确定性轮。"""
    if problem.search_mode == SEARCH_MODE_HIGH_UTILIZATION:
        container_count = sum(container.quantity for container in problem.containers)
        box_type_count = len(problem.boxes)
        if container_count >= 12 or box_type_count >= 20:
            # 大规模时每轮要几十秒，缩轮数保住分钟级预算
            return [(0, None), (1, None), (0, 1)]
        deterministic = [(variant, None) for variant in MULTISTART_VARIANTS]
        randomized = [(seed % len(MULTISTART_VARIANTS), seed) for seed in range(1, GRASP_ROUNDS_HIGH_UTILIZATION + 1)]
        return deterministic + randomized
    if problem.search_mode == SEARCH_MODE_BALANCED:
        return [(0, None)] + [(0, seed) for seed in range(1, GRASP_ROUNDS_BALANCED + 1)]
    return [(0, None)]


def _best_of_rounds(
    problem: MultiContainerPackingInput,
    rounds: list[tuple[int, int | None]],
) -> MultiContainerPackingResult:
    if not rounds:
        return _pack_multi_profile_variant(problem, variant=0)
    if len(rounds) == 1:
        variant, seed = rounds[0]
        return _pack_multi_profile_round(problem, variant, seed)

    worker_count = min(MAX_PARALLEL_SEARCH_PROCESSES, len(rounds))
    with ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        futures = [
            executor.submit(_pack_multi_profile_round, problem, variant, seed)
            for variant, seed in rounds
        ]

    best_result: MultiContainerPackingResult | None = None
    best_score: tuple[object, ...] | None = None
    for future in futures:
        result = future.result()
        score = _multi_result_score(problem, result)
        if best_result is None or score > best_score:
            best_result = result
            best_score = score
    return best_result


def _pack_multi_profile_round(
    problem: MultiContainerPackingInput,
    variant: int,
    seed: int | None,
) -> MultiContainerPackingResult:
    rng = random.Random(seed) if seed is not None else None
    return _pack_multi_profile_variant(problem, variant=variant, rng=rng)


def _multi_result_score(problem: MultiContainerPackingInput, result: MultiContainerPackingResult) -> tuple[float, ...]:
    used_container_count = sum(1 for container in result.containers if container.result.placements)
    required_unloaded_count = _required_unloaded_count_from_result(problem, result)
    if problem.objective == "maximize_count":
        return (-required_unloaded_count, -result.unloaded_count, -used_container_count, result.loaded_count, result.used_volume)
    return (-required_unloaded_count, -result.unloaded_count, -used_container_count, result.used_volume, result.loaded_count)


def _required_unloaded_count_from_result(
    problem: MultiContainerPackingInput,
    result: MultiContainerPackingResult,
) -> int:
    required_box_ids = {box.id for box in problem.boxes if box.required_container_types}
    return sum(item.quantity for item in result.unloaded if item.box_id in required_box_ids)


def _pack_multi_profile_variant(
    problem: MultiContainerPackingInput,
    variant: int,
    rng: random.Random | None = None,
) -> MultiContainerPackingResult:
    box_by_id = {box.id: box for box in problem.boxes}
    limits = _global_search_limits(problem)
    primary_states = [_initial_global_state(problem)]
    volume_states: list[GlobalPackingState] = []
    volume_rng: random.Random | None = None
    if rng is not None:
        volume_rng = random.Random()
        volume_rng.setstate(rng.getstate())
    for _ in range(min(sum(box.quantity for box in problem.boxes), limits.max_steps)):
        next_primary_states, primary_expanded = _expand_global_states(
            problem,
            primary_states,
            box_by_id,
            limits,
            variant,
            rng,
        )
        next_volume_states, volume_expanded = _expand_global_states(
            problem,
            volume_states,
            box_by_id,
            limits,
            variant,
            volume_rng,
        )
        if not primary_expanded and not volume_expanded:
            break
        primary_states = _select_global_beam_states(problem, next_primary_states, limits.beam_width)
        volume_state = _supplemental_volume_progress_state(
            problem,
            [*next_primary_states, *next_volume_states],
            primary_states,
            limits.beam_width,
        )
        volume_states = [volume_state] if volume_state is not None else []

    states = [*primary_states, *volume_states]
    best_state = max(states, key=lambda state: _global_state_score(problem, state))
    best_state = _refill_remaining_boxes_in_used_containers(problem, best_state, box_by_id, limits)
    best_state = _rescue_unloaded_boxes(problem, best_state, box_by_id, limits)
    best_state = _local_rearrange_state(problem, best_state, box_by_id, limits)
    return _multi_result_from_global_state(problem, best_state)


def _expand_global_states(
    problem: MultiContainerPackingInput,
    states: list[GlobalPackingState],
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    variant: int,
    rng: random.Random | None,
) -> tuple[list[GlobalPackingState], bool]:
    next_states: list[GlobalPackingState] = []
    expanded_any = False
    for state in states:
        branches = _global_placement_branches(problem, state, box_by_id, limits, variant=variant, rng=rng)
        if branches:
            expanded_any = True
            next_states.extend(branches)
        else:
            next_states.append(state)
    return next_states, expanded_any


def _initial_global_state(problem: MultiContainerPackingInput) -> GlobalPackingState:
    return GlobalPackingState(
        containers=[
            ContainerState(
                spec=container,
                container_id=container_id,
                placements=[],
                free_spaces=_initial_free_spaces_for_spec(container),
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
            max_free_spaces=30,
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
            max_free_spaces=20,
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
            max_free_spaces=80,
        )
    return SearchLimits(
        beam_width=DEFAULT_BEAM_WIDTH,
        box_type_candidates=MAX_GLOBAL_BOX_TYPE_CANDIDATES,
        container_candidates=MAX_GLOBAL_CONTAINER_CANDIDATES,
        placement_branches=MAX_PLACEMENT_BRANCHES,
        global_branches_per_state=MAX_GLOBAL_BRANCHES_PER_STATE,
        batch_placements=MAX_BATCH_PLACEMENTS,
        max_steps=MAX_GLOBAL_SEARCH_STEPS,
        max_free_spaces=80,
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
            max_free_spaces=max(40, limits.max_free_spaces // 2),
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
            max_free_spaces=max(240, round(limits.max_free_spaces * 1.8)),
        )
    return limits


def _global_placement_branches(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits | None = None,
    active_only: bool = False,
    variant: int = 0,
    rng: random.Random | None = None,
) -> list[GlobalPackingState]:
    limits = limits or _global_search_limits(problem)
    branches: list[GlobalPackingState] = []
    tried_box_types = 0
    column_walls_tried: set[tuple[int, tuple[float, float]]] = set()
    ranked_box_types = _ranked_candidate_box_types(problem, state, box_by_id, variant)
    if rng is not None:
        ranked_box_types = _rcl_order(ranked_box_types, rng)
    for box in ranked_box_types:
        if tried_box_types >= limits.box_type_candidates and branches:
            break
        tried_box_types += 1
        for option_index, (container_index, container_state, profile_input, candidates) in enumerate(
            _container_candidate_options(problem, state, box, limits, active_only=active_only, rng=rng)
        ):
            quantity = state.remaining_counter[box.id]
            instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
            repeated_orientations: set[tuple[float, float]] = set()
            for placement in candidates[: limits.placement_branches + 1]:
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
                orientation = (placement.length, placement.width)
                if orientation not in repeated_orientations:
                    repeated_orientations.add(orientation)
                    repeated_branch = _repeat_box_in_container(
                        problem,
                        single_branch,
                        container_index,
                        box,
                        limits,
                        preferred_orientation=orientation,
                    )
                    if len(repeated_branch.containers[container_index].placements) > len(single_branch.containers[container_index].placements):
                        branches.append(repeated_branch)
            layer_branch = _layer_branch_in_container(problem, state, container_index, box, limits)
            if layer_branch is not None:
                branches.append(layer_branch)
            # 立柱墙只在该箱型评分最高的容器里试，控制大规模耗时
            wall_key = (container_index, _footprint_key(box))
            if option_index == 0 and wall_key not in column_walls_tried:
                column_walls_tried.add(wall_key)
                branches.extend(_column_branch_in_container(problem, state, container_index, box, limits))
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
    rng: random.Random | None = None,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
    limits = limits or _global_search_limits(problem)
    quantity = state.remaining_counter[box.id]
    instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"

    active_pool = [
        (index, container)
        for index, container in enumerate(state.containers)
        if container.placements
        and _box_allowed_in_container(box, container)
        and _box_can_fit_container(box, container.spec)
        and _container_remaining_volume(container) >= box.volume
    ]
    active_options = _container_options_from_pool(problem, active_pool, box, instance_id, limits, rng=rng)
    if active_options:
        return _sort_container_options(active_options, limits)
    if active_only:
        return []

    container_pool = _candidate_container_pool(state.containers, box, limits)
    return _sort_container_options(
        _container_options_from_pool(problem, container_pool, box, instance_id, limits, rng=rng),
        limits,
    )


def _container_options_from_pool(
    problem: MultiContainerPackingInput,
    container_pool: list[tuple[int, ContainerState]],
    box: BoxSpec,
    instance_id: str,
    limits: SearchLimits,
    rng: random.Random | None = None,
) -> list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]]:
    options: list[tuple[int, ContainerState, ProfilePackingInput, list[BoxPlacement]]] = []
    for container_index, container_state in container_pool:
        profile_input = _profile_input_for_container(problem, container_state)
        candidates = _placement_candidates(
            box,
            instance_id,
            profile_input,
            container_state.placements,
            container_state.free_spaces,
        )
        if rng is not None:
            # 只扰动头部：截断后只用前几个候选，整条列表重排是 O(n^2) 纯浪费
            head = max(8, limits.placement_branches * 3)
            candidates = _rcl_order(candidates[:head], rng) + candidates[head:]
        if candidates:
            options.append((container_index, container_state, profile_input, _diverse_orientation_candidates(candidates, limits.placement_branches)))
    return options


def _rcl_order(items: list, rng: random.Random, window: int = GRASP_RCL_WINDOW) -> list:
    """GRASP 受限候选列表：每次从前 window 个里随机挑一个，保持对高分项的偏置。"""
    pool = list(items)
    ordered = []
    while pool:
        ordered.append(pool.pop(rng.randrange(min(window, len(pool)))))
    return ordered


def _diverse_orientation_candidates(candidates: list[BoxPlacement], limit: int) -> list[BoxPlacement]:
    """截断候选时保证另一种朝向至少保留一个，避免批量推进只看到单一朝向。"""
    selected = candidates[:limit]
    orientations = {(placement.length, placement.width) for placement in selected}
    for candidate in candidates[limit:]:
        if (candidate.length, candidate.width) not in orientations:
            selected = [*selected, candidate]
            break
    return selected


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
        if _box_allowed_in_container(box, container)
        and _box_can_fit_container(box, container.spec)
        and _container_remaining_volume(container) >= box.volume
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
        key=lambda item: (item[1].used_volume, item[0]),
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
    remaining_after_box = _container_remaining_volume(container) - box.volume
    return (container.used_volume, -remaining_after_box)


def _container_remaining_volume(container: ContainerState) -> float:
    return container.container_volume - container.used_volume


def _container_option_score(container: ContainerState, first_candidate: BoxPlacement) -> tuple[float, float]:
    slack_after_placement = container.container_volume - container.used_volume - first_candidate.volume
    return (container.used_volume, -slack_after_placement)


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
    required_priority = 1 if box.required_container_types else 0
    fit_count = sum(
        1
        for container in state.containers
        if _box_allowed_in_container(box, container) and _box_can_fit_container(box, container.spec)
    )
    remaining_quantity = state.remaining_counter[box.id]
    longest_edge = max(box.length, box.width, box.height)
    if variant == 1:
        return (required_priority, -fit_count, box.volume, remaining_quantity, longest_edge)
    if variant == 2:
        return (required_priority, -fit_count, longest_edge, box.volume, remaining_quantity)
    if variant == 3:
        return (required_priority, -fit_count, box.volume * remaining_quantity, longest_edge, remaining_quantity)
    if variant == 4:
        # 高箱优先：先让高箱占住截面全高区，矮箱整层退到斜边下的矮带
        return (required_priority, -fit_count, box.height, box.volume, remaining_quantity)
    if problem.objective == "maximize_count":
        return (required_priority, -fit_count, remaining_quantity, box.volume, longest_edge)
    return (required_priority, -fit_count, box.volume, remaining_quantity, longest_edge)


def _box_can_fit_any_container(box: BoxSpec, containers: list[ContainerState]) -> bool:
    return any(
        _box_allowed_in_container(box, container) and _box_can_fit_container(box, container.spec)
        for container in containers
    )


def _box_allowed_in_container(box: BoxSpec, container: ContainerState) -> bool:
    return not box.required_container_types or container.spec.id in box.required_container_types


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
    preferred_orientation: tuple[float, float] | None = None,
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
            container_state.free_spaces,
        )
        if not candidates:
            break
        chosen = candidates[0]
        if preferred_orientation is not None:
            for candidate in candidates:
                if (candidate.length, candidate.width) == preferred_orientation:
                    chosen = candidate
                    break
        current_state = _place_box_in_global_state(
            current_state,
            container_index,
            container_state,
            profile_input,
            box,
            chosen,
            limits,
        )
        repeated += 1
    return current_state


def _layer_branch_in_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box: BoxSpec,
    limits: SearchLimits,
) -> GlobalPackingState | None:
    """对剩余数量多的箱型，在空闲空间底面铺一整层混合朝向的行组合。

    逐箱贪心会被放置评分的朝向偏好牵着走，整层 6+6、6+5 这类
    混排组合永远不会出现在分支里。这里直接枚举行组合生成整层放置。
    """
    remaining = state.remaining_counter[box.id]
    if remaining < LAYER_BUILD_MIN_QUANTITY:
        return None
    container_state = state.containers[container_index]
    profile_input = _profile_input_for_container(problem, container_state)
    best_layout: list[BoxPlacement] | None = None
    for space in container_state.free_spaces:
        layout = _layer_layout_in_space(box, space, profile_input, remaining)
        if len(layout) >= 2 and (best_layout is None or len(layout) > len(best_layout)):
            best_layout = layout
    if best_layout is None:
        return None
    current_state = state
    placed = 0
    for layout_placement in best_layout:
        container_state = current_state.containers[container_index]
        quantity = current_state.remaining_counter[box.id]
        if quantity <= 0:
            break
        placement = BoxPlacement(
            box_id=box.id,
            instance_id=f"{box.id}-{box.quantity - quantity + 1:03d}",
            x=layout_placement.x,
            y=layout_placement.y,
            z=layout_placement.z,
            length=layout_placement.length,
            width=layout_placement.width,
            height=layout_placement.height,
        )
        if not _placement_is_valid(profile_input, placement, container_state.placements):
            continue
        current_state = _place_box_in_global_state(
            current_state,
            container_index,
            container_state,
            profile_input,
            box,
            placement,
            limits,
        )
        placed += 1
    if placed < 2:
        return None
    return current_state


def _layer_layout_in_space(
    box: BoxSpec,
    space: FreeSpace,
    problem: ProfilePackingInput,
    max_count: int,
) -> list[BoxPlacement]:
    """在单个空闲空间底面上枚举两种朝向的行组合，返回箱数最多的整层摆法。"""
    if box.height > space.height + EPSILON:
        return []
    interval = convex_y_interval(problem.uld.cross_section, space.z, space.z + box.height)
    if interval is None:
        return []
    y_start = max(space.y, interval[0])
    y_end = min(space.y + space.width, interval[1])
    x_end = min(space.x + space.length, problem.uld.length)
    available_width = y_end - y_start
    available_length = x_end - space.x
    if available_width <= EPSILON or available_length <= EPSILON:
        return []

    row_options: list[tuple[float, float, int]] = []
    for length, width, _height in _orientation_options(box):
        columns = int((available_length + EPSILON) // length)
        if columns > 0 and width <= available_width + EPSILON:
            row_options.append((length, width, columns))
    if not row_options:
        return []

    first = row_options[0]
    second = row_options[1] if len(row_options) > 1 else None
    best_rows: list[tuple[float, float, int]] | None = None
    best_key: tuple[int, float] | None = None
    max_first_rows = int((available_width + EPSILON) // first[1])
    for first_rows in range(max_first_rows + 1):
        used_width = first_rows * first[1]
        second_rows = 0
        if second is not None:
            second_rows = int((available_width - used_width + EPSILON) // second[1])
        count = min(first_rows * first[2] + second_rows * second[2] if second else first_rows * first[2], max_count)
        key = (count, -(used_width + second_rows * second[1] if second else used_width))
        if count > 0 and (best_key is None or key > best_key):
            best_key = key
            best_rows = [first] * first_rows + ([second] * second_rows if second else [])
    if best_rows is None:
        return []

    placements: list[BoxPlacement] = []
    y = y_start
    for length, width, columns in sorted(best_rows, key=lambda row: -row[1]):
        for column in range(columns):
            if len(placements) >= max_count:
                return placements
            placements.append(
                BoxPlacement(
                    box_id=box.id,
                    instance_id="",
                    x=space.x + column * length,
                    y=y,
                    z=space.z,
                    length=length,
                    width=width,
                    height=box.height,
                )
            )
        y += width
    return placements


def _footprint_key(box: BoxSpec) -> tuple[float, float]:
    return (min(box.length, box.width), max(box.length, box.width))


def _cross_section_is_rectangular(cross_section: list[tuple[float, float]]) -> bool:
    max_y = max(y for y, _ in cross_section)
    max_z = max(z for _, z in cross_section)
    return abs(polygon_area(cross_section) - max_y * max_z) <= EPSILON * max(1.0, max_y * max_z)


def _topper_orientation(
    candidate: BoxSpec,
    length: float,
    width: float,
    min_ratio: float,
) -> tuple[float, float] | None:
    """箱子作为柱顶压顶箱时使用的朝向；支撑率不达标则不可用。

    允许少量探出立柱底面（如 108 宽箱压在 98 宽的 D 箱顶上），
    只要按模式支撑率阈值仍然合法。
    """
    best: tuple[float, float] | None = None
    best_overlap = 0.0
    for option_length, option_width, _height in _orientation_options(candidate):
        overlap = min(option_length, length) * min(option_width, width)
        if overlap + EPSILON < option_length * option_width * min_ratio:
            continue
        if overlap > best_overlap:
            best_overlap = overlap
            best = (option_length, option_width)
    return best


def _column_branch_in_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box: BoxSpec,
    limits: SearchLimits,
) -> list[GlobalPackingState]:
    """同底面箱型族沿高度方向叠立柱墙，柱顶允许一个跨箱型压顶箱。

    层构建只在单一 z 面上铺开，矮箱整层会占满截面全高区，
    高箱之后无处可叠。立柱分支把底面一致的箱型按高度组合
    叠到尽量贴近截面顶，柱顶压顶箱补上最后一段（如 D+D 顶上
    放 J 刚好 202+88=290），让"矮箱让出全高带"的方案进入 beam。
    纯同族墙和带压顶墙各出一个分支：压顶箱会消耗别的箱型，
    哪种更优交给 beam 全局评分裁决。
    """
    container_state = state.containers[container_index]
    if _cross_section_is_rectangular(container_state.spec.cross_section):
        # 矩形截面没有高度带错配，整层构建已经覆盖，避免无谓分支挤占 beam
        return []
    family = [
        candidate
        for candidate in problem.boxes
        if state.remaining_counter[candidate.id] > 0 and _footprint_key(candidate) == _footprint_key(box)
        and _box_allowed_in_container(candidate, container_state)
    ]
    if not family:
        return []
    profile_input = _profile_input_for_container(problem, container_state)
    min_ratio = _min_support_ratio_for_mode(problem.search_mode)
    min_height = min(candidate.height for candidate in family)
    branches: list[GlobalPackingState] = []
    for with_toppers in (False, True):
        best_layout: list[list[tuple[BoxSpec, BoxPlacement]]] | None = None
        best_key: tuple[float, int] | None = None
        used_topper = False
        for seed_length, seed_width, _height in _orientation_options(box):
            toppers: list[tuple[BoxSpec, float, float]] = []
            if with_toppers:
                for candidate in problem.boxes:
                    if state.remaining_counter[candidate.id] <= 0 or _footprint_key(candidate) == _footprint_key(box):
                        continue
                    if not _box_allowed_in_container(candidate, container_state):
                        continue
                    orientation = _topper_orientation(candidate, seed_length, seed_width, min_ratio)
                    if orientation is not None:
                        toppers.append((candidate, orientation[0], orientation[1]))
                toppers.sort(key=lambda item: -item[0].volume)
                del toppers[COLUMN_TOPPER_CANDIDATES:]
                if not toppers:
                    continue
            for space in container_state.free_spaces[:COLUMN_BUILD_MAX_SPACES]:
                if 2 * min_height > space.height + EPSILON:
                    continue
                layout = _column_wall_layout(
                    family,
                    toppers,
                    state.remaining_counter,
                    space,
                    seed_length,
                    seed_width,
                    profile_input,
                )
                if layout is None:
                    continue
                key = (
                    sum(placement.volume for column in layout for _, placement in column),
                    max(len(column) for column in layout),
                )
                if best_key is None or key > best_key:
                    best_key = key
                    best_layout = layout
        if best_layout is None:
            continue
        family_ids = {candidate.id for candidate in family}
        used_topper = any(spec.id not in family_ids for column in best_layout for spec, _ in column)
        if with_toppers and not used_topper:
            # 压顶墙退化成纯同族墙时和上一个分支重复
            continue
        branch = _apply_column_layout(problem, state, container_index, best_layout, limits)
        if branch is not None:
            branches.append(branch)
    return branches


def _apply_column_layout(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    layout: list[list[tuple[BoxSpec, BoxPlacement]]],
    limits: SearchLimits,
) -> GlobalPackingState | None:
    current_state = state
    placed = 0
    for column in layout:
        for spec, layout_placement in column:
            container_state = current_state.containers[container_index]
            profile_input = _profile_input_for_container(problem, container_state)
            quantity = current_state.remaining_counter[spec.id]
            if quantity <= 0:
                break
            placement = BoxPlacement(
                box_id=spec.id,
                instance_id=f"{spec.id}-{spec.quantity - quantity + 1:03d}",
                x=layout_placement.x,
                y=layout_placement.y,
                z=layout_placement.z,
                length=layout_placement.length,
                width=layout_placement.width,
                height=layout_placement.height,
            )
            if not _placement_is_valid(profile_input, placement, container_state.placements):
                # 下方箱子没放进去时上方失去支撑，整列从此截断
                break
            current_state = _place_box_in_global_state(
                current_state,
                container_index,
                container_state,
                profile_input,
                spec,
                placement,
                limits,
            )
            placed += 1
    if placed < COLUMN_BUILD_MIN_BOXES:
        return None
    return current_state


def _column_wall_layout(
    family: list[BoxSpec],
    toppers: list[tuple[BoxSpec, float, float]],
    remaining_counter: Counter,
    space: FreeSpace,
    seed_length: float,
    seed_width: float,
    problem: ProfilePackingInput,
) -> list[list[tuple[BoxSpec, BoxPlacement]]] | None:
    """在单个空闲空间里沿 x 排立柱，每列选总体积最大的同族组合加可选压顶箱。"""
    min_height = min(spec.height for spec in family)
    interval = convex_y_interval(problem.uld.cross_section, space.z, space.z + min_height)
    if interval is None:
        return None
    y = max(space.y, interval[0])
    if y + seed_width > min(space.y + space.width, interval[1]) + EPSILON:
        return None
    capacity = _column_capacity(problem.uld.cross_section, y, seed_width, space.z, space.height)
    if capacity < 2 * min_height - EPSILON:
        return None
    columns_limit = int((min(space.length, problem.uld.length - space.x) + EPSILON) // seed_length)
    if columns_limit <= 0:
        return None
    remaining = Counter(
        {spec.id: remaining_counter[spec.id] for spec in family}
        | {spec.id: remaining_counter[spec.id] for spec, _, _ in toppers}
    )
    layout: list[list[tuple[BoxSpec, BoxPlacement]]] = []
    tallest_column = 0
    for index in range(columns_limit):
        family_types = [(spec, seed_length, seed_width, remaining[spec.id]) for spec in family]
        best_column: list[tuple[BoxSpec, float, float]] | None = None
        best_volume = 0.0
        for topper in [None, *toppers]:
            topper_height = topper[0].height if topper is not None else 0.0
            if topper is not None and (remaining[topper[0].id] <= 0 or topper_height > capacity + EPSILON):
                continue
            combo = _max_volume_combo(family_types, capacity - topper_height)
            column_boxes = [(spec, length, width) for spec, length, width, count in combo for _ in range(count)]
            if topper is not None:
                if not column_boxes:
                    continue
                column_boxes.append(topper)
            volume = sum(spec.volume for spec, _, _ in column_boxes)
            if column_boxes and volume > best_volume + EPSILON:
                best_volume = volume
                best_column = column_boxes
        if best_column is None:
            break
        x = space.x + index * seed_length
        z = space.z
        column: list[tuple[BoxSpec, BoxPlacement]] = []
        for spec, length, width in best_column:
            column.append(
                (
                    spec,
                    BoxPlacement(
                        box_id=spec.id,
                        instance_id="",
                        x=x,
                        y=y,
                        z=z,
                        length=length,
                        width=width,
                        height=spec.height,
                    ),
                )
            )
            z += spec.height
            remaining[spec.id] -= 1
        layout.append(column)
        tallest_column = max(tallest_column, len(column))
    if tallest_column < 2 or sum(len(column) for column in layout) < COLUMN_BUILD_MIN_BOXES:
        return None
    return layout


def _column_capacity(
    cross_section: list[tuple[float, float]],
    y: float,
    width: float,
    z: float,
    max_height: float,
) -> float:
    """固定 y 区间后立柱在截面里的最大可用高度，按斜边二分收敛。"""

    def fits(height: float) -> bool:
        interval = convex_y_interval(cross_section, z, z + height)
        return interval is not None and y >= interval[0] - EPSILON and y + width <= interval[1] + EPSILON

    if fits(max_height):
        return max_height
    low, high = 0.0, max_height
    for _ in range(32):
        mid = (low + high) / 2
        if fits(mid):
            low = mid
        else:
            high = mid
    return low


def _max_volume_combo(
    types: list[tuple[BoxSpec, float, float, int]],
    capacity: float,
) -> list[tuple[BoxSpec, float, float, int]]:
    """有限数量下的一维装填：枚举各箱型数量组合，总体积最大且总高不超容量。

    按体积/高度密度降序搜索，配合乐观上界剪枝，
    族内箱型多时也能保持枚举量很小。
    """
    ordered = sorted(types, key=lambda item: -(item[0].volume / item[0].height))
    suffix_density = [0.0] * (len(ordered) + 1)
    for index in range(len(ordered) - 1, -1, -1):
        density = ordered[index][0].volume / ordered[index][0].height
        suffix_density[index] = max(density, suffix_density[index + 1])
    best_volume = 0.0
    best_counts = [0] * len(ordered)
    counts = [0] * len(ordered)

    def search(index: int, total_height: float, total_volume: float) -> None:
        nonlocal best_volume, best_counts
        if total_volume > best_volume + EPSILON:
            best_volume = total_volume
            best_counts = counts.copy()
        if index >= len(ordered):
            return
        if total_volume + (capacity - total_height) * suffix_density[index] <= best_volume + EPSILON:
            return
        spec, _length, _width, available = ordered[index]
        max_count = min(available, int((capacity - total_height + EPSILON) // spec.height))
        for count in range(max_count, -1, -1):
            counts[index] = count
            search(index + 1, total_height + count * spec.height, total_volume + count * spec.volume)
        counts[index] = 0

    search(0, 0.0, 0.0)
    return [
        (ordered[index][0], ordered[index][1], ordered[index][2], count)
        for index, count in enumerate(best_counts)
        if count > 0
    ]


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


def _rescue_unloaded_boxes(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState:
    """主搜索结束后，对静态可装却没装上的箱型做定向腾挪。

    强约束箱型（如只有一个 ULD 装得下的超长箱）在 beam 中途会被
    大批量分支挤出，等轮到它时空间已经碎了。这里腾空目标容器、
    先放该箱再回填，分数更优才接受。
    """
    current_state = state
    current_score = _global_state_score(problem, current_state)
    for box_id in sorted(current_state.remaining_counter):
        if current_state.remaining_counter[box_id] <= 0:
            continue
        box = box_by_id[box_id]
        for container_index, container in enumerate(current_state.containers):
            if not _box_allowed_in_container(box, container):
                continue
            if not _box_can_fit_container(box, container.spec):
                continue
            candidate = _rescue_box_into_container(problem, current_state, container_index, box, box_by_id, limits)
            if candidate is None:
                continue
            candidate_score = _global_state_score(problem, candidate)
            if candidate_score > current_score:
                current_state = candidate
                current_score = candidate_score
                break
    return current_state


def _rescue_box_into_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box: BoxSpec,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
) -> GlobalPackingState | None:
    """按破坏强度从小到大尝试：先只拆顶层（超长箱常见落点是层顶），再全腾空。"""
    best_state: GlobalPackingState | None = None
    best_score: tuple[object, ...] | None = None
    for ruined in (
        _strip_container_top_layer(problem, state, container_index, limits),
        _evacuate_containers(state, [container_index]),
    ):
        if ruined is state:
            continue
        seeded = _seed_box_in_container(problem, ruined, container_index, box, limits)
        if seeded is None:
            continue
        refilled = _resolve_active_only_beam(problem, seeded, box_by_id, limits)
        refilled = _refill_remaining_boxes_in_used_containers(problem, refilled, box_by_id, limits)
        score = _global_state_score(problem, refilled)
        if best_state is None or score > best_score:
            best_state = refilled
            best_score = score
    return best_state


def _strip_container_top_layer(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    limits: SearchLimits,
) -> GlobalPackingState:
    container = state.containers[container_index]
    if not container.placements:
        return state
    top_z = max(placement.z for placement in container.placements)
    if top_z <= 0:
        return state
    kept = [placement for placement in container.placements if placement.z < top_z]
    removed = [placement for placement in container.placements if placement.z >= top_z]
    if not kept or not removed:
        return state
    next_remaining = state.remaining_counter.copy()
    for placement in removed:
        next_remaining[placement.box_id] += 1
    profile_input = _profile_input_for_container(problem, container)
    next_containers = [*state.containers]
    next_containers[container_index] = ContainerState(
        spec=container.spec,
        container_id=container.container_id,
        placements=kept,
        free_spaces=_free_spaces_for_placements(profile_input, kept, limits),
    )
    return GlobalPackingState(containers=next_containers, remaining_counter=next_remaining)


def _seed_box_in_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box: BoxSpec,
    limits: SearchLimits,
) -> GlobalPackingState | None:
    container_state = state.containers[container_index]
    if not _box_allowed_in_container(box, container_state):
        return None
    profile_input = _profile_input_for_container(problem, container_state)
    quantity = state.remaining_counter[box.id]
    instance_id = f"{box.id}-{box.quantity - quantity + 1:03d}"
    candidates = _placement_candidates(
        box,
        instance_id,
        profile_input,
        container_state.placements,
        container_state.free_spaces,
    )
    if not candidates:
        return None
    return _place_box_in_global_state(
        state,
        container_index,
        container_state,
        profile_input,
        box,
        candidates[0],
        limits,
    )


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
    best_state, best_score = _run_rearrange_strategy(
        problem,
        best_state,
        best_score,
        box_by_id,
        limits,
        tried_signatures,
        _repack_and_refill,
        targets_per_pass=2,
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
                free_spaces=_initial_free_spaces_for_spec(container.spec),
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
    active_only: bool = True,
) -> GlobalPackingState:
    remaining_count = sum(quantity for quantity in state.remaining_counter.values() if quantity > 0)
    if remaining_count == 0:
        return state
    states = [state]
    for _ in range(min(remaining_count, limits.max_steps)):
        next_states: list[GlobalPackingState] = []
        expanded_any = False
        for current in states:
            branches = _global_placement_branches(problem, current, box_by_id, limits, active_only=active_only)
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
    current_state = state
    for index in target_indices:
        current_state = _strip_container_top_layer(problem, current_state, index, limits)
    if current_state is state:
        return state
    return _refill_remaining_boxes_in_used_containers(problem, current_state, box_by_id, limits)


def _repack_and_refill(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    target_indices: list[int],
) -> GlobalPackingState:
    """把最差的几个容器一起腾空，用全量分支联合重装。

    单容器腾挪只能在其余容器的缝隙里找位置，两个装载率都低的
    容器需要把箱子合并重摆才能腾出整块空间，所以这里允许重新
    打开被腾空的容器。
    """
    evacuated = _evacuate_containers(state, target_indices)
    if evacuated is state:
        return state
    resolved = _resolve_active_only_beam(problem, evacuated, box_by_id, limits, active_only=False)
    return _refill_remaining_boxes_in_used_containers(problem, resolved, box_by_id, limits)


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
        if not _box_allowed_in_container(box, container_state):
            continue
        if not _box_can_fit_container(box, container_state.spec) or _container_remaining_volume(container_state) < box.volume:
            continue
        profile_input = _profile_input_for_container(problem, container_state)
        candidates = _placement_candidates(
            box,
            instance_id,
            profile_input,
            container_state.placements,
            container_state.free_spaces,
        )
        if candidates:
            options.append((container_index, container_state, profile_input, candidates[0]))
    if not options:
        return None
    return max(options, key=lambda option: _container_option_score(option[1], option[3]))


def _free_spaces_for_placements(
    problem: ProfilePackingInput,
    placements: list[BoxPlacement],
    limits: SearchLimits | None,
) -> list[FreeSpace]:
    spaces = _initial_free_spaces(problem)
    max_spaces = _free_space_limit(limits) if limits else 160
    for placement in placements:
        spaces = _subtract_placement_from_spaces(spaces, placement, max_spaces)
    return spaces


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
    next_free_spaces = _subtract_placement_from_spaces(
        container_state.free_spaces,
        placement,
        _free_space_limit(limits),
    )
    next_container = ContainerState(
        spec=container_state.spec,
        container_id=container_state.container_id,
        placements=next_placements,
        free_spaces=next_free_spaces,
        container_volume=container_state.container_volume,
        used_volume=container_state.used_volume + placement.volume,
        max_x=max(container_state.max_x, placement.x + placement.length),
        max_y=max(container_state.max_y, placement.y + placement.width),
        max_z=max(container_state.max_z, placement.z + placement.height),
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


def _supplemental_volume_progress_state(
    problem: MultiContainerPackingInput,
    candidates: list[GlobalPackingState],
    primary_states: list[GlobalPackingState],
    beam_width: int,
) -> GlobalPackingState | None:
    if beam_width <= 1 or not candidates:
        return None

    # 层、立柱和重复箱型分支一次可以放入多个箱子，普通分支通常只放一个。
    # 单按“剩余箱数”裁剪会让批量小箱分支挤掉大体积箱子的长期可行路径。
    # 体积路径使用独立的补充 frontier，不能进入或替换主 beam。
    volume_progress_leader = max(
        candidates,
        key=lambda state: _global_volume_progress_score(problem, state),
    )
    primary_signatures = {_global_state_signature(state) for state in primary_states}
    if _global_state_signature(volume_progress_leader) in primary_signatures:
        return None
    return volume_progress_leader


def _global_volume_progress_score(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
) -> tuple[float, ...]:
    """为 beam 保留体积进展路径，避免不同批量步长造成单一方向剪枝。"""
    required_unloaded_count = _required_unloaded_count_from_state(problem, state)
    used_volume = sum(container.used_volume for container in state.containers)
    return (-required_unloaded_count, used_volume)


def _global_state_score(problem: MultiContainerPackingInput, state: GlobalPackingState) -> tuple[float, ...]:
    used_volume = sum(container.used_volume for container in state.containers)
    loaded_count = sum(len(container.placements) for container in state.containers)
    unloaded_count = sum(quantity for quantity in state.remaining_counter.values() if quantity > 0)
    remaining_volume = sum(state.remaining_counter[box.id] * box.volume for box in problem.boxes)
    has_merged_box_rows = any(box._merge_source_count > 1 for box in problem.boxes)
    required_unloaded_count = _required_unloaded_count_from_state(problem, state)
    compactness = sum(_container_bounding_volume(container) for container in state.containers)
    used_container_count = _used_container_count(state.containers)
    active_container_utilization = _active_container_utilization(state.containers)
    if problem.objective == "maximize_count":
        return (
            -required_unloaded_count,
            -unloaded_count,
            -used_container_count,
            loaded_count,
            *((-remaining_volume,) if has_merged_box_rows else ()),
            used_volume,
            active_container_utilization,
            -compactness,
        )
    return (
        -required_unloaded_count,
        *((-remaining_volume, -unloaded_count) if has_merged_box_rows else (-unloaded_count,)),
        -used_container_count,
        used_volume,
        loaded_count,
        active_container_utilization,
        -compactness,
    )


def _required_unloaded_count_from_state(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
) -> int:
    return sum(state.remaining_counter[box.id] for box in problem.boxes if box.required_container_types)


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
                free_spaces=container_state.free_spaces,
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
    validation_errors.extend(_required_container_validation_errors(problem, state))
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


def _required_container_validation_errors(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
) -> list[str]:
    box_by_id = {box.id: box for box in problem.boxes}
    errors: list[str] = []
    for container in state.containers:
        for placement in container.placements:
            required_container_types = box_by_id[placement.box_id].required_container_types
            if required_container_types and container.spec.id not in required_container_types:
                errors.append(
                    f"{placement.instance_id} must be placed in one of container types {list(required_container_types)}"
                )
    return errors


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
    return container.max_x * container.max_y * container.max_z


def _used_container_count(containers: list[ContainerState]) -> int:
    return sum(1 for container in containers if container.placements)


def _active_container_utilization(containers: list[ContainerState]) -> float:
    used_volume = 0
    active_volume = 0
    for container in containers:
        if not container.placements:
            continue
        active_volume += container.container_volume
        used_volume += container.used_volume
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
    free_spaces: list[FreeSpace],
) -> list[BoxPlacement]:
    candidates: list[tuple[BoxPlacement, PlacementScore]] = []
    seen: set[tuple[float, float, float, float, float, float]] = set()
    current_extents = _bounding_extents(placements)
    scan_index = _placement_scan_index(placements)
    max_y = max(y for y, _ in problem.uld.cross_section)
    max_z = max(z for _, z in problem.uld.cross_section)
    for space in free_spaces:
        for length, width, height in _orientation_options(box):
            position = _position_in_space(space, length, width, height, problem)
            if position is None:
                continue
            x, y, z = position
            key = (x, y, z, length, width, height)
            if key in seen:
                continue
            seen.add(key)
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
            metrics = _placement_candidate_metrics(problem, placement, scan_index, max_y, max_z)
            if metrics is not None:
                support_ratio, dominant_support_ratio, contact_count = metrics
                candidates.append(
                    (
                        placement,
                        _placement_score(
                            placement,
                            current_extents,
                            support_ratio,
                            dominant_support_ratio,
                            contact_count,
                        ),
                    )
                )
    return [placement for placement, _score in sorted(candidates, key=lambda item: item[1])]


def _position_in_space(
    space: FreeSpace,
    length: float,
    width: float,
    height: float,
    problem: ProfilePackingInput,
) -> Point3D | None:
    """箱子放进空闲空间的最小角位置；y 方向沿截面斜边滑入到第一个合法值。"""
    if length > space.length + EPSILON or height > space.height + EPSILON:
        return None
    if space.x + length > problem.uld.length + EPSILON:
        return None
    interval = convex_y_interval(problem.uld.cross_section, space.z, space.z + height)
    if interval is None:
        return None
    y_left, y_right = interval
    y = max(space.y, y_left)
    y_limit = min(space.y + space.width, y_right)
    if y + width > y_limit + EPSILON:
        return None
    return (space.x, y, space.z)


def _placement_score(
    placement: BoxPlacement,
    current_extents: Point3D,
    support_ratio: float,
    dominant_support_ratio: float,
    contact_count: int,
) -> PlacementScore:
    max_x = max(current_extents[0], placement.x + placement.length)
    max_y = max(current_extents[1], placement.y + placement.width)
    max_z = max(current_extents[2], placement.z + placement.height)
    bounding_volume = max_x * max_y * max_z
    return (
        bounding_volume,
        max_z,
        max_y,
        max_x,
        -support_ratio,
        -dominant_support_ratio,
        -contact_count,
        placement.z,
        placement.y,
        placement.x,
    )


def _placement_candidate_metrics(
    problem: ProfilePackingInput,
    placement: BoxPlacement,
    scan_index: PlacementScanIndex,
    max_y: float,
    max_z: float,
) -> tuple[float, float, int] | None:
    """一次扫描完成候选的碰撞、支撑和接触面计算。"""
    if placement.x + placement.length > problem.uld.length:
        return None
    if not rectangle_inside_polygon(
        y=placement.y,
        z=placement.z,
        width=placement.width,
        height=placement.height,
        polygon=problem.uld.cross_section,
    ):
        return None

    contacts = 0
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

    for existing in scan_index.placements:
        if placements_overlap(placement, existing):
            return None

    contact_indices: set[int] = set()
    contact_indices.update(scan_index.x_ends.get(placement.x, ()))
    contact_indices.update(scan_index.x_starts.get(placement.x + placement.length, ()))
    contact_indices.update(scan_index.y_ends.get(placement.y, ()))
    contact_indices.update(scan_index.y_starts.get(placement.y + placement.width, ()))
    contact_indices.update(scan_index.z_ends.get(placement.z, ()))
    contact_indices.update(scan_index.z_starts.get(placement.z + placement.height, ()))
    for index in contact_indices:
        contacts += _face_contact_count(placement, scan_index.placements[index])

    if placement.z == 0:
        return (1, 1, contacts)

    support_area = 0.0
    dominant_support_area = 0.0
    start = bisect_left(scan_index.top_heights, placement.z - EPSILON)
    end = bisect_right(scan_index.top_heights, placement.z + EPSILON)
    supporter_indices: list[int] = []
    for top_height in scan_index.top_heights[start:end]:
        supporter_indices.extend(scan_index.z_ends[top_height])
    for index in sorted(supporter_indices):
        overlap_area = _support_overlap_area(placement, scan_index.placements[index])
        support_area += overlap_area
        dominant_support_area = max(dominant_support_area, overlap_area)

    bottom_area = placement.length * placement.width
    support_ratio = support_area / bottom_area if bottom_area else 0
    if support_ratio < _min_support_ratio_for_mode(problem.search_mode):
        return None
    dominant_support_ratio = dominant_support_area / bottom_area if bottom_area else 0
    return (support_ratio, dominant_support_ratio, contacts)


def _placement_scan_index(placements: list[BoxPlacement]) -> PlacementScanIndex:
    x_starts: defaultdict[float, list[int]] = defaultdict(list)
    x_ends: defaultdict[float, list[int]] = defaultdict(list)
    y_starts: defaultdict[float, list[int]] = defaultdict(list)
    y_ends: defaultdict[float, list[int]] = defaultdict(list)
    z_starts: defaultdict[float, list[int]] = defaultdict(list)
    z_ends: defaultdict[float, list[int]] = defaultdict(list)
    for index, placement in enumerate(placements):
        x_starts[placement.x].append(index)
        x_ends[placement.x + placement.length].append(index)
        y_starts[placement.y].append(index)
        y_ends[placement.y + placement.width].append(index)
        z_starts[placement.z].append(index)
        z_ends[placement.z + placement.height].append(index)
    return PlacementScanIndex(
        placements=placements,
        x_starts={coordinate: tuple(indices) for coordinate, indices in x_starts.items()},
        x_ends={coordinate: tuple(indices) for coordinate, indices in x_ends.items()},
        y_starts={coordinate: tuple(indices) for coordinate, indices in y_starts.items()},
        y_ends={coordinate: tuple(indices) for coordinate, indices in y_ends.items()},
        z_starts={coordinate: tuple(indices) for coordinate, indices in z_starts.items()},
        z_ends={coordinate: tuple(indices) for coordinate, indices in z_ends.items()},
        top_heights=tuple(sorted(z_ends)),
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


def _initial_free_spaces(problem: ProfilePackingInput) -> list[FreeSpace]:
    return _initial_free_spaces_for_profile(problem.uld.length, problem.uld.cross_section)


def _initial_free_spaces_for_spec(spec: ContainerSpec) -> list[FreeSpace]:
    return _initial_free_spaces_for_profile(spec.length, spec.cross_section)


def _initial_free_spaces_for_profile(length: float, cross_section: list[tuple[float, float]]) -> list[FreeSpace]:
    max_y = max(y for y, _ in cross_section)
    max_z = max(z for _, z in cross_section)
    return [FreeSpace(x=0, y=0, z=0, length=length, width=max_y, height=max_z)]


def _subtract_placement_from_spaces(
    spaces: list[FreeSpace],
    placement: BoxPlacement,
    max_spaces: int,
) -> list[FreeSpace]:
    """从空闲空间集合中扣掉一个箱子，维持极大空间不互相包含的不变量。"""
    survivors: list[FreeSpace] = []
    parts: list[FreeSpace] = []
    for space in spaces:
        if _space_intersects_placement(space, placement):
            parts.extend(_split_space_around_placement(space, placement))
        else:
            survivors.append(space)
    unique_parts: dict[tuple[float, float, float, float, float, float], FreeSpace] = {}
    for part in parts:
        unique_parts[(part.x, part.y, part.z, part.length, part.width, part.height)] = part
    # 体积大的先进，后续小空间若被已留空间包含则丢弃
    for part in sorted(unique_parts.values(), key=lambda item: -item.volume):
        if any(_space_contains_space(other, part) for other in survivors):
            continue
        survivors.append(part)
    return _cap_free_spaces(survivors, max_spaces)


def _space_intersects_placement(space: FreeSpace, placement: BoxPlacement) -> bool:
    return (
        space.x + space.length > placement.x + EPSILON
        and placement.x + placement.length > space.x + EPSILON
        and space.y + space.width > placement.y + EPSILON
        and placement.y + placement.width > space.y + EPSILON
        and space.z + space.height > placement.z + EPSILON
        and placement.z + placement.height > space.z + EPSILON
    )


def _split_space_around_placement(space: FreeSpace, placement: BoxPlacement) -> list[FreeSpace]:
    parts: list[FreeSpace] = []
    if placement.x - space.x > EPSILON:
        parts.append(FreeSpace(space.x, space.y, space.z, placement.x - space.x, space.width, space.height))
    right = placement.x + placement.length
    if space.x + space.length - right > EPSILON:
        parts.append(FreeSpace(right, space.y, space.z, space.x + space.length - right, space.width, space.height))
    if placement.y - space.y > EPSILON:
        parts.append(FreeSpace(space.x, space.y, space.z, space.length, placement.y - space.y, space.height))
    back = placement.y + placement.width
    if space.y + space.width - back > EPSILON:
        parts.append(FreeSpace(space.x, back, space.z, space.length, space.y + space.width - back, space.height))
    if placement.z - space.z > EPSILON:
        parts.append(FreeSpace(space.x, space.y, space.z, space.length, space.width, placement.z - space.z))
    top = placement.z + placement.height
    if space.z + space.height - top > EPSILON:
        parts.append(FreeSpace(space.x, space.y, top, space.length, space.width, space.z + space.height - top))
    return parts


def _space_contains_space(outer: FreeSpace, inner: FreeSpace) -> bool:
    return (
        outer.x <= inner.x + EPSILON
        and outer.y <= inner.y + EPSILON
        and outer.z <= inner.z + EPSILON
        and outer.x + outer.length >= inner.x + inner.length - EPSILON
        and outer.y + outer.width >= inner.y + inner.width - EPSILON
        and outer.z + outer.height >= inner.z + inner.height - EPSILON
    )


def _cap_free_spaces(spaces: list[FreeSpace], max_spaces: int) -> list[FreeSpace]:
    sorted_spaces = sorted(spaces, key=_free_space_sort_key)
    if len(sorted_spaces) <= max_spaces:
        return sorted_spaces
    return _select_diverse_free_spaces(sorted_spaces, max_spaces)


def _free_space_sort_key(space: FreeSpace) -> tuple[float, float, float, float]:
    return (space.z, space.y, space.x, -space.volume)


def _select_diverse_free_spaces(sorted_spaces: list[FreeSpace], max_spaces: int) -> list[FreeSpace]:
    """先保留低层空间，再按高度层轮流保留，避免上层堆叠空间被裁掉。"""
    if max_spaces <= 0:
        return []

    selected: list[FreeSpace] = []
    seen: set[int] = set()

    floor_quota = max(1, max_spaces // 3)
    for space in sorted_spaces[:floor_quota]:
        selected.append(space)
        seen.add(id(space))

    layers: dict[float, list[FreeSpace]] = {}
    for space in sorted_spaces:
        layers.setdefault(space.z, []).append(space)

    layer_index = 0
    layer_heights = sorted(layers)
    while len(selected) < max_spaces:
        progressed = False
        for height in layer_heights:
            layer = layers[height]
            if layer_index >= len(layer):
                continue
            progressed = True
            space = layer[layer_index]
            if id(space) in seen:
                continue
            selected.append(space)
            seen.add(id(space))
            if len(selected) >= max_spaces:
                break
        if not progressed:
            break
        layer_index += 1

    return sorted(selected, key=_free_space_sort_key)


def _free_space_limit(limits: SearchLimits) -> int:
    return max(160, limits.max_free_spaces)


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
