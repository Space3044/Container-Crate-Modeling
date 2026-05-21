import unittest
import json
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
        self.assertIn(r"line.split(/[\s*×xX]+/)", script)
        self.assertIn("quantity: readNonNegativeInteger(quantity", script)
        self.assertIn("exportExcelButton.addEventListener", script)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", script)
        self.assertIn("downloadExcelWorkbook(buildExcelWorkbook(state.result), buildExcelFileName(state.result, currentExportCreatedAt()))", script)
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
        self.assertIn("minmax(370px, 0.95fr) minmax(640px, 1.9fr) minmax(350px, 0.92fr)", css)
        self.assertIn("grid-template-rows: auto minmax(640px, 1fr) auto auto", css)
        self.assertIn("min-height: 980px", css)
        self.assertIn("min-height: 640px", css)
        self.assertIn("height: 160px", css)
        self.assertIn("max-height: calc(100vh - 112px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("position: sticky", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("border: 1px solid rgba(226, 232, 240, 0.28)", css)
        self.assertIn("box-shadow: inset 0 0 120px rgba(0, 0, 0, 0.68)", css)
        self.assertIn("background: linear-gradient(160deg, #040813 0%, #071426 52%, #01040a 100%)", css)

    def test_visualizer_defaults_to_field_uld_rows_and_no_sample_box(self):
        script = Path("web/app.js").read_text(encoding="utf-8")
        sample = json.loads(Path("data/profile_packing_input.json").read_text(encoding="utf-8"))
        expected_containers = [
            ("Q7", 306, [[0, 0], [240, 0], [240, 240], [120, 240], [0, 290]]),
            ("Q6", 306, [[0, 0], [240, 0], [240, 240], [0, 240]]),
            ("L", 346, [[0, 0], [240, 0], [240, 160], [0, 160]]),
            ("PGA", 600, [[0, 0], [240, 0], [240, 190], [120, 290], [0, 290]]),
            ("Q5", 306, [[0, 0], [240, 0], [240, 290], [120, 290], [0, 290]]),
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
        self.assertTrue(all(isinstance(container["quantity"], int) and container["quantity"] >= 0 for container in sample["containers"]))
        self.assertIn('class="container-quantity" type="number" min="0"', script)
        self.assertIn("readNonNegativeInteger(row.querySelector(\".container-quantity\").value", script)
        self.assertEqual(sample["boxes"], [])


if __name__ == "__main__":
    unittest.main()
