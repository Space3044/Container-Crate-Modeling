from __future__ import annotations

from collections import Counter
from itertools import permutations

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


def pack_packing(problem: ProfilePackingInput | MultiContainerPackingInput) -> ProfilePackingResult | MultiContainerPackingResult:
    if isinstance(problem, MultiContainerPackingInput):
        return pack_multi_profile(problem)
    return pack_profile(problem)


def pack_profile(problem: ProfilePackingInput) -> ProfilePackingResult:
    expanded_boxes = _expand_boxes(problem.boxes)
    placements: list[BoxPlacement] = []
    candidate_points: list[Point3D] = [(0, 0, 0)]
    unloaded_counter: Counter[str] = Counter()

    for box, instance_id in expanded_boxes:
        placement = _find_placement(box, instance_id, problem, placements, candidate_points)
        if placement is None:
            unloaded_counter[box.id] += 1
            continue
        placements.append(placement)
        candidate_points.extend(_new_candidate_points(placement))
        candidate_points = _prune_candidate_points(candidate_points, problem)

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


def pack_multi_profile(problem: MultiContainerPackingInput) -> MultiContainerPackingResult:
    remaining = {box.id: box.quantity for box in problem.boxes}
    box_by_id = {box.id: box for box in problem.boxes}
    container_results: list[ContainerPackingResult] = []

    for container, container_id in _expand_containers(problem.containers):
        remaining_boxes = [
            BoxSpec(
                id=box.id,
                length=box.length,
                width=box.width,
                height=box.height,
                quantity=remaining[box.id],
                rotatable=box.rotatable,
            )
            for box in problem.boxes
            if remaining[box.id] > 0
        ]
        single_result = pack_profile(
            ProfilePackingInput(
                uld=ULDProfile(id=container_id, length=container.length, cross_section=container.cross_section),
                boxes=remaining_boxes,
                objective=problem.objective,
            )
        )
        for loaded in single_result.loaded:
            remaining[loaded.box_id] -= loaded.quantity
        container_results.append(
            ContainerPackingResult(
                container_id=container_id,
                container_type=container.id,
                result=single_result,
            )
        )

    unloaded = [
        UnloadedBox(box_id=box_id, quantity=quantity, reason="no feasible space across containers")
        for box_id, quantity in sorted(remaining.items())
        if quantity > 0
    ]
    loaded = [
        LoadedBox(box_id=box_id, quantity=box_by_id[box_id].quantity - quantity)
        for box_id, quantity in sorted(remaining.items())
        if box_by_id[box_id].quantity - quantity > 0
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


def _expand_boxes(boxes: list[BoxSpec]) -> list[tuple[BoxSpec, str]]:
    expanded: list[tuple[BoxSpec, str]] = []
    for box in sorted(boxes, key=lambda item: (-item.volume, item.id)):
        for index in range(1, box.quantity + 1):
            expanded.append((box, f"{box.id}-{index:03d}"))
    return expanded


def _find_placement(
    box: BoxSpec,
    instance_id: str,
    problem: ProfilePackingInput,
    placements: list[BoxPlacement],
    candidate_points: list[Point3D],
) -> BoxPlacement | None:
    for x, y, z in sorted(set(candidate_points), key=lambda point: (point[2], point[1], point[0])):
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
                return placement
    return None


def _orientation_options(box: BoxSpec) -> list[tuple[float, float, float]]:
    if not box.rotatable:
        return [(box.length, box.width, box.height)]
    return sorted(set(permutations((box.length, box.width, box.height), 3)))


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


def _prune_candidate_points(candidate_points: list[Point3D], problem: ProfilePackingInput) -> list[Point3D]:
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
    return sorted(points, key=lambda item: (item[2], item[1], item[0]))
