from __future__ import annotations

from dataclasses import dataclass, field

from cargo_loading.profile_geometry import is_convex_polygon


class PackingInputError(ValueError):
    """Raised when profile packing input data is invalid."""


Point2D = tuple[float, float]
SEARCH_MODE_FAST = "fast"
SEARCH_MODE_BALANCED = "balanced"
SEARCH_MODE_HIGH_UTILIZATION = "high_utilization"
VALID_SEARCH_MODES = {SEARCH_MODE_FAST, SEARCH_MODE_BALANCED, SEARCH_MODE_HIGH_UTILIZATION}


def _positive(value: float, name: str) -> None:
    if value <= 0:
        raise PackingInputError(f"{name} must be positive")


def _non_empty(value: str, name: str) -> None:
    if not value:
        raise PackingInputError(f"{name} must not be empty")


def _valid_search_mode(value: str) -> None:
    if value not in VALID_SEARCH_MODES:
        raise PackingInputError(f"search_mode must be one of {sorted(VALID_SEARCH_MODES)}")


def _valid_cross_section(points: list[Point2D], name: str) -> None:
    if len(points) < 3:
        raise PackingInputError(f"{name} must have at least 3 points")
    if not is_convex_polygon(points):
        raise PackingInputError(f"{name} must be a convex polygon")


@dataclass(frozen=True)
class ContainerSpec:
    id: str
    length: float
    cross_section: list[Point2D]
    quantity: int = 1

    def __post_init__(self) -> None:
        _non_empty(self.id, "container.id")
        _positive(self.length, "container.length")
        _valid_cross_section(self.cross_section, "container.cross_section")
        if self.quantity < 0:
            raise PackingInputError("container.quantity must be non-negative")


@dataclass(frozen=True)
class ULDProfile:
    id: str
    length: float
    cross_section: list[Point2D]

    def __post_init__(self) -> None:
        _non_empty(self.id, "uld.id")
        _positive(self.length, "uld.length")
        _valid_cross_section(self.cross_section, "uld.cross_section")


@dataclass(frozen=True)
class BoxSpec:
    id: str
    length: float
    width: float
    height: float
    quantity: int
    rotatable: bool = True
    full_rotatable: bool = False
    required_container_types: tuple[str, ...] = field(default_factory=tuple)
    _merge_source_count: int = field(default=1, init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        _non_empty(self.id, "box.id")
        _positive(self.length, "box.length")
        _positive(self.width, "box.width")
        _positive(self.height, "box.height")
        if self.quantity < 0:
            raise PackingInputError("box.quantity must be non-negative")
        if isinstance(self.required_container_types, str):
            raise PackingInputError("box.required_container_types must be a list of container types")
        required_container_types = tuple(self.required_container_types)
        for container_type in required_container_types:
            _non_empty(container_type, "box.required_container_types")
        object.__setattr__(self, "required_container_types", required_container_types)

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


def merge_box_specs(boxes: list[BoxSpec]) -> list[BoxSpec]:
    """按实际装箱属性合并箱型，并保留每组第一行的 ID。

    长宽可互换的箱子，其长宽顺序不影响可选朝向，因此也视为同一箱型。
    长宽高可互换的箱子，三个尺寸的顺序都不影响可选朝向，按三维排序后比较。
    ULD 限制按集合比较，列表顺序和重复项不影响业务含义。合并只改变数量，
    使用第一条记录的其它字段，确保输出仍然使用用户输入的第一行 ID。
    """
    merged: dict[tuple[object, ...], BoxSpec] = {}
    for box in boxes:
        key = _box_merge_key(box)
        first = merged.get(key)
        if first is None:
            merged[key] = box
            continue
        merged_box = BoxSpec(
            id=first.id,
            length=first.length,
            width=first.width,
            height=first.height,
            quantity=first.quantity + box.quantity,
            rotatable=first.rotatable,
            full_rotatable=first.full_rotatable,
            required_container_types=first.required_container_types,
        )
        object.__setattr__(
            merged_box,
            "_merge_source_count",
            first._merge_source_count + box._merge_source_count,
        )
        merged[key] = merged_box
    return list(merged.values())


def _box_merge_key(box: BoxSpec) -> tuple[object, ...]:
    if box.full_rotatable:
        # 全互换已包含长宽互换，rotatable 取值不再影响可选朝向
        dimensions = tuple(sorted((box.length, box.width, box.height)))
        rotatable = True
    elif box.rotatable:
        dimensions = (*sorted((box.length, box.width)), box.height)
        rotatable = True
    else:
        dimensions = (box.length, box.width, box.height)
        rotatable = False
    allowed_container_types = tuple(sorted(set(box.required_container_types)))
    return (*dimensions, rotatable, box.full_rotatable, allowed_container_types)


@dataclass(frozen=True)
class ProfilePackingInput:
    uld: ULDProfile
    boxes: list[BoxSpec]
    objective: str = "maximize_count"
    search_mode: str = SEARCH_MODE_BALANCED

    def __post_init__(self) -> None:
        _valid_search_mode(self.search_mode)


@dataclass(frozen=True)
class MultiContainerPackingInput:
    containers: list[ContainerSpec]
    boxes: list[BoxSpec]
    objective: str = "maximize_count"
    search_mode: str = SEARCH_MODE_BALANCED

    def __post_init__(self) -> None:
        if not self.containers:
            raise PackingInputError("containers must not be empty")
        _valid_search_mode(self.search_mode)
        container_types = {container.id for container in self.containers}
        for box in self.boxes:
            for container_type in box.required_container_types:
                if container_type not in container_types:
                    raise PackingInputError(
                        f"box {box.id} required_container_types contains unknown container type {container_type}"
                    )


@dataclass(frozen=True)
class BoxPlacement:
    box_id: str
    instance_id: str
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    height_swapped: bool = False
    """放置高度与箱型录入高度不同，即该箱子被立起或倒置装入（仅 full_rotatable 箱型可能出现）。"""

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class LoadedBox:
    box_id: str
    quantity: int


@dataclass(frozen=True)
class UnloadedBox:
    box_id: str
    quantity: int
    reason: str


@dataclass(frozen=True)
class ProfilePackingResult:
    uld_id: str
    loaded_count: int
    unloaded_count: int
    used_volume: float
    cross_section_area: float
    uld_volume: float
    volume_utilization: float
    placements: list[BoxPlacement]
    unloaded: list[UnloadedBox]
    validation_passed: bool
    validation_errors: list[str] = field(default_factory=list)
    loaded: list[LoadedBox] = field(default_factory=list)


@dataclass(frozen=True)
class ContainerPackingResult:
    container_id: str
    container_type: str
    result: ProfilePackingResult


@dataclass(frozen=True)
class MultiContainerPackingResult:
    loaded_count: int
    unloaded_count: int
    used_volume: float
    container_volume: float
    volume_utilization: float
    containers: list[ContainerPackingResult]
    loaded: list[LoadedBox]
    unloaded: list[UnloadedBox]
    validation_passed: bool
    validation_errors: list[str] = field(default_factory=list)
