import unittest
import json
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
        ]:
            self.assertIn(f'id="{expected_id}"', html)
        self.assertNotIn("只改变截面查看，不改变装箱结果", html)
        self.assertNotIn("x 从 ULD 前端沿长度方向量起", html)
        self.assertNotIn('class="slice-note"', html)
        self.assertIn("添加 ULD", html)
        self.assertIn("批量粘贴箱子", html)
        self.assertIn("识别并添加箱子", html)
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
        self.assertNotIn('class="input-toolbar"', html)
        self.assertNotIn('class="input-actions"', html)
        self.assertNotIn("<h1>ULD 装箱可视化</h1>", html)
        self.assertIn("当前 ULD", html)
        self.assertIn("最近10次计算记录", html)
        self.assertIn("装箱动画", html)
        self.assertIn("播放动画", html)
        self.assertIn("倍速", html)
        self.assertIn("选择要查看的 ULD 实例", html)
        self.assertIn("单个 ULD 装载率", html)
        self.assertIn("导出 XLSX", html)
        self.assertIn("悬停箱子信息", html)
        self.assertIn("<th>ID</th>", html)
        self.assertIn("<th>长宽互换</th>", html)
        self.assertNotIn("<th>类型</th>", html)
        self.assertNotIn("<th>旋转</th>", html)
        self.assertNotIn("容器", html)

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
            "parseBulkBoxLines",
            "parseBulkBoxLine",
            "exportExcel",
            "buildExcelWorkbook",
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
        self.assertIn("bulkBoxInput", script)
        self.assertIn("140*105*94*20", script)
        self.assertIn("40.5*40.5*14*1", script)
        self.assertIn(r".split(/\r\n|\n|\r/)", script)
        self.assertIn(r"line.split(/[\s*＊×xXｘＸ✕✖⨯]+/)", script)
        self.assertIn("quantity: readNonNegativeInteger(quantity", script)
        self.assertIn("exportExcelButton.addEventListener", script)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", script)
        self.assertIn("downloadExcelWorkbook(buildExcelWorkbook(state.result, state.input), buildExcelFileName(state.result, currentExportCreatedAt()))", script)
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

    def test_visualizer_styles_scene_tooltip_and_clearer_box_edges(self):
        css = Path("web/styles.css").read_text(encoding="utf-8")

        self.assertIn(".scene-stage", css)
        self.assertIn(".scene-tooltip", css)
        self.assertIn(".panel-title", css)
        self.assertIn(".section-card", css)
        self.assertIn(".result-section", css)
        self.assertIn(".history-list", css)
        self.assertIn(".history-record", css)
        self.assertIn(".bulk-box-import", css)
        self.assertIn(".bulk-box-import textarea", css)
        self.assertIn("--result-panel-height: calc(var(--history-list-height) + 360px)", css)
        self.assertIn("--input-panel-height: var(--result-panel-height)", css)
        self.assertIn("--history-list-height: 592px", css)
        self.assertIn("--scene-min-height: clamp(560px, 58vh, 760px)", css)
        self.assertIn("minmax(520px, 1.3fr) minmax(480px, 1.15fr) minmax(320px, 0.85fr)", css)
        self.assertIn("minmax(620px, 1.15fr) minmax(580px, 1.4fr) minmax(380px, 0.8fr)", css)
        self.assertIn("grid-template-rows: auto minmax(var(--scene-min-height), 1fr) auto auto", css)
        self.assertIn("height: var(--projection-height)", css)
        self.assertIn("@media (min-width: 2200px)", css)
        self.assertIn("@media (max-width: 1599px)", css)
        self.assertIn('\"uld boxes\"', css)
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
        self.assertIn("max-height: calc(100vh - 112px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("position: sticky", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("border: 1px solid rgba(226, 232, 240, 0.28)", css)
        self.assertIn("box-shadow: inset 0 0 120px rgba(0, 0, 0, 0.68)", css)
        self.assertIn("background: linear-gradient(160deg, #040813 0%, #071426 52%, #01040a 100%)", css)

    def test_visualizer_defaults_to_field_uld_rows_with_zero_quantities_and_no_sample_box(self):
        script = Path("web/app.js").read_text(encoding="utf-8")
        sample = json.loads(Path("data/profile_packing_input.json").read_text(encoding="utf-8"))
        expected_containers = [
            ("Q7", 306, [[0, 0], [240, 0], [240, 240], [120, 290], [0, 290]]),
            ("Q6", 306, [[0, 0], [240, 0], [240, 240], [0, 240]]),
            ("L", 346, [[0, 0], [240, 0], [240, 160], [0, 160]]),
            ("PGA", 600, [[0, 0], [240, 0], [240, 190], [120, 290], [0, 290]]),
            ("Q5", 306, [[0, 0], [240, 0], [240, 190], [120, 290], [0, 290]]),
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
