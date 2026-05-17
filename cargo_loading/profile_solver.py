from __future__ import annotations

import json
from pathlib import Path

from cargo_loading.profile_models import BoxPlacement, BoxSpec, LoadedBox, ProfilePackingInput, ProfilePackingResult, ULDProfile, UnloadedBox
from cargo_loading.profile_packer import pack_profile
from cargo_loading.profile_visualizer import render_cross_section_svg, render_x_slice_svg


def solve_profile_file(input_path: str | Path, output_dir: str | Path) -> ProfilePackingResult:
    problem = load_profile_input(input_path)
    result = pack_profile(problem)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "packing_result.json").write_text(
        json.dumps(profile_result_to_dict(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
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


def profile_input_from_dict(data: dict[str, object]) -> ProfilePackingInput:
    uld_data = data["uld"]
    uld = ULDProfile(
        id=uld_data["id"],
        length=uld_data["length"],
        cross_section=[tuple(point) for point in uld_data["cross_section"]],
    )
    boxes = [BoxSpec(**box_data) for box_data in data["boxes"]]
    return ProfilePackingInput(
        uld=uld,
        boxes=boxes,
        objective=data.get("objective", "maximize_volume"),
    )


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
