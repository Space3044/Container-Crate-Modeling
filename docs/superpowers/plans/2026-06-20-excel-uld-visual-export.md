# Excel ULD Visual Export Implementation Plan

**Goal:** Add one `ULD 可视化` workbook sheet that lists each ULD's loaded dimensions and shows an x-y top-view position map.

**Architecture:** Keep the current browser-only XLSX writer. Extend `buildWorkbookSheets` with one generated sheet and small helper functions in `web/app.js`.

**Tech Stack:** Plain JavaScript, current custom XLSX XML writer, Python unittest with Node VM checks.

---

## Implementation Summary

Implemented a simplified anchor-based top-view grid:

- Grid columns derived from unique `anchorX` (minX of each stack), rows from unique `anchorY` (minY of each stack)
- Each stack occupies exactly one non-merged cell at its anchor position
- Same-anchor stacks (overlapping footprints) write content in the same cell, separated by newlines, z-bottom-to-top
- Column width = max length of stacks in that column; row height = max width of stacks in that row
- No merges needed; eliminates Excel merge-overlap errors
- anchorX ascending (left to right), anchorY descending (y-large at top, first quadrant)

---

## Completed Tasks

### Task 1: Lock Workbook Sheet Shape ✓

**Implemented:**
- Node VM test that calls `buildWorkbookSheets(result, input)`
- Assert that `ULD 可视化` exists
- Assert sheet contains `ULD Q7-001`
- Assert loaded boxes are summarized horizontally as `长*宽*高*数量`
- Assert sheet contains `俯视位置图`
- Assert top-view grid coordinates from stack anchor and size ranges
- Assert each box appears in exactly one top-view position cell
- Assert top-view quantity total equals loading-list quantity total
- Assert outer empty y ranges trimmed, stacked boxes stay in one cell
- Assert front boxes appear near y=0
- **Assert top view uses NO merged cells** (simplified from original complex design)
- Assert sheet does not include instance IDs

Result: ✓ PASS

### Task 2: Generate ULD Loading List Sheet ✓

**Implemented:**
- `buildUldVisualizationSheet(containers)` — generates complete sheet with all ULD sections
- `buildUldVisualizationSection(container)` — renders one ULD's loading list and top-view grid
- `placementSizeSummaries(placements)` — aggregates placements by size
- `buildTopViewRows(placements)` — builds anchor-based grid (no merges, no maximal rectangle decomposition)
- Stack footprints built from vertically related placements via `buildPlacementStacks`
- Grid discretized by unique anchorX/anchorY
- Each stack assigned to single anchor cell (no merge)
- Complete `长*宽*高*数量` summaries written in assigned cell
- Multiple same-anchor stacks write in same cell with newline separator
- Row auto-height and wrapText enabled for multi-line cells
- Sheet appended in `buildWorkbookSheets`

Result: ✓ PASS

### Task 3: Regression Check ✓

- `python -m unittest tests.test_web_visualizer_assets` → 9/9 PASS
- `python -m unittest discover -s tests` → 65/65 PASS

All tests pass. No regressions detected.

---

## Design Changes from Original Plan

| Aspect | Original Plan | Implemented |
|--------|---------------|-------------|
| Cell Merging | Clean stacks: maximal rectangle decomposition; conflict stacks: single merged cell | No merging at all: each stack = one non-merged cell at anchor |
| Multi-stack Handling | Separate cells with merge coverage | Same cell with newline separator in content |
| Grid Granularity | Atomic rectangle decomposition + merging | Anchor discretization (simpler, no Excel errors) |
| Implementation Complexity | `decomposeMaximalRectangles`, conflict detection | Simple anchor lookup + content concatenation |
