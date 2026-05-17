from __future__ import annotations

import html

from cargo_loading.profile_models import BoxPlacement, ProfilePackingInput, ProfilePackingResult


def render_cross_section_svg(problem: ProfilePackingInput, result: ProfilePackingResult, scale: float = 3.0, padding: float = 20.0) -> str:
    max_y = max(point[0] for point in problem.uld.cross_section)
    max_z = max(point[1] for point in problem.uld.cross_section)
    width = max_y * scale + padding * 2
    height = max_z * scale + padding * 2
    polygon_points = " ".join(_svg_point(y, z, max_z, scale, padding) for y, z in problem.uld.cross_section)
    rectangles = "\n".join(_placement_rect(placement, max_z, scale, padding) for placement in result.placements)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="#f8fafc"/>
  <polygon points="{polygon_points}" fill="#e0f2fe" stroke="#0369a1" stroke-width="2"/>
  {rectangles}
  <text x="{padding:.0f}" y="{height - 5:.0f}" font-family="Arial" font-size="12" fill="#334155">y-z cross-section preview, x positions are collapsed</text>
</svg>
"""


def render_x_slice_svg(problem: ProfilePackingInput, result: ProfilePackingResult, scale: float = 2.0, padding: float = 20.0, gap: float = 40.0) -> str:
    slice_starts = sorted({placement.x for placement in result.placements})
    max_y = max(point[0] for point in problem.uld.cross_section)
    max_z = max(point[1] for point in problem.uld.cross_section)
    panel_width = max_y * scale + padding * 2
    panel_height = max_z * scale + padding * 2 + 20
    width = panel_width
    height = max(panel_height * len(slice_starts) + gap * max(len(slice_starts) - 1, 0), panel_height)
    panels = []
    for index, slice_x in enumerate(slice_starts):
        offset_y = index * (panel_height + gap)
        panels.append(_slice_panel(problem, result, slice_x, max_z, panel_width, panel_height, scale, padding, offset_y))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="#f8fafc"/>
  {"".join(panels)}
</svg>
"""


def _svg_point(y: float, z: float, max_z: float, scale: float, padding: float) -> str:
    svg_x = padding + y * scale
    svg_y = padding + (max_z - z) * scale
    return f"{svg_x:.2f},{svg_y:.2f}"


def _slice_panel(
    problem: ProfilePackingInput,
    result: ProfilePackingResult,
    slice_x: float,
    max_z: float,
    panel_width: float,
    panel_height: float,
    scale: float,
    padding: float,
    offset_y: float,
) -> str:
    polygon_points = " ".join(_svg_point_with_offset(y, z, max_z, scale, padding, offset_y) for y, z in problem.uld.cross_section)
    placements = [placement for placement in result.placements if placement.x <= slice_x < placement.x + placement.length]
    rectangles = "\n".join(_placement_rect_with_offset(placement, max_z, scale, padding, offset_y) for placement in placements)
    return f"""<g>
    <rect x="0" y="{offset_y:.2f}" width="{panel_width:.2f}" height="{panel_height:.2f}" fill="#ffffff" stroke="#cbd5e1"/>
    <text x="{padding:.2f}" y="{offset_y + 15:.2f}" font-family="Arial" font-size="12" fill="#0f172a">x = {slice_x:g}</text>
    <polygon points="{polygon_points}" fill="#e0f2fe" stroke="#0369a1" stroke-width="2"/>
    {rectangles}
  </g>"""


def _svg_point_with_offset(y: float, z: float, max_z: float, scale: float, padding: float, offset_y: float) -> str:
    svg_x = padding + y * scale
    svg_y = offset_y + padding + 20 + (max_z - z) * scale
    return f"{svg_x:.2f},{svg_y:.2f}"


def _placement_rect(placement: BoxPlacement, max_z: float, scale: float, padding: float) -> str:
    svg_x = padding + placement.y * scale
    svg_y = padding + (max_z - placement.z - placement.height) * scale
    width = placement.width * scale
    height = placement.height * scale
    label = html.escape(placement.instance_id)
    return f"""<g>
    <rect x="{svg_x:.2f}" y="{svg_y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#f97316" fill-opacity="0.35" stroke="#9a3412" stroke-width="1"/>
    <title>{label}</title>
    <text x="{svg_x + 3:.2f}" y="{svg_y + 13:.2f}" font-family="Arial" font-size="10" fill="#7c2d12">{label}</text>
  </g>"""


def _placement_rect_with_offset(placement: BoxPlacement, max_z: float, scale: float, padding: float, offset_y: float) -> str:
    svg_x = padding + placement.y * scale
    svg_y = offset_y + padding + 20 + (max_z - placement.z - placement.height) * scale
    width = placement.width * scale
    height = placement.height * scale
    label = html.escape(placement.instance_id)
    return f"""<g>
      <rect x="{svg_x:.2f}" y="{svg_y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#22c55e" fill-opacity="0.35" stroke="#166534" stroke-width="1"/>
      <title>{label}</title>
      <text x="{svg_x + 3:.2f}" y="{svg_y + 13:.2f}" font-family="Arial" font-size="10" fill="#14532d">{label}</text>
    </g>"""
