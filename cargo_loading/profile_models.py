from __future__ import annotations

from dataclasses import dataclass, field


class PackingInputError(ValueError):
    """Raised when profile packing input data is invalid."""


Point2D = tuple[float, float]


def _positive(value: float, name: str) -> None:
    if value <= 0:
        raise PackingInputError(f"{name} must be positive")


def _non_empty(value: str, name: str) -> None:
    if not value:
        raise PackingInputError(f"{name} must not be empty")


@dataclass(frozen=True)
class ContainerSpec:
    id: str
    length: float
    cross_section: list[Point2D]
    quantity: int = 1

    def __post_init__(self) -> None:
        _non_empty(self.id, "container.id")
        _positive(self.length, "container.length")
        if len(self.cross_section) < 3:
            raise PackingInputError("container.cross_section must have at least 3 points")
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
        if len(self.cross_section) < 3:
            raise PackingInputError("uld.cross_section must have at least 3 points")


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


@dataclass(frozen=True)
class MultiContainerPackingInput:
    containers: list[ContainerSpec]
    boxes: list[BoxSpec]
    objective: str = "maximize_volume"

    def __post_init__(self) -> None:
        if not self.containers:
            raise PackingInputError("containers must not be empty")


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
