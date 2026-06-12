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

    def __post_init__(self) -> None:
        _non_empty(self.id, "box.id")
        _positive(self.length, "box.length")
        _positive(self.width, "box.width")
        _positive(self.height, "box.height")
        if self.quantity < 0:
            raise PackingInputError("box.quantity must be non-negative")

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class ProfilePackingInput:
    uld: ULDProfile
    boxes: list[BoxSpec]
    objective: str = "maximize_volume"
    search_mode: str = SEARCH_MODE_BALANCED

    def __post_init__(self) -> None:
        _valid_search_mode(self.search_mode)


@dataclass(frozen=True)
class MultiContainerPackingInput:
    containers: list[ContainerSpec]
    boxes: list[BoxSpec]
    objective: str = "maximize_volume"
    search_mode: str = SEARCH_MODE_BALANCED

    def __post_init__(self) -> None:
        if not self.containers:
            raise PackingInputError("containers must not be empty")
        _valid_search_mode(self.search_mode)


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
