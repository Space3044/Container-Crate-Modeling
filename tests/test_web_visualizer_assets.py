import unittest
import json
import os
import subprocess
from pathlib import Path


class WebVisualizerAssetsTests(unittest.TestCase):
    def test_visualizer_page_has_projection_views_slice_control_and_selection_details(self):
        html = Path("web/index.html").read_text(encoding="utf-8")

        for expected_id in [
            "containerTableBody",
            "addContainerButton",
            "containerSelector",
            "sceneTooltip",
            "topViewCanvas",
            "sideViewCanvas",
            "sectionViewCanvas",
            "sliceSlider",
            "sliceValue",
            "loadedList",
            "historyList",
            "exportExcelButton",
            "exportHtmlButton",
            "clearBoxesButton",
            "bulkBoxInput",
            "importBoxesButton",
            "searchModeSelect",
            "activeContainerStats",
            "selectedBoxDetails",
            "isometricViewButton",
            "topViewButton",
            "sideViewButton",
            "sectionViewButton",
            "animationPlayButton",
            "animationResetButton",
            "animationSpeedSlider",
            "animationSpeedValue",
            "themeToggleButton",
        ]:
            self.assertIn(f'id="{expected_id}"', html)
        self.assertNotIn("只改变截面查看，不改变装箱结果", html)
        self.assertNotIn("x 从 ULD 前端沿长度方向量起", html)
        self.assertNotIn('class="slice-note"', html)
        self.assertIn("添加 ULD", html)
        self.assertIn("批量粘贴箱子", html)
        self.assertIn("识别并添加箱子", html)
        self.assertIn("清空箱子", html)
        self.assertIn("算法模式", html)
        self.assertIn('value="fast"', html)
        self.assertIn('value="balanced"', html)
        self.assertIn('value="high_utilization"', html)
        self.assertIn("140*105*94*20", html)
        self.assertIn('<h1>Multi ULD Profile Packing</h1>', html)
        self.assertIn('class="header-actions"', html)
        self.assertIn('class="panel-title"', html)
        self.assertIn('class="panel-kicker"', html)
        self.assertIn('class="section-card"', html)
        self.assertIn('class="result-section"', html)
        self.assertIn('class="viewer-copy"', html)
        self.assertIn('class="viewer-body"', html)
        self.assertLess(html.index('class="slice-control"'), html.index('class="viewer-body"'))
        self.assertNotIn('class="input-toolbar"', html)
        self.assertNotIn('class="input-actions"', html)
        self.assertNotIn("<h1>ULD 装箱可视化</h1>", html)
        self.assertIn("当前 ULD", html)
        self.assertIn('class="result-section detail-current"', html)
        self.assertIn('class="result-section detail-loaded"', html)
        self.assertIn('class="result-section detail-unloaded"', html)
        self.assertIn('class="result-section detail-selected"', html)
        self.assertIn('class="result-section detail-placements"', html)
        self.assertIn("最近10次计算记录", html)
        self.assertIn("装箱动画", html)
        self.assertIn("播放动画", html)
        self.assertIn("倍速", html)
        self.assertIn("选择要查看的 ULD 实例", html)
        self.assertIn("单个 ULD 装载率", html)
        self.assertIn("导出 XLSX", html)
        self.assertIn("导出 HTML", html)
        self.assertIn('class="export-actions"', html)
        self.assertIn("悬停箱子信息", html)
        self.assertIn("<th>ID</th>", html)
        self.assertIn("<th>长宽互换</th>", html)
        self.assertNotIn("<th>类型</th>", html)
        self.assertNotIn("<th>旋转</th>", html)
        self.assertNotIn("容器", html)

    def test_visualizer_page_has_light_default_theme_bootstrap_and_toggle(self):
        html = Path("web/index.html").read_text(encoding="utf-8")

        self.assertNotIn('<html lang="zh-CN" data-theme="dark">', html)
        self.assertIn('localStorage.getItem("uld-packing-theme") === "dark"', html)
        self.assertIn('document.documentElement.dataset.theme = "dark"', html)
        self.assertLess(html.index("uld-packing-theme"), html.index('<link rel="stylesheet" href="/styles.css" />'))
        self.assertIn('id="themeToggleButton"', html)
        self.assertIn('class="secondary-button theme-toggle-button"', html)
        self.assertIn('aria-label="切换深色主题"', html)
        self.assertIn(">深色模式</button>", html)

    def test_visualizer_script_contains_projection_and_selection_behaviors(self):
        script = Path("web/app.js").read_text(encoding="utf-8")

        for expected_function in [
            "drawProjectionViews",
            "drawTopView",
            "drawSideView",
            "drawSectionView",
            "selectPlacement",
            "drawAxes",
            "setCameraView",
            "focusProjectionCameraView",
            "togglePackingAnimation",
            "resetPackingAnimation",
            "setAnimationSpeed",
            "startPackingAnimation",
            "stopPackingAnimation",
            "animationFrame",
            "visibleScenePlacements",
            "updateAnimationControls",
            "renderLoadedList",
            "readJsonResponse",
            "addContainerRow",
            "readContainersFromForm",
            "renderContainerSelector",
            "selectContainer",
            "normalizeInput",
            "expandContainerSpecs",
            "getActiveResult",
            "getActiveProfileInput",
            "renderActiveContainerDetails",
            "renderActiveContainerStats",
            "renderUnloadedList",
            "loadPersistedHistoryRecords",
            "loadHistoryRecords",
            "savePersistedHistoryRecords",
            "saveHistoryRecords",
            "addHistoryRecord",
            "renderHistoryRecords",
            "selectHistoryRecord",
            "historyRecordLabel",
            "importBulkBoxes",
            "clearBoxRows",
            "parseBulkBoxLines",
            "parseBulkBoxLine",
            "exportExcel",
            "exportHtmlReport",
            "buildExcelWorkbook",
            "buildHtmlReport",
            "buildHtmlFileName",
            "buildExcelFileName",
            "currentExportCreatedAt",
            "formatExportTimestamp",
            "formatExportUtilization",
            "buildWorkbookSheets",
            "buildXlsxWorkbook",
            "buildExcelStyleModel",
            "uldStyleKey",
            "boxStyleKey",
            "downloadExcelWorkbook",
            "downloadHtmlReport",
            "buildHtmlProjectionSvg",
            "buildHtmlReportContainerSection",
            "createZipArchive",
            "crc32",
            "updateHoveredScenePlacement",
            "clearHoveredScenePlacement",
            "renderSceneTooltip",
            "hideSceneTooltip",
            "sceneMatchAtPoint",
            "boxFaceStyle",
            "drawFloorGrid",
            "drawBoxWireframes",
            "drawBoxWireframe",
            "getSceneViewport",
            "sceneViewportBounds",
            "sceneEnvelopePoints",
            "projectScenePoint",
            "currentAnimatedInstanceId",
            "setSceneBoxFocus",
            "clearSceneBoxFocus",
            "initializeTheme",
            "currentTheme",
            "toggleTheme",
            "applyTheme",
            "updateThemeToggle",
        ]:
            self.assertIn(f"function {expected_function}", script)
        self.assertIn("containers:", script)
        self.assertIn("containerSelector.addEventListener", script)
        self.assertIn('topViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "top"))', script)
        self.assertIn('sideViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "side"))', script)
        self.assertIn('sectionViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "section"))', script)
        self.assertIn("animationPlayButton.addEventListener", script)
        self.assertIn("animationResetButton.addEventListener", script)
        self.assertIn("animationSpeedSlider.addEventListener", script)
        self.assertIn("requestAnimationFrame(animationFrame)", script)
        self.assertIn("cancelAnimationFrame", script)
        self.assertIn("visibleScenePlacements(activeResult)", script)
        self.assertNotIn("uldIdInput", script)
        self.assertNotIn("uldLengthInput", script)
        self.assertNotIn("crossSectionInput", script)
        self.assertNotIn("容器", script)
        self.assertIn("ULD ID", script)
        self.assertIn("缺少 ID", script)
        self.assertNotIn("ULD 类型", script)
        self.assertNotIn("缺少类型", script)
        self.assertIn("AXIS_EXTENSION_FACTOR", script)
        self.assertIn("dimensions.length * AXIS_EXTENSION_FACTOR", script)
        self.assertIn("允许长宽互换", script)
        self.assertIn("activeContainerStats", script)
        self.assertIn("formatPercent(activeResult.volume_utilization)", script)
        self.assertIn("单个 ULD 装载率", script)
        self.assertIn("hoveredInstanceId", script)
        self.assertIn("sceneTooltip", script)
        self.assertIn("boxFaceStyle(color, selected, hovered, alpha)", script)
        self.assertIn("drawFloorGrid(context, projector, dimensions)", script)
        self.assertIn("drawBoxWireframes(context, visiblePlacements, projector, latestAnimatedId)", script)
        self.assertIn("SCENE_SAFE_PADDING", script)
        self.assertIn("const viewport = getSceneViewport(rect, dimensions)", script)
        self.assertIn("projectPoint(point, dimensions, viewport, rect)", script)
        self.assertIn("dimensions.length * AXIS_EXTENSION_FACTOR", script)
        self.assertIn("currentAnimatedInstanceId(visiblePlacements)", script)
        self.assertIn("const BOX_COLOR_PALETTE", script)
        self.assertIn("function colorForBox(id)", script)
        self.assertIn("function lightenColor(color, ratio)", script)
        self.assertIn("function rgbaColor(color, alpha)", script)
        self.assertIn("focusedBoxId", script)
        self.assertIn("importBoxesButton.addEventListener", script)
        self.assertIn('elements.clearBoxesButton = document.getElementById("clearBoxesButton")', script)
        self.assertIn('elements.clearBoxesButton.addEventListener("click", () => clearBoxRows())', script)
        self.assertIn("bulkBoxInput", script)
        self.assertIn("140*105*94*20", script)
        self.assertIn("40.5*40.5*14*1", script)
        self.assertIn(r".split(/\r\n|\n|\r/)", script)
        self.assertIn(r"line.split(/[\s*＊×xXｘＸ✕✖⨯]+/)", script)
        self.assertIn("quantity: readNonNegativeInteger(quantity", script)
        self.assertIn("exportExcelButton.addEventListener", script)
        self.assertIn("exportHtmlButton.addEventListener", script)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", script)
        self.assertIn("text/html;charset=utf-8", script)
        self.assertIn("downloadExcelWorkbook(buildExcelWorkbook(state.result, state.input), buildExcelFileName(state.result, currentExportCreatedAt()))", script)
        self.assertIn("downloadHtmlReport(buildHtmlReport(state.result, state.input, currentExportCreatedAt()), buildHtmlFileName(state.result, currentExportCreatedAt()))", script)
        self.assertIn("装载率", script)
        self.assertIn("selectedHistoryId", script)
        self.assertIn(".xlsx", script)
        self.assertIn("xl/styles.xml", script)
        self.assertIn("const EXCEL_COLOR_PALETTE", script)
        self.assertIn("styleKey: uldStyleKey", script)
        self.assertIn("styleKey: boxStyleKey", script)
        self.assertIn("buildStylesXml(styleModel)", script)
        self.assertIn("buildWorksheetXml(sheet, styleModel)", script)
        self.assertIn("excelColorForKey", script)
        self.assertIn("<fonts count=", script)
        self.assertIn("<fills count=", script)
        self.assertIn("freezePane", script)
        self.assertIn("<autoFilter", script)
        self.assertIn("装箱坐标", script)
        self.assertIn("MAX_HISTORY_RECORDS = 10", script)
        self.assertIn("HISTORY_STORAGE_KEY", script)
        self.assertIn('THEME_STORAGE_KEY = "uld-packing-theme"', script)
        self.assertIn('elements.themeToggleButton = document.getElementById("themeToggleButton")', script)
        self.assertIn('elements.themeToggleButton.addEventListener("click", toggleTheme)', script)
        self.assertIn('localStorage.setItem(THEME_STORAGE_KEY, "dark")', script)
        self.assertIn("localStorage.removeItem(THEME_STORAGE_KEY)", script)
        self.assertIn('document.documentElement.dataset.theme = "dark"', script)
        self.assertIn("delete document.documentElement.dataset.theme", script)
        self.assertIn('elements.themeToggleButton.setAttribute("aria-pressed", String(dark))', script)
        self.assertIn('drawAllViews()', script)
        self.assertIn('elements.searchModeSelect = document.getElementById("searchModeSelect")', script)
        self.assertIn("search_mode: elements.searchModeSelect.value", script)
        self.assertIn("search_mode: input.search_mode ?? \"balanced\"", script)
        self.assertIn("function searchModeLabel", script)
        self.assertIn("record.input?.search_mode ?? \"balanced\"", script)
        self.assertIn('class="history-mode"', script)
        self.assertIn('fetch("/api/history")', script)
        self.assertIn('fetch("/api/history", {', script)
        self.assertIn("await loadPersistedHistoryRecords()", script)
        self.assertIn("await addHistoryRecord(input, data.result)", script)
        self.assertIn("async function addHistoryRecord", script)
        self.assertIn("localStorage", script)
        self.assertIn("state.historyRecords", script)
        self.assertIn('selectPlacement(row.dataset.instanceId, { syncSlice: true, focusSameBoxType: true })', script)
        self.assertIn("state.focusedBoxId ? placements.filter((placement) => placement.box_id === state.focusedBoxId) : placements", script)
        self.assertIn("3D 聚焦同类箱子", script)
        self.assertNotIn("colorForBox(placement.box_id, index)", script)
        self.assertIn("rgba(15, 23, 42, 0.72)", script)
        self.assertIn("rgba(255, 255, 255, 0.88)", script)
        self.assertIn("if (isSelected) {", script)
        self.assertNotIn("rect.width > 52", script)
        self.assertNotIn("允许旋转", script)

    def test_visualizer_script_keeps_default_loading_when_bulk_import_controls_are_absent(self):
        script = Path("web/app.js").read_text(encoding="utf-8")

        self.assertIn("if (elements.importBoxesButton) {", script)
        self.assertIn('elements.importBoxesButton.addEventListener("click", importBulkBoxes)', script)
        self.assertIn("if (!elements.bulkBoxInput) {", script)
        self.assertIn("批量粘贴入口不可用", script)

    def test_export_file_names_are_stable_across_runner_timezones(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const result = { volume_utilization: 0.037 };
const excelName = context.buildExcelFileName(result, "2026-06-23T01:02:03.000Z");
const htmlName = context.buildHtmlFileName(result, "2026-06-23T01:02:03.000Z");
if (excelName !== "20260623-090203-装载率3.70%.xlsx") {
  throw new Error(`unexpected excel file name: ${excelName}`);
}
if (htmlName !== "20260623-090203-装载率3.70%.html") {
  throw new Error(`unexpected html file name: ${htmlName}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            env={**os.environ, "TZ": "UTC"},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_bulk_box_import_accepts_mac_newlines_and_full_width_separators(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);
const boxes = context.parseBulkBoxLines("140＊105＊94＊20\r107✕107✖117⨯10\r\n443*95*109*1");
const expected = [
  { length: 140, width: 105, height: 94, quantity: 20, rotatable: true },
  { length: 107, width: 107, height: 117, quantity: 10, rotatable: true },
  { length: 443, width: 95, height: 109, quantity: 1, rotatable: true },
];
if (JSON.stringify(boxes) !== JSON.stringify(expected)) {
  throw new Error(`unexpected boxes: ${JSON.stringify(boxes)}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_clear_box_rows_removes_all_box_inputs(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const tableBody = { innerHTML: "<tr><td>BOX-A</td></tr><tr><td>BOX-B</td></tr>" };
context.clearBoxRows(tableBody);
if (tableBody.innerHTML !== "") {
  throw new Error(`box rows were not cleared: ${tableBody.innerHTML}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_visualizer_styles_scene_tooltip_and_clearer_box_edges(self):
        css = Path("web/styles.css").read_text(encoding="utf-8")

        self.assertIn(".scene-stage", css)
        self.assertIn(".scene-tooltip", css)
        self.assertIn(".panel-title", css)
        self.assertIn(".section-card", css)
        self.assertIn(".result-section", css)
        self.assertIn(".export-actions {\n  display: grid;\n  grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn(".export-actions .small-button {\n  width: 100%;", css)
        self.assertIn(".history-list", css)
        self.assertIn(".history-record", css)
        self.assertIn(".bulk-box-import", css)
        self.assertIn(".bulk-box-import textarea", css)
        self.assertIn("--result-panel-height: calc(var(--history-list-height) + 360px)", css)
        self.assertIn("--input-panel-height: var(--result-panel-height)", css)
        self.assertIn("--history-list-height: 592px", css)
        self.assertIn("--details-summary-row-height: 212px", css)
        self.assertIn("--scene-min-height: clamp(560px, 58vh, 760px)", css)
        self.assertIn("minmax(520px, 1.3fr) minmax(480px, 1.15fr) minmax(320px, 0.85fr)", css)
        self.assertIn("minmax(620px, 1.15fr) minmax(580px, 1.4fr) minmax(380px, 0.8fr)", css)
        self.assertIn('"uld boxes overview"\n    "details details details"\n    "viewer viewer viewer"', css)
        self.assertIn('grid-template-columns: minmax(240px, 1fr) minmax(180px, 0.78fr) minmax(220px, 0.92fr)', css)
        self.assertIn("grid-template-rows: auto var(--details-summary-row-height) minmax(0, 1fr)", css)
        self.assertIn("height: var(--input-panel-height)", css)
        self.assertIn(".result-details > .panel-title {\n  grid-column: 1 / -1;", css)
        self.assertIn(".detail-current {\n  grid-column: 1;", css)
        self.assertIn(".detail-current {\n  grid-column: 1;\n  grid-row: 2;", css)
        self.assertIn(".detail-loaded {\n  grid-column: 1;", css)
        self.assertIn(".detail-loaded {\n  grid-column: 1;\n  grid-row: 3;", css)
        self.assertIn(".detail-placements {\n  grid-column: 2 / -1;\n  grid-row: 3;", css)
        self.assertIn(".result-details .result-list,\n.result-details .selected-box-card,\n.result-details .placements-scroll", css)
        self.assertIn(".container-selector-label {\n  grid-template-columns: auto minmax(0, 1fr);", css)
        self.assertIn(".container-selector-label select {\n  height: 36px;", css)
        self.assertIn(".active-container-stats {\n  display: grid;\n  gap: 0;\n  margin-top: 0;", css)
        self.assertIn("grid-template-rows: auto minmax(var(--scene-min-height), 1fr)", css)
        self.assertIn(".viewer-body", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) minmax(280px, 340px)", css)
        self.assertIn(".projection-grid {\n  display: grid;\n  grid-template-columns: 1fr;", css)
        self.assertIn("grid-template-rows: repeat(3, minmax(0, 1fr))", css)
        self.assertIn(".projection-card {\n  display: grid;\n  grid-template-rows: auto minmax(0, 1fr)", css)
        self.assertIn(".projection-card canvas {\n  height: 100%;", css)
        self.assertIn("@media (min-width: 2200px)", css)
        self.assertIn("@media (max-width: 1599px)", css)
        self.assertIn('\"uld boxes\"', css)
        self.assertIn('\"overview overview\"', css)
        self.assertIn('\"details details\"', css)
        self.assertIn('\"viewer viewer\"', css)
        self.assertIn("@media (max-width: 1100px)", css)
        self.assertIn("@media (max-width: 900px)", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("height: var(--result-panel-height)", css)
        self.assertIn("height: var(--history-list-height)", css)
        self.assertIn("max-height: var(--history-list-height)", css)
        self.assertIn("height: var(--history-record-height)", css)
        self.assertIn(".history-record .history-mode", css)
        self.assertIn("top: 12px", css)
        self.assertIn("right: 18px", css)
        self.assertIn(".uld-panel .table-scroll,\n.boxes-panel .table-scroll {\n  overflow-x: hidden;", css)
        self.assertIn(".box-table th:nth-child(n+5),\n.box-table td:nth-child(n+5)", css)
        self.assertIn(".box-table td:nth-child(5) input", css)
        self.assertIn("max-width: 76px", css)
        self.assertIn(".box-table .icon-button", css)
        self.assertNotIn("--input-panel-height: clamp(", css)
        self.assertNotIn(".result-overview {\n    height: auto;", css)
        self.assertNotIn(".result-overview,\n  .result-details {\n    height: auto;", css)
        self.assertNotIn("max-height: calc(100vh - 112px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertNotIn(".result-details {\n  display: grid;\n  gap: 14px;\n  align-content: start;\n  position: sticky", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("border: 1px solid var(--tooltip-border)", css)
        self.assertIn("box-shadow: var(--scene-canvas-shadow)", css)
        self.assertIn("background: var(--scene-canvas-bg)", css)

    def test_visualizer_styles_define_light_tokens_and_dark_overrides(self):
        css = Path("web/styles.css").read_text(encoding="utf-8")

        self.assertIn(":root {\n  color-scheme: light;", css)
        self.assertIn("--bg: #f5f8fc;", css)
        self.assertIn("--panel: rgba(255, 255, 255, 0.9);", css)
        self.assertIn("--text: #1e293b;", css)
        self.assertIn("--muted: #64748b;", css)
        self.assertIn("--header-bg:", css)
        self.assertIn("--panel-title-bg:", css)
        self.assertIn("--scene-canvas-bg:", css)
        self.assertIn("--tooltip-border:", css)
        self.assertIn('html[data-theme="dark"] {\n  color-scheme: dark;', css)
        self.assertIn("--bg: #070d1c;", css)
        self.assertIn("--panel: rgba(15, 23, 42, 0.78);", css)
        self.assertIn("--text: #e6edfb;", css)
        self.assertIn("--muted: #94a3b8;", css)
        self.assertIn(".theme-toggle-button", css)

    def test_visualizer_defaults_to_field_uld_rows_with_zero_quantities_and_no_sample_box(self):
        script = Path("web/app.js").read_text(encoding="utf-8")
        sample = json.loads(Path("data/profile_packing_input.json").read_text(encoding="utf-8"))
        expected_containers = [
            ("Q7", 306, [[0, 0], [240, 0], [240, 240], [120, 290], [0, 290]]),
            ("Q6", 306, [[0, 0], [240, 0], [240, 240], [0, 240]]),
            ("L", 346, [[0, 0], [240, 0], [240, 160], [0, 160]]),
            ("PGA", 600, [[0, 0], [240, 0], [240, 190], [120, 290], [0, 290]]),
            ("Q5", 306, [[0, 0], [240, 0], [240, 190], [120, 290], [0, 290]]),
            ("Q4", 306, [[0, 0], [240, 0], [240, 130], [120, 290], [0, 290]]),
        ]

        for container_id, length, _ in expected_containers:
            self.assertIn(f'id: "{container_id}"', script)
            self.assertIn(f"length: {length}", script)
        self.assertNotIn('id: "BOX-A"', script)
        self.assertNotIn('id: "BOX-B"', script)
        self.assertIn("function nextAlphabeticId", script)
        self.assertIn("function alphabeticLabel", script)
        self.assertIn('nextAlphabeticId("ULD", ".container-id")', script)
        self.assertIn('nextAlphabeticId("BOX", ".box-id")', script)
        self.assertEqual(
            [(container["id"], container["length"], container["cross_section"]) for container in sample["containers"]],
            expected_containers,
        )
        self.assertTrue(all(container["quantity"] == 0 for container in sample["containers"]))
        self.assertIn('class="container-quantity" type="number" min="0"', script)
        self.assertIn('value="${container.quantity ?? 0}"', script)
        self.assertIn("readNonNegativeInteger(row.querySelector(\".container-quantity\").value", script)
        self.assertEqual(sample["boxes"], [])

    def test_visualizer_normalizes_initial_uld_quantities_to_zero(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const fallback = context.normalizeInput({});
const multi = context.normalizeInput({
  containers: [{ id: "ULD-X", length: 100, cross_section: [[0, 0], [10, 0], [10, 10]] }],
  boxes: [],
});
const legacy = context.normalizeInput({
  uld: { id: "ULD-L", length: 100, cross_section: [[0, 0], [10, 0], [10, 10]] },
  boxes: [],
});

const quantities = [
  ...fallback.containers.map((container) => container.quantity),
  multi.containers[0].quantity,
  legacy.containers[0].quantity,
];
if (!quantities.every((quantity) => quantity === 0)) {
  throw new Error(`unexpected default quantities: ${JSON.stringify(quantities)}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_active_container_stats_keeps_default_metric_placeholders(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const html = context.activeContainerStatsMarkup(null);
for (const expected of [
  "<span>单个 ULD 装载率</span><strong>--</strong>",
  "<span>已装箱</span><strong>--</strong>",
  "<span>已用体积</span><strong>-- / --</strong>",
]) {
  if (!html.includes(expected)) {
    throw new Error(`missing placeholder row ${expected}: ${html}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_loaded_list_markup_includes_box_dimensions(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const html = context.loadedListMarkup(
  {
    loaded: [
      { box_id: "BOX-A", quantity: 2 },
      { box_id: "BOX-B", quantity: 1, length: 90, width: 50, height: 40 },
    ],
  },
  {
    boxes: [
      { id: "BOX-A", length: 60, width: 40, height: 30 },
      { id: "BOX-B", length: 80, width: 45, height: 35 },
    ],
  },
);

for (const expected of [
  "BOX-A (60 × 40 × 30) × 2",
  "BOX-B (90 × 50 × 40) × 1",
]) {
  if (!html.includes(expected)) {
    throw new Error(`missing loaded dimension row ${expected}: ${html}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_unloaded_list_markup_includes_box_dimensions(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const html = context.unloadedListMarkup(
  {
    unloaded: [
      { box_id: "BOX-A", quantity: 3, reason: "超出空间" },
      { box_id: "BOX-B", quantity: 1, reason: "未匹配", length: 90, width: 50, height: 40 },
    ],
  },
  {
    boxes: [
      { id: "BOX-A", length: 60, width: 40, height: 30 },
      { id: "BOX-B", length: 80, width: 45, height: 35 },
    ],
  },
);

for (const expected of [
  "BOX-A (60 × 40 × 30) × 3：超出空间",
  "BOX-B (90 × 50 × 40) × 1：未匹配",
]) {
  if (!html.includes(expected)) {
    throw new Error(`missing unloaded dimension row ${expected}: ${html}`);
  }
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_active_container_details_renders_loaded_types_for_selected_uld(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

vm.runInContext(`
const classList = { add: () => {}, remove: () => {} };
state.input = {
  boxes: [
    { id: "BOX-A", length: 60, width: 40, height: 30 },
    { id: "BOX-B", length: 80, width: 50, height: 40 },
  ],
};
state.result = {
  containers: [
    { container_id: "ULD-1", loaded: [{ box_id: "BOX-A", quantity: 1 }], placements: [] },
    { container_id: "ULD-2", loaded: [{ box_id: "BOX-B", quantity: 2 }], placements: [] },
  ],
};
state.selectedContainerId = "ULD-2";
elements.loadedList = { textContent: "", innerHTML: "", classList };
elements.activeContainerStats = { textContent: "", innerHTML: "", classList };
elements.placementsTableBody = { innerHTML: "", querySelectorAll: () => [] };
elements.selectedBoxDetails = { textContent: "", innerHTML: "", classList };

renderActiveContainerDetails();
globalThis.__loadedHtml = elements.loadedList.innerHTML;
`, context);

const html = context.__loadedHtml;
if (!html.includes("BOX-B (80 × 50 × 40) × 2")) {
  throw new Error(`selected ULD loaded type missing: ${html}`);
}
if (html.includes("BOX-A")) {
  throw new Error(`loaded type from another ULD should not render: ${html}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_excel_export_includes_input_uld_and_box_data(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    {
      id: "Q7",
      length: 306,
      quantity: 2,
      cross_section: [[0, 0], [240, 0], [240, 240], [120, 290], [0, 290]],
    },
  ],
  boxes: [
    { id: "BOX-A", length: 60, width: 40, height: 30, quantity: 5, rotatable: false },
  ],
  objective: "maximize_volume",
  search_mode: "balanced",
};
const result = {
  loaded_count: 1,
  unloaded_count: 0,
  used_volume: 72000,
  container_volume: 1000000,
  volume_utilization: 0.072,
  loaded: [{ box_id: "BOX-A", quantity: 1 }],
  unloaded: [],
  validation_passed: true,
  validation_errors: [],
  containers: [
    {
      container_id: "Q7-001",
      container_type: "Q7",
      loaded_count: 1,
      unloaded_count: 0,
      used_volume: 72000,
      uld_volume: 1000000,
      volume_utilization: 0.072,
      validation_passed: true,
      placements: [
        { box_id: "BOX-A", instance_id: "BOX-A-001", x: 0, y: 0, z: 0, length: 60, width: 40, height: 30 },
      ],
    },
  ],
};

const sheets = context.buildWorkbookSheets(result, input);
const sheetByName = new Map(sheets.map((sheet) => [sheet.name, sheet]));
const uldRows = sheetByName.get("ULD 数据")?.rows;
const boxRows = sheetByName.get("箱子数据")?.rows;
const expectedCrossSection = JSON.stringify(input.containers[0].cross_section);
const uldRow = uldRows?.[1] ?? [];
const boxRow = boxRows?.[1] ?? [];

if (!uldRows || !boxRows) {
  throw new Error(`missing input sheets: ${sheets.map((sheet) => sheet.name).join(",")}`);
}
if (JSON.stringify(uldRows[0]) !== JSON.stringify(["ULD ID", "长度", "数量", "截面"])) {
  throw new Error(`unexpected ULD header: ${JSON.stringify(uldRows[0])}`);
}
if (uldRow[0] !== "Q7" || uldRow[1] !== 306 || uldRow[2] !== 2 || uldRow[3] !== expectedCrossSection) {
  throw new Error(`unexpected ULD row: ${JSON.stringify(uldRow)}`);
}
if (JSON.stringify(boxRows[0]) !== JSON.stringify(["箱子 ID", "长", "宽", "高", "数量", "长宽互换"])) {
  throw new Error(`unexpected box header: ${JSON.stringify(boxRows[0])}`);
}
if (boxRow[0] !== "BOX-A" || boxRow[1] !== 60 || boxRow[2] !== 40 || boxRow[3] !== 30 || boxRow[4] !== 5 || boxRow[5] !== "否") {
  throw new Error(`unexpected box row: ${JSON.stringify(boxRow)}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_html_report_export_includes_svg_views_and_tables(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    {
      id: "Q7",
      length: 300,
      quantity: 1,
      cross_section: [[0, 0], [120, 0], [120, 120], [0, 120]],
    },
  ],
  boxes: [
    { id: "BOX-A", length: 100, width: 80, height: 20, quantity: 1, rotatable: true },
  ],
  objective: "maximize_volume",
  search_mode: "balanced",
};
const result = {
  loaded_count: 1,
  unloaded_count: 0,
  used_volume: 160000,
  container_volume: 4320000,
  volume_utilization: 0.037,
  loaded: [{ box_id: "BOX-A", quantity: 1 }],
  unloaded: [],
  validation_passed: true,
  validation_errors: [],
  containers: [
    {
      container_id: "Q7-001",
      container_type: "Q7",
      loaded_count: 1,
      unloaded_count: 0,
      used_volume: 160000,
      uld_volume: 4320000,
      volume_utilization: 0.037,
      validation_passed: true,
      placements: [
        { box_id: "BOX-A", instance_id: "BOX-A-001", x: 25, y: 35, z: 10, length: 100, width: 80, height: 20 },
      ],
    },
  ],
};

const html = context.buildHtmlReport(result, input, "2026-06-23T01:02:03.000Z");
for (const expected of [
  "<!doctype html>",
  "ULD 装载报告",
  "Q7-001",
  "BOX-A",
  "BOX-A-001",
  "查看 ULD",
  "全部 ULD",
  "data-uld-filter",
  "data-uld-section=\"Q7-001\"",
  "俯视位置图",
  "交互 3D 视图",
  "scene-view-controls",
  "data-scene-view=\"isometric\"",
  "data-scene-view=\"top\"",
  "data-scene-view=\"side\"",
  "data-scene-view=\"section\"",
  "data-scene-reset",
  "等轴",
  "俯视",
  "侧视",
  "截面",
  "重置",
  "data-report-scene=\"Q7-001\"",
  "const reportSceneData",
  "function setHtmlReportSceneView",
  "function drawHtmlReportScene",
  "pointerdown",
  "wheel",
  "dblclick",
  "装箱坐标",
  "未装箱",
  "sheet-tabs",
  "sheet-page active",
  "data-sheet-name=\"总体结果\"",
  "data-sheet-name=\"ULD 明细\"",
  "data-sheet-name=\"ULD 数据\"",
  "data-sheet-name=\"箱子数据\"",
  "data-sheet-name=\"已装箱类型\"",
  "data-sheet-name=\"未装箱\"",
  "data-sheet-name=\"ULD 可视化\"",
  "data-sheet-name=\"装箱坐标\"",
  "top-views-grid",
  "scene-row",
  "view-card-heading",
  "3D 俯视图",
  "data-report-top-view=\"Q7-001\"",
  "report-scene-stage",
  "data-report-tooltip",
  "data-report-selection",
  "data-position-map",
  "data-position-label-toggle",
  "隐藏标识",
  "function initHtmlReportPositionMap",
  "function initHtmlReportPositionMapLabelToggle",
  "function selectHtmlReportPositionPile",
  "function initHtmlReportTopView",
  "function updateHtmlReportSceneHover",
  "function selectHtmlReportScenePlacement",
  "function renderHtmlReportSceneTooltip",
  "function drawHtmlReportFloorGrid",
  "function drawHtmlReportTopProjection",
  "function drawHtmlReportTopProjectionLabel",
  "if (selected) {\n            drawHtmlReportTopProjectionLabel(context, rect, placement.instance_id, selected);",
  ".top-views-grid .view-card { display: grid; grid-template-rows: auto minmax(0, 1fr);",
  ".position-map-svg-wrap { width: 100%; overflow: hidden;",
  ".position-map-svg { width: 100%; min-width: 0; aspect-ratio: 17 / 8;",
  ".position-pile { cursor: pointer;",
  ".position-pile.selected .position-pile-rect",
  ".position-map-svg.position-map-label-hidden .position-pile-label-layer",
  ".position-pile-label-item.selected .position-pile-label-bg",
  ".position-pile-label { fill: #ffffff; stroke: rgba(2, 6, 23, 0.88); stroke-width: 3px; paint-order: stroke; font-size: 12px; font-weight: 900; pointer-events: none; }",
  "data-placement-x=\"25\"",
  "data-placement-y=\"35\"",
  "data-placement-z=\"10\"",
  "25-125",
  "35-115",
  "BOX-A（100*80*20）*1",
  "<canvas",
  "100 × 80 × 20",
]) {
  if (!html.includes(expected)) {
    throw new Error(`missing html report content ${expected}: ${html.slice(0, 600)}`);
  }
}
if (html.includes("<script src=") || html.includes("<link rel=\"stylesheet\"")) {
  throw new Error("html report should be self-contained");
}
for (const removed of [
  "sheet-page-wide",
  ".sheet-page-wide",
]) {
  if (html.includes(removed)) {
    throw new Error(`html visualization page should use the original report width, but found ${removed}`);
  }
}
const inlineScript = html.match(/<script>([\s\S]*)<\/script>/)?.[1];
if (!inlineScript) {
  throw new Error("html report should include an inline script");
}
new vm.Script(inlineScript);
const visualizationStart = html.indexOf('data-sheet-name="ULD 可视化"');
const coordinateStart = html.indexOf('data-sheet-name="装箱坐标"');
const visualizationHtml = html.slice(visualizationStart, coordinateStart);
if (visualizationHtml.includes("俯视 X-Y") || visualizationHtml.includes("侧视 X-Z") || visualizationHtml.includes("截面 Y-Z")) {
  throw new Error(`HTML visualization page should only include the position map and interactive 3D view: ${visualizationHtml}`);
}
if (inlineScript.includes("drawHtmlReportTopProjectionLabel(context, rect, placement.box_id, selected)")) {
  throw new Error("3D top view should not show box type labels by default");
}
const loadSummaryStart = visualizationHtml.indexOf("装载清单");
const loadSummaryEnd = visualizationHtml.indexOf("top-views-grid", loadSummaryStart);
const loadSummaryHtml = visualizationHtml.slice(loadSummaryStart, loadSummaryEnd);
if (!loadSummaryHtml.includes("BOX-A（100*80*20）*1")) {
  throw new Error(`load summary should include box id with dimensions and quantity: ${loadSummaryHtml}`);
}
if (loadSummaryHtml.includes("100*80*20*1")) {
  throw new Error(`load summary should not omit box id: ${loadSummaryHtml}`);
}
const fileName = context.buildHtmlFileName(result, "2026-06-23T01:02:03.000Z");
if (fileName !== "20260623-090203-装载率3.70%.html") {
  throw new Error(`unexpected html file name: ${fileName}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_html_report_top_position_map_uses_actual_coordinate_piles(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    { id: "Q7", length: 220, quantity: 1, cross_section: [[0, 0], [100, 0], [100, 80], [0, 80]] },
  ],
  boxes: [],
};
const result = {
  loaded_count: 3,
  unloaded_count: 0,
  used_volume: 160000,
  container_volume: 1760000,
  volume_utilization: 0.09,
  loaded: [],
  unloaded: [],
  validation_passed: true,
  validation_errors: [],
  containers: [
    {
      container_id: "Q7-001",
      container_type: "Q7",
      loaded_count: 3,
      unloaded_count: 0,
      used_volume: 160000,
      uld_volume: 1760000,
      volume_utilization: 0.09,
      validation_passed: true,
      placements: [
        { box_id: "BOTTOM", instance_id: "BOTTOM-001", x: 10, y: 20, z: 0, length: 100, width: 50, height: 20 },
        { box_id: "TOP", instance_id: "TOP-001", x: 20, y: 30, z: 20, length: 80, width: 40, height: 20 },
        { box_id: "SOLO", instance_id: "SOLO-001", x: 150, y: 20, z: 0, length: 40, width: 30, height: 20 },
      ],
    },
  ],
};

const html = context.buildHtmlReport(result, input, "2026-06-23T01:02:03.000Z");
const mapStart = html.indexOf("俯视位置图");
const topViewStart = html.indexOf("3D 俯视图", mapStart);
const mapHtml = html.slice(mapStart, topViewStart);

for (const expected of [
  "position-map-svg",
  "data-position-map",
  "view-card-heading",
  "data-position-label-toggle",
  "aria-pressed=\"true\"",
  "隐藏标识",
  "data-pile-index=\"1\"",
  "data-pile-count=\"2\"",
  "role=\"button\"",
  "tabindex=\"0\"",
  "data-pile-x=\"10\"",
  "data-pile-y=\"20\"",
  "data-pile-width=\"100\"",
  "data-pile-height=\"50\"",
  "data-pile-members=\"TOP-001,BOTTOM-001\"",
  "position-pile-layer",
  "position-pile-label-layer",
  "position-pile-label-bg",
  "TOP（80*40*20）*1",
  "BOTTOM（100*50*20）*1",
  "data-pile-index=\"2\"",
  "data-pile-count=\"1\"",
  "data-pile-x=\"150\"",
  "data-pile-y=\"20\"",
  "data-pile-width=\"40\"",
  "data-pile-height=\"30\"",
]) {
  if (!mapHtml.includes(expected)) {
    throw new Error(`missing actual coordinate pile content ${expected}: ${mapHtml}`);
  }
}
if (mapHtml.includes("<table")) {
  throw new Error(`top position map should not use equal-width table cells: ${mapHtml}`);
}
if (mapHtml.includes("position-map-toolbar")) {
  throw new Error(`position label toggle should sit in the view-card heading: ${mapHtml}`);
}
if (html.includes("overflow-x: auto; }\n    .position-map-svg { min-width: 640px")) {
  throw new Error("top position map should scale inside the card without a horizontal scrollbar");
}
const shapeLayerIndex = mapHtml.indexOf("position-pile-layer");
const labelLayerIndex = mapHtml.indexOf("position-pile-label-layer");
if (shapeLayerIndex < 0 || labelLayerIndex < 0 || shapeLayerIndex > labelLayerIndex) {
  throw new Error(`pile labels should be rendered after all pile rectangles: ${mapHtml}`);
}
const topLayerIndex = mapHtml.indexOf("TOP（80*40*20）*1");
const bottomLayerIndex = mapHtml.indexOf("BOTTOM（100*50*20）*1");
if (topLayerIndex < 0 || bottomLayerIndex < 0 || topLayerIndex > bottomLayerIndex) {
  throw new Error(`pile labels should be ordered from top to bottom: ${mapHtml}`);
}
if (mapHtml.includes("80*40*20*1") || mapHtml.includes("100*50*20*1")) {
  throw new Error(`pile labels should include box id and parenthesized dimensions: ${mapHtml}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_html_report_top_position_map_keeps_l_shaped_pile_footprints(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    { id: "Q7", length: 100, quantity: 1, cross_section: [[0, 0], [100, 0], [100, 100], [0, 100]] },
  ],
  boxes: [],
};
const result = {
  loaded_count: 2,
  unloaded_count: 0,
  used_volume: 80000,
  container_volume: 1000000,
  volume_utilization: 0.08,
  loaded: [],
  unloaded: [],
  validation_passed: true,
  validation_errors: [],
  containers: [
    {
      container_id: "Q7-001",
      container_type: "Q7",
      loaded_count: 2,
      unloaded_count: 0,
      used_volume: 80000,
      uld_volume: 1000000,
      volume_utilization: 0.08,
      validation_passed: true,
      placements: [
        { box_id: "BAR-X", instance_id: "BAR-X-001", x: 0, y: 0, z: 0, length: 100, width: 40, height: 20 },
        { box_id: "BAR-Y", instance_id: "BAR-Y-001", x: 60, y: 0, z: 20, length: 40, width: 100, height: 20 },
      ],
    },
  ],
};

const html = context.buildHtmlReport(result, input, "2026-06-23T01:02:03.000Z");
const mapStart = html.indexOf("俯视位置图");
const topViewStart = html.indexOf("3D 俯视图", mapStart);
const mapHtml = html.slice(mapStart, topViewStart);
const pileMatch = mapHtml.match(/<g class="position-pile"[^>]*data-pile-index="1"[\s\S]*?<\/g>/);
if (!pileMatch) {
  throw new Error(`missing first pile: ${mapHtml}`);
}
const pileHtml = pileMatch[0];
for (const expected of [
  "data-pile-count=\"2\"",
  "data-pile-width=\"100\"",
  "data-pile-height=\"100\"",
  "position-pile-footprint",
  "data-footprint-width=\"100\" data-footprint-height=\"40\"",
  "data-footprint-width=\"40\" data-footprint-height=\"100\"",
]) {
  if (!pileHtml.includes(expected)) {
    throw new Error(`missing L-shaped pile footprint content ${expected}: ${pileHtml}`);
  }
}
if (pileHtml.includes("data-footprint-width=\"100\" data-footprint-height=\"100\"")) {
  throw new Error(`L-shaped pile should not be filled as its bounding rectangle: ${pileHtml}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_excel_export_box_references_include_dimensions(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    { id: "ULD", length: 300, quantity: 1, cross_section: [[0, 0], [120, 0], [120, 120], [0, 120]] },
  ],
  boxes: [
    { id: "BOX-A", length: 60, width: 40, height: 30, quantity: 3, rotatable: true },
    { id: "BOX-B", length: 80, width: 50, height: 40, quantity: 1, rotatable: true },
  ],
};
const result = {
  loaded_count: 1,
  unloaded_count: 1,
  volume_utilization: 0.1,
  validation_passed: true,
  loaded: [{ box_id: "BOX-A", quantity: 1 }],
  unloaded: [{ box_id: "BOX-B", quantity: 1, reason: "超出空间" }],
  containers: [
    {
      container_id: "ULD-001",
      container_type: "ULD",
      loaded_count: 1,
      unloaded_count: 1,
      volume_utilization: 0.1,
      validation_passed: true,
      placements: [
        { box_id: "BOX-A", instance_id: "BOX-A-001", x: 0, y: 0, z: 0, length: 60, width: 40, height: 30 },
      ],
    },
  ],
};
const cellValue = (cell) => cell && typeof cell === "object" && "value" in cell ? cell.value : cell;
const sheetByName = new Map(context.buildWorkbookSheets(result, input).map((sheet) => [sheet.name, sheet]));
const loadedBox = cellValue(sheetByName.get("已装箱类型").rows[1][0]);
const unloadedBox = cellValue(sheetByName.get("未装箱").rows[1][0]);
const placementBox = cellValue(sheetByName.get("装箱坐标").rows[1][2]);

if (loadedBox !== "BOX-A (60 × 40 × 30)") {
  throw new Error(`loaded sheet box should include dimensions: ${JSON.stringify(loadedBox)}`);
}
if (unloadedBox !== "BOX-B (80 × 50 × 40)") {
  throw new Error(`unloaded sheet box should include dimensions: ${JSON.stringify(unloadedBox)}`);
}
if (placementBox !== "BOX-A (60 × 40 × 30)") {
  throw new Error(`placement sheet box should include dimensions: ${JSON.stringify(placementBox)}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_excel_column_widths_expand_to_fit_long_cell_values(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const longBoxLabel = "BOX-SUPER-LONG-TYPE (120 × 110 × 100)";
const sheet = {
  name: "宽度测试",
  widths: [12],
  rows: [
    ["箱子 ID"],
    [longBoxLabel],
  ],
};
const worksheetXml = context.buildWorksheetXml(sheet, context.buildExcelStyleModel([sheet]));
const widthMatch = worksheetXml.match(/<col min="1" max="1" width="([^"]+)"/);
if (!widthMatch) {
  throw new Error(`missing first column width: ${worksheetXml}`);
}
const width = Number(widthMatch[1]);
const expectedMinimumWidth = longBoxLabel.length + 4;
if (width < expectedMinimumWidth) {
  throw new Error(`column width ${width} should fit ${longBoxLabel.length} chars: ${worksheetXml}`);
}
"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_excel_export_includes_uld_visualization_sheet(self):
        node_script = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync("web/app.js", "utf8");
const context = {
  document: { addEventListener: () => {} },
  structuredClone,
  console,
};
vm.createContext(context);
vm.runInContext(code, context);

const input = {
  containers: [
    {
      id: "Q7",
      length: 300,
      quantity: 1,
      cross_section: [[0, 0], [120, 0], [120, 120], [0, 120]],
    },
  ],
  boxes: [],
  objective: "maximize_volume",
  search_mode: "balanced",
};
const result = {
  loaded_count: 11,
  unloaded_count: 0,
  used_volume: 260000,
  container_volume: 4320000,
  volume_utilization: 0.0601,
  loaded: [
    { box_id: "FRONT-A", quantity: 1 },
    { box_id: "FRONT-B", quantity: 1 },
    { box_id: "REAR-LONG", quantity: 1 },
    { box_id: "SMALL", quantity: 8 },
  ],
  unloaded: [],
  validation_passed: true,
  validation_errors: [],
  containers: [
    {
      container_id: "Q7-001",
      container_type: "Q7",
      loaded_count: 11,
      unloaded_count: 0,
      used_volume: 260000,
      uld_volume: 4320000,
      volume_utilization: 0.0601,
      validation_passed: true,
      placements: [
        { box_id: "FRONT-A", instance_id: "FRONT-A-001", x: 0, y: 0, z: 0, length: 80, width: 40, height: 20 },
        { box_id: "FRONT-B", instance_id: "FRONT-B-001", x: 80, y: 0, z: 0, length: 80, width: 40, height: 30 },
        { box_id: "REAR-LONG", instance_id: "REAR-LONG-001", x: 0, y: 80, z: 0, length: 220, width: 40, height: 50 },
        { box_id: "SMALL", instance_id: "SMALL-001", x: 0, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-002", x: 20, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-003", x: 40, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-004", x: 60, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-005", x: 80, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-006", x: 100, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-007", x: 120, y: 0, z: 50, length: 20, width: 20, height: 10 },
        { box_id: "SMALL", instance_id: "SMALL-008", x: 140, y: 0, z: 50, length: 20, width: 20, height: 10 },
      ],
    },
  ],
};

const sheets = context.buildWorkbookSheets(result, input);
const visualSheet = sheets.find((sheet) => sheet.name === "ULD 可视化");
if (!visualSheet) {
  throw new Error(`missing visualization sheet: ${sheets.map((sheet) => sheet.name).join(",")}`);
}
const cellValue = (cell) => typeof cell === "object" ? cell.value : cell;
const flat = visualSheet.rows.flat().map(cellValue);
const listRow = visualSheet.rows.find((row) => cellValue(row[0]) === "装载清单") ?? [];
for (const expectedSummary of ["80*40*20*1", "80*40*30*1", "220*40*50*1", "20*20*10*8"]) {
  if (!flat.some((value) => String(value) === expectedSummary)) {
    throw new Error(`missing size summary ${expectedSummary}: ${JSON.stringify(visualSheet.rows)}`);
  }
  if (!listRow.some((cell) => String(cellValue(cell)) === expectedSummary)) {
    throw new Error(`loading list should write summaries horizontally: ${JSON.stringify(visualSheet.rows)}`);
  }
}
if (!flat.some((value) => String(value).includes("ULD Q7-001"))) {
  throw new Error(`missing ULD title: ${JSON.stringify(visualSheet.rows)}`);
}
if (!flat.some((value) => String(value).includes("俯视位置图"))) {
  throw new Error(`missing top view label: ${JSON.stringify(visualSheet.rows)}`);
}
if (flat.some((value) => String(value).includes("箱型尺寸矩阵") || String(value).includes("x-z 侧视图") || String(value).includes("z \\ x"))) {
  throw new Error(`visual sheet should not include old matrix or x-z views: ${JSON.stringify(visualSheet.rows)}`);
}
if (flat.some((value) => String(value).includes("REAR-LONG-001"))) {
  throw new Error(`visual sheet should not include box instance ids: ${JSON.stringify(visualSheet.rows)}`);
}
if (flat.some((value) => String(value).includes("FRONT-A x 1") || String(value).includes("REAR-LONG x 1"))) {
  throw new Error(`visual summary should use size quantities: ${JSON.stringify(visualSheet.rows)}`);
}
if (flat.some((value) => /^y \d/.test(String(value)))) {
  throw new Error(`visual sheet should not include y channel labels: ${JSON.stringify(visualSheet.rows)}`);
}
const topViewIndex = visualSheet.rows.findIndex((row) => String(cellValue(row[0])).includes("俯视位置图"));
const headerRow = visualSheet.rows[topViewIndex + 1].map(cellValue);
if (JSON.stringify(headerRow) !== JSON.stringify(["y \\ x", "0-220", "80-160"])) {
  throw new Error(`top view header should use each pile anchor x extended by its max length: ${JSON.stringify(headerRow)}`);
}
const bodyRows = visualSheet.rows.slice(topViewIndex + 2);
const rowByY = new Map(bodyRows.filter((row) => String(cellValue(row[0])).includes("-")).map((row) => [String(cellValue(row[0])), row.map(cellValue)]));
if (JSON.stringify([...rowByY.keys()]) !== JSON.stringify(["80-120", "0-40"])) {
  throw new Error(`top view rows should be one row per anchor y, descending with first quadrant y-up: ${JSON.stringify([...rowByY.keys()])}`);
}
const frontRow = rowByY.get("0-40") ?? [];
const frontText = frontRow.slice(1).map((value) => String(value ?? "")).join("\n");
for (const expectedFrontSummary of ["80*40*20*1", "80*40*30*1", "20*20*10*4"]) {
  if (!frontText.includes(expectedFrontSummary)) {
    throw new Error(`front row should show boxes near y=0: ${JSON.stringify(visualSheet.rows)}`);
  }
}
const frontFirstCell = String(frontRow[1] ?? "");
if (frontFirstCell !== "80*40*20*1\n20*20*10*4") {
  throw new Error(`front stack should list layers bottom-to-top: ${JSON.stringify(frontFirstCell)}`);
}
const rearRow = rowByY.get("80-120") ?? [];
const rearCells = rearRow.slice(1).map((value) => String(value ?? ""));
if (rearCells.filter((value) => value.includes("220*40*50*1")).length !== 1) {
  throw new Error(`rear long box should appear once in top view: ${JSON.stringify(visualSheet.rows)}`);
}
const worksheetXml = context.buildWorksheetXml(visualSheet, context.buildExcelStyleModel([visualSheet]));
const visualMerges = visualSheet.merges ?? [];
if (visualMerges.length !== 0) {
  throw new Error(`each pile occupies a single cell, so the visualization sheet should never merge: ${JSON.stringify(visualMerges)}`);
}
const frontRowNumber = topViewIndex + 2 + [...rowByY.keys()].indexOf("0-40") + 1;
if (!worksheetXml.includes(`<row r="${frontRowNumber}" ht="40" customHeight="1">`)) {
  throw new Error(`multi-line top view row should be tall enough: ${worksheetXml}`);
}
const stylesXml = context.buildStylesXml(context.buildExcelStyleModel([visualSheet]));
if (!stylesXml.includes('wrapText="1"')) {
  throw new Error(`multi-line top view cells should enable Excel wrapText: ${stylesXml}`);
}
function sizeQuantityTotal(cells) {
  return cells.reduce((total, cell) => {
    const text = String(cellValue(cell) ?? "");
    const matches = [...text.matchAll(/\d+(?:\.\d+)?\*\d+(?:\.\d+)?\*\d+(?:\.\d+)?\*(\d+)/g)];
    return total + matches.reduce((sum, match) => sum + Number(match[1]), 0);
  }, 0);
}
function visibleCellsAfterMerges(rows, merges) {
  return rows.flatMap((row, rowIndex) =>
    row.filter((_, columnIndex) => !merges.some((merge) =>
      rowIndex >= merge.startRow &&
      rowIndex <= merge.endRow &&
      columnIndex >= merge.startColumn &&
      columnIndex <= merge.endColumn &&
      (rowIndex !== merge.startRow || columnIndex !== merge.startColumn)
    ))
  );
}
const topViewRows = [...rowByY.values()];
const listTotal = sizeQuantityTotal(listRow.slice(1));
const topViewTotal = sizeQuantityTotal(topViewRows.flatMap((row) => row.slice(1)));
if (listTotal !== topViewTotal) {
  throw new Error(`loading list total ${listTotal} must equal top view total ${topViewTotal}: ${JSON.stringify(visualSheet.rows)}`);
}
const multiSupportPlacements = [
  { box_id: "LOW-A", x: 0, y: 0, z: 0, length: 80, width: 40, height: 50 },
  { box_id: "LOW-B", x: 80, y: 0, z: 0, length: 80, width: 40, height: 50 },
  { box_id: "TOP", x: 0, y: 0, z: 50, length: 160, width: 40, height: 20 },
];
const multiSupportStacks = context.buildPlacementStacks(multiSupportPlacements);
if (multiSupportStacks.length !== 1 || multiSupportStacks[0].placements.length !== 3) {
  throw new Error(`a box supported by multiple lower boxes should form one stack: ${JSON.stringify(multiSupportStacks)}`);
}
const multiSupportRows = context.buildTopViewRows(
  multiSupportPlacements,
  { length: 300, cross_section: [[0, 0], [120, 0], [120, 120], [0, 120]] },
);
if (JSON.stringify(multiSupportRows[0].map(cellValue)) !== JSON.stringify(["y \\ x", "0-160"])) {
  throw new Error(`multi-support stack should use the largest box length as one x cell: ${JSON.stringify(multiSupportRows)}`);
}
const multiSupportAnchor = String(cellValue(multiSupportRows[1][1]) ?? "");
if (multiSupportAnchor !== "80*40*50*2\n160*40*20*1") {
  throw new Error(`multi-support stack should list bottom layer then top layer: ${JSON.stringify(multiSupportAnchor)}`);
}
const multiSupportVisibleTotal = sizeQuantityTotal(visibleCellsAfterMerges(multiSupportRows, multiSupportRows.merges ?? []));
if (multiSupportVisibleTotal !== 3) {
  throw new Error(`multi-support stack should keep all boxes visible once: ${JSON.stringify(multiSupportRows)}, merges=${JSON.stringify(multiSupportRows.merges ?? [])}`);
}
const stackedRows = context.buildTopViewRows(
  [
    { box_id: "STACK-A", x: 0, y: 0, z: 0, length: 100, width: 80, height: 20 },
    { box_id: "STACK-B", x: 0, y: 0, z: 20, length: 100, width: 80, height: 30 },
    { box_id: "STACK-C", x: 100, y: 0, z: 0, length: 50, width: 40, height: 40 },
  ],
  { length: 200, cross_section: [[0, 0], [120, 0], [120, 120], [0, 120]] },
);
const stackedHeader = stackedRows[0].map(cellValue);
if (JSON.stringify(stackedHeader) !== JSON.stringify(["y \\ x", "0-100", "100-150"])) {
  throw new Error(`top view should take each stack max length for x ranges: ${JSON.stringify(stackedHeader)}`);
}
if (JSON.stringify(stackedRows.slice(1).map((row) => String(cellValue(row[0])))) !== JSON.stringify(["0-80"])) {
  throw new Error(`stacked piles share one anchor-y row spanning their max width: ${JSON.stringify(stackedRows)}`);
}
const stackedAnchor = String(cellValue(stackedRows[1][1]) ?? "");
if (stackedAnchor !== "100*80*20*1\n100*80*30*1") {
  throw new Error(`stacked boxes should stay in one cell listed bottom-to-top: ${JSON.stringify(stackedAnchor)}`);
}
if ((stackedRows.merges ?? []).length !== 0) {
  throw new Error(`stacked piles each occupy a single cell and should not merge: ${JSON.stringify(stackedRows.merges ?? [])}`);
}
const stackedVisibleTotal = sizeQuantityTotal(visibleCellsAfterMerges(stackedRows, stackedRows.merges ?? []));
if (stackedVisibleTotal !== 3) {
  throw new Error(`stacked top view should keep every box visible once: ${JSON.stringify(stackedRows)}, merges=${JSON.stringify(stackedRows.merges ?? [])}`);
}
// 两个互相独立（无支撑关系）但俯视格子直接重叠的摞各自降级为单格、不合并，
// 保持各摞独立不并组，避免合并矩形互相覆盖导致 Excel 报错。
const overlapRows = context.buildTopViewRows(
  [
    { box_id: "PILE-A", x: 0, y: 0, z: 0, length: 100, width: 100, height: 50 },
    { box_id: "PILE-B", x: 50, y: 50, z: 0, length: 100, width: 100, height: 50 },
  ],
  { length: 200, cross_section: [[0, 0], [200, 0], [200, 200], [0, 200]] },
);
if ((overlapRows.merges ?? []).length !== 0) {
  throw new Error(`overlapping piles must not merge to avoid Excel overlap errors: ${JSON.stringify(overlapRows.merges ?? [])}`);
}
const overlapBody = overlapRows.slice(1).flatMap((row) => row.slice(1)).map((value) => String(cellValue(value) ?? ""));
const overlapNonEmpty = overlapBody.filter((value) => value !== "");
if (overlapNonEmpty.length !== 2) {
  throw new Error(`overlapping piles should each stay as its own single cell: ${JSON.stringify(overlapRows)}`);
}
const overlapTotal = sizeQuantityTotal(overlapRows.slice(1).flatMap((row) => row.slice(1)));
if (overlapTotal !== 2) {
  throw new Error(`overlapping piles should each stay visible once: ${JSON.stringify(overlapRows)}`);
}

"""
        completed = subprocess.run(
            ["node", "-"],
            input=node_script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
