from __future__ import annotations

from functools import lru_cache

Point2D = tuple[float, float]
PolygonKey = tuple[Point2D, ...]

EPSILON = 1e-9


def polygon_area(points: list[Point2D]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def is_convex_polygon(points: list[Point2D]) -> bool:
    if len(points) < 3 or polygon_area(points) <= EPSILON:
        return False
    sign = 0
    count = len(points)
    for index in range(count):
        y1, z1 = points[index]
        y2, z2 = points[(index + 1) % count]
        y3, z3 = points[(index + 2) % count]
        cross = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2)
        if abs(cross) <= EPSILON:
            continue
        current = 1 if cross > 0 else -1
        if sign == 0:
            sign = current
        elif current != sign:
            return False
    return True


def rectangle_inside_polygon(y: float, z: float, width: float, height: float, polygon: list[Point2D]) -> bool:
    # 凸多边形前提下，4 个角点在内即整个矩形在内
    return _rectangle_inside_polygon_cached(y, z, width, height, _polygon_key(polygon))


@lru_cache(maxsize=131_072)
def _rectangle_inside_polygon_cached(
    y: float,
    z: float,
    width: float,
    height: float,
    polygon: PolygonKey,
) -> bool:
    corners = [
        (y, z),
        (y + width, z),
        (y + width, z + height),
        (y, z + height),
    ]
    return all(point_in_polygon(corner, polygon) for corner in corners)


def convex_y_interval(polygon: list[Point2D], z_low: float, z_high: float) -> tuple[float, float] | None:
    """凸多边形在高度区间 [z_low, z_high] 内全程可用的 y 区间。"""
    return _convex_y_interval_cached(_polygon_key(polygon), z_low, z_high)


def _polygon_key(polygon: list[Point2D]) -> PolygonKey:
    return tuple((y, z) for y, z in polygon)


@lru_cache(maxsize=131_072)
def _convex_y_interval_cached(polygon: PolygonKey, z_low: float, z_high: float) -> tuple[float, float] | None:
    low_interval = _y_interval_at_z(polygon, z_low)
    high_interval = _y_interval_at_z(polygon, z_high)
    if low_interval is None or high_interval is None:
        return None
    left = max(low_interval[0], high_interval[0])
    right = min(low_interval[1], high_interval[1])
    if right - left <= EPSILON:
        return None
    return (left, right)


@lru_cache(maxsize=131_072)
def _y_interval_at_z(polygon: PolygonKey, z: float) -> tuple[float, float] | None:
    crossings: list[float] = []
    count = len(polygon)
    for index in range(count):
        y1, z1 = polygon[index]
        y2, z2 = polygon[(index + 1) % count]
        if abs(z1 - z) <= EPSILON and abs(z2 - z) <= EPSILON:
            crossings.extend((y1, y2))
            continue
        if min(z1, z2) - EPSILON <= z <= max(z1, z2) + EPSILON and abs(z2 - z1) > EPSILON:
            ratio = (z - z1) / (z2 - z1)
            crossings.append(y1 + ratio * (y2 - y1))
    if not crossings:
        return None
    return (min(crossings), max(crossings))


def point_in_polygon(point: Point2D, polygon: list[Point2D]) -> bool:
    y, z = point
    inside = False
    for index, (y1, z1) in enumerate(polygon):
        y2, z2 = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, (y1, z1), (y2, z2)):
            return True
        crosses = (z1 > z) != (z2 > z)
        if crosses:
            intersection_y = (y2 - y1) * (z - z1) / (z2 - z1) + y1
            if y < intersection_y:
                inside = not inside
    return inside


def _point_on_segment(point: Point2D, start: Point2D, end: Point2D) -> bool:
    y, z = point
    y1, z1 = start
    y2, z2 = end
    cross = (y - y1) * (z2 - z1) - (z - z1) * (y2 - y1)
    if abs(cross) > EPSILON:
        return False
    return min(y1, y2) - EPSILON <= y <= max(y1, y2) + EPSILON and min(z1, z2) - EPSILON <= z <= max(z1, z2) + EPSILON
