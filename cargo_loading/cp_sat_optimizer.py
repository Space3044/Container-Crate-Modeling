from __future__ import annotations

"""Optional CP-SAT local optimizer for small, high-value container neighborhoods."""

from math import ceil, sqrt
from typing import TYPE_CHECKING

from cargo_loading.profile_models import BoxPlacement, BoxSpec, MultiContainerPackingInput

try:
    from ortools.sat.python import cp_model
except (ImportError, OSError):  # pragma: no cover - exercised by stdlib-only deployments
    cp_model = None

if TYPE_CHECKING:
    from cargo_loading.profile_packer import GlobalPackingState, SearchLimits


CP_SCALE = 1000
DEFAULT_TIME_LIMIT_SECONDS = 0.35
DEFAULT_MAX_ITEMS = 16
MAX_INVALID_SOLUTIONS = 3


def is_available() -> bool:
    return cp_model is not None


def optimize_single_container(
    problem: MultiContainerPackingInput,
    state: GlobalPackingState,
    container_index: int,
    box_by_id: dict[str, BoxSpec],
    limits: SearchLimits,
    *,
    time_limit_seconds: float = DEFAULT_TIME_LIMIT_SECONDS,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> GlobalPackingState | None:
    """Repack one container with CP-SAT and return only a geometrically valid result."""
    if cp_model is None:
        return None

    from cargo_loading.profile_packer import (
        _evacuate_containers,
        _free_spaces_for_placements,
        _box_allowed_in_container,
        _min_support_ratio_for_mode,
        _orientation_options,
        _profile_input_for_container,
        validate_profile_packing,
    )

    target = state.containers[container_index]
    if not target.placements:
        return None
    evacuated = _evacuate_containers(state, [container_index])
    empty_container = evacuated.containers[container_index]
    profile_input = _profile_input_for_container(problem, empty_container)

    items: list[tuple[str, BoxSpec]] = [
        (f"placed-{index:03d}", box_by_id[placement.box_id])
        for index, placement in enumerate(target.placements)
        if placement.box_id in box_by_id
    ]
    for box_id, quantity in state.remaining_counter.items():
        box = box_by_id.get(box_id)
        if box is None or quantity <= 0:
            continue
        if not _box_allowed_in_container(box, empty_container):
            continue
        if not _box_can_fit_container_for_optimizer(box, empty_container.spec, _orientation_options):
            continue
        for index in range(quantity):
            items.append((f"remaining-{box_id}-{index:03d}", box))
            if len(items) > max_items:
                break
        if len(items) > max_items:
            break
    if not items or len(items) > max_items:
        return None

    dimensions = _scaled_dimensions(empty_container.spec.length, empty_container.spec.cross_section)
    container_length, max_y, max_z = dimensions[:3]
    orientations = [_orientation_options(box) for _, box in items]
    if any(not options for options in orientations):
        return None

    forbidden: list[tuple[int, int, int, int, int, int]] = []
    for _ in range(MAX_INVALID_SOLUTIONS):
        model_data = _build_model(
            items,
            orientations,
            empty_container.spec.cross_section,
            container_length,
            max_y,
            max_z,
            _min_support_ratio_for_mode(problem.search_mode),
            forbidden,
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.05, time_limit_seconds)
        solver.parameters.num_search_workers = 1
        status = solver.Solve(model_data.model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        placements = _placements_from_solution(model_data, solver, items, orientations)
        errors = validate_profile_packing(profile_input, placements)
        if not errors:
            return _state_with_optimized_container(
                problem,
                state,
                evacuated,
                container_index,
                placements,
                limits,
                _free_spaces_for_placements,
            )
        forbidden.extend(_forbidden_assignments_for_invalid_placements(model_data, solver))
        if not forbidden:
            return None
    return None


def _box_can_fit_container_for_optimizer(box: BoxSpec, spec, orientation_options) -> bool:
    max_y = max(y for y, _ in spec.cross_section)
    max_z = max(z for _, z in spec.cross_section)
    return any(
        length <= spec.length
        and width <= max_y
        and height <= max_z
        for length, width, height in orientation_options(box)
    )


def _scaled_dimensions(length: float, cross_section: list[tuple[float, float]]) -> tuple[int, int, int]:
    max_y = max(y for y, _ in cross_section)
    max_z = max(z for _, z in cross_section)
    return (_scale(length), _scale(max_y), _scale(max_z))


def _scale(value: float) -> int:
    return int(round(value * CP_SCALE))


class _ModelData:
    def __init__(self, model, present, x, y, z, orientation, length, width, height):
        self.model = model
        self.present = present
        self.x = x
        self.y = y
        self.z = z
        self.orientation = orientation
        self.length = length
        self.width = width
        self.height = height


def _build_model(
    items: list[tuple[str, BoxSpec]],
    orientations: list[list[tuple[float, float, float]]],
    cross_section: list[tuple[float, float]],
    container_length: int,
    max_y: int,
    max_z: int,
    min_support_ratio: float,
    forbidden: list[tuple[int, int, int, int, int, int]],
) -> _ModelData:
    model = cp_model.CpModel()
    present = []
    x_vars = []
    y_vars = []
    z_vars = []
    orientation_vars = []
    length_vars = []
    width_vars = []
    height_vars = []

    for index, (_item_id, _box) in enumerate(items):
        options = orientations[index]
        present_var = model.NewBoolVar(f"present_{index}")
        orientation_var = model.NewIntVar(0, len(options) - 1, f"orientation_{index}")
        x_var = model.NewIntVar(0, container_length, f"x_{index}")
        y_var = model.NewIntVar(0, max_y, f"y_{index}")
        z_var = model.NewIntVar(0, max_z, f"z_{index}")
        length_var = model.NewIntVar(0, container_length, f"length_{index}")
        width_var = model.NewIntVar(0, max_y, f"width_{index}")
        height_var = model.NewIntVar(0, max_z, f"height_{index}")
        model.AddElement(orientation_var, [_scale(option[0]) for option in options], length_var)
        model.AddElement(orientation_var, [_scale(option[1]) for option in options], width_var)
        model.AddElement(orientation_var, [_scale(option[2]) for option in options], height_var)

        model.Add(x_var + length_var <= container_length).OnlyEnforceIf(present_var)
        model.Add(y_var + width_var <= max_y).OnlyEnforceIf(present_var)
        model.Add(z_var + height_var <= max_z).OnlyEnforceIf(present_var)
        _add_cross_section_constraints(
            model,
            present_var,
            y_var,
            z_var,
            width_var,
            height_var,
            cross_section,
        )
        present.append(present_var)
        x_vars.append(x_var)
        y_vars.append(y_var)
        z_vars.append(z_var)
        orientation_vars.append(orientation_var)
        length_vars.append(length_var)
        width_vars.append(width_var)
        height_vars.append(height_var)

    for first in range(len(items)):
        for second in range(first + 1, len(items)):
            alternatives = [model.NewBoolVar(f"separation_{first}_{second}_{axis}") for axis in range(6)]
            model.AddBoolOr([present[first].Not(), present[second].Not(), *alternatives])
            model.Add(x_vars[first] + length_vars[first] <= x_vars[second]).OnlyEnforceIf(
                [present[first], present[second], alternatives[0]]
            )
            model.Add(x_vars[second] + length_vars[second] <= x_vars[first]).OnlyEnforceIf(
                [present[first], present[second], alternatives[1]]
            )
            model.Add(y_vars[first] + width_vars[first] <= y_vars[second]).OnlyEnforceIf(
                [present[first], present[second], alternatives[2]]
            )
            model.Add(y_vars[second] + width_vars[second] <= y_vars[first]).OnlyEnforceIf(
                [present[first], present[second], alternatives[3]]
            )
            model.Add(z_vars[first] + height_vars[first] <= z_vars[second]).OnlyEnforceIf(
                [present[first], present[second], alternatives[4]]
            )
            model.Add(z_vars[second] + height_vars[second] <= z_vars[first]).OnlyEnforceIf(
                [present[first], present[second], alternatives[5]]
            )

    _add_support_constraints(
        model,
        present,
        x_vars,
        y_vars,
        z_vars,
        orientation_vars,
        orientations,
        min_support_ratio,
    )

    for assignment in forbidden:
        item_index, present_value, x_value, y_value, z_value, orientation_value = assignment
        model.AddForbiddenAssignments(
            [present[item_index], x_vars[item_index], y_vars[item_index], z_vars[item_index], orientation_vars[item_index]],
            [[present_value, x_value, y_value, z_value, orientation_value]],
        )

    volume_sum = sum(
        _scale(box.volume) * present[index]
        for index, (_item_id, box) in enumerate(items)
    )
    count_weight = sum(_scale(box.volume) for _item_id, box in items) + 1
    model.Maximize(count_weight * sum(present) + volume_sum)
    return _ModelData(
        model,
        present,
        x_vars,
        y_vars,
        z_vars,
        orientation_vars,
        length_vars,
        width_vars,
        height_vars,
    )


def _add_support_constraints(
    model,
    present,
    x_vars,
    y_vars,
    z_vars,
    orientation_vars,
    orientations,
    min_support_ratio: float,
) -> None:
    overlap_patterns = (
        (min_support_ratio, 1.0),
        (sqrt(min_support_ratio), sqrt(min_support_ratio)),
        (1.0, min_support_ratio),
    )
    for upper in range(len(present)):
        on_floor = model.NewBoolVar(f"on_floor_{upper}")
        model.AddImplication(on_floor, present[upper])
        model.Add(z_vars[upper] == 0).OnlyEnforceIf(on_floor)
        model.Add(z_vars[upper] >= 1).OnlyEnforceIf([present[upper], on_floor.Not()])
        supporters = []
        for lower in range(len(present)):
            if lower == upper:
                continue
            for upper_orientation, upper_dimensions in enumerate(orientations[upper]):
                upper_length = _scale(upper_dimensions[0])
                upper_width = _scale(upper_dimensions[1])
                for lower_orientation, lower_dimensions in enumerate(orientations[lower]):
                    lower_height = _scale(lower_dimensions[2])
                    for pattern_index, (length_ratio, width_ratio) in enumerate(overlap_patterns):
                        support = model.NewBoolVar(
                            f"support_{lower}_{upper}_{lower_orientation}_{upper_orientation}_{pattern_index}"
                        )
                        model.AddImplication(support, present[lower])
                        model.AddImplication(support, present[upper])
                        model.Add(orientation_vars[lower] == lower_orientation).OnlyEnforceIf(support)
                        model.Add(orientation_vars[upper] == upper_orientation).OnlyEnforceIf(support)
                        model.Add(z_vars[upper] == z_vars[lower] + lower_height).OnlyEnforceIf(support)
                        required_length = ceil(upper_length * length_ratio)
                        required_width = ceil(upper_width * width_ratio)
                        model.Add(x_vars[upper] + required_length <= x_vars[lower] + _scale(lower_dimensions[0])).OnlyEnforceIf(support)
                        model.Add(x_vars[lower] + required_length <= x_vars[upper] + upper_length).OnlyEnforceIf(support)
                        model.Add(y_vars[upper] + required_width <= y_vars[lower] + _scale(lower_dimensions[1])).OnlyEnforceIf(support)
                        model.Add(y_vars[lower] + required_width <= y_vars[upper] + upper_width).OnlyEnforceIf(support)
                        supporters.append(support)
        model.AddBoolOr([present[upper].Not(), on_floor, *supporters])


def _add_cross_section_constraints(
    model,
    present,
    y_var,
    z_var,
    width_var,
    height_var,
    cross_section: list[tuple[float, float]],
) -> None:
    centroid_y = sum(point[0] for point in cross_section) / len(cross_section)
    centroid_z = sum(point[1] for point in cross_section) / len(cross_section)
    for index, start in enumerate(cross_section):
        end = cross_section[(index + 1) % len(cross_section)]
        dy = end[1] - start[1]
        dz = end[0] - start[0]
        coefficient_y = _scale(dy)
        coefficient_z = -_scale(dz)
        bound = coefficient_y * _scale(start[0]) + coefficient_z * _scale(start[1])
        if coefficient_y * _scale(centroid_y) + coefficient_z * _scale(centroid_z) > bound:
            coefficient_y = -coefficient_y
            coefficient_z = -coefficient_z
            bound = -bound
        model.Add(coefficient_y * y_var + coefficient_z * z_var <= bound).OnlyEnforceIf(present)
        model.Add(
            coefficient_y * (y_var + width_var) + coefficient_z * z_var <= bound
        ).OnlyEnforceIf(present)
        model.Add(
            coefficient_y * y_var + coefficient_z * (z_var + height_var) <= bound
        ).OnlyEnforceIf(present)
        model.Add(
            coefficient_y * (y_var + width_var) + coefficient_z * (z_var + height_var) <= bound
        ).OnlyEnforceIf(present)


def _placements_from_solution(model_data, solver, items, orientations) -> list[BoxPlacement]:
    placements: list[BoxPlacement] = []
    for index, (item_id, box) in enumerate(items):
        if not solver.Value(model_data.present[index]):
            continue
        orientation_index = solver.Value(model_data.orientation[index])
        length, width, height = orientations[index][orientation_index]
        placements.append(
            BoxPlacement(
                box_id=box.id,
                instance_id=f"CP-{item_id}",
                x=solver.Value(model_data.x[index]) / CP_SCALE,
                y=solver.Value(model_data.y[index]) / CP_SCALE,
                z=solver.Value(model_data.z[index]) / CP_SCALE,
                length=length,
                width=width,
                height=height,
            )
        )
    return placements


def _forbidden_assignments_for_invalid_placements(model_data, solver) -> list[tuple[int, int, int, int, int, int]]:
    forbidden: list[tuple[int, int, int, int, int, int]] = []
    for index, present_var in enumerate(model_data.present):
        if not solver.Value(present_var):
            continue
        forbidden.append(
            (
                index,
                1,
                solver.Value(model_data.x[index]),
                solver.Value(model_data.y[index]),
                solver.Value(model_data.z[index]),
                solver.Value(model_data.orientation[index]),
            )
        )
    return forbidden


def _state_with_optimized_container(
    problem,
    original_state,
    evacuated,
    container_index,
    placements,
    limits,
    free_spaces_for_placements,
):
    from cargo_loading.profile_packer import ContainerState, _profile_input_for_container

    remaining = evacuated.remaining_counter.copy()
    for placement in placements:
        remaining[placement.box_id] -= 1
    container = evacuated.containers[container_index]
    profile_input = _profile_input_for_container(problem, container)
    next_container = ContainerState(
        spec=container.spec,
        container_id=container.container_id,
        placements=placements,
        free_spaces=free_spaces_for_placements(profile_input, placements, limits),
    )
    next_containers = [*evacuated.containers]
    next_containers[container_index] = next_container
    return type(original_state)(containers=next_containers, remaining_counter=remaining)
