from __future__ import annotations

from cargo_loading.profile_models import Point2D


EPSILON = 1e-9


def polygon_area(points: list[Point2D]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def rectangle_inside_polygon(y: float, z: float, width: float, height: float, polygon: list[Point2D]) -> bool:
    sample_points = [
        (y, z),
        (y + width, z),
        (y + width, z + height),
        (y, z + height),
        (y + width / 2, z),
        (y + width, z + height / 2),
        (y + width / 2, z + height),
        (y, z + height / 2),
        (y + width / 2, z + height / 2),
    ]
    return all(point_in_polygon(point, polygon) for point in sample_points)


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
