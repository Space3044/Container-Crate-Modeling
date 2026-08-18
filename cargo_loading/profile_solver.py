from __future__ import annotations

import json
from pathlib import Path

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
    merge_box_specs,
)
from cargo_loading.profile_packer import pack_packing
from cargo_loading.profile_visualizer import render_cross_section_svg, render_x_slice_svg


def solve_profile_file(input_path: str | Path, output_dir: str | Path) -> ProfilePackingResult | MultiContainerPackingResult:
    problem = load_packing_input(input_path)
    result = pack_packing(problem)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "packing_result.json").write_text(
        json.dumps(packing_result_to_dict(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if isinstance(problem, ProfilePackingInput) and isinstance(result, ProfilePackingResult):
        (output_path / "packing_preview.svg").write_text(
            render_cross_section_svg(problem, result),
            encoding="utf-8",
        )
        (output_path / "packing_x_slices.svg").write_text(
            render_x_slice_svg(problem, result),
            encoding="utf-8",
        )
    return result


def load_profile_input(input_path: str | Path) -> ProfilePackingInput:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return profile_input_from_dict(data)


def load_packing_input(input_path: str | Path) -> ProfilePackingInput | MultiContainerPackingInput:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return packing_input_from_dict(data)


def packing_input_from_dict(data: dict[str, object]) -> ProfilePackingInput | MultiContainerPackingInput:
    if "containers" in data:
        return multi_container_input_from_dict(data)
    return profile_input_from_dict(data)


def profile_input_from_dict(data: dict[str, object]) -> ProfilePackingInput:
    uld_data = data["uld"]
    uld = ULDProfile(
        id=uld_data["id"],
        length=uld_data["length"],
        cross_section=[tuple(point) for point in uld_data["cross_section"]],
    )
    boxes = merge_box_specs([BoxSpec(**box_data) for box_data in data["boxes"]])
    return ProfilePackingInput(
        uld=uld,
        boxes=boxes,
        objective=data.get("objective", "maximize_volume"),
        search_mode=data.get("search_mode", "balanced"),
    )


def multi_container_input_from_dict(data: dict[str, object]) -> MultiContainerPackingInput:
    containers = [
        ContainerSpec(
            id=container_data["id"],
            length=container_data["length"],
            cross_section=[tuple(point) for point in container_data["cross_section"]],
            quantity=container_data.get("quantity", 1),
        )
        for container_data in data["containers"]
    ]
    boxes = merge_box_specs([BoxSpec(**box_data) for box_data in data["boxes"]])
    return MultiContainerPackingInput(
        containers=containers,
        boxes=boxes,
        objective=data.get("objective", "maximize_volume"),
        search_mode=data.get("search_mode", "balanced"),
    )


def packing_result_to_dict(result: ProfilePackingResult | MultiContainerPackingResult) -> dict[str, object]:
    if isinstance(result, MultiContainerPackingResult):
        return multi_container_result_to_dict(result)
    return profile_result_to_dict(result)


def profile_result_to_dict(result: ProfilePackingResult) -> dict[str, object]:
    return {
        "uld_id": result.uld_id,
        "loaded_count": result.loaded_count,
        "unloaded_count": result.unloaded_count,
        "used_volume": result.used_volume,
        "cross_section_area": result.cross_section_area,
        "uld_volume": result.uld_volume,
        "volume_utilization": result.volume_utilization,
        "loaded": [_loaded_to_dict(item) for item in result.loaded],
        "placements": [_placement_to_dict(placement) for placement in result.placements],
        "unloaded": [_unloaded_to_dict(item) for item in result.unloaded],
        "validation_passed": result.validation_passed,
        "validation_errors": result.validation_errors,
    }


def multi_container_result_to_dict(result: MultiContainerPackingResult) -> dict[str, object]:
    return {
        "loaded_count": result.loaded_count,
        "unloaded_count": result.unloaded_count,
        "used_volume": result.used_volume,
        "container_volume": result.container_volume,
        "volume_utilization": result.volume_utilization,
        "loaded": [_loaded_to_dict(item) for item in result.loaded],
        "unloaded": [_unloaded_to_dict(item) for item in result.unloaded],
        "containers": [_container_result_to_dict(container) for container in result.containers],
        "validation_passed": result.validation_passed,
        "validation_errors": result.validation_errors,
    }


def _container_result_to_dict(container: ContainerPackingResult) -> dict[str, object]:
    data = profile_result_to_dict(container.result)
    data["container_id"] = container.container_id
    data["container_type"] = container.container_type
    return data


def _placement_to_dict(placement: BoxPlacement) -> dict[str, object]:
    return {
        "box_id": placement.box_id,
        "instance_id": placement.instance_id,
        "x": placement.x,
        "y": placement.y,
        "z": placement.z,
        "length": placement.length,
        "width": placement.width,
        "height": placement.height,
        "height_swapped": placement.height_swapped,
    }


def _unloaded_to_dict(unloaded: UnloadedBox) -> dict[str, object]:
    return {
        "box_id": unloaded.box_id,
        "quantity": unloaded.quantity,
        "reason": unloaded.reason,
    }


def _loaded_to_dict(loaded: LoadedBox) -> dict[str, object]:
    return {
        "box_id": loaded.box_id,
        "quantity": loaded.quantity,
    }
