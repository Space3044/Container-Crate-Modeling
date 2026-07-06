const fallbackInput = {
  containers: [
    {
      id: "Q7",
      length: 306,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 240],
        [120, 290],
        [0, 290],
      ],
    },
    {
      id: "Q6",
      length: 306,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 240],
        [0, 240],
      ],
    },
    {
      id: "Q6-2",
      length: 306,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 220],
        [120, 240],
        [0, 240],
      ],
    },
    {
      id: "L",
      length: 346,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 160],
        [0, 160],
      ],
    },
    {
      id: "PGA",
      length: 600,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 190],
        [120, 290],
        [0, 290],
      ],
    },
    {
      id: "Q5",
      length: 306,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 190],
        [120, 290],
        [0, 290],
      ],
    },
    {
      id: "Q4",
      length: 306,
      quantity: 0,
      cross_section: [
        [0, 0],
        [240, 0],
        [240, 130],
        [120, 290],
        [0, 290],
      ],
    },
  ],
  boxes: [],
  objective: "maximize_volume",
  search_mode: "balanced",
};

const AXIS_EXTENSION_FACTOR = 1.18;
const SCENE_SAFE_PADDING = 72;
const BOX_ANIMATION_INTERVAL_MS = 320;
const MAX_HISTORY_RECORDS = 10;
const HISTORY_STORAGE_KEY = "uld-packing-history";
const THEME_STORAGE_KEY = "uld-packing-theme";
const BULK_BOX_EXAMPLE = "140*105*94*20\n40.5*40.5*14*1";
const BOX_COLOR_PALETTE = [
  { r: 14, g: 165, b: 233 },
  { r: 245, g: 158, b: 11 },
  { r: 168, g: 85, b: 247 },
  { r: 16, g: 185, b: 129 },
  { r: 244, g: 63, b: 94 },
  { r: 99, g: 102, b: 241 },
  { r: 20, g: 184, b: 166 },
  { r: 249, g: 115, b: 22 },
  { r: 217, g: 70, b: 239 },
  { r: 132, g: 204, b: 22 },
  { r: 236, g: 72, b: 153 },
  { r: 59, g: 130, b: 246 },
];
const EXCEL_COLOR_PALETTE = [
  "FFE0F2FE",
  "FFFEF3C7",
  "FFF3E8FF",
  "FFD1FAE5",
  "FFFFE4E6",
  "FFE0E7FF",
  "FFCCFBF1",
  "FFFFEDD5",
  "FFFAE8FF",
  "FFECFCCB",
  "FFFCE7F3",
  "FFDBEAFE",
  "FFDCFCE7",
  "FFFEF9C3",
  "FFEDE9FE",
  "FFE2E8F0",
  "FFCFFAFE",
  "FFFEE2E2",
];
const CRC32_TABLE = buildCrc32Table();

const state = {
  input: structuredClone(fallbackInput),
  result: null,
  selectedContainerId: null,
  selectedInstanceId: null,
  selectedHistoryId: null,
  hoveredInstanceId: null,
  focusedBoxId: null,
  historyRecords: [],
  sliceX: 0,
  camera: {
    yaw: -0.72,
    pitch: 0.58,
    zoom: 1,
    panX: 0,
    panY: 10,
  },
  pointer: {
    active: false,
    mode: "rotate",
    x: 0,
    y: 0,
    moved: false,
  },
  hitRegions: {
    scene: [],
    top: [],
    side: [],
    section: [],
  },
  animation: {
    active: false,
    frameId: null,
    startedAt: 0,
    elapsed: 0,
    speed: 1,
    visibleCount: null,
  },
};

const elements = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  initializeTheme();
  bindEvents();
  state.historyRecords = await loadPersistedHistoryRecords();
  renderHistoryRecords();
  await loadSample();
  await calculatePacking({ recordHistory: false });
  window.addEventListener("resize", drawAllViews);
}

function cacheElements() {
  elements.containerTableBody = document.getElementById("containerTableBody");
  elements.addContainerButton = document.getElementById("addContainerButton");
  elements.containerSelector = document.getElementById("containerSelector");
  elements.boxTableBody = document.getElementById("boxTableBody");
  elements.addBoxButton = document.getElementById("addBoxButton");
  elements.clearBoxesButton = document.getElementById("clearBoxesButton");
  elements.bulkBoxInput = document.getElementById("bulkBoxInput");
  elements.importBoxesButton = document.getElementById("importBoxesButton");
  elements.searchModeSelect = document.getElementById("searchModeSelect");
  elements.themeToggleButton = document.getElementById("themeToggleButton");
  elements.calculateButton = document.getElementById("calculateButton");
  elements.loadSampleButton = document.getElementById("loadSampleButton");
  elements.resetViewButton = document.getElementById("resetViewButton");
  elements.animationPlayButton = document.getElementById("animationPlayButton");
  elements.animationResetButton = document.getElementById("animationResetButton");
  elements.animationSpeedSlider = document.getElementById("animationSpeedSlider");
  elements.animationSpeedValue = document.getElementById("animationSpeedValue");
  elements.animationProgress = document.getElementById("animationProgress");
  elements.isometricViewButton = document.getElementById("isometricViewButton");
  elements.topViewButton = document.getElementById("topViewButton");
  elements.sideViewButton = document.getElementById("sideViewButton");
  elements.sectionViewButton = document.getElementById("sectionViewButton");
  elements.sliceSlider = document.getElementById("sliceSlider");
  elements.sliceValue = document.getElementById("sliceValue");
  elements.errorMessage = document.getElementById("errorMessage");
  elements.summaryCards = document.getElementById("summaryCards");
  elements.historyList = document.getElementById("historyList");
  elements.exportExcelButton = document.getElementById("exportExcelButton");
  elements.exportHtmlButton = document.getElementById("exportHtmlButton");
  elements.loadedList = document.getElementById("loadedList");
  elements.unloadedList = document.getElementById("unloadedList");
  elements.activeContainerStats = document.getElementById("activeContainerStats");
  elements.selectedBoxDetails = document.getElementById("selectedBoxDetails");
  elements.placementsTableBody = document.getElementById("placementsTableBody");
  elements.canvas = document.getElementById("sceneCanvas");
  elements.sceneTooltip = document.getElementById("sceneTooltip");
  elements.sceneStage = elements.canvas.parentElement;
  elements.topViewCanvas = document.getElementById("topViewCanvas");
  elements.sideViewCanvas = document.getElementById("sideViewCanvas");
  elements.sectionViewCanvas = document.getElementById("sectionViewCanvas");
}

function bindEvents() {
  elements.addContainerButton.addEventListener("click", () => addContainerRow());
  elements.addBoxButton.addEventListener("click", () => addBoxRow());
  elements.clearBoxesButton.addEventListener("click", () => clearBoxRows());
  if (elements.importBoxesButton) {
    elements.importBoxesButton.addEventListener("click", importBulkBoxes);
  }
  if (elements.exportExcelButton) {
    elements.exportExcelButton.addEventListener("click", exportExcel);
  }
  if (elements.exportHtmlButton) {
    elements.exportHtmlButton.addEventListener("click", exportHtmlReport);
  }
  elements.calculateButton.addEventListener("click", () => calculatePacking());
  elements.themeToggleButton.addEventListener("click", toggleTheme);
  elements.containerSelector.addEventListener("change", () => selectContainer(elements.containerSelector.value));
  elements.loadSampleButton.addEventListener("click", async () => {
    await loadSample();
    drawAllViews();
  });
  elements.resetViewButton.addEventListener("click", () => {
    resetView();
    drawAllViews();
  });
  elements.isometricViewButton.addEventListener("click", () => setCameraView("isometric"));
  elements.topViewButton.addEventListener("click", () => setCameraView("top"));
  elements.sideViewButton.addEventListener("click", () => setCameraView("side"));
  elements.sectionViewButton.addEventListener("click", () => setCameraView("section"));
  elements.animationPlayButton.addEventListener("click", togglePackingAnimation);
  elements.animationResetButton.addEventListener("click", resetPackingAnimation);
  elements.animationSpeedSlider.addEventListener("input", () => setAnimationSpeed(elements.animationSpeedSlider.value));
  elements.sliceSlider.addEventListener("input", () => {
    state.sliceX = Number(elements.sliceSlider.value);
    updateSliceValue();
    drawAllViews();
  });

  elements.canvas.addEventListener("pointerdown", startPointerDrag);
  elements.canvas.addEventListener("pointermove", movePointerDrag);
  elements.canvas.addEventListener("pointerup", endPointerDrag);
  elements.canvas.addEventListener("pointerleave", (event) => {
    endPointerDrag(event);
    clearHoveredScenePlacement();
  });
  elements.canvas.addEventListener("click", selectScenePlacementAtPointer);
  elements.canvas.addEventListener("dblclick", () => {
    resetView();
    drawAllViews();
  });
  elements.canvas.addEventListener("wheel", zoomScene, { passive: false });
  elements.canvas.addEventListener("contextmenu", (event) => event.preventDefault());

  elements.topViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "top"));
  elements.sideViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "side"));
  elements.sectionViewCanvas.addEventListener("click", (event) => focusProjectionCameraView(event, "section"));
}

function initializeTheme() {
  updateThemeToggle();
}

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function toggleTheme() {
  const nextTheme = currentTheme() === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
}

function applyTheme(theme) {
  if (theme === "dark") {
    document.documentElement.dataset.theme = "dark";
    try {
      localStorage.setItem(THEME_STORAGE_KEY, "dark");
    } catch {
      // Theme still changes for the current session when storage is unavailable.
    }
  } else {
    delete document.documentElement.dataset.theme;
    try {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } catch {
      // Theme still changes for the current session when storage is unavailable.
    }
  }
  updateThemeToggle();
  drawAllViews();
}

function updateThemeToggle() {
  if (!elements.themeToggleButton) {
    return;
  }
  const dark = currentTheme() === "dark";
  elements.themeToggleButton.textContent = dark ? "亮色模式" : "深色模式";
  elements.themeToggleButton.setAttribute("aria-label", dark ? "切换亮色主题" : "切换深色主题");
  elements.themeToggleButton.setAttribute("aria-pressed", String(dark));
}

async function loadSample() {
  try {
    const response = await fetch("/api/sample");
    if (!response.ok) {
      throw new Error("sample api unavailable");
    }
    state.input = normalizeInput(await readJsonResponse(response));
  } catch {
    state.input = structuredClone(fallbackInput);
  }
  writeInputToForm(state.input);
  configureSliceControl(state.input.containers[0].length);
  clearError();
}

function writeInputToForm(input) {
  const normalized = normalizeInput(input);
  elements.containerTableBody.innerHTML = "";
  normalized.containers.forEach((container) => addContainerRow(container));
  elements.boxTableBody.innerHTML = "";
  normalized.boxes.forEach((box) => addBoxRow(box));
  elements.searchModeSelect.value = normalized.search_mode;
}

async function readJsonResponse(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    if (text.trim().startsWith("<")) {
      throw new Error("接口返回了 HTML。请用 python -m cargo_loading.cli serve-profile 启动页面，不要直接打开 web/index.html 或普通静态服务器。");
    }
    throw new Error("接口返回的内容不是 JSON。");
  }
}

function normalizeInput(input) {
  if (Array.isArray(input?.containers)) {
    return {
      containers: input.containers.map((container) => ({
        id: String(container.id ?? "ULD"),
        length: Number(container.length),
        quantity: Number(container.quantity ?? 0),
        cross_section: container.cross_section.map(([y, z]) => [Number(y), Number(z)]),
      })),
      boxes: input.boxes ?? [],
      objective: input.objective ?? "maximize_volume",
      search_mode: input.search_mode ?? "balanced",
    };
  }
  if (input?.uld) {
    return {
      containers: [
        {
          id: input.uld.id,
          length: input.uld.length,
          quantity: 0,
          cross_section: input.uld.cross_section,
        },
      ],
      boxes: input.boxes ?? [],
      objective: input.objective ?? "maximize_volume",
      search_mode: input.search_mode ?? "balanced",
    };
  }
  return structuredClone(fallbackInput);
}

function addContainerRow(container = {}) {
  const row = document.createElement("tr");
  const id = container.id ?? nextAlphabeticId("ULD", ".container-id");
  const crossSection = container.cross_section ?? [
    [0, 0],
    [220, 0],
    [220, 110],
    [170, 160],
    [0, 160],
  ];
  row.innerHTML = `
    <td><input class="container-id" type="text" value="${escapeAttribute(id)}" aria-label="ULD ID" /></td>
    <td><input class="container-length" type="number" min="1" step="1" value="${container.length ?? 300}" aria-label="ULD 长度" /></td>
    <td><input class="container-quantity" type="number" min="0" step="1" value="${container.quantity ?? 0}" aria-label="ULD 数量" /></td>
    <td><textarea class="container-cross-section" rows="3" aria-label="ULD y-z 截面点">${escapeHtml(JSON.stringify(crossSection))}</textarea></td>
    <td><button class="icon-button" type="button" aria-label="删除 ULD">×</button></td>
  `;
  row.querySelector("button").addEventListener("click", () => row.remove());
  elements.containerTableBody.appendChild(row);
}

function addBoxRow(box = {}) {
  const row = document.createElement("tr");
  const id = box.id ?? nextAlphabeticId("BOX", ".box-id");
  const requiredContainerTypes = Array.isArray(box.required_container_types) ? box.required_container_types.join(", ") : "";
  row.innerHTML = `
    <td><input class="box-id" type="text" value="${escapeAttribute(id)}" aria-label="箱子 ID" /></td>
    <td><input class="box-length" type="number" min="1" step="1" value="${box.length ?? 60}" aria-label="箱子长度" /></td>
    <td><input class="box-width" type="number" min="1" step="1" value="${box.width ?? 40}" aria-label="箱子宽度" /></td>
    <td><input class="box-height" type="number" min="1" step="1" value="${box.height ?? 30}" aria-label="箱子高度" /></td>
    <td><input class="box-quantity" type="number" min="0" step="1" value="${box.quantity ?? 1}" aria-label="箱子数量" /></td>
    <td><input class="box-rotatable" type="checkbox" ${box.rotatable ?? true ? "checked" : ""} aria-label="允许长宽互换" /></td>
    <td><input class="box-required-container-types" type="text" value="${escapeAttribute(requiredContainerTypes)}" aria-label="指定 ULD 类型" /></td>
    <td><button class="icon-button" type="button" aria-label="删除箱子">×</button></td>
  `;
  row.querySelector("button").addEventListener("click", () => row.remove());
  elements.boxTableBody.appendChild(row);
}

function importBulkBoxes() {
  try {
    clearError();
    if (!elements.bulkBoxInput) {
      throw new Error("批量粘贴入口不可用");
    }
    const boxes = parseBulkBoxLines(elements.bulkBoxInput.value);
    boxes.forEach((box) => addBoxRow(box));
    elements.bulkBoxInput.value = "";
  } catch (error) {
    showError(error.message);
  }
}

function clearBoxRows(tableBody = elements.boxTableBody) {
  tableBody.innerHTML = "";
  if (elements.errorMessage) {
    clearError();
  }
}

function parseBulkBoxLines(rawValue) {
  const boxes = String(rawValue)
    .split(/\r\n|\n|\r/)
    .map((line, index) => parseBulkBoxLine(line, index))
    .filter(Boolean);
  if (boxes.length === 0) {
    throw new Error(`请先粘贴箱子尺寸，格式为：${BULK_BOX_EXAMPLE.split("\n")[0]}`);
  }
  return boxes;
}

function parseBulkBoxLine(rawLine, index) {
  const line = rawLine.trim();
  if (!line) {
    return null;
  }
  const parts = line.split(/[\s*＊×xXｘＸ✕✖⨯]+/).filter(Boolean);
  if (parts.length !== 4) {
    throw new Error(`第 ${index + 1} 行格式应为：长*宽*高*数量`);
  }
  const [length, width, height, quantity] = parts;
  return {
    length: readPositiveNumber(length, `第 ${index + 1} 行长度`),
    width: readPositiveNumber(width, `第 ${index + 1} 行宽度`),
    height: readPositiveNumber(height, `第 ${index + 1} 行高度`),
    quantity: readNonNegativeInteger(quantity, `第 ${index + 1} 行数量`),
    rotatable: true,
  };
}

function exportExcel() {
  try {
    clearError();
    if (!state.result) {
      throw new Error("请先计算装箱结果后再导出 Excel");
    }
    downloadExcelWorkbook(buildExcelWorkbook(state.result, state.input), buildExcelFileName(state.result, currentExportCreatedAt()));
  } catch (error) {
    showError(error.message);
  }
}

function exportHtmlReport() {
  try {
    clearError();
    if (!state.result) {
      throw new Error("请先计算装箱结果后再导出 HTML");
    }
    downloadHtmlReport(buildHtmlReport(state.result, state.input, currentExportCreatedAt()), buildHtmlFileName(state.result, currentExportCreatedAt()));
  } catch (error) {
    showError(error.message);
  }
}

function buildExcelWorkbook(result, input = null) {
  return buildXlsxWorkbook(buildWorkbookSheets(result, input));
}

function buildHtmlFileName(result, createdAt) {
  return `${formatExportTimestamp(createdAt)}-装载率${formatExportUtilization(result?.volume_utilization)}.html`;
}

function buildExcelFileName(result, createdAt) {
  return `${formatExportTimestamp(createdAt)}-装载率${formatExportUtilization(result?.volume_utilization)}.xlsx`;
}

function currentExportCreatedAt() {
  const record = state.historyRecords.find((item) => item.id === state.selectedHistoryId);
  return record?.createdAt ?? new Date().toISOString();
}

const EXPORT_FILE_TIMEZONE_OFFSET_MINUTES = 8 * 60;

function formatExportTimestamp(value) {
  const date = new Date(value);
  const validDate = Number.isNaN(date.getTime()) ? new Date() : date;
  const exportDate = new Date(validDate.getTime() + EXPORT_FILE_TIMEZONE_OFFSET_MINUTES * 60 * 1000);
  const parts = [
    exportDate.getUTCFullYear(),
    String(exportDate.getUTCMonth() + 1).padStart(2, "0"),
    String(exportDate.getUTCDate()).padStart(2, "0"),
    String(exportDate.getUTCHours()).padStart(2, "0"),
    String(exportDate.getUTCMinutes()).padStart(2, "0"),
    String(exportDate.getUTCSeconds()).padStart(2, "0"),
  ];
  return `${parts[0]}${parts[1]}${parts[2]}-${parts[3]}${parts[4]}${parts[5]}`;
}

function formatExportUtilization(value) {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

const HTML_REPORT_SVG_WIDTH = 680;
const HTML_REPORT_SVG_HEIGHT = 320;

function buildHtmlReport(result, input = null, createdAt = new Date().toISOString()) {
  const containers = resultContainersForExport(result);
  const exportInput = input ? normalizeInput(input) : { containers: [], boxes: [] };
  const inputBoxById = new Map((exportInput.boxes ?? []).map((box) => [box.id, box]));
  const reportSceneData = buildHtmlReportSceneData(containers, exportInput);
  const sheets = buildWorkbookSheets(result, exportInput);
  const sheetPages = sheets.map((sheet, index) => ({
    id: htmlSheetId(index),
    name: sheet.name,
    active: index === 0,
    content:
      sheet.name === "ULD 可视化"
        ? buildHtmlVisualizationSheetPage(containers, exportInput, inputBoxById)
        : buildHtmlWorkbookSheetContent(sheet),
  }));

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ULD 装载报告</title>
  <style>${htmlReportStyles()}</style>
</head>
<body>
  <main class="report">
    <header class="report-header">
      <div>
        <p class="kicker">ULD Packing Report</p>
        <h1>ULD 装载报告</h1>
        <p class="meta">导出时间 ${escapeHtml(formatHtmlDateTime(createdAt))}</p>
      </div>
      <div class="status ${result.validation_passed ? "passed" : "failed"}">${result.validation_passed ? "校验通过" : "校验失败"}</div>
    </header>

    <nav class="sheet-tabs" aria-label="报告分页">
      ${sheetPages
        .map((page) => `<button class="sheet-tab${page.active ? " active" : ""}" type="button" data-target="${page.id}">${escapeHtml(page.name)}</button>`)
        .join("")}
    </nav>

    <div class="sheet-pages">
      ${sheetPages
        .map(
          (page) => `<section id="${page.id}" class="sheet-page${page.active ? " active" : ""}" data-sheet-name="${escapeHtml(page.name)}">
        <h2>${escapeHtml(page.name)}</h2>
        ${page.content}
      </section>`,
        )
        .join("\n")}
    </div>
  </main>
  <script>${htmlReportScript(reportSceneData)}</script>
</body>
</html>`;
}

function htmlSheetId(index) {
  return `sheet-${index + 1}`;
}

function buildHtmlWorkbookSheetContent(sheet) {
  return `<div class="table-wrap"><table><tbody>${sheet.rows
    .map((row, rowIndex) => {
      const tag = rowIndex === 0 ? "th" : "td";
      return `<tr>${row.map((cell) => `<${tag}>${htmlCellContent(cell)}</${tag}>`).join("")}</tr>`;
    })
    .join("")}</tbody></table></div>`;
}

function buildHtmlVisualizationSheetPage(containers, exportInput, inputBoxById) {
  const profileById = new Map((exportInput.containers ?? []).map((container) => [container.id, container]));
  return `<div class="visualization-toolbar">
    <label>查看 ULD
      <select data-uld-filter>
        <option value="">全部 ULD</option>
        ${containers
          .map((container) => {
            const containerId = container.container_id ?? container.uld_id ?? "";
            return `<option value="${escapeAttribute(containerId)}">${escapeHtml(containerId)}</option>`;
          })
          .join("")}
      </select>
    </label>
  </div>
  <div class="visualization-pages">${containers
    .map((container) => buildHtmlReportContainerSection(container, htmlReportProfileInput(container, profileById.get(container.container_type)), inputBoxById))
    .join("\n")}</div>`;
}

function buildHtmlReportContainerSection(container, profileInput, inputBoxById) {
  const containerId = container.container_id ?? container.uld_id ?? "";
  const placements = container.placements ?? [];
  return `<article class="uld-section" data-uld-section="${escapeAttribute(containerId)}">
    <div class="section-title">
      <h2>ULD ${escapeHtml(containerId)}</h2>
      <div class="section-meta">
        <span>类型 ${escapeHtml(container.container_type ?? container.uld_id ?? "")}</span>
        <span>已装 ${escapeHtml(container.loaded_count ?? placements.length)}</span>
        <span>装载率 ${escapeHtml(formatPercent(container.volume_utilization))}</span>
        <span>已用体积 ${escapeHtml(formatNumber(container.used_volume ?? 0))}</span>
      </div>
    </div>
    <div class="load-summary">
      <h3>装载清单</h3>
      ${htmlSummaryList(htmlPlacementTypeSummaries(placements).map((summary) => [summary, ""]), "暂无已装箱")}
    </div>
    <div class="top-views-grid">
      <article class="view-card">
        <div class="view-card-heading">
          <h3>俯视位置图</h3>
          ${placements.length ? `<button class="position-map-label-toggle" type="button" data-position-label-toggle aria-pressed="true">隐藏标识</button>` : ""}
        </div>
        ${buildHtmlTopPositionMap(placements, profileInput)}
      </article>
      ${buildHtmlTopProjectionCanvas(containerId)}
    </div>
    <div class="scene-row">
      ${buildHtmlInteractiveSceneCanvas(containerId)}
    </div>
    <h3>本 ULD 坐标</h3>
    ${htmlTable(
      ["实例", "箱子 ID", "尺寸", "x", "y", "z"],
      placements.map((placement) => [
        placement.instance_id,
        htmlBoxLabel(placement, inputBoxById),
        htmlPlacementDimensions(placement),
        `${formatNumber(placement.x)} ~ ${formatNumber(placement.x + placement.length)}`,
        `${formatNumber(placement.y)} ~ ${formatNumber(placement.y + placement.width)}`,
        `${formatNumber(placement.z)} ~ ${formatNumber(placement.z + placement.height)}`,
      ]),
    )}
  </article>`;
}

function buildHtmlTopProjectionCanvas(containerId) {
  return `<article class="view-card">
    <div class="view-card-heading">
      <h3>3D 俯视图</h3>
    </div>
    <canvas class="projection-canvas" data-report-top-view="${escapeAttribute(containerId)}" width="680" height="320" aria-label="${escapeAttribute(containerId)} 3D 俯视图"></canvas>
  </article>`;
}

function buildHtmlInteractiveSceneCanvas(containerId) {
  return `<article class="view-card">
    <h3>交互 3D 视图</h3>
    <div class="scene-view-controls" aria-label="3D 视图控制">
      <button type="button" data-scene-view="isometric">等轴</button>
      <button type="button" data-scene-view="top">俯视</button>
      <button type="button" data-scene-view="side">侧视</button>
      <button type="button" data-scene-view="section">截面</button>
      <button type="button" data-scene-reset>重置</button>
    </div>
    <div class="report-scene-stage">
      <canvas class="scene-canvas" data-report-scene="${escapeAttribute(containerId)}" width="960" height="540" aria-label="${escapeAttribute(containerId)} 交互 3D 视图"></canvas>
      <div class="scene-tooltip" data-report-tooltip role="status" aria-label="悬停箱子信息"></div>
    </div>
    <div class="scene-selection muted" data-report-selection>点击 3D 视图中的箱子查看位置范围。</div>
  </article>`;
}

function buildHtmlReportSceneData(containers, exportInput) {
  const profileById = new Map((exportInput.containers ?? []).map((container) => [container.id, container]));
  return containers.map((container) => {
    const containerId = container.container_id ?? container.uld_id ?? "";
    const profileInput = htmlReportProfileInput(container, profileById.get(container.container_type));
    const dimensions = getSceneDimensions(profileInput);
    return {
      id: containerId,
      dimensions,
      crossSection: profileInput.uld.cross_section,
      placements: (container.placements ?? []).map((placement) => ({
        box_id: placement.box_id,
        instance_id: placement.instance_id,
        x: Number(placement.x),
        y: Number(placement.y),
        z: Number(placement.z),
        length: Number(placement.length),
        width: Number(placement.width),
        height: Number(placement.height),
      })),
    };
  });
}

function buildHtmlProjectionSvg(container, profileInput, viewKey) {
  const placements = container.placements ?? [];
  const dimensions = getSceneDimensions(profileInput);
  const config = htmlProjectionConfig(viewKey, dimensions);
  const mapper = createPlaneMapper({ width: HTML_REPORT_SVG_WIDTH, height: HTML_REPORT_SVG_HEIGHT }, config.worldWidth, config.worldHeight, config.horizontalAxis, config.verticalAxis);
  const frame = viewKey === "section"
    ? htmlSectionPolygon(profileInput.uld.cross_section, mapper)
    : htmlSvgRect(mapper.rectToScreen(0, 0, config.worldWidth, config.worldHeight), "uld-frame", "", "none");
  const boxes = placements.map((placement) => htmlPlacementRect(placement, mapper, viewKey)).join("\n");
  return `<article class="view-card">
    <h3>${escapeHtml(config.title)}</h3>
    <svg viewBox="0 0 ${HTML_REPORT_SVG_WIDTH} ${HTML_REPORT_SVG_HEIGHT}" role="img" aria-label="${escapeXmlAttribute(config.title)}">
      <rect class="svg-bg" x="0" y="0" width="${HTML_REPORT_SVG_WIDTH}" height="${HTML_REPORT_SVG_HEIGHT}" rx="10"></rect>
      ${htmlGridLines(mapper, config.worldWidth, config.worldHeight)}
      ${frame}
      ${boxes}
      <text class="axis-label" x="${HTML_REPORT_SVG_WIDTH - 86}" y="${HTML_REPORT_SVG_HEIGHT - 14}">${escapeXmlText(config.horizontalLabel)}</text>
      <text class="axis-label" x="16" y="24">${escapeXmlText(config.verticalLabel)}</text>
    </svg>
  </article>`;
}

function buildHtmlTopPositionMap(placements, profileInput = null) {
  if (!placements.length) {
    return `<p class="muted">暂无已装箱</p>`;
  }
  const dimensions = profileInput ? getSceneDimensions(profileInput) : htmlTopMapFallbackDimensions(placements);
  const mapper = createPlaneMapper({ width: HTML_REPORT_SVG_WIDTH, height: HTML_REPORT_SVG_HEIGHT }, dimensions.length, dimensions.maxY, "x", "y");
  const piles = buildHtmlTopPositionPiles(placements);
  const pileItems = piles.map((pile, index) => htmlTopPositionPileSvg(pile, mapper, index));
  const pileRects = pileItems.map((item) => item.rect).join("\n");
  const pileLabels = pileItems.map((item) => item.label).join("\n");
  return `<div class="position-map-svg-wrap">
    <svg class="position-map-svg" data-position-map viewBox="0 0 ${HTML_REPORT_SVG_WIDTH} ${HTML_REPORT_SVG_HEIGHT}" role="img" aria-label="按实际 x/y 坐标绘制的俯视位置图">
      <rect class="svg-bg" x="0" y="0" width="${HTML_REPORT_SVG_WIDTH}" height="${HTML_REPORT_SVG_HEIGHT}" rx="10"></rect>
      ${htmlGridLines(mapper, dimensions.length, dimensions.maxY)}
      ${htmlSvgRect(mapper.rectToScreen(0, 0, dimensions.length, dimensions.maxY), "uld-frame", "", "none")}
      <g class="position-pile-layer">
        ${pileRects}
      </g>
      <g class="position-pile-label-layer">
        ${pileLabels}
      </g>
      <text class="axis-label" x="${HTML_REPORT_SVG_WIDTH - 86}" y="${HTML_REPORT_SVG_HEIGHT - 14}">x 长度</text>
      <text class="axis-label" x="16" y="24">y 宽度</text>
    </svg>
  </div>`;
}

function htmlTopMapFallbackDimensions(placements) {
  return {
    length: Math.max(1, ...placements.map((placement) => Number(placement.x) + Number(placement.length))),
    maxY: Math.max(1, ...placements.map((placement) => Number(placement.y) + Number(placement.width))),
  };
}

function parseRequiredContainerTypes(rawValue) {
  return String(rawValue)
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildHtmlTopPositionPiles(placements) {
  const piles = [];
  const normalizedPlacements = placements.map((placement) => ({
    ...placement,
    x: Number(placement.x),
    y: Number(placement.y),
    z: Number(placement.z),
    length: Number(placement.length),
    width: Number(placement.width),
    height: Number(placement.height),
  }));
  normalizedPlacements.forEach((placement) => {
    const overlappingPiles = piles.filter((pile) => pile.placements.some((item) => placementFootprintsOverlap(placement, item)));
    const targetPile = overlappingPiles[0] ?? createPlacementStack(placement);
    overlappingPiles.slice(1).forEach((pile) => {
      targetPile.placements.push(...pile.placements);
      targetPile.minX = Math.min(targetPile.minX, pile.minX);
      targetPile.maxX = Math.max(targetPile.maxX, pile.maxX);
      targetPile.minY = Math.min(targetPile.minY, pile.minY);
      targetPile.maxY = Math.max(targetPile.maxY, pile.maxY);
      piles.splice(piles.indexOf(pile), 1);
    });
    if (overlappingPiles.length === 0) {
      piles.push(targetPile);
    }
    targetPile.placements.push(placement);
    targetPile.minX = Math.min(targetPile.minX, placement.x);
    targetPile.maxX = Math.max(targetPile.maxX, placement.x + placement.length);
    targetPile.minY = Math.min(targetPile.minY, placement.y);
    targetPile.maxY = Math.max(targetPile.maxY, placement.y + placement.width);
  });
  return piles.sort((first, second) => first.minY - second.minY || first.minX - second.minX);
}

function htmlTopPositionPileSvg(pile, mapper, index) {
  const pileRect = mapper.rectToScreen(pile.minX, pile.minY, pile.maxX - pile.minX, pile.maxY - pile.minY);
  const placements = htmlTopPilePlacementsTopDown(pile.placements);
  const footprintRects = htmlTopPileFootprints(placements).map((footprint) => ({
    footprint,
    rect: mapper.rectToScreen(footprint.x, footprint.y, footprint.length, footprint.width),
  }));
  const color = colorForBox(placements[0]?.box_id ?? "");
  const labelLines = htmlTopPileLayerTypeSummariesTopDown(placements);
  const title = [
    `摞 ${index + 1}`,
    `x ${formatNumber(pile.minX)}-${formatNumber(pile.maxX)}`,
    `y ${formatNumber(pile.minY)}-${formatNumber(pile.maxY)}`,
    ...labelLines,
  ].join("\n");
  const text = htmlTopPileText(htmlTopPileLabelRect(footprintRects, pileRect), labelLines);
  const attributes = `data-pile-index="${index + 1}" data-pile-count="${placements.length}" data-pile-x="${escapeXmlAttribute(formatNumber(pile.minX))}" data-pile-y="${escapeXmlAttribute(formatNumber(pile.minY))}" data-pile-width="${escapeXmlAttribute(formatNumber(pile.maxX - pile.minX))}" data-pile-height="${escapeXmlAttribute(formatNumber(pile.maxY - pile.minY))}" data-pile-members="${escapeXmlAttribute(placements.map((placement) => placement.instance_id).join(","))}" data-placement-x="${escapeXmlAttribute(formatNumber(placements[0]?.x ?? pile.minX))}" data-placement-y="${escapeXmlAttribute(formatNumber(placements[0]?.y ?? pile.minY))}" data-placement-z="${escapeXmlAttribute(formatNumber(placements[0]?.z ?? 0))}"`;
  const actionLabel = `选中摞 ${index + 1}，${placements.length} 个箱子，x ${formatNumber(pile.minX)}-${formatNumber(pile.maxX)}，y ${formatNumber(pile.minY)}-${formatNumber(pile.maxY)}`;
  const footprintSvg = footprintRects.map(({ footprint, rect }) => `<rect class="position-pile-rect position-pile-footprint" data-footprint-x="${escapeXmlAttribute(formatNumber(footprint.x))}" data-footprint-y="${escapeXmlAttribute(formatNumber(footprint.y))}" data-footprint-width="${escapeXmlAttribute(formatNumber(footprint.length))}" data-footprint-height="${escapeXmlAttribute(formatNumber(footprint.width))}" data-footprint-count="${footprint.count}" x="${formatSvgNumber(rect.x)}" y="${formatSvgNumber(rect.y)}" width="${formatSvgNumber(rect.width)}" height="${formatSvgNumber(rect.height)}" fill="${rgbaColor(color, 0.68)}" stroke="${rgbaColor(lightenColor(color, 0.38), 0.98)}"></rect>`).join("\n    ");
  return {
    rect: `<g class="position-pile" ${attributes} role="button" tabindex="0" aria-label="${escapeXmlAttribute(actionLabel)}">
    <title>${escapeXmlText(title)}</title>
    ${footprintSvg}
  </g>`,
    label: `<g class="position-pile-label-item" ${attributes}>
    ${text}
  </g>`,
  };
}

function htmlTopPileFootprints(placements) {
  const footprintsByKey = new Map();
  placements.forEach((placement) => {
    const footprint = {
      x: Number(placement.x),
      y: Number(placement.y),
      length: Number(placement.length),
      width: Number(placement.width),
    };
    const key = [footprint.x, footprint.y, footprint.length, footprint.width].map(formatNumber).join("|");
    const existing = footprintsByKey.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      footprintsByKey.set(key, { ...footprint, count: 1 });
    }
  });
  return [...footprintsByKey.values()].sort((first, second) =>
    second.length * second.width - first.length * first.width
    || first.y - second.y
    || first.x - second.x
    || first.length - second.length
    || first.width - second.width);
}

function htmlTopPileLabelRect(footprintRects, fallbackRect) {
  return footprintRects.reduce((largest, current) => {
    const largestArea = largest.width * largest.height;
    const currentArea = current.rect.width * current.rect.height;
    return currentArea > largestArea ? current.rect : largest;
  }, fallbackRect);
}

function htmlTopPilePlacementsTopDown(placements) {
  return [...placements].sort((first, second) => (Number(second.z) + Number(second.height)) - (Number(first.z) + Number(first.height)) || Number(second.z) - Number(first.z));
}

function htmlTopPileLayerTypeSummariesTopDown(placements) {
  const byTop = new Map();
  placements.forEach((placement) => {
    const layerTop = Number(placement.z) + Number(placement.height);
    const layer = byTop.get(layerTop) ?? [];
    layer.push(placement);
    byTop.set(layerTop, layer);
  });
  return [...byTop.entries()]
    .sort((first, second) => second[0] - first[0])
    .flatMap(([, layer]) => htmlPlacementTypeSummaries(layer));
}

function htmlTopPileText(rect, lines) {
  if (rect.width < 54 || rect.height < 24 || lines.length === 0) {
    return "";
  }
  const maxLines = Math.max(1, Math.floor((rect.height - 10) / 14));
  const visibleLines = lines.slice(0, maxLines);
  const renderedLines = visibleLines.length < lines.length
    ? [...visibleLines.slice(0, Math.max(0, maxLines - 1)), `+${lines.length - visibleLines.length + 1}`]
    : visibleLines;
  const labelWidth = Math.min(rect.width - 8, Math.max(...renderedLines.map((line) => line.length)) * 7.2 + 10);
  const labelHeight = renderedLines.length * 14 + 8;
  const labelX = rect.x + 4;
  const labelY = rect.y + 5;
  return `<rect class="position-pile-label-bg" x="${formatSvgNumber(labelX)}" y="${formatSvgNumber(labelY)}" width="${formatSvgNumber(labelWidth)}" height="${formatSvgNumber(labelHeight)}" rx="4"></rect>
  <text class="position-pile-label" x="${formatSvgNumber(rect.x + 8)}" y="${formatSvgNumber(rect.y + 19)}">${renderedLines
    .map((line, index) => `<tspan x="${formatSvgNumber(rect.x + 8)}" dy="${index === 0 ? 0 : 14}">${escapeXmlText(line)}</tspan>`)
    .join("")}</text>`;
}

function htmlProjectionConfig(viewKey, dimensions) {
  if (viewKey === "top") {
    return { title: "俯视 X-Y", worldWidth: dimensions.length, worldHeight: dimensions.maxY, horizontalAxis: "x", verticalAxis: "y", horizontalLabel: "x 长度", verticalLabel: "y 宽度" };
  }
  if (viewKey === "side") {
    return { title: "侧视 X-Z", worldWidth: dimensions.length, worldHeight: dimensions.maxZ, horizontalAxis: "x", verticalAxis: "z", horizontalLabel: "x 长度", verticalLabel: "z 高度" };
  }
  return { title: "截面 Y-Z", worldWidth: dimensions.maxY, worldHeight: dimensions.maxZ, horizontalAxis: "y", verticalAxis: "z", horizontalLabel: "y 宽度", verticalLabel: "z 高度" };
}

function htmlReportProfileInput(container, profile) {
  if (profile?.length && Array.isArray(profile.cross_section)) {
    return {
      uld: {
        id: profile.id ?? container.container_type ?? container.container_id ?? "ULD",
        length: Number(profile.length),
        cross_section: profile.cross_section,
      },
    };
  }
  const placements = container.placements ?? [];
  const length = Math.max(1, ...placements.map((placement) => Number(placement.x) + Number(placement.length)));
  const maxY = Math.max(1, ...placements.map((placement) => Number(placement.y) + Number(placement.width)));
  const maxZ = Math.max(1, ...placements.map((placement) => Number(placement.z) + Number(placement.height)));
  return {
    uld: {
      id: container.container_id ?? container.uld_id ?? "ULD",
      length,
      cross_section: [[0, 0], [maxY, 0], [maxY, maxZ], [0, maxZ]],
    },
  };
}

function htmlPlacementRect(placement, mapper, viewKey) {
  const rect = projectionRectForPlacement(mapper, placement, viewKey);
  const color = colorForBox(placement.box_id);
  const label = rect.width >= 52 && rect.height >= 20
    ? `<text class="box-label" x="${rect.x + 5}" y="${rect.y + 15}">${escapeXmlText(placement.box_id)}</text>`
    : "";
  return `${htmlSvgRect(
    rect,
    "box-rect",
    `fill="${rgbaColor(color, 0.7)}" stroke="${rgbaColor(lightenColor(color, 0.38), 0.98)}" data-instance-id="${escapeXmlAttribute(placement.instance_id ?? "")}" data-placement-x="${escapeXmlAttribute(formatNumber(placement.x))}" data-placement-y="${escapeXmlAttribute(formatNumber(placement.y))}" data-placement-z="${escapeXmlAttribute(formatNumber(placement.z))}"`,
    "",
  )}${label}`;
}

function htmlSvgRect(rect, className, extraAttributes, fallbackFill) {
  const fill = fallbackFill ? ` fill="${fallbackFill}"` : "";
  return `<rect class="${className}" x="${formatSvgNumber(rect.x)}" y="${formatSvgNumber(rect.y)}" width="${formatSvgNumber(rect.width)}" height="${formatSvgNumber(rect.height)}"${fill} ${extraAttributes}></rect>`;
}

function htmlSectionPolygon(points, mapper) {
  const polygonPoints = points
    .map(([y, z]) => {
      const point = mapper.toScreen(y, z);
      return `${formatSvgNumber(point.x)},${formatSvgNumber(point.y)}`;
    })
    .join(" ");
  return `<polygon class="uld-frame" points="${polygonPoints}"></polygon>`;
}

function htmlGridLines(mapper, worldWidth, worldHeight) {
  const xStep = htmlGridStep(worldWidth);
  const yStep = htmlGridStep(worldHeight);
  const lines = [];
  for (let x = 0; x <= worldWidth; x += xStep) {
    const start = mapper.toScreen(x, 0);
    const end = mapper.toScreen(x, worldHeight);
    lines.push(`<line class="grid-line" x1="${formatSvgNumber(start.x)}" y1="${formatSvgNumber(start.y)}" x2="${formatSvgNumber(end.x)}" y2="${formatSvgNumber(end.y)}"></line>`);
  }
  for (let y = 0; y <= worldHeight; y += yStep) {
    const start = mapper.toScreen(0, y);
    const end = mapper.toScreen(worldWidth, y);
    lines.push(`<line class="grid-line" x1="${formatSvgNumber(start.x)}" y1="${formatSvgNumber(start.y)}" x2="${formatSvgNumber(end.x)}" y2="${formatSvgNumber(end.y)}"></line>`);
  }
  return lines.join("\n");
}

function htmlGridStep(value) {
  const target = Math.max(1, Number(value) / 6);
  const magnitude = 10 ** Math.floor(Math.log10(target));
  const normalized = target / magnitude;
  if (normalized <= 2) {
    return 2 * magnitude;
  }
  if (normalized <= 5) {
    return 5 * magnitude;
  }
  return 10 * magnitude;
}

function htmlMetricCard(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function htmlCellContent(cell) {
  return escapeHtml(excelCellValue(cell)).replace(/\r\n|\r|\n/g, "<br>");
}

function htmlSummaryList(items, emptyText) {
  if (!items.length) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `<div class="chip-list">${items
    .map(([label, value]) => `<span class="chip">${escapeHtml(label)}${value !== "" ? ` <strong>${escapeHtml(value)}</strong>` : ""}</span>`)
    .join("")}</div>`;
}

function htmlPlacementTypeSummaries(placements) {
  const counter = new Map();
  placements.forEach((placement) => {
    const size = [placement.length, placement.width, placement.height].map(formatNumber).join("*");
    const key = `${placement.box_id}（${size}）`;
    counter.set(key, (counter.get(key) ?? 0) + 1);
  });
  return [...counter.entries()].map(([label, quantity]) => `${label}*${quantity}`);
}

function htmlTable(headers, rows) {
  if (!rows.length) {
    return `<p class="muted">暂无</p>`;
  }
  return `<div class="table-wrap"><table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}

function htmlBoxLabel(item, inputBoxById) {
  const dimensions = boxItemDimensions(item, inputBoxById.get(item.box_id));
  return dimensions ? `${item.box_id} (${dimensions})` : item.box_id;
}

function htmlPlacementDimensions(placement) {
  return [placement.length, placement.width, placement.height].map(formatNumber).join(" × ");
}

function formatSvgNumber(value) {
  return Number(value).toFixed(2).replace(/\.?0+$/, "");
}

function formatHtmlDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value ?? "") : date.toLocaleString("zh-CN", { hour12: false });
}

function safeJsonForHtmlScript(value) {
  return JSON.stringify(value)
    .replaceAll("<", "\\u003c")
    .replaceAll(">", "\\u003e")
    .replaceAll("&", "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

function htmlReportScript(reportSceneData = []) {
  return `
    (() => {
      const reportSceneData = ${safeJsonForHtmlScript(reportSceneData)};
      const HTML_REPORT_AXIS_EXTENSION_FACTOR = 1.18;
      const HTML_REPORT_SCENE_SAFE_PADDING = 72;
      const tabs = [...document.querySelectorAll(".sheet-tab")];
      const pages = [...document.querySelectorAll(".sheet-page")];
      const sceneById = new Map(reportSceneData.map((scene) => [scene.id, scene]));
      const sceneStateById = new Map();
      const activate = (id) => {
        tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.target === id));
        pages.forEach((page) => page.classList.toggle("active", page.id === id));
        redrawHtmlReportVisibleScenes();
      };
      tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab.dataset.target)));
      const uldFilter = document.querySelector("[data-uld-filter]");
      const uldSections = [...document.querySelectorAll("[data-uld-section]")];
      if (uldFilter) {
        uldFilter.addEventListener("change", () => {
          const selected = uldFilter.value;
          uldSections.forEach((section) => {
            section.hidden = selected !== "" && section.dataset.uldSection !== selected;
          });
          redrawHtmlReportVisibleScenes();
        });
      }
      document.querySelectorAll("[data-report-scene]").forEach((canvas) => initHtmlReportScene(canvas, stateForHtmlReportScene(sceneById.get(canvas.dataset.reportScene))));
      document.querySelectorAll("[data-report-top-view]").forEach((canvas) => initHtmlReportTopView(canvas, stateForHtmlReportScene(sceneById.get(canvas.dataset.reportTopView))));
      document.querySelectorAll("[data-position-map]").forEach(initHtmlReportPositionMap);
      document.querySelectorAll("[data-position-label-toggle]").forEach(initHtmlReportPositionMapLabelToggle);
      if (location.hash) {
        const id = location.hash.slice(1);
        if (pages.some((page) => page.id === id)) {
          activate(id);
        }
      }

      function stateForHtmlReportScene(scene) {
        if (!scene) {
          return null;
        }
        let state = sceneStateById.get(scene.id);
        if (!state) {
          state = {
            scene,
            yaw: -0.72,
            pitch: 0.58,
            zoom: 1,
            panX: 0,
            panY: 10,
            pointer: null,
            hitRegions: [],
            topHitRegions: [],
            hoveredInstanceId: null,
            selectedInstanceId: null,
            sceneCanvas: null,
            topCanvas: null,
            tooltip: null,
            selection: null,
          };
          sceneStateById.set(scene.id, state);
        }
        return state;
      }

      function redrawHtmlReportVisibleScenes() {
        sceneStateById.forEach((state) => redrawHtmlReportSceneState(state));
      }

      function redrawHtmlReportSceneState(state) {
        if (state.sceneCanvas) {
          drawHtmlReportScene(state.sceneCanvas, state.scene, state);
        }
        if (state.topCanvas) {
          drawHtmlReportTopProjection(state.topCanvas, state);
        }
        renderHtmlReportSceneSelection(state);
      }

      function initHtmlReportScene(canvas, state) {
        if (!state || !canvas.getContext) {
          return;
        }
        state.sceneCanvas = canvas;
        const draw = () => redrawHtmlReportSceneState(state);
        const viewCard = canvas.closest(".view-card");
        state.tooltip = viewCard?.querySelector("[data-report-tooltip]") ?? null;
        state.selection = viewCard?.querySelector("[data-report-selection]") ?? null;
        viewCard?.querySelectorAll("[data-scene-view]").forEach((button) => {
          button.addEventListener("click", () => {
            setHtmlReportSceneView(state, button.dataset.sceneView);
            draw();
          });
        });
        viewCard?.querySelector("[data-scene-reset]")?.addEventListener("click", () => {
          resetHtmlReportSceneView(state);
          draw();
        });
        canvas.addEventListener("pointerdown", (event) => {
          state.pointer = { x: event.clientX, y: event.clientY, mode: event.shiftKey || event.button === 2 ? "pan" : "rotate", moved: false };
          hideHtmlReportSceneTooltip(state);
          canvas.setPointerCapture?.(event.pointerId);
        });
        canvas.addEventListener("pointermove", (event) => {
          if (!state.pointer) {
            updateHtmlReportSceneHover(state, event);
            return;
          }
          const dx = event.clientX - state.pointer.x;
          const dy = event.clientY - state.pointer.y;
          state.pointer.x = event.clientX;
          state.pointer.y = event.clientY;
          if (Math.abs(dx) + Math.abs(dy) > 2) {
            state.pointer.moved = true;
          }
          if (state.pointer.mode === "pan") {
            state.panX += dx;
            state.panY += dy;
          } else {
            state.yaw += dx * 0.008;
            state.pitch += dy * 0.008;
          }
          draw();
        });
        const endPointer = (event) => {
          const pointer = state.pointer;
          if (state.pointer && event?.pointerId !== undefined) {
            canvas.releasePointerCapture?.(event.pointerId);
          }
          if (pointer && !pointer.moved && event?.type === "pointerup") {
            selectHtmlReportScenePlacement(state, event);
          }
          state.pointer = null;
        };
        canvas.addEventListener("pointerup", endPointer);
        canvas.addEventListener("pointerleave", (event) => {
          endPointer(event);
          clearHtmlReportSceneHover(state);
        });
        canvas.addEventListener("contextmenu", (event) => event.preventDefault());
        canvas.addEventListener("wheel", (event) => {
          event.preventDefault();
          state.zoom = Math.max(0.25, Math.min(4, state.zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
          draw();
        }, { passive: false });
        canvas.addEventListener("dblclick", () => {
          resetHtmlReportSceneView(state);
          draw();
        });
        window.addEventListener("resize", draw);
        draw();
      }

      function initHtmlReportTopView(canvas, state) {
        if (!state || !canvas.getContext) {
          return;
        }
        state.topCanvas = canvas;
        canvas.addEventListener("click", (event) => selectHtmlReportTopPlacement(state, event));
        window.addEventListener("resize", () => redrawHtmlReportSceneState(state));
        redrawHtmlReportSceneState(state);
      }

      function initHtmlReportPositionMap(svg) {
        svg.querySelectorAll(".position-pile").forEach((pile) => {
          pile.setAttribute("aria-pressed", "false");
          const selectPile = () => selectHtmlReportPositionPile(svg, pile.dataset.pileIndex);
          pile.addEventListener("click", selectPile);
          pile.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              selectPile();
            }
          });
        });
      }

      function initHtmlReportPositionMapLabelToggle(button) {
        const viewCard = button.closest(".view-card");
        const svg = viewCard?.querySelector("[data-position-map]");
        if (!svg) {
          return;
        }
        let labelsVisible = true;
        const sync = () => {
          svg.classList.toggle("position-map-label-hidden", !labelsVisible);
          button.setAttribute("aria-pressed", labelsVisible ? "true" : "false");
          button.textContent = labelsVisible ? "隐藏标识" : "显示标识";
        };
        button.addEventListener("click", () => {
          labelsVisible = !labelsVisible;
          sync();
        });
        sync();
      }

      function selectHtmlReportPositionPile(svg, pileIndex) {
        const selectedPileIndex = String(pileIndex ?? "");
        svg.querySelectorAll("[data-pile-index]").forEach((node) => {
          const isSelected = node.dataset.pileIndex === selectedPileIndex;
          node.classList.toggle("selected", isSelected);
          if (node.classList.contains("position-pile")) {
            node.setAttribute("aria-pressed", isSelected ? "true" : "false");
          }
        });
      }

      function setHtmlReportSceneView(state, view) {
        const views = {
          isometric: { yaw: -0.72, pitch: 0.58 },
          top: { yaw: 0, pitch: 1.5708 },
          side: { yaw: 0, pitch: 0 },
          section: { yaw: -1.5708, pitch: 0 },
        };
        const next = views[view] ?? views.isometric;
        state.yaw = next.yaw;
        state.pitch = next.pitch;
        state.panX = 0;
        state.panY = 10;
      }

      function resetHtmlReportSceneView(state) {
        state.yaw = -0.72;
        state.pitch = 0.58;
        state.zoom = 1;
        state.panX = 0;
        state.panY = 10;
      }

      function drawHtmlReportScene(canvas, scene, state) {
        const { context, width, height } = setupHtmlReportCanvas(canvas);
        state.hitRegions = [];
        context.clearRect(0, 0, width, height);
        const viewport = htmlReportSceneViewport(width, height, scene.dimensions, state);
        const projector = (point) => htmlReportProjectPoint(point, scene.dimensions, viewport, state);
        drawHtmlReportFloorGrid(context, projector, scene.dimensions);
        drawHtmlReportPrism(context, scene, projector);
        const faces = scene.placements.flatMap((placement) => htmlReportBoxFaces(placement, state));
        drawHtmlReportFaces(context, faces, projector, state.hitRegions);
        drawHtmlReportBoxWireframes(context, scene.placements, projector, state);
        drawHtmlReportPrismEdges(context, scene, projector);
        drawHtmlReportAxes(context, scene.dimensions, projector);
        drawHtmlReportBackgroundText(context, width, height);
      }

      function setupHtmlReportCanvas(canvas) {
        const context = canvas.getContext("2d");
        const bounds = canvas.getBoundingClientRect();
        const width = Math.max(1, bounds.width || Number(canvas.getAttribute("width")) || canvas.width);
        const height = Math.max(1, bounds.height || Number(canvas.getAttribute("height")) || canvas.height);
        const ratio = window.devicePixelRatio || 1;
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        return { context, width, height };
      }

      function htmlReportSceneViewport(width, height, dimensions, state) {
        const bounds = htmlReportSceneViewportBounds(dimensions, state);
        const usableWidth = Math.max(1, width - HTML_REPORT_SCENE_SAFE_PADDING * 2);
        const usableHeight = Math.max(1, height - HTML_REPORT_SCENE_SAFE_PADDING * 2);
        const scale = Math.min(usableWidth / Math.max(bounds.width, 1), usableHeight / Math.max(bounds.height, 1)) * state.zoom;
        return {
          scale,
          offsetX: width / 2 + state.panX - ((bounds.minX + bounds.maxX) / 2) * scale,
          offsetY: height / 2 + state.panY - ((bounds.minY + bounds.maxY) / 2) * scale,
        };
      }

      function htmlReportSceneViewportBounds(dimensions, state) {
        const projected = htmlReportSceneEnvelopePoints(dimensions).map((point) => htmlReportProjectScenePoint(point, dimensions, state));
        const xs = projected.map((point) => point.x);
        const ys = projected.map((point) => point.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
      }

      function htmlReportSceneEnvelopePoints(dimensions) {
        return [
          { x: 0, y: 0, z: 0 },
          { x: dimensions.length, y: 0, z: 0 },
          { x: dimensions.length, y: dimensions.maxY, z: 0 },
          { x: 0, y: dimensions.maxY, z: 0 },
          { x: 0, y: 0, z: dimensions.maxZ },
          { x: dimensions.length, y: 0, z: dimensions.maxZ },
          { x: dimensions.length, y: dimensions.maxY, z: dimensions.maxZ },
          { x: 0, y: dimensions.maxY, z: dimensions.maxZ },
          { x: dimensions.length * HTML_REPORT_AXIS_EXTENSION_FACTOR, y: 0, z: 0 },
          { x: 0, y: dimensions.maxY * HTML_REPORT_AXIS_EXTENSION_FACTOR, z: 0 },
          { x: 0, y: 0, z: dimensions.maxZ * HTML_REPORT_AXIS_EXTENSION_FACTOR },
        ];
      }

      function htmlReportProjectPoint(point, dimensions, viewport, state) {
        const projected = htmlReportProjectScenePoint(point, dimensions, state);
        return {
          x: viewport.offsetX + projected.x * viewport.scale,
          y: viewport.offsetY + projected.y * viewport.scale,
          depth: projected.depth,
        };
      }

      function htmlReportProjectScenePoint(point, dimensions, state) {
        const centered = {
          x: point.x - dimensions.length / 2,
          y: point.y - dimensions.maxY / 2,
          z: point.z - dimensions.maxZ / 2,
        };
        const cosYaw = Math.cos(state.yaw);
        const sinYaw = Math.sin(state.yaw);
        const x1 = centered.x * cosYaw - centered.y * sinYaw;
        const y1 = centered.x * sinYaw + centered.y * cosYaw;
        const z1 = centered.z;
        const cosPitch = Math.cos(state.pitch);
        const sinPitch = Math.sin(state.pitch);
        const y2 = y1 * cosPitch - z1 * sinPitch;
        const z2 = y1 * sinPitch + z1 * cosPitch;
        return { x: x1, y: -z2, depth: y2 };
      }

      function drawHtmlReportFloorGrid(context, projector, dimensions) {
        const floor = [
          { x: 0, y: 0, z: 0 },
          { x: dimensions.length, y: 0, z: 0 },
          { x: dimensions.length, y: dimensions.maxY, z: 0 },
          { x: 0, y: dimensions.maxY, z: 0 },
        ];
        context.save();
        drawHtmlReportProjectedPolygon(context, floor, projector, {
          fill: "rgba(15, 23, 42, 0.34)",
          stroke: "rgba(125, 211, 252, 0.18)",
          lineWidth: 1.2,
        });
        context.strokeStyle = "rgba(148, 163, 184, 0.17)";
        context.lineWidth = 1;
        const xStep = htmlReportSceneGridStep(dimensions.length);
        const yStep = htmlReportSceneGridStep(dimensions.maxY);
        for (let x = 0; x <= dimensions.length; x += xStep) {
          drawHtmlReportWorldPolyline(context, [{ x, y: 0, z: 0 }, { x, y: dimensions.maxY, z: 0 }], projector);
        }
        for (let y = 0; y <= dimensions.maxY; y += yStep) {
          drawHtmlReportWorldPolyline(context, [{ x: 0, y, z: 0 }, { x: dimensions.length, y, z: 0 }], projector);
        }
        context.strokeStyle = "rgba(226, 232, 240, 0.24)";
        context.lineWidth = 1.6;
        drawHtmlReportWorldPolyline(context, [floor[0], floor[1], floor[2], floor[3], floor[0]], projector);
        context.restore();
      }

      function htmlReportSceneGridStep(size) {
        const raw = Math.max(1, Number(size)) / 8;
        const power = 10 ** Math.floor(Math.log10(raw));
        const normalized = raw / power;
        if (normalized <= 2) {
          return 2 * power;
        }
        if (normalized <= 5) {
          return 5 * power;
        }
        return 10 * power;
      }

      function drawHtmlReportProjectedPolygon(context, points, projector, style) {
        const projected = points.map(projector);
        context.beginPath();
        projected.forEach((point, index) => {
          if (index === 0) {
            context.moveTo(point.x, point.y);
          } else {
            context.lineTo(point.x, point.y);
          }
        });
        context.closePath();
        context.fillStyle = style.fill;
        context.strokeStyle = style.stroke;
        context.lineWidth = style.lineWidth ?? 1;
        context.fill();
        context.stroke();
      }

      function drawHtmlReportPrism(context, scene, projector) {
        const faces = htmlReportPrismFaces(scene).map((points) => ({
          points,
          fill: "rgba(56, 189, 248, 0.026)",
          stroke: "rgba(125, 211, 252, 0.16)",
          lineWidth: 0.8,
        }));
        context.save();
        drawHtmlReportFaces(context, faces, projector);
        context.restore();
      }

      function drawHtmlReportPrismEdges(context, scene, projector) {
        const length = scene.dimensions.length;
        const front = scene.crossSection.map(([y, z]) => ({ x: 0, y, z }));
        const back = scene.crossSection.map(([y, z]) => ({ x: length, y, z }));
        context.save();
        context.strokeStyle = "rgba(186, 230, 253, 0.92)";
        context.lineWidth = 2.4;
        context.shadowColor = "rgba(56, 189, 248, 0.42)";
        context.shadowBlur = 10;
        drawHtmlReportWorldPolyline(context, [...front, front[0]], projector);
        drawHtmlReportWorldPolyline(context, [...back, back[0]], projector);
        front.forEach((point, index) => drawHtmlReportWorldPolyline(context, [point, back[index]], projector));
        context.restore();
      }

      function drawHtmlReportAxes(context, dimensions, projector) {
        const axes = [
          [{ x: 0, y: 0, z: 0 }, { x: dimensions.length * HTML_REPORT_AXIS_EXTENSION_FACTOR, y: 0, z: 0 }, "x", "#f87171"],
          [{ x: 0, y: 0, z: 0 }, { x: 0, y: dimensions.maxY * HTML_REPORT_AXIS_EXTENSION_FACTOR, z: 0 }, "y", "#34d399"],
          [{ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: dimensions.maxZ * HTML_REPORT_AXIS_EXTENSION_FACTOR }, "z", "#60a5fa"],
        ];
        context.save();
        context.font = "700 14px system-ui, sans-serif";
        axes.forEach(([start, end, label, color]) => {
          const a = projector(start);
          const b = projector(end);
          context.strokeStyle = color;
          context.fillStyle = color;
          context.lineWidth = 3;
          context.shadowColor = color;
          context.shadowBlur = 6;
          drawHtmlReportPolyline(context, [a, b]);
          drawHtmlReportAxisArrow(context, a, b);
          context.shadowBlur = 0;
          const labelWidth = context.measureText(label).width + 14;
          context.fillStyle = "rgba(15, 23, 42, 0.72)";
          context.fillRect(b.x + 3, b.y - 22, labelWidth, 22);
          context.strokeStyle = "rgba(255, 255, 255, 0.22)";
          context.strokeRect(b.x + 3, b.y - 22, labelWidth, 22);
          context.fillStyle = color;
          context.fillText(label, b.x + 10, b.y - 6);
        });
        context.restore();
      }

      function drawHtmlReportAxisArrow(context, start, end) {
        const angle = Math.atan2(end.y - start.y, end.x - start.x);
        const size = 9;
        context.beginPath();
        context.moveTo(end.x, end.y);
        context.lineTo(end.x - Math.cos(angle - Math.PI / 6) * size, end.y - Math.sin(angle - Math.PI / 6) * size);
        context.moveTo(end.x, end.y);
        context.lineTo(end.x - Math.cos(angle + Math.PI / 6) * size, end.y - Math.sin(angle + Math.PI / 6) * size);
        context.stroke();
      }

      function htmlReportPrismFaces(scene) {
        const length = scene.dimensions.length;
        const front = scene.crossSection.map(([y, z]) => ({ x: 0, y, z }));
        const back = scene.crossSection.map(([y, z]) => ({ x: length, y, z }));
        const faces = [[...front].reverse(), back];
        scene.crossSection.forEach((_, index) => {
          const next = (index + 1) % scene.crossSection.length;
          faces.push([front[index], front[next], back[next], back[index]]);
        });
        return faces;
      }

      function htmlReportBoxFaces(placement, state) {
        const v = htmlReportBoxVertices(placement);
        const color = htmlReportColorForId(placement.box_id);
        const selected = placement.instance_id === state.selectedInstanceId;
        const hovered = placement.instance_id === state.hoveredInstanceId;
        return [
          htmlReportFace([v.a, v.b, v.c, v.d], color, selected, hovered, placement.instance_id, 0.52),
          htmlReportFace([v.e, v.f, v.g, v.h], color, selected, hovered, placement.instance_id, 0.96),
          htmlReportFace([v.a, v.b, v.f, v.e], color, selected, hovered, placement.instance_id, 0.78),
          htmlReportFace([v.b, v.c, v.g, v.f], color, selected, hovered, placement.instance_id, 0.7),
          htmlReportFace([v.c, v.d, v.h, v.g], color, selected, hovered, placement.instance_id, 0.62),
          htmlReportFace([v.d, v.a, v.e, v.h], color, selected, hovered, placement.instance_id, 0.74),
        ];
      }

      function htmlReportFace(points, color, selected, hovered, instanceId, alpha) {
        return { points, instanceId, ...htmlReportBoxFaceStyle(color, selected, hovered, alpha) };
      }

      function htmlReportBoxFaceStyle(color, selected, hovered, alpha) {
        if (selected) {
          const selectedColor = htmlReportLightenColor(color, 0.1);
          return {
            fill: htmlReportRgbaColor(selectedColor, 0.98),
            stroke: "#fef08a",
            lineWidth: 3.4,
            shadow: "rgba(254, 240, 138, 0.55)",
          };
        }
        if (hovered) {
          const hoveredColor = htmlReportLightenColor(color, 0.16);
          return {
            fill: htmlReportRgbaColor(hoveredColor, 0.92),
            stroke: htmlReportRgbaColor(htmlReportLightenColor(color, 0.62), 1),
            lineWidth: 2.4,
            shadow: "rgba(226, 232, 240, 0.35)",
          };
        }
        return {
          fill: htmlReportRgbaColor(color, alpha),
          stroke: htmlReportRgbaColor(htmlReportLightenColor(color, 0.38), 0.98),
          lineWidth: 1.45,
          shadow: "",
        };
      }

      function htmlReportBoxVertices(placement) {
        const x = placement.x;
        const y = placement.y;
        const z = placement.z;
        const length = placement.length;
        const width = placement.width;
        const height = placement.height;
        return {
          a: { x, y, z },
          b: { x: x + length, y, z },
          c: { x: x + length, y: y + width, z },
          d: { x, y: y + width, z },
          e: { x, y, z: z + height },
          f: { x: x + length, y, z: z + height },
          g: { x: x + length, y: y + width, z: z + height },
          h: { x, y: y + width, z: z + height },
        };
      }

      function drawHtmlReportFaces(context, faces, projector, hitRegions = null) {
        const projectedFaces = faces.map((item) => {
          const projected = item.points.map(projector);
          return {
            ...item,
            projected,
            depth: projected.reduce((total, point) => total + point.depth, 0) / projected.length,
          };
        });
        projectedFaces.sort((first, second) => first.depth - second.depth);
        context.save();
        projectedFaces.forEach((item) => {
          context.beginPath();
          item.projected.forEach((point, index) => {
            if (index === 0) {
              context.moveTo(point.x, point.y);
            } else {
              context.lineTo(point.x, point.y);
            }
          });
          context.closePath();
          context.fillStyle = item.fill;
          context.strokeStyle = item.stroke;
          context.lineWidth = item.lineWidth ?? 1;
          context.shadowColor = item.shadow || "transparent";
          context.shadowBlur = item.shadow ? 12 : 0;
          context.fill();
          context.stroke();
          if (hitRegions && item.instanceId) {
            hitRegions.push({ instanceId: item.instanceId, polygon: item.projected, depth: item.depth });
          }
        });
        context.restore();
      }

      function drawHtmlReportPolyline(context, points) {
        context.beginPath();
        points.forEach((point, index) => {
          if (index === 0) {
            context.moveTo(point.x, point.y);
          } else {
            context.lineTo(point.x, point.y);
          }
        });
        context.stroke();
      }

      function drawHtmlReportWorldPolyline(context, points, projector) {
        drawHtmlReportPolyline(context, points.map(projector));
      }

      function drawHtmlReportBoxWireframes(context, placements, projector, state) {
        const mutedStroke = placements.length > 220 ? "rgba(15, 23, 42, 0.46)" : "rgba(15, 23, 42, 0.72)";
        context.save();
        context.lineJoin = "round";
        context.lineCap = "round";
        placements.forEach((placement) => {
          const highlighted = placement.instance_id === state.selectedInstanceId || placement.instance_id === state.hoveredInstanceId;
          context.strokeStyle = highlighted ? "rgba(255, 255, 255, 0.88)" : mutedStroke;
          context.lineWidth = highlighted ? 2.2 : 0.75;
          htmlReportBoxEdges(htmlReportBoxVertices(placement)).forEach(([start, end]) => drawHtmlReportWorldPolyline(context, [start, end], projector));
        });
        context.restore();
      }

      function htmlReportBoxEdges(vertices) {
        return [
          [vertices.a, vertices.b],
          [vertices.b, vertices.c],
          [vertices.c, vertices.d],
          [vertices.d, vertices.a],
          [vertices.e, vertices.f],
          [vertices.f, vertices.g],
          [vertices.g, vertices.h],
          [vertices.h, vertices.e],
          [vertices.a, vertices.e],
          [vertices.b, vertices.f],
          [vertices.c, vertices.g],
          [vertices.d, vertices.h],
        ];
      }

      function drawHtmlReportBackgroundText(context, width, height) {
        context.save();
        context.fillStyle = "rgba(2, 6, 23, 0.72)";
        context.fillRect(14, height - 39, 268, 26);
        context.strokeStyle = "rgba(125, 211, 252, 0.22)";
        context.strokeRect(14, height - 39, 268, 26);
        context.fillStyle = "rgba(226, 232, 240, 0.88)";
        context.font = "13px system-ui, sans-serif";
        context.fillText("x = 长度方向，y = 截面宽度，z = 高度", 18, height - 20);
        context.restore();
      }

      function drawHtmlReportTopProjection(canvas, state) {
        const { context, width, height } = setupHtmlReportCanvas(canvas);
        const scene = state.scene;
        state.topHitRegions = [];
        context.clearRect(0, 0, width, height);
        const mapper = htmlReportPlaneMapper(width, height, scene.dimensions.length, scene.dimensions.maxY);
        drawHtmlReportProjectionFrame(context, width, height, "x 长度", "y 宽度");
        drawHtmlReportProjectionUldRect(context, mapper, scene.dimensions.length, scene.dimensions.maxY);
        scene.placements.forEach((placement) => {
          const color = htmlReportColorForId(placement.box_id);
          const rect = mapper.rectToScreen(placement.x, placement.y, placement.length, placement.width);
          const selected = placement.instance_id === state.selectedInstanceId;
          const hovered = placement.instance_id === state.hoveredInstanceId;
          const strokeColor = htmlReportLightenColor(color, selected ? 0.58 : hovered ? 0.5 : 0.34);
          context.save();
          context.fillStyle = htmlReportRgbaColor(color, selected ? 0.84 : hovered ? 0.74 : 0.56);
          context.strokeStyle = selected ? "#fef08a" : htmlReportRgbaColor(strokeColor, 0.96);
          context.lineWidth = selected ? 3 : hovered ? 2.2 : 1.2;
          context.fillRect(rect.x, rect.y, rect.width, rect.height);
          context.strokeRect(rect.x, rect.y, rect.width, rect.height);
          if (selected) {
            drawHtmlReportTopProjectionLabel(context, rect, placement.instance_id, selected);
          }
          context.restore();
          state.topHitRegions.push({ instanceId: placement.instance_id, rect });
        });
      }

      function drawHtmlReportTopProjectionLabel(context, rect, label, selected) {
        if (rect.width < 18 || rect.height < 14) {
          return;
        }
        const fontSize = Math.max(10, Math.min(12, Math.floor(rect.height * 0.38)));
        const textX = rect.x + 5;
        const textY = rect.y + Math.min(rect.height - 4, fontSize + 5);
        context.save();
        context.beginPath();
        context.rect(rect.x + 1, rect.y + 1, Math.max(0, rect.width - 2), Math.max(0, rect.height - 2));
        context.clip();
        context.font = "700 " + fontSize + "px system-ui, sans-serif";
        context.lineWidth = 3;
        context.strokeStyle = "rgba(2, 6, 23, 0.78)";
        context.fillStyle = selected ? "#fef08a" : "#f8fafc";
        context.strokeText(label, textX, textY, Math.max(10, rect.width - 10));
        context.fillText(label, textX, textY, Math.max(10, rect.width - 10));
        context.restore();
      }

      function htmlReportPlaneMapper(width, height, worldWidth, worldHeight) {
        const padding = 34;
        const usableWidth = Math.max(1, width - padding * 2);
        const usableHeight = Math.max(1, height - padding * 2);
        const scale = Math.min(usableWidth / Math.max(worldWidth, 1), usableHeight / Math.max(worldHeight, 1));
        const offsetX = (width - worldWidth * scale) / 2;
        const offsetY = (height - worldHeight * scale) / 2;
        return {
          toScreen(horizontal, vertical) {
            return { x: offsetX + horizontal * scale, y: height - offsetY - vertical * scale };
          },
          rectToScreen(horizontal, vertical, rectWidth, rectHeight) {
            const start = this.toScreen(horizontal, vertical + rectHeight);
            return { x: start.x, y: start.y, width: rectWidth * scale, height: rectHeight * scale };
          },
        };
      }

      function drawHtmlReportProjectionFrame(context, width, height, horizontalLabel, verticalLabel) {
        context.save();
        context.fillStyle = "rgba(226, 232, 240, 0.76)";
        context.font = "12px system-ui, sans-serif";
        context.fillText(horizontalLabel, width - 80, height - 12);
        context.fillText(verticalLabel, 12, 18);
        context.restore();
      }

      function drawHtmlReportProjectionUldRect(context, mapper, width, height) {
        const rect = mapper.rectToScreen(0, 0, width, height);
        context.save();
        context.strokeStyle = "rgba(186, 230, 253, 0.75)";
        context.lineWidth = 1.6;
        context.strokeRect(rect.x, rect.y, rect.width, rect.height);
        context.restore();
      }

      function updateHtmlReportSceneHover(state, event) {
        const match = htmlReportSceneMatchAtPoint(state, event);
        const nextInstanceId = match?.instanceId ?? null;
        if (!nextInstanceId) {
          clearHtmlReportSceneHover(state);
          return;
        }
        if (state.hoveredInstanceId !== nextInstanceId) {
          state.hoveredInstanceId = nextInstanceId;
          redrawHtmlReportSceneState(state);
        }
        renderHtmlReportSceneTooltip(state, event, htmlReportPlacementByInstanceId(state, nextInstanceId));
      }

      function clearHtmlReportSceneHover(state) {
        if (state.hoveredInstanceId) {
          state.hoveredInstanceId = null;
          redrawHtmlReportSceneState(state);
        }
        hideHtmlReportSceneTooltip(state);
      }

      function selectHtmlReportScenePlacement(state, event) {
        const match = htmlReportSceneMatchAtPoint(state, event);
        if (!match) {
          return;
        }
        state.selectedInstanceId = match.instanceId;
        redrawHtmlReportSceneState(state);
      }

      function selectHtmlReportTopPlacement(state, event) {
        const point = htmlReportCanvasPoint(event, event.currentTarget);
        const match = [...state.topHitRegions].reverse().find((region) => htmlReportPointInRect(point, region.rect));
        if (!match) {
          return;
        }
        state.selectedInstanceId = match.instanceId;
        redrawHtmlReportSceneState(state);
      }

      function htmlReportSceneMatchAtPoint(state, event) {
        const point = htmlReportCanvasPoint(event, state.sceneCanvas);
        return [...state.hitRegions]
          .sort((first, second) => second.depth - first.depth)
          .find((region) => htmlReportPointInPolygon(point, region.polygon));
      }

      function renderHtmlReportSceneTooltip(state, event, placement) {
        if (!state.tooltip || !placement) {
          hideHtmlReportSceneTooltip(state);
          return;
        }
        state.tooltip.innerHTML =
          "<strong>" + htmlReportEscape(placement.instance_id) + "</strong>" +
          "<div>类型：" + htmlReportEscape(placement.box_id) + "</div>" +
          "<div>尺寸：" + htmlReportFormatNumber(placement.length) + " × " + htmlReportFormatNumber(placement.width) + " × " + htmlReportFormatNumber(placement.height) + "</div>" +
          "<div>坐标：x " + htmlReportFormatNumber(placement.x) + "，y " + htmlReportFormatNumber(placement.y) + "，z " + htmlReportFormatNumber(placement.z) + "</div>";
        state.tooltip.classList.add("visible");
        const stageRect = state.tooltip.parentElement.getBoundingClientRect();
        const tooltipRect = state.tooltip.getBoundingClientRect();
        const maxLeft = Math.max(8, stageRect.width - tooltipRect.width - 8);
        const maxTop = Math.max(8, stageRect.height - tooltipRect.height - 8);
        const left = htmlReportClamp(event.clientX - stageRect.left + 14, 8, maxLeft);
        const top = htmlReportClamp(event.clientY - stageRect.top + 14, 8, maxTop);
        state.tooltip.style.left = left + "px";
        state.tooltip.style.top = top + "px";
      }

      function hideHtmlReportSceneTooltip(state) {
        state.tooltip?.classList.remove("visible");
      }

      function renderHtmlReportSceneSelection(state) {
        if (!state.selection) {
          return;
        }
        const placement = htmlReportPlacementByInstanceId(state, state.selectedInstanceId);
        if (!placement) {
          state.selection.classList.add("muted");
          state.selection.textContent = "点击 3D 视图中的箱子查看位置范围。";
          return;
        }
        state.selection.classList.remove("muted");
        state.selection.innerHTML =
          "<strong>" + htmlReportEscape(placement.instance_id) + "</strong>" +
          "<div>类型：<code>" + htmlReportEscape(placement.box_id) + "</code></div>" +
          "<div>x：<code>" + htmlReportFormatNumber(placement.x) + " ~ " + htmlReportFormatNumber(placement.x + placement.length) + "</code></div>" +
          "<div>y：<code>" + htmlReportFormatNumber(placement.y) + " ~ " + htmlReportFormatNumber(placement.y + placement.width) + "</code></div>" +
          "<div>z：<code>" + htmlReportFormatNumber(placement.z) + " ~ " + htmlReportFormatNumber(placement.z + placement.height) + "</code></div>" +
          "<div>尺寸：<code>" + htmlReportFormatNumber(placement.length) + " × " + htmlReportFormatNumber(placement.width) + " × " + htmlReportFormatNumber(placement.height) + "</code></div>";
      }

      function htmlReportPlacementByInstanceId(state, instanceId) {
        return state.scene.placements.find((placement) => placement.instance_id === instanceId) ?? null;
      }

      function htmlReportCanvasPoint(event, canvas) {
        const rect = canvas.getBoundingClientRect();
        return { x: event.clientX - rect.left, y: event.clientY - rect.top };
      }

      function htmlReportPointInRect(point, rect) {
        return point.x >= rect.x && point.x <= rect.x + rect.width && point.y >= rect.y && point.y <= rect.y + rect.height;
      }

      function htmlReportPointInPolygon(point, polygon) {
        let inside = false;
        for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
          const currentPoint = polygon[index];
          const previousPoint = polygon[previous];
          const crosses = currentPoint.y > point.y !== previousPoint.y > point.y;
          if (crosses) {
            const intersectionX = ((previousPoint.x - currentPoint.x) * (point.y - currentPoint.y)) / (previousPoint.y - currentPoint.y) + currentPoint.x;
            if (point.x < intersectionX) {
              inside = !inside;
            }
          }
        }
        return inside;
      }

      function htmlReportClamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
      }

      function htmlReportEscape(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }

      function htmlReportFormatNumber(value) {
        return Number(value).toFixed(2).replace(/\\.00$/, "").replace(/(\\.\\d*[1-9])0$/, "$1");
      }

      function htmlReportColorForId(id) {
        const palette = [
          { r: 14, g: 165, b: 233 }, { r: 245, g: 158, b: 11 }, { r: 168, g: 85, b: 247 },
          { r: 16, g: 185, b: 129 }, { r: 244, g: 63, b: 94 }, { r: 99, g: 102, b: 241 },
          { r: 20, g: 184, b: 166 }, { r: 249, g: 115, b: 22 }, { r: 217, g: 70, b: 239 },
          { r: 132, g: 204, b: 22 }, { r: 236, g: 72, b: 153 }, { r: 59, g: 130, b: 246 },
        ];
        let hash = 0;
        for (const char of String(id)) {
          hash = (hash * 31 + char.charCodeAt(0)) % 9973;
        }
        return palette[hash % palette.length];
      }

      function htmlReportLightenColor(color, ratio) {
        return {
          r: Math.round(color.r + (255 - color.r) * ratio),
          g: Math.round(color.g + (255 - color.g) * ratio),
          b: Math.round(color.b + (255 - color.b) * ratio),
        };
      }

      function htmlReportRgbaColor(color, alpha) {
        return "rgba(" + color.r + ", " + color.g + ", " + color.b + ", " + alpha + ")";
      }
    })();
  `;
}

function htmlReportStyles() {
  return `
    :root { color-scheme: light; font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; color: #0f172a; background: #f8fafc; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f8fafc; }
    .report { max-width: 1280px; margin: 0 auto; padding: 28px; display: grid; gap: 18px; }
    .report-header, .sheet-page, .metric, .uld-section { background: #fff; border: 1px solid #dbe4ee; border-radius: 8px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); }
    .report-header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; padding: 22px 24px; }
    .kicker, .meta, .muted { color: #64748b; }
    .kicker { margin: 0 0 6px; font-size: 12px; font-weight: 800; text-transform: uppercase; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { margin-bottom: 8px; font-size: 30px; }
    h2 { font-size: 20px; }
    h3 { font-size: 15px; }
    .status { padding: 8px 12px; border-radius: 6px; font-weight: 700; }
    .status.passed { color: #047857; background: #d1fae5; }
    .status.failed { color: #be123c; background: #ffe4e6; }
    .sheet-tabs { position: sticky; top: 0; z-index: 2; display: flex; flex-wrap: wrap; gap: 8px; padding: 10px; border: 1px solid #dbe4ee; border-radius: 8px; background: rgba(248, 250, 252, 0.94); backdrop-filter: blur(10px); }
    .sheet-tab { min-height: 34px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; background: #fff; font-weight: 700; cursor: pointer; }
    .sheet-tab.active { color: #075985; border-color: #38bdf8; background: #e0f2fe; }
    .sheet-pages { display: grid; gap: 18px; }
    .sheet-page { display: none; padding: 20px; gap: 14px; }
    .sheet-page.active { display: grid; }
    .visualization-toolbar { display: flex; justify-content: flex-end; }
    .visualization-toolbar label { display: flex; align-items: center; gap: 8px; color: #475569; font-size: 13px; font-weight: 700; }
    .visualization-toolbar select { min-height: 34px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color: #0f172a; }
    .summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .metric { padding: 16px; display: grid; gap: 8px; }
    .metric span { color: #64748b; font-size: 13px; }
    .metric strong { font-size: 24px; }
    .uld-section { padding: 16px; display: grid; gap: 14px; }
    .section-title { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
    .section-meta { display: flex; flex-wrap: wrap; gap: 8px; color: #475569; font-size: 13px; }
    .section-meta span, .chip { border: 1px solid #dbe4ee; border-radius: 6px; padding: 6px 8px; background: #f8fafc; }
    .chip-list { display: flex; flex-wrap: wrap; gap: 8px; }
    .top-views-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; align-items: stretch; }
    .scene-row { display: grid; }
    .view-card { border: 1px solid #dbe4ee; border-radius: 8px; padding: 12px; background: #f8fafc; }
    .top-views-grid .view-card { display: grid; grid-template-rows: auto minmax(0, 1fr); }
    .view-card-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 30px; margin-bottom: 8px; }
    .view-card-heading h3 { margin: 0; }
    .scene-view-controls { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 10px; }
    .scene-view-controls button { min-height: 34px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; background: #fff; font-weight: 700; cursor: pointer; transition: color 160ms ease, border-color 160ms ease, background 160ms ease; }
    .scene-view-controls button:hover, .scene-view-controls button:focus-visible { color: #075985; border-color: #38bdf8; background: #e0f2fe; outline: none; }
    .report-scene-stage { position: relative; overflow: hidden; border-radius: 8px; }
    .scene-canvas, .projection-canvas { width: 100%; display: block; border-radius: 8px; background: linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px), radial-gradient(circle at center, rgba(14, 165, 233, 0.13), transparent 32rem), #06101e; background-size: 32px 32px, 32px 32px, auto, auto; }
    .projection-canvas { aspect-ratio: 17 / 8; min-height: 230px; cursor: crosshair; }
    .scene-canvas { aspect-ratio: 16 / 9; min-height: 420px; cursor: grab; touch-action: none; box-shadow: inset 0 0 120px rgba(0, 0, 0, 0.62); }
    .scene-canvas:active { cursor: grabbing; }
    .scene-tooltip { position: absolute; z-index: 4; display: none; max-width: min(280px, calc(100% - 24px)); padding: 10px 12px; border: 1px solid rgba(226, 232, 240, 0.28); border-radius: 8px; color: #e2e8f0; background: rgba(15, 23, 42, 0.92); box-shadow: 0 18px 44px rgba(0, 0, 0, 0.35); pointer-events: none; line-height: 1.55; font-size: 12.5px; }
    .scene-tooltip.visible { display: block; }
    .scene-tooltip strong { display: block; margin-bottom: 4px; color: #fef08a; }
    .scene-selection { margin-top: 10px; padding: 10px 12px; border: 1px solid #dbe4ee; border-radius: 8px; background: #fff; font-size: 13px; line-height: 1.55; }
    .scene-selection strong { color: #0f172a; }
    svg { width: 100%; height: auto; display: block; }
    .svg-bg { fill: #07111f; }
    .grid-line { stroke: rgba(148, 163, 184, 0.18); stroke-width: 1; }
    .uld-frame { fill: rgba(56, 189, 248, 0.08); stroke: rgba(186, 230, 253, 0.9); stroke-width: 2; }
    .box-rect { stroke-width: 1.4; }
    .box-label { fill: #fff7ed; font-size: 12px; font-weight: 700; }
    .position-map-label-toggle { min-height: 30px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; background: #fff; font-size: 12px; font-weight: 800; cursor: pointer; transition: color 160ms ease, border-color 160ms ease, background 160ms ease; }
    .position-map-label-toggle:hover, .position-map-label-toggle:focus-visible { color: #075985; border-color: #38bdf8; background: #e0f2fe; outline: none; }
    .position-map-svg-wrap { width: 100%; overflow: hidden; min-height: 0; }
    .position-map-svg { width: 100%; min-width: 0; aspect-ratio: 17 / 8; background: #07111f; border-radius: 8px; }
    .position-map-svg.position-map-label-hidden .position-pile-label-layer { display: none; }
    .position-pile { cursor: pointer; outline: none; }
    .position-pile-rect { stroke-width: 1.6; transition: stroke 160ms ease, stroke-width 160ms ease, filter 160ms ease; }
    .position-pile:hover .position-pile-rect, .position-pile:focus-visible .position-pile-rect { stroke: #fef08a; stroke-width: 2.8; }
    .position-pile.selected .position-pile-rect { stroke: #facc15; stroke-width: 4; filter: drop-shadow(0 0 9px rgba(250, 204, 21, 0.7)); }
    .position-pile-label-item { pointer-events: none; }
    .position-pile-label-bg { fill: rgba(2, 6, 23, 0.64); stroke: rgba(255, 255, 255, 0.14); stroke-width: 1; }
    .position-pile-label-item.selected .position-pile-label-bg { fill: rgba(2, 6, 23, 0.88); stroke: rgba(250, 204, 21, 0.86); stroke-width: 1.8; }
    .position-pile-label-item.selected .position-pile-label { fill: #fef08a; }
    .position-pile-label { fill: #ffffff; stroke: rgba(2, 6, 23, 0.88); stroke-width: 3px; paint-order: stroke; font-size: 12px; font-weight: 900; pointer-events: none; }
    .axis-label { fill: #cbd5e1; font-size: 12px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border: 1px solid #dbe4ee; padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: #e2e8f0; font-weight: 800; }
    .position-map th, .position-map td { min-width: 96px; height: 48px; font-weight: 700; }
    [hidden] { display: none !important; }
    @media print { body { background: #fff; } .report { max-width: none; padding: 0; } .sheet-tabs { display: none; } .sheet-page { display: grid !important; break-before: page; box-shadow: none; } .sheet-page:first-of-type { break-before: auto; } .metric, .report-header, .uld-section { box-shadow: none; break-inside: avoid; } }
    @media (max-width: 900px) { .summary-grid, .top-views-grid { grid-template-columns: 1fr; } .report-header, .section-title { display: grid; } .scene-canvas { min-height: 300px; } }
  `;
}

function buildWorkbookSheets(result, input = null) {
  const containers = resultContainersForExport(result);
  const placements = allPlacementsForExport(containers);
  const loaded = result.loaded ?? loadedSummaryFromPlacements(placements);
  const unloaded = result.unloaded ?? [];
  const validationErrors = result.validation_errors?.length ? result.validation_errors.join("；") : "";
  const exportInput = input ? normalizeInput(input) : { containers: [], boxes: [] };
  const inputBoxById = new Map((exportInput.boxes ?? []).map((box) => [box.id, box]));

  return [
    {
      name: "总体结果",
      rows: [
        ["指标", "数值"],
        ["已装箱", result.loaded_count ?? 0],
        ["未装箱", result.unloaded_count ?? 0],
        ["体积利用率", formatPercent(result.volume_utilization)],
        ["已用体积", result.used_volume ?? 0],
        ["总体体积", result.container_volume ?? result.uld_volume ?? 0],
        ["校验", result.validation_passed ? "通过" : "失败"],
        ["校验信息", validationErrors],
      ],
      widths: [18, 28],
    },
    {
      name: "ULD 明细",
      rows: [
        ["ULD", "类型", "已装箱", "未装箱", "体积利用率", "已用体积", "ULD 体积", "校验"],
        ...containers.map((container) => {
          const containerId = container.container_id ?? container.uld_id ?? "";
          return [
            { value: containerId, styleKey: uldStyleKey(containerId) },
            container.container_type ?? container.uld_id ?? "",
            container.loaded_count ?? 0,
            container.unloaded_count ?? 0,
            formatPercent(container.volume_utilization),
            container.used_volume ?? 0,
            container.uld_volume ?? 0,
            container.validation_passed ? "通过" : "失败",
          ];
        }),
      ],
      widths: [18, 14, 12, 12, 14, 16, 16, 12],
    },
    {
      name: "ULD 数据",
      rows: [
        ["ULD ID", "长度", "数量", "截面"],
        ...exportInput.containers.map((container) => [
          container.id,
          Number(container.length),
          Number(container.quantity ?? 0),
          JSON.stringify(container.cross_section ?? []),
        ]),
      ],
      widths: [18, 12, 12, 48],
    },
    {
      name: "箱子数据",
      rows: [
        ["箱子 ID", "长", "宽", "高", "数量", "长宽互换", "ULD 类型"],
        ...(exportInput.boxes ?? []).map((box) => [
          box.id ?? "",
          Number(box.length),
          Number(box.width),
          Number(box.height),
          Number(box.quantity ?? 0),
          box.rotatable ?? true ? "是" : "否",
          (box.required_container_types ?? []).join(", "),
        ]),
      ],
      widths: [22, 12, 12, 12, 12, 14, 24],
    },
    {
      name: "已装箱类型",
      rows: [
        ["箱子 ID", "数量"],
        ...loaded.map((item) => [{ value: excelBoxLabel(item, inputBoxById), styleKey: boxStyleKey(item.box_id) }, item.quantity]),
      ],
      widths: [22, 12],
    },
    {
      name: "未装箱",
      rows: [
        ["箱子 ID", "数量", "原因"],
        ...unloaded.map((item) => [{ value: excelBoxLabel(item, inputBoxById), styleKey: boxStyleKey(item.box_id) }, item.quantity, item.reason ?? ""]),
      ],
      widths: [22, 12, 32],
    },
    buildUldVisualizationSheet(containers, exportInput),
    {
      name: "装箱坐标",
      rows: [
        ["ULD", "实例", "箱子 ID", "x", "y", "z", "L", "W", "H"],
        ...placements.map((placement) => [
          { value: placement.container_id, styleKey: uldStyleKey(placement.container_id) },
          placement.instance_id,
          { value: excelBoxLabel(placement, inputBoxById), styleKey: boxStyleKey(placement.box_id) },
          placement.x,
          placement.y,
          placement.z,
          placement.length,
          placement.width,
          placement.height,
        ]),
      ],
      widths: [18, 20, 18, 10, 10, 10, 10, 10, 10],
    },
  ];
}

function excelBoxLabel(item, inputBoxById) {
  const dimensions = boxItemDimensions(item, inputBoxById.get(item.box_id));
  return dimensions ? `${item.box_id} (${dimensions})` : item.box_id;
}

function buildXlsxWorkbook(sheets) {
  const styleModel = buildExcelStyleModel(sheets);
  const files = {
    "[Content_Types].xml": buildContentTypesXml(sheets),
    "_rels/.rels": buildRootRelsXml(),
    "xl/workbook.xml": buildWorkbookXml(sheets),
    "xl/_rels/workbook.xml.rels": buildWorkbookRelsXml(sheets),
    "xl/styles.xml": buildStylesXml(styleModel),
  };
  sheets.forEach((sheet, index) => {
    files[`xl/worksheets/sheet${index + 1}.xml`] = buildWorksheetXml(sheet, styleModel);
  });
  return createZipArchive(files);
}

function buildContentTypesXml(sheets) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  ${sheets
    .map((_, index) => `<Override PartName="/xl/worksheets/sheet${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`)
    .join("\n  ")}
</Types>`;
}

function buildRootRelsXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`;
}

function buildWorkbookXml(sheets) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    ${sheets.map((sheet, index) => `<sheet name="${escapeXmlAttribute(sheet.name)}" sheetId="${index + 1}" r:id="rId${index + 1}"/>`).join("\n    ")}
  </sheets>
</workbook>`;
}

function buildWorkbookRelsXml(sheets) {
  const worksheetRelationships = sheets
    .map(
      (_, index) =>
        `<Relationship Id="rId${index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${index + 1}.xml"/>`,
    )
    .join("\n  ");
  return `<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  ${worksheetRelationships}
  <Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`;
}

function buildExcelStyleModel(sheets) {
  const styleKeys = [];
  const seenStyleKeys = new Set();
  sheets.forEach((sheet) => {
    sheet.rows.forEach((row) => {
      row.forEach((cell) => {
        const styleKey = normalizeExcelCell(cell).styleKey;
        if (styleKey && !seenStyleKeys.has(styleKey)) {
          seenStyleKeys.add(styleKey);
          styleKeys.push(styleKey);
        }
      });
    });
  });

  const styleIndexByKey = new Map();
  const styleEntries = styleKeys.map((key, index) => {
    const entry = {
      key,
      color: excelColorForKey(key, index),
      fillId: 4 + index,
      styleIndex: 4 + index,
    };
    styleIndexByKey.set(key, entry.styleIndex);
    return entry;
  });

  return { styleEntries, styleIndexByKey };
}

function uldStyleKey(id) {
  const value = excelCellValue(id);
  return value ? `uld:${value}` : "";
}

function boxStyleKey(id) {
  const value = excelCellValue(id);
  return value ? `box:${value}` : "";
}

function excelColorForKey(key, index = 0) {
  if (index < EXCEL_COLOR_PALETTE.length) {
    return EXCEL_COLOR_PALETTE[index];
  }
  let hash = 0;
  for (const char of key) {
    hash = (hash * 33 + char.charCodeAt(0)) % 360;
  }
  return hslToExcelColor((hash + index * 47) % 360, 58, 86);
}

function hslToExcelColor(hue, saturation, lightness) {
  const s = saturation / 100;
  const l = lightness / 100;
  const chroma = (1 - Math.abs(2 * l - 1)) * s;
  const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
  const m = l - chroma / 2;
  const [red, green, blue] =
    hue < 60
      ? [chroma, x, 0]
      : hue < 120
        ? [x, chroma, 0]
        : hue < 180
          ? [0, chroma, x]
          : hue < 240
            ? [0, x, chroma]
            : hue < 300
              ? [x, 0, chroma]
              : [chroma, 0, x];
  return `FF${excelColorChannel(red + m)}${excelColorChannel(green + m)}${excelColorChannel(blue + m)}`;
}

function excelColorChannel(value) {
  return Math.round(value * 255)
    .toString(16)
    .padStart(2, "0")
    .toUpperCase();
}

function buildStylesXml(styleModel) {
  const styleEntries = styleModel?.styleEntries ?? [];
  const dynamicFills = styleEntries
    .map((entry) => `<fill><patternFill patternType="solid"><fgColor rgb="${entry.color}"/><bgColor indexed="64"/></patternFill></fill>`)
    .join("\n    ");
  const dynamicCellXfs = styleEntries
    .map(
      (entry) =>
        `<xf numFmtId="0" fontId="2" fillId="${entry.fillId}" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>`,
    )
    .join("\n    ");
  return `<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><sz val="11"/><color rgb="FF111827"/><name val="Microsoft YaHei"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Microsoft YaHei"/></font>
    <font><b/><sz val="11"/><color rgb="FF0F172A"/><name val="Microsoft YaHei"/></font>
  </fonts>
  <fills count="${4 + styleEntries.length}">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE0F2FE"/><bgColor indexed="64"/></patternFill></fill>
    ${dynamicFills}
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FF94A3B8"/></left>
      <right style="thin"><color rgb="FF94A3B8"/></right>
      <top style="thin"><color rgb="FF94A3B8"/></top>
      <bottom style="thin"><color rgb="FF94A3B8"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="${4 + styleEntries.length}">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    ${dynamicCellXfs}
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;
}

function buildWorksheetXml(sheet, styleModel) {
  const columnCount = Math.max(...sheet.rows.map((row) => row.length), 1);
  const range = `A1:${columnName(columnCount)}${Math.max(sheet.rows.length, 1)}`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews>
    <sheetView workbookViewId="0">
      ${freezePaneXml()}
      <selection pane="bottomLeft"/>
    </sheetView>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="20"/>
  <cols>
    ${Array.from({ length: columnCount }, (_, index) => `<col min="${index + 1}" max="${index + 1}" width="${worksheetColumnWidth(sheet, index)}" customWidth="1"/>`).join("\n    ")}
  </cols>
  <sheetData>
    ${sheet.rows.map((row, rowIndex) => worksheetRowXml(row, rowIndex, styleModel, sheet.heights?.[rowIndex])).join("\n    ")}
  </sheetData>
  <autoFilter ref="${range}"/>
  ${mergeCellsXml(sheet.merges)}
</worksheet>`;
}

function mergeCellsXml(merges = []) {
  const refs = merges
    .filter((merge) => merge.endRow > merge.startRow || merge.endColumn > merge.startColumn)
    .map((merge) => {
      const start = `${columnName(merge.startColumn + 1)}${merge.startRow + 1}`;
      const end = `${columnName(merge.endColumn + 1)}${merge.endRow + 1}`;
      return `<mergeCell ref="${start}:${end}"/>`;
    });

  if (refs.length === 0) {
    return "";
  }

  return `<mergeCells count="${refs.length}">${refs.join("")}</mergeCells>`;
}

function worksheetRowXml(row, rowIndex, styleModel, explicitHeight) {
  const rowNumber = rowIndex + 1;
  const rowHeight = worksheetRowHeight(row, rowIndex, explicitHeight);
  return `<row r="${rowNumber}" ht="${rowHeight}" customHeight="1">${row
    .map((cell, columnIndex) => worksheetCellXml(cell, rowIndex, columnIndex, styleModel))
    .join("")}</row>`;
}

function worksheetRowHeight(row, rowIndex, explicitHeight) {
  const baseHeight = rowIndex === 0 ? 24 : 20;
  const lineCount = Math.max(1, ...row.map((cell) => excelCellValue(cell).split(/\r\n|\r|\n/).length));
  const contentHeight = Math.max(baseHeight, lineCount * 20);
  return explicitHeight != null ? Math.max(explicitHeight, contentHeight) : contentHeight;
}

function freezePaneXml() {
  return `<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>`;
}

function worksheetCellXml(value, rowIndex, columnIndex, styleModel) {
  const cell = normalizeExcelCell(value);
  const rawValue = cell.value;
  const reference = `${columnName(columnIndex + 1)}${rowIndex + 1}`;
  const taggedStyle = cell.styleKey ? styleModel?.styleIndexByKey.get(cell.styleKey) : null;
  const style = rowIndex === 0 ? 1 : taggedStyle ?? (columnIndex === 0 ? 2 : typeof rawValue === "number" ? 3 : 0);
  if (typeof rawValue === "number" && Number.isFinite(rawValue)) {
    return `<c r="${reference}" s="${style}"><v>${rawValue}</v></c>`;
  }
  return `<c r="${reference}" s="${style}" t="inlineStr"><is><t>${escapeXmlText(excelCellValue(rawValue))}</t></is></c>`;
}

function worksheetColumnWidth(sheet, columnIndex) {
  return Math.max(Number(sheet.widths?.[columnIndex] ?? 0), columnWidth(sheet.rows, columnIndex));
}

function columnWidth(rows, columnIndex) {
  const width = Math.max(...rows.map((row) => excelCellValue(row[columnIndex]).length), 8) + 4;
  return Math.min(72, Math.max(10, width));
}

function columnName(columnIndex) {
  let name = "";
  let remaining = columnIndex;
  while (remaining > 0) {
    const modulo = (remaining - 1) % 26;
    name = String.fromCharCode(65 + modulo) + name;
    remaining = Math.floor((remaining - modulo) / 26);
  }
  return name;
}

function resultContainersForExport(result) {
  if (Array.isArray(result.containers)) {
    return result.containers;
  }
  return [
    {
      ...result,
      container_id: result.uld_id ?? "ULD",
      container_type: result.uld_id ?? "ULD",
    },
  ];
}

function allPlacementsForExport(containers) {
  return containers.flatMap((container) =>
    (container.placements ?? []).map((placement) => ({
      ...placement,
      container_id: container.container_id ?? container.uld_id ?? "",
    })),
  );
}

function buildUldVisualizationSheet(containers, input) {
  const rows = [["ULD 可视化", "按 ULD 汇总已装箱尺寸数量"]];
  const heights = [null];
  const columnWidths = [];
  const profileById = new Map((input?.containers ?? []).map((container) => [container.id, container]));

  containers.forEach((container) => {
    rows.push([]);
    heights.push(null);
    const section = buildUldVisualizationSection(container, profileById.get(container.container_type));
    rows.push(...section.rows);
    heights.push(...section.heights);
    (section.widths ?? []).forEach((width, index) => {
      columnWidths[index] = Math.max(columnWidths[index] ?? 0, width);
    });
  });

  const columnCount = Math.max(...rows.map((row) => row.length), 1);
  const widths = Array.from({ length: columnCount }, (_, index) =>
    index === 0 ? Math.max(columnWidths[0] ?? 0, 16) : columnWidths[index] ?? 28,
  );
  return { name: "ULD 可视化", rows, widths, heights, merges: [] };
}

function buildUldVisualizationSection(container, profileInput) {
  const containerId = container.container_id ?? container.uld_id ?? "";
  const placements = container.placements ?? [];
  const rows = [
    [
      { value: `ULD ${containerId}`, styleKey: uldStyleKey(containerId) },
      `类型 ${container.container_type ?? container.uld_id ?? ""}`,
      `已装 ${container.loaded_count ?? placements.length}`,
      `装载率 ${formatPercent(container.volume_utilization)}`,
    ],
    ["装载清单", ...placementSizeSummaries(placements)],
  ];

  if (placements.length === 0) {
    rows.push(["暂无已装箱"]);
    return { rows, merges: [], heights: rows.map(() => null), widths: [] };
  }

  rows.push([]);
  rows.push(["俯视位置图"]);
  const topViewRows = buildTopViewRows(placements, profileInput);
  const heights = [...rows.map(() => null), ...(topViewRows.heights ?? [])];
  rows.push(...topViewRows);

  return { rows, merges: [], heights, widths: topViewRows.widths ?? [] };
}

function placementSizeSummaries(placements) {
  const counter = new Map();
  placements.forEach((placement) => {
    const key = [placement.length, placement.width, placement.height].map(formatNumber).join("*");
    counter.set(key, (counter.get(key) ?? 0) + 1);
  });
  return [...counter.entries()].map(([size, quantity]) => `${size}*${quantity}`);
}

const TOP_VIEW_LABEL_WIDTH = 12;
const TOP_VIEW_HEADER_HEIGHT = 22;
const TOP_VIEW_MIN_WIDTH = 10;
const TOP_VIEW_MAX_WIDTH = 60;
const TOP_VIEW_MIN_HEIGHT = 20;
const TOP_VIEW_MAX_HEIGHT = 240;
const TOP_VIEW_LINE_HEIGHT = 20;
const TOP_VIEW_LENGTH_TO_WIDTH = 0.16;
const TOP_VIEW_WIDTH_TO_HEIGHT = 0.6;

// 俯视位置图：每一摞占一个格子，按各摞锚点 (minX, minY) 落到行列网格。
// 列 = 不同 anchorX 升序（x 长度方向向右），行 = 不同 anchorY 降序（第一象限 y 向上）。
// 列宽取该列各摞箱子的最大长，行高取该行各摞箱子的最大宽，近似反映每摞占地大小。
// 格子内容按高度 z 从下到上逐层书写 长*宽*高*数量；锚点相同的多摞在同一格内上下叠写。
// 不再合并单元格，因此不会出现 Excel 合并矩形互相覆盖的报错。
function buildTopViewRows(placements, profileInput) {
  const stacks = buildPlacementStacks(placements);
  if (placements.length === 0) {
    const rows = [["y \\ x"]];
    rows.merges = [];
    rows.heights = [TOP_VIEW_HEADER_HEIGHT];
    rows.widths = [TOP_VIEW_LABEL_WIDTH];
    return rows;
  }
  const piles = stacks.map((stack) => ({
    anchorX: stack.minX,
    anchorY: stack.minY,
    maxLength: Math.max(...stack.placements.map((placement) => placement.length)),
    maxWidth: Math.max(...stack.placements.map((placement) => placement.width)),
    summary: layerSizeSummaries(stack.placements).join("\n"),
    styleKey: boxStyleKey(stack.placements[0].box_id),
  }));
  const xs = [...new Set(piles.map((pile) => pile.anchorX))].sort((first, second) => first - second);
  const ys = [...new Set(piles.map((pile) => pile.anchorY))].sort((first, second) => second - first);
  const columnByX = new Map(xs.map((x, index) => [x, index]));
  const rowByY = new Map(ys.map((y, index) => [y, index]));
  const colMaxLength = xs.map(() => 0);
  const rowMaxWidth = ys.map(() => 0);
  piles.forEach((pile) => {
    const column = columnByX.get(pile.anchorX);
    const row = rowByY.get(pile.anchorY);
    colMaxLength[column] = Math.max(colMaxLength[column], pile.maxLength);
    rowMaxWidth[row] = Math.max(rowMaxWidth[row], pile.maxWidth);
  });
  const header = ["y \\ x", ...xs.map((x, column) => `${formatNumber(x)}-${formatNumber(x + colMaxLength[column])}`)];
  const body = ys.map((y, row) => [
    `${formatNumber(y)}-${formatNumber(y + rowMaxWidth[row])}`,
    ...xs.map(() => ""),
  ]);
  piles.forEach((pile) => {
    const column = columnByX.get(pile.anchorX) + 1;
    const row = rowByY.get(pile.anchorY);
    const existing = body[row][column];
    const existingText = existing && existing !== "" ? String(excelCellValue(existing)) : "";
    const nextText = existingText !== "" ? `${existingText}\n${pile.summary}` : pile.summary;
    body[row][column] = { value: nextText, styleKey: pile.styleKey };
  });
  const rows = [header, ...body];
  rows.merges = [];
  rows.heights = [
    TOP_VIEW_HEADER_HEIGHT,
    ...body.map((cells, row) => topViewRowHeight(rowMaxWidth[row], cells)),
  ];
  rows.widths = [
    TOP_VIEW_LABEL_WIDTH,
    ...colMaxLength.map((length, column) =>
      topViewColumnWidth(length, body.map((cells) => cells[column + 1])),
    ),
  ];
  return rows;
}

// 列宽：按该列各摞最大长缩放，并保证至少容纳格内最长一行文本。
function topViewColumnWidth(maxLength, cells) {
  const textWidth = Math.max(0, ...cells.map((cell) => longestLineLength(excelCellValue(cell))));
  const scaled = maxLength * TOP_VIEW_LENGTH_TO_WIDTH;
  return Math.round(clampNumber(Math.max(scaled, textWidth + 2), TOP_VIEW_MIN_WIDTH, TOP_VIEW_MAX_WIDTH));
}

// 行高：按该行各摞最大宽缩放，并保证至少容纳格内逐层书写的行数。
function topViewRowHeight(maxWidth, cells) {
  const lineCount = Math.max(1, ...cells.map((cell) => excelCellValue(cell).split(/\r\n|\r|\n/).length));
  const scaled = maxWidth * TOP_VIEW_WIDTH_TO_HEIGHT;
  return Math.round(clampNumber(Math.max(scaled, lineCount * TOP_VIEW_LINE_HEIGHT), TOP_VIEW_MIN_HEIGHT, TOP_VIEW_MAX_HEIGHT));
}

function longestLineLength(text) {
  return Math.max(0, ...String(text).split(/\r\n|\r|\n/).map((line) => line.length));
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function buildPlacementStacks(placements) {
  const stacks = [];
  const stackByPlacement = new Map();
  [...placements]
    .sort((first, second) => first.z - second.z)
    .forEach((placement) => {
      const supporters = placementSupporters(placement, [...stackByPlacement.keys()]);
      const stack = mergeSupporterStacks(supporters, stacks, stackByPlacement) ?? createPlacementStack(placement);
      stack.placements.push(placement);
      stack.minX = Math.min(stack.minX, placement.x);
      stack.maxX = Math.max(stack.maxX, placement.x + placement.length);
      stack.minY = Math.min(stack.minY, placement.y);
      stack.maxY = Math.max(stack.maxY, placement.y + placement.width);
      stackByPlacement.set(placement, stack);
      if (supporters.length === 0) {
        stacks.push(stack);
      }
    });
  return stacks;
}

function placementSupporters(placement, candidates) {
  const belowPlacements = candidates.filter((candidate) => {
    const candidateTop = candidate.z + candidate.height;
    return candidateTop <= placement.z && placementFootprintsOverlap(placement, candidate);
  });
  const supportTop = Math.max(...belowPlacements.map((candidate) => candidate.z + candidate.height));
  if (!Number.isFinite(supportTop)) {
    return [];
  }
  return belowPlacements.filter((candidate) => candidate.z + candidate.height === supportTop);
}

function mergeSupporterStacks(supporters, stacks, stackByPlacement) {
  if (supporters.length === 0) {
    return null;
  }

  const supporterStacks = [...new Set(supporters.map((supporter) => stackByPlacement.get(supporter)).filter(Boolean))];
  const targetStack = supporterStacks[0];
  supporterStacks.slice(1).forEach((stack) => {
    targetStack.placements.push(...stack.placements);
    targetStack.minX = Math.min(targetStack.minX, stack.minX);
    targetStack.maxX = Math.max(targetStack.maxX, stack.maxX);
    targetStack.minY = Math.min(targetStack.minY, stack.minY);
    targetStack.maxY = Math.max(targetStack.maxY, stack.maxY);
    stack.placements.forEach((placement) => stackByPlacement.set(placement, targetStack));
    const stackIndex = stacks.indexOf(stack);
    if (stackIndex >= 0) {
      stacks.splice(stackIndex, 1);
    }
  });
  return targetStack;
}

function createPlacementStack(placement) {
  return {
    placements: [],
    minX: placement.x,
    maxX: placement.x + placement.length,
    minY: placement.y,
    maxY: placement.y + placement.width,
  };
}

function placementFootprintsOverlap(first, second) {
  return intervalsOverlap(first.x, first.x + first.length, second.x, second.x + second.length)
    && intervalsOverlap(first.y, first.y + first.width, second.y, second.y + second.width);
}

// 一摞格子的逐层内容：按高度 z 从下到上书写，每层按 长*宽*高 聚合数量。
function layerSizeSummaries(placements) {
  const byHeight = new Map();
  placements.forEach((placement) => {
    const layer = byHeight.get(placement.z) ?? [];
    layer.push(placement);
    byHeight.set(placement.z, layer);
  });
  return [...byHeight.entries()]
    .sort((first, second) => first[0] - second[0])
    .flatMap(([, layer]) => placementSizeSummaries(layer));
}

function intervalsOverlap(firstStart, firstEnd, secondStart, secondEnd) {
  return firstStart < secondEnd && firstEnd > secondStart;
}

function excelCellValue(value) {
  if (value && typeof value === "object" && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, "value")) {
    return excelCellValue(value.value);
  }
  if (value === null || value === undefined) {
    return "";
  }
  return typeof value === "number" ? Number(value).toString() : String(value);
}

function normalizeExcelCell(value) {
  if (value && typeof value === "object" && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, "value")) {
    return {
      value: value.value,
      styleKey: value.styleKey ?? "",
    };
  }
  return { value, styleKey: "" };
}

function downloadExcelWorkbook(content, fileName) {
  const blob = new Blob([content], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadHtmlReport(content, fileName) {
  const blob = new Blob([content], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function createZipArchive(files) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  let offset = 0;

  Object.entries(files).forEach(([fileName, content]) => {
    const nameBytes = encoder.encode(fileName);
    const data = encoder.encode(content);
    const checksum = crc32(data);
    const localHeader = zipLocalHeader(nameBytes, data, checksum);
    const centralHeader = zipCentralDirectoryHeader(nameBytes, data, checksum, offset);
    localParts.push(localHeader, data);
    centralParts.push(centralHeader);
    offset += localHeader.length + data.length;
  });

  const centralDirectorySize = centralParts.reduce((total, part) => total + part.length, 0);
  const endRecord = zipEndRecord(centralParts.length, centralDirectorySize, offset);
  return concatUint8Arrays([...localParts, ...centralParts, endRecord]);
}

function zipLocalHeader(nameBytes, data, checksum) {
  const header = new Uint8Array(30 + nameBytes.length);
  const view = new DataView(header.buffer);
  view.setUint32(0, 0x04034b50, true);
  view.setUint16(4, 20, true);
  view.setUint16(6, 0, true);
  view.setUint16(8, 0, true);
  view.setUint16(10, 0, true);
  view.setUint16(12, 0, true);
  view.setUint32(14, checksum, true);
  view.setUint32(18, data.length, true);
  view.setUint32(22, data.length, true);
  view.setUint16(26, nameBytes.length, true);
  view.setUint16(28, 0, true);
  header.set(nameBytes, 30);
  return header;
}

function zipCentralDirectoryHeader(nameBytes, data, checksum, offset) {
  const header = new Uint8Array(46 + nameBytes.length);
  const view = new DataView(header.buffer);
  view.setUint32(0, 0x02014b50, true);
  view.setUint16(4, 20, true);
  view.setUint16(6, 20, true);
  view.setUint16(8, 0, true);
  view.setUint16(10, 0, true);
  view.setUint16(12, 0, true);
  view.setUint16(14, 0, true);
  view.setUint32(16, checksum, true);
  view.setUint32(20, data.length, true);
  view.setUint32(24, data.length, true);
  view.setUint16(28, nameBytes.length, true);
  view.setUint16(30, 0, true);
  view.setUint16(32, 0, true);
  view.setUint16(34, 0, true);
  view.setUint16(36, 0, true);
  view.setUint32(38, 0, true);
  view.setUint32(42, offset, true);
  header.set(nameBytes, 46);
  return header;
}

function zipEndRecord(entryCount, centralDirectorySize, centralDirectoryOffset) {
  const record = new Uint8Array(22);
  const view = new DataView(record.buffer);
  view.setUint32(0, 0x06054b50, true);
  view.setUint16(4, 0, true);
  view.setUint16(6, 0, true);
  view.setUint16(8, entryCount, true);
  view.setUint16(10, entryCount, true);
  view.setUint32(12, centralDirectorySize, true);
  view.setUint32(16, centralDirectoryOffset, true);
  view.setUint16(20, 0, true);
  return record;
}

function concatUint8Arrays(parts) {
  const totalLength = parts.reduce((total, part) => total + part.length, 0);
  const output = new Uint8Array(totalLength);
  let offset = 0;
  parts.forEach((part) => {
    output.set(part, offset);
    offset += part.length;
  });
  return output;
}

function crc32(bytes) {
  let checksum = 0xffffffff;
  bytes.forEach((byte) => {
    checksum = (checksum >>> 8) ^ CRC32_TABLE[(checksum ^ byte) & 0xff];
  });
  return (checksum ^ 0xffffffff) >>> 0;
}

function buildCrc32Table() {
  return Array.from({ length: 256 }, (_, index) => {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    return value >>> 0;
  });
}

function nextAlphabeticId(prefix, selector) {
  const usedIds = new Set([...document.querySelectorAll(selector)].map((input) => input.value.trim()));
  let index = 0;
  let id = `${prefix}-${alphabeticLabel(index)}`;
  while (usedIds.has(id)) {
    index += 1;
    id = `${prefix}-${alphabeticLabel(index)}`;
  }
  return id;
}

function alphabeticLabel(index) {
  let value = index;
  let label = "";
  do {
    label = String.fromCharCode(65 + (value % 26)) + label;
    value = Math.floor(value / 26) - 1;
  } while (value >= 0);
  return label;
}

async function calculatePacking(options = {}) {
  try {
    stopPackingAnimation();
    setBusy(true);
    clearError();
    const input = readInputFromForm();
    const response = await fetch("/api/pack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const data = await readJsonResponse(response);
    if (!response.ok) {
      throw new Error(data.error || "计算失败");
    }
    state.input = input;
    state.result = data.result;
    if (options.recordHistory !== false) {
      await addHistoryRecord(input, data.result);
    }
    state.selectedContainerId = null;
    state.selectedInstanceId = null;
    state.hoveredInstanceId = null;
    state.focusedBoxId = null;
    resetAnimationState({ showFull: true });
    hideSceneTooltip();
    renderContainerSelector(data.result);
    renderResult(data.result);
    selectContainer(elements.containerSelector.value, { preserveSelection: false });
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

function loadHistoryRecords() {
  try {
    const records = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || "[]");
    return normalizeHistoryRecords(records);
  } catch {
    return [];
  }
}

async function loadPersistedHistoryRecords() {
  const localRecords = loadHistoryRecords();
  try {
    const response = await fetch("/api/history");
    if (!response.ok) {
      return localRecords;
    }
    const data = await readJsonResponse(response);
    const serverRecords = normalizeHistoryRecords(data.records);
    if (serverRecords.length > 0) {
      saveHistoryRecords(serverRecords);
      return serverRecords;
    }
    if (localRecords.length > 0) {
      await savePersistedHistoryRecords(localRecords);
    }
  } catch {
    return localRecords;
  }
  return localRecords;
}

function saveHistoryRecords(records = state.historyRecords) {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(normalizeHistoryRecords(records)));
  } catch {
    // Ignore storage failures. The current calculation result is still usable.
  }
}

async function savePersistedHistoryRecords(records = state.historyRecords) {
  saveHistoryRecords(records);
  try {
    await fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ records: normalizeHistoryRecords(records) }),
    });
  } catch {
    // Browser localStorage remains the fallback when the page is not served by the bundled app.
  }
}

function normalizeHistoryRecords(records) {
  if (!Array.isArray(records)) {
    return [];
  }
  return records
    .filter((record) => record?.id && record?.input && record?.result)
    .slice(0, MAX_HISTORY_RECORDS);
}

async function addHistoryRecord(input, result) {
  const record = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    input: structuredClone(input),
    result: structuredClone(result),
  };
  state.historyRecords = [record, ...state.historyRecords].slice(0, MAX_HISTORY_RECORDS);
  state.selectedHistoryId = record.id;
  await savePersistedHistoryRecords();
  renderHistoryRecords();
}

function renderHistoryRecords() {
  if (!elements.historyList) {
    return;
  }
  if (state.historyRecords.length === 0) {
    elements.historyList.textContent = "暂无计算记录";
    elements.historyList.classList.add("muted-text");
    return;
  }
  elements.historyList.classList.remove("muted-text");
  elements.historyList.innerHTML = state.historyRecords
    .map((record) => {
      const active = record.id === state.selectedHistoryId ? " active" : "";
      return `
        <button type="button" class="history-record${active}" data-history-id="${escapeAttribute(record.id)}">
          ${historyRecordLabel(record)}
        </button>
      `;
    })
    .join("");
  elements.historyList.querySelectorAll(".history-record").forEach((button) => {
    button.addEventListener("click", () => selectHistoryRecord(button.dataset.historyId));
  });
}

function selectHistoryRecord(recordId) {
  const record = state.historyRecords.find((item) => item.id === recordId);
  if (!record) {
    return;
  }
  stopPackingAnimation();
  state.selectedHistoryId = record.id;
  state.input = normalizeInput(structuredClone(record.input));
  state.result = structuredClone(record.result);
  state.selectedContainerId = null;
  state.selectedInstanceId = null;
  state.hoveredInstanceId = null;
  state.focusedBoxId = null;
  writeInputToForm(state.input);
  clearError();
  resetAnimationState({ showFull: true });
  hideSceneTooltip();
  renderContainerSelector(state.result);
  renderResult(state.result);
  renderHistoryRecords();
  selectContainer(elements.containerSelector.value, { preserveSelection: false });
}

function historyRecordLabel(record) {
  const created = new Date(record.createdAt);
  const time = Number.isNaN(created.getTime()) ? "未知时间" : created.toLocaleString("zh-CN", { hour12: false });
  const result = record.result ?? {};
  const loaded = result.loaded_count ?? 0;
  const unloaded = result.unloaded_count ?? 0;
  const util = formatPercent(result.volume_utilization);
  const mode = searchModeLabel(record.input?.search_mode ?? "balanced");
  return `
    <span class="history-time">${escapeHtml(time)}</span>
    <span class="history-mode">${escapeHtml(mode)}</span>
    <span class="history-headline">
      <span class="history-stat history-loaded"><em>已装</em><b>${loaded}</b></span>
      <span class="history-stat history-unloaded"><em>未装</em><b>${unloaded}</b></span>
    </span>
    <span class="history-util">${util}</span>
  `;
}

function searchModeLabel(value) {
  const labels = {
    fast: "快速",
    balanced: "均衡",
    high_utilization: "高装载率",
  };
  return labels[value] ?? labels.balanced;
}

function readInputFromForm() {
  return {
    containers: readContainersFromForm(),
    boxes: readBoxesFromForm(),
    objective: "maximize_volume",
    search_mode: elements.searchModeSelect.value,
  };
}

function readContainersFromForm() {
  const containers = [...elements.containerTableBody.querySelectorAll("tr")].map((row, index) => {
    const id = row.querySelector(".container-id").value.trim();
    if (!id) {
      throw new Error(`第 ${index + 1} 行 ULD 缺少 ID`);
    }
    const crossSection = validateCrossSection(row.querySelector(".container-cross-section").value, `${id} 截面`);
    return {
      id,
      length: readPositiveNumber(row.querySelector(".container-length").value, `${id} 长度`),
      quantity: readNonNegativeInteger(row.querySelector(".container-quantity").value, `${id} 数量`),
      cross_section: crossSection,
    };
  });
  if (containers.length === 0) {
    throw new Error("至少需要 1 个 ULD");
  }
  return containers;
}

function readBoxesFromForm() {
  return [...elements.boxTableBody.querySelectorAll("tr")].map((row, index) => {
    const id = row.querySelector(".box-id").value.trim();
    if (!id) {
      throw new Error(`第 ${index + 1} 行箱子缺少 ID`);
    }
    const box = {
      id,
      length: readPositiveNumber(row.querySelector(".box-length").value, `${id} 长度`),
      width: readPositiveNumber(row.querySelector(".box-width").value, `${id} 宽度`),
      height: readPositiveNumber(row.querySelector(".box-height").value, `${id} 高度`),
      quantity: readNonNegativeInteger(row.querySelector(".box-quantity").value, `${id} 数量`),
      rotatable: row.querySelector(".box-rotatable").checked,
    };
    const requiredContainerTypes = parseRequiredContainerTypes(row.querySelector(".box-required-container-types").value);
    if (requiredContainerTypes.length > 0) {
      box.required_container_types = requiredContainerTypes;
    }
    return box;
  });
}

function validateCrossSection(rawValue, name) {
  let crossSection;
  try {
    crossSection = JSON.parse(rawValue);
  } catch {
    throw new Error(`${name} 必须是 JSON 数组`);
  }
  if (!Array.isArray(crossSection) || crossSection.length < 3) {
    throw new Error(`${name} 至少需要 3 个点`);
  }
  crossSection.forEach((point, index) => {
    if (!Array.isArray(point) || point.length !== 2 || point.some((value) => !Number.isFinite(Number(value)))) {
      throw new Error(`${name} 的第 ${index + 1} 个点必须是 [y,z] 数组`);
    }
  });
  return crossSection.map(([y, z]) => [Number(y), Number(z)]);
}

function readPositiveNumber(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) {
    throw new Error(`${name} 必须大于 0`);
  }
  return number;
}

function readPositiveInteger(value, name) {
  const number = Number(value);
  if (!Number.isInteger(number) || number <= 0) {
    throw new Error(`${name} 必须是正整数`);
  }
  return number;
}

function readNonNegativeInteger(value, name) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 0) {
    throw new Error(`${name} 必须是非负整数`);
  }
  return number;
}

function configureSliceControl(length) {
  const max = Math.max(1, Math.floor(Number(length)));
  elements.sliceSlider.max = String(max);
  elements.sliceSlider.step = String(Math.max(1, Math.round(max / 300)));
  state.sliceX = clamp(state.sliceX, 0, max);
  elements.sliceSlider.value = String(state.sliceX);
  updateSliceValue();
}

function updateSliceValue() {
  elements.sliceValue.textContent = formatNumber(state.sliceX);
}

function renderContainerSelector(result) {
  const containers = result.containers ?? [{ container_id: result.uld_id, container_type: result.uld_id, loaded_count: result.loaded_count }];
  elements.containerSelector.innerHTML = containers
    .map((container) => {
      const label = `${container.container_id}（${container.container_type ?? container.uld_id}，已装 ${container.loaded_count ?? 0}）`;
      return `<option value="${escapeAttribute(container.container_id)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  const firstContainerId = containers[0]?.container_id ?? "";
  elements.containerSelector.value = state.selectedContainerId && containers.some((item) => item.container_id === state.selectedContainerId)
    ? state.selectedContainerId
    : firstContainerId;
}

function selectContainer(containerId, options = {}) {
  if (!state.result) {
    return;
  }
  if (!options.preserveAnimation) {
    resetAnimationState({ showFull: true });
  }
  state.selectedContainerId = containerId || firstResultContainerId(state.result);
  state.hoveredInstanceId = null;
  state.focusedBoxId = null;
  hideSceneTooltip();
  if (elements.containerSelector.value !== state.selectedContainerId) {
    elements.containerSelector.value = state.selectedContainerId;
  }
  const activeResult = getActiveResult();
  const activeInput = getActiveProfileInput();
  if (!options.preserveSelection) {
    state.selectedInstanceId = activeResult?.placements?.[0]?.instance_id ?? null;
  }
  if (!activeResult?.placements?.some((placement) => placement.instance_id === state.selectedInstanceId)) {
    state.selectedInstanceId = activeResult?.placements?.[0]?.instance_id ?? null;
  }
  if (activeInput) {
    configureSliceControl(activeInput.uld.length);
  }
  if (state.selectedInstanceId) {
    syncSliceToSelectedPlacement();
  }
  renderActiveContainerDetails();
  drawAllViews();
}

function firstResultContainerId(result) {
  return result.containers?.[0]?.container_id ?? result.uld_id ?? "";
}

function getActiveResult() {
  if (!state.result?.containers) {
    return state.result;
  }
  return state.result.containers.find((container) => container.container_id === state.selectedContainerId) ?? state.result.containers[0] ?? null;
}

function getActiveProfileInput() {
  if (!state.input) {
    return null;
  }
  const containers = expandContainerSpecs(state.input.containers);
  const active = containers.find((container) => container.container_id === state.selectedContainerId) ?? containers[0];
  if (!active) {
    return null;
  }
  return {
    uld: {
      id: active.container_id,
      length: active.length,
      cross_section: active.cross_section,
    },
    boxes: state.input.boxes,
    objective: state.input.objective ?? "maximize_volume",
    search_mode: state.input.search_mode ?? "balanced",
  };
}

function expandContainerSpecs(containers) {
  const counters = new Map();
  return containers.flatMap((container) => {
    const quantity = Number(container.quantity ?? 1);
    return Array.from({ length: quantity }, () => {
      const index = (counters.get(container.id) ?? 0) + 1;
      counters.set(container.id, index);
      return {
        container_id: `${container.id}-${String(index).padStart(3, "0")}`,
        container_type: container.id,
        length: Number(container.length),
        cross_section: container.cross_section,
      };
    });
  });
}

function renderResult(result) {
  const utilization = formatPercent(result.volume_utilization);
  elements.summaryCards.innerHTML = `
    ${summaryCard("已装箱", result.loaded_count)}
    ${summaryCard("未装箱", result.unloaded_count)}
    ${summaryCard("体积利用率", utilization)}
    ${summaryCard("校验", result.validation_passed ? "通过" : "失败", result.validation_passed ? "ok" : "bad")}
  `;

  renderUnloadedList(result);
  renderActiveContainerDetails();
}

function renderActiveContainerDetails() {
  const activeResult = getActiveResult();
  renderActiveContainerStats(activeResult);
  renderLoadedList(activeResult);
  const placements = activeResult?.placements ?? [];
  const rows = placements
    .slice(0, 300)
    .map(
      (placement) => `
      <tr data-instance-id="${escapeAttribute(placement.instance_id)}" class="${placement.instance_id === state.selectedInstanceId ? "selected-row" : ""}">
        <td>${escapeHtml(placement.instance_id)}</td>
        <td>${formatNumber(placement.x)}</td>
        <td>${formatNumber(placement.y)}</td>
        <td>${formatNumber(placement.z)}</td>
        <td>${formatNumber(placement.length)}</td>
        <td>${formatNumber(placement.width)}</td>
        <td>${formatNumber(placement.height)}</td>
      </tr>
    `,
    )
    .join("");
  elements.placementsTableBody.innerHTML = rows;
  elements.placementsTableBody.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => selectPlacement(row.dataset.instanceId, { syncSlice: true, focusSameBoxType: true }));
  });
  renderSelectedBoxDetails();
}

function renderActiveContainerStats(activeResult) {
  if (!activeResult) {
    elements.activeContainerStats.classList.add("muted-text");
    elements.activeContainerStats.innerHTML = activeContainerStatsMarkup(null);
    return;
  }

  elements.activeContainerStats.classList.remove("muted-text");
  elements.activeContainerStats.innerHTML = activeContainerStatsMarkup(activeResult);
}

function activeContainerStatsMarkup(activeResult) {
  if (!activeResult) {
    return `
    <div><span>单个 ULD 装载率</span><strong>--</strong></div>
    <div><span>已装箱</span><strong>--</strong></div>
    <div><span>已用体积</span><strong>-- / --</strong></div>
  `;
  }

  const utilization = formatPercent(activeResult.volume_utilization);
  const loadedCount = activeResult.loaded_count ?? 0;
  const usedVolume = formatNumber(activeResult.used_volume ?? 0);
  const uldVolume = formatNumber(activeResult.uld_volume ?? 0);
  return `
    <div><span>单个 ULD 装载率</span><strong>${utilization}</strong></div>
    <div><span>已装箱</span><strong>${loadedCount}</strong></div>
    <div><span>已用体积</span><strong>${usedVolume} / ${uldVolume}</strong></div>
  `;
}

function renderLoadedList(result) {
  const loaded = result ? result.loaded ?? loadedSummaryFromPlacements(result.placements ?? []) : [];
  if (loaded.length === 0) {
    elements.loadedList.textContent = "暂无";
    elements.loadedList.classList.add("muted-text");
    return;
  }

  elements.loadedList.classList.remove("muted-text");
  elements.loadedList.innerHTML = loadedListMarkup(result, state.input);
}

function loadedListMarkup(result, input = state.input) {
  const loaded = result.loaded ?? loadedSummaryFromPlacements(result.placements ?? []);
  const inputBoxById = new Map((input?.boxes ?? []).map((box) => [box.id, box]));
  return loaded
    .map((item) => {
      const dimensions = boxItemDimensions(item, inputBoxById.get(item.box_id));
      const dimensionText = dimensions ? ` (${dimensions})` : "";
      return `<div>${escapeHtml(item.box_id)}${dimensionText} × ${item.quantity}</div>`;
    })
    .join("");
}

function boxItemDimensions(item, inputBox) {
  const source = [item, inputBox].find((candidate) =>
    candidate && [candidate.length, candidate.width, candidate.height].every((value) => Number.isFinite(Number(value)))
  );
  if (!source) {
    return "";
  }
  return [source.length, source.width, source.height].map(formatNumber).join(" × ");
}

function renderUnloadedList(result) {
  const unloaded = result.unloaded ?? [];
  if (unloaded.length === 0) {
    elements.unloadedList.textContent = "暂无";
    elements.unloadedList.classList.add("muted-text");
    return;
  }

  elements.unloadedList.classList.remove("muted-text");
  elements.unloadedList.innerHTML = unloadedListMarkup(result, state.input);
}

function unloadedListMarkup(result, input = state.input) {
  const unloaded = result.unloaded ?? [];
  const inputBoxById = new Map((input?.boxes ?? []).map((box) => [box.id, box]));
  return unloaded
    .map((item) => {
      const dimensions = boxItemDimensions(item, inputBoxById.get(item.box_id));
      const dimensionText = dimensions ? ` (${dimensions})` : "";
      return `<div>${escapeHtml(item.box_id)}${dimensionText} × ${item.quantity}：${escapeHtml(item.reason)}</div>`;
    })
    .join("");
}

function loadedSummaryFromPlacements(placements) {
  const counter = new Map();
  placements.forEach((placement) => {
    counter.set(placement.box_id, (counter.get(placement.box_id) ?? 0) + 1);
  });
  return [...counter.entries()]
    .sort(([first], [second]) => first.localeCompare(second))
    .map(([box_id, quantity]) => ({ box_id, quantity }));
}

function summaryCard(label, value, className = "") {
  return `
    <div class="summary-card">
      <span>${label}</span>
      <strong class="${className}">${value}</strong>
    </div>
  `;
}

function togglePackingAnimation() {
  if (state.animation.active) {
    stopPackingAnimation();
    updateAnimationControls();
    return;
  }
  startPackingAnimation();
}

function resetPackingAnimation() {
  resetAnimationState({ showFull: false });
  drawScene();
}

function setAnimationSpeed(value) {
  const nextSpeed = clamp(Number(value), 0.5, 4);
  if (state.animation.active) {
    state.animation.elapsed = animationElapsedAt(performance.now());
    state.animation.startedAt = performance.now();
  }
  state.animation.speed = nextSpeed;
  elements.animationSpeedSlider.value = String(nextSpeed);
  updateAnimationControls();
}

function startPackingAnimation() {
  const total = getActiveResult()?.placements?.length ?? 0;
  if (!total) {
    updateAnimationControls();
    return;
  }
  if (state.animation.visibleCount === null || state.animation.visibleCount >= total) {
    state.animation.elapsed = 0;
    state.animation.visibleCount = 0;
  }
  state.animation.active = true;
  state.animation.startedAt = performance.now();
  state.animation.frameId = requestAnimationFrame(animationFrame);
  updateAnimationControls();
}

function stopPackingAnimation() {
  if (state.animation.frameId !== null) {
    cancelAnimationFrame(state.animation.frameId);
  }
  if (state.animation.active) {
    state.animation.elapsed = animationElapsedAt(performance.now());
  }
  state.animation.active = false;
  state.animation.frameId = null;
}

function animationFrame(timestamp) {
  const activeResult = getActiveResult();
  const total = activeResult?.placements?.length ?? 0;
  const elapsed = animationElapsedAt(timestamp);
  state.animation.visibleCount = Math.min(total, Math.floor(elapsed / BOX_ANIMATION_INTERVAL_MS));
  drawScene();

  if (state.animation.visibleCount >= total) {
    state.animation.elapsed = total * BOX_ANIMATION_INTERVAL_MS;
    state.animation.active = false;
    state.animation.frameId = null;
    updateAnimationControls();
    return;
  }

  state.animation.frameId = requestAnimationFrame(animationFrame);
  updateAnimationControls();
}

function visibleScenePlacements(activeResult) {
  let placements = activeResult?.placements ?? [];
  if (state.animation.visibleCount !== null) {
    placements = placements.slice(0, state.animation.visibleCount);
  }
  return state.focusedBoxId ? placements.filter((placement) => placement.box_id === state.focusedBoxId) : placements;
}

function resetAnimationState({ showFull }) {
  stopPackingAnimation();
  state.animation.elapsed = 0;
  state.animation.visibleCount = showFull ? null : 0;
  updateAnimationControls();
}

function animationElapsedAt(timestamp) {
  if (!state.animation.active) {
    return state.animation.elapsed;
  }
  return state.animation.elapsed + (timestamp - state.animation.startedAt) * state.animation.speed;
}

function updateAnimationControls() {
  const total = getActiveResult()?.placements?.length ?? 0;
  const visible = state.animation.visibleCount === null ? total : Math.min(total, state.animation.visibleCount);
  elements.animationPlayButton.disabled = total === 0;
  elements.animationResetButton.disabled = total === 0;
  elements.animationPlayButton.textContent = state.animation.active ? "暂停动画" : "播放动画";
  elements.animationSpeedValue.textContent = `${formatSpeed(state.animation.speed)}x`;
  elements.animationProgress.textContent = state.animation.visibleCount === null ? "完整结果" : `${visible} / ${total}`;
}

function drawAllViews() {
  drawScene();
  drawProjectionViews();
}

function drawScene() {
  const { canvas, context, rect } = setupCanvas(elements.canvas);
  state.hitRegions.scene = [];
  context.clearRect(0, 0, rect.width, rect.height);

  const activeInput = getActiveProfileInput();
  if (!activeInput) {
    return;
  }

  const activeResult = getActiveResult();
  const dimensions = getSceneDimensions(activeInput);
  const viewport = getSceneViewport(rect, dimensions);
  const projector = (point) => projectPoint(point, dimensions, viewport, rect);
  drawFloorGrid(context, projector, dimensions);
  drawPrism(context, activeInput, projector);

  if (activeResult) {
    const visiblePlacements = visibleScenePlacements(activeResult);
    const latestAnimatedId = currentAnimatedInstanceId(visiblePlacements);
    const boxFaces = visiblePlacements.flatMap((placement) => createBoxFaces(placement, latestAnimatedId));
    drawFaces(context, boxFaces, projector, state.hitRegions.scene);
    drawBoxWireframes(context, visiblePlacements, projector, latestAnimatedId);
  }

  drawPrismEdges(context, activeInput, projector);
  drawAxes(context, projector, dimensions);
  drawBackgroundText(context, rect);
}

function drawProjectionViews() {
  if (!getActiveProfileInput()) {
    return;
  }
  drawTopView();
  drawSideView();
  drawSectionView();
}

function drawTopView() {
  const view = setupProjectionCanvas(elements.topViewCanvas, "top");
  const mapper = createPlaneMapper(view.rect, view.dimensions.length, view.dimensions.maxY, "x", "y");
  drawProjectionFrame(view.context, view.rect, "x 长度", "y 宽度");
  drawProjectionUldRect(view.context, mapper, view.dimensions.length, view.dimensions.maxY);
  drawProjectionBoxes(view.context, mapper, "top");
  drawSliceLine(view.context, mapper, view.dimensions.maxY);
}

function drawSideView() {
  const view = setupProjectionCanvas(elements.sideViewCanvas, "side");
  const mapper = createPlaneMapper(view.rect, view.dimensions.length, view.dimensions.maxZ, "x", "z");
  drawProjectionFrame(view.context, view.rect, "x 长度", "z 高度");
  drawProjectionUldRect(view.context, mapper, view.dimensions.length, view.dimensions.maxZ);
  drawProjectionBoxes(view.context, mapper, "side");
  drawSliceLine(view.context, mapper, view.dimensions.maxZ);
}

function drawSectionView() {
  const view = setupProjectionCanvas(elements.sectionViewCanvas, "section");
  const mapper = createPlaneMapper(view.rect, view.dimensions.maxY, view.dimensions.maxZ, "y", "z");
  drawProjectionFrame(view.context, view.rect, "y 宽度", "z 高度");
  drawSectionPolygon(view.context, mapper, getActiveProfileInput().uld.cross_section);
  drawProjectionBoxes(view.context, mapper, "section");
}

function setupProjectionCanvas(canvas, key) {
  const { context, rect } = setupCanvas(canvas);
  state.hitRegions[key] = [];
  context.clearRect(0, 0, rect.width, rect.height);
  return { context, rect, dimensions: getSceneDimensions(getActiveProfileInput()) };
}

function setupCanvas(canvas) {
  const context = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { canvas, context, rect };
}

function themeCssValue(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function createPlaneMapper(rect, worldWidth, worldHeight, horizontalAxis, verticalAxis) {
  const padding = 34;
  const usableWidth = Math.max(1, rect.width - padding * 2);
  const usableHeight = Math.max(1, rect.height - padding * 2);
  const scale = Math.min(usableWidth / worldWidth, usableHeight / worldHeight);
  const offsetX = (rect.width - worldWidth * scale) / 2;
  const offsetY = (rect.height - worldHeight * scale) / 2;
  return {
    horizontalAxis,
    verticalAxis,
    toScreen(horizontal, vertical) {
      return {
        x: offsetX + horizontal * scale,
        y: rect.height - offsetY - vertical * scale,
      };
    },
    rectToScreen(horizontal, vertical, width, height) {
      const start = this.toScreen(horizontal, vertical + height);
      return {
        x: start.x,
        y: start.y,
        width: width * scale,
        height: height * scale,
      };
    },
  };
}

function drawProjectionFrame(context, rect, horizontalLabel, verticalLabel) {
  context.save();
  context.fillStyle = themeCssValue("--muted-strong", "rgba(226, 232, 240, 0.76)");
  context.font = "12px system-ui, sans-serif";
  context.fillText(horizontalLabel, rect.width - 80, rect.height - 12);
  context.fillText(verticalLabel, 12, 18);
  context.restore();
}

function drawProjectionUldRect(context, mapper, width, height) {
  const rect = mapper.rectToScreen(0, 0, width, height);
  context.save();
  context.strokeStyle = themeCssValue("--accent", "rgba(186, 230, 253, 0.75)");
  context.lineWidth = 1.6;
  context.strokeRect(rect.x, rect.y, rect.width, rect.height);
  context.restore();
}

function drawSectionPolygon(context, mapper, points) {
  context.save();
  context.beginPath();
  points.forEach(([y, z], index) => {
    const point = mapper.toScreen(y, z);
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });
  context.closePath();
  context.fillStyle = "rgba(56, 189, 248, 0.08)";
  context.strokeStyle = "rgba(186, 230, 253, 0.85)";
  context.lineWidth = 1.8;
  context.fill();
  context.stroke();
  context.restore();
}

function drawProjectionBoxes(context, mapper, viewKey) {
  if (!getActiveResult()) {
    return;
  }

  const placements = placementsForView(viewKey);
  placements.forEach((placement) => {
    const color = colorForBox(placement.box_id);
    const rect = projectionRectForPlacement(mapper, placement, viewKey);
    const isSelected = placement.instance_id === state.selectedInstanceId;
    const strokeColor = lightenColor(color, isSelected ? 0.58 : 0.34);
    context.save();
    context.fillStyle = rgbaColor(color, isSelected ? 0.84 : 0.56);
    context.strokeStyle = isSelected ? "#fef08a" : rgbaColor(strokeColor, 0.96);
    context.lineWidth = isSelected ? 3 : 1.2;
    context.fillRect(rect.x, rect.y, rect.width, rect.height);
    context.strokeRect(rect.x, rect.y, rect.width, rect.height);
    if (isSelected) {
      context.fillStyle = "#fff7ed";
      context.font = "11px system-ui, sans-serif";
      context.fillText(placement.instance_id, rect.x + 4, rect.y + 14);
    }
    context.restore();
    state.hitRegions[viewKey].push({ instanceId: placement.instance_id, rect });
  });
}

function placementsForView(viewKey) {
  const activeResult = getActiveResult();
  const placements = activeResult?.placements ?? [];
  if (viewKey !== "section") {
    return placements;
  }
  return placements.filter((placement) => placement.x <= state.sliceX && state.sliceX <= placement.x + placement.length);
}

function projectionRectForPlacement(mapper, placement, viewKey) {
  if (viewKey === "top") {
    return mapper.rectToScreen(placement.x, placement.y, placement.length, placement.width);
  }
  if (viewKey === "side") {
    return mapper.rectToScreen(placement.x, placement.z, placement.length, placement.height);
  }
  return mapper.rectToScreen(placement.y, placement.z, placement.width, placement.height);
}

function drawSliceLine(context, mapper, verticalMax) {
  const start = mapper.toScreen(state.sliceX, 0);
  const end = mapper.toScreen(state.sliceX, verticalMax);
  context.save();
  context.strokeStyle = "#fef08a";
  context.lineWidth = 2;
  context.setLineDash([6, 5]);
  context.beginPath();
  context.moveTo(start.x, start.y);
  context.lineTo(end.x, end.y);
  context.stroke();
  context.fillStyle = "#fef08a";
  context.font = "12px system-ui, sans-serif";
  context.fillText(`x=${formatNumber(state.sliceX)}`, start.x + 6, 18);
  context.restore();
}

function getSceneDimensions(input) {
  return {
    length: Number(input.uld.length),
    maxY: Math.max(...input.uld.cross_section.map(([y]) => y)),
    maxZ: Math.max(...input.uld.cross_section.map(([, z]) => z)),
  };
}

function getSceneScale(rect, dimensions) {
  return getSceneViewport(rect, dimensions).scale;
}

function getSceneViewport(rect, dimensions) {
  const bounds = sceneViewportBounds(dimensions);
  const usableWidth = Math.max(1, rect.width - SCENE_SAFE_PADDING * 2);
  const usableHeight = Math.max(1, rect.height - SCENE_SAFE_PADDING * 2);
  const scale =
    Math.min(usableWidth / Math.max(bounds.width, 1), usableHeight / Math.max(bounds.height, 1)) * state.camera.zoom;
  return {
    scale,
    offsetX: rect.width / 2 + state.camera.panX - ((bounds.minX + bounds.maxX) / 2) * scale,
    offsetY: rect.height / 2 + state.camera.panY - ((bounds.minY + bounds.maxY) / 2) * scale,
  };
}

function sceneViewportBounds(dimensions) {
  const projected = sceneEnvelopePoints(dimensions).map((point) => projectScenePoint(point, dimensions));
  const xs = projected.map((point) => point.x);
  const ys = projected.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    minY,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

function sceneEnvelopePoints(dimensions) {
  const length = dimensions.length;
  const maxY = dimensions.maxY;
  const maxZ = dimensions.maxZ;
  const xAxisEnd = dimensions.length * AXIS_EXTENSION_FACTOR;
  const yAxisEnd = dimensions.maxY * AXIS_EXTENSION_FACTOR;
  const zAxisEnd = dimensions.maxZ * AXIS_EXTENSION_FACTOR;
  return [
    { x: 0, y: 0, z: 0 },
    { x: length, y: 0, z: 0 },
    { x: length, y: maxY, z: 0 },
    { x: 0, y: maxY, z: 0 },
    { x: 0, y: 0, z: maxZ },
    { x: length, y: 0, z: maxZ },
    { x: length, y: maxY, z: maxZ },
    { x: 0, y: maxY, z: maxZ },
    { x: xAxisEnd, y: 0, z: 0 },
    { x: 0, y: yAxisEnd, z: 0 },
    { x: 0, y: 0, z: zAxisEnd },
  ];
}

function projectPoint(point, dimensions, viewport, rect) {
  const projected = projectScenePoint(point, dimensions);
  const scale = typeof viewport === "number" ? viewport : viewport.scale;
  const offsetX = typeof viewport === "number" ? rect.width / 2 + state.camera.panX : viewport.offsetX;
  const offsetY = typeof viewport === "number" ? rect.height / 2 + state.camera.panY : viewport.offsetY;
  return {
    x: offsetX + projected.x * scale,
    y: offsetY + projected.y * scale,
    depth: projected.depth,
  };
}

function projectScenePoint(point, dimensions) {
  const centered = {
    x: point.x - dimensions.length / 2,
    y: point.y - dimensions.maxY / 2,
    z: point.z - dimensions.maxZ / 2,
  };
  const yawCos = Math.cos(state.camera.yaw);
  const yawSin = Math.sin(state.camera.yaw);
  const x1 = centered.x * yawCos - centered.y * yawSin;
  const y1 = centered.x * yawSin + centered.y * yawCos;
  const z1 = centered.z;

  const pitchCos = Math.cos(state.camera.pitch);
  const pitchSin = Math.sin(state.camera.pitch);
  const y2 = y1 * pitchCos - z1 * pitchSin;
  const z2 = y1 * pitchSin + z1 * pitchCos;

  return {
    x: x1,
    y: -z2,
    depth: y2,
  };
}

function drawBackgroundText(context, rect) {
  context.save();
  context.fillStyle = themeCssValue("--axis-label-bg", "rgba(15, 23, 42, 0.72)");
  context.fillRect(14, rect.height - 39, 268, 26);
  context.strokeStyle = themeCssValue("--axis-label-border", "rgba(255, 255, 255, 0.22)");
  context.strokeRect(14, rect.height - 39, 268, 26);
  context.fillStyle = themeCssValue("--muted-strong", "rgba(226, 232, 240, 0.88)");
  context.font = "13px system-ui, sans-serif";
  context.fillText("x = 长度方向，y = 截面宽度，z = 高度", 18, rect.height - 20);
  context.restore();
}

function drawFloorGrid(context, projector, dimensions) {
  const floor = [
    { x: 0, y: 0, z: 0 },
    { x: dimensions.length, y: 0, z: 0 },
    { x: dimensions.length, y: dimensions.maxY, z: 0 },
    { x: 0, y: dimensions.maxY, z: 0 },
  ];

  context.save();
  drawProjectedPolygon(context, floor, projector, {
    fill: "rgba(15, 23, 42, 0.34)",
    stroke: "rgba(125, 211, 252, 0.18)",
    lineWidth: 1.2,
  });

  context.strokeStyle = "rgba(148, 163, 184, 0.17)";
  context.lineWidth = 1;
  const xStep = sceneGridStep(dimensions.length);
  const yStep = sceneGridStep(dimensions.maxY);
  for (let x = 0; x <= dimensions.length; x += xStep) {
    drawPolyline(context, [{ x, y: 0, z: 0 }, { x, y: dimensions.maxY, z: 0 }], projector);
  }
  for (let y = 0; y <= dimensions.maxY; y += yStep) {
    drawPolyline(context, [{ x: 0, y, z: 0 }, { x: dimensions.length, y, z: 0 }], projector);
  }

  context.strokeStyle = "rgba(226, 232, 240, 0.24)";
  context.lineWidth = 1.6;
  drawPolyline(context, [floor[0], floor[1], floor[2], floor[3], floor[0]], projector);
  context.restore();
}

function sceneGridStep(size) {
  const raw = Math.max(1, Number(size)) / 8;
  const power = 10 ** Math.floor(Math.log10(raw));
  const normalized = raw / power;
  if (normalized <= 2) {
    return 2 * power;
  }
  if (normalized <= 5) {
    return 5 * power;
  }
  return 10 * power;
}

function drawProjectedPolygon(context, points, projector, style) {
  const projected = points.map(projector);
  context.beginPath();
  projected.forEach((point, index) => {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });
  context.closePath();
  context.fillStyle = style.fill;
  context.strokeStyle = style.stroke;
  context.lineWidth = style.lineWidth ?? 1;
  context.fill();
  context.stroke();
}

function drawPrism(context, input, projector) {
  const faces = createPrismFaces(input).map((face) => ({
    ...face,
    fill: "rgba(56, 189, 248, 0.026)",
    stroke: "rgba(125, 211, 252, 0.16)",
    lineWidth: 0.8,
  }));
  drawFaces(context, faces, projector);
}

function createPrismFaces(input) {
  const length = Number(input.uld.length);
  const points = input.uld.cross_section.map(([y, z]) => ({ y, z }));
  const front = points.map((point) => ({ x: 0, y: point.y, z: point.z }));
  const back = points.map((point) => ({ x: length, y: point.y, z: point.z }));
  const faces = [
    { points: [...front].reverse() },
    { points: back },
  ];

  points.forEach((_, index) => {
    const next = (index + 1) % points.length;
    faces.push({
      points: [front[index], front[next], back[next], back[index]],
    });
  });

  return faces;
}

function drawPrismEdges(context, input, projector) {
  const length = Number(input.uld.length);
  const front = input.uld.cross_section.map(([y, z]) => ({ x: 0, y, z }));
  const back = input.uld.cross_section.map(([y, z]) => ({ x: length, y, z }));
  context.save();
  context.strokeStyle = "rgba(186, 230, 253, 0.96)";
  context.lineWidth = 2.4;
  context.shadowColor = "rgba(56, 189, 248, 0.42)";
  context.shadowBlur = 10;
  drawPolyline(context, [...front, front[0]], projector);
  drawPolyline(context, [...back, back[0]], projector);
  front.forEach((point, index) => drawPolyline(context, [point, back[index]], projector));
  context.restore();
}

function drawAxes(context, projector, dimensions) {
  const origin = { x: 0, y: 0, z: 0 };
  drawAxis(context, projector, origin, { x: dimensions.length * AXIS_EXTENSION_FACTOR, y: 0, z: 0 }, "x", "#f87171");
  drawAxis(context, projector, origin, { x: 0, y: dimensions.maxY * AXIS_EXTENSION_FACTOR, z: 0 }, "y", "#34d399");
  drawAxis(context, projector, origin, { x: 0, y: 0, z: dimensions.maxZ * AXIS_EXTENSION_FACTOR }, "z", "#60a5fa");
}

function drawAxis(context, projector, start, end, label, color) {
  const a = projector(start);
  const b = projector(end);
  context.save();
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 3;
  context.shadowColor = color;
  context.shadowBlur = 6;
  context.beginPath();
  context.moveTo(a.x, a.y);
  context.lineTo(b.x, b.y);
  context.stroke();
  drawAxisArrow(context, a, b);
  context.shadowBlur = 0;
  context.font = "700 14px system-ui, sans-serif";
  const labelText = label;
  const labelWidth = context.measureText(labelText).width + 14;
  context.fillStyle = themeCssValue("--axis-label-bg", "rgba(15, 23, 42, 0.72)");
  context.fillRect(b.x + 3, b.y - 22, labelWidth, 22);
  context.strokeStyle = themeCssValue("--axis-label-border", "rgba(255, 255, 255, 0.22)");
  context.strokeRect(b.x + 3, b.y - 22, labelWidth, 22);
  context.fillStyle = color;
  context.fillText(labelText, b.x + 10, b.y - 6);
  context.restore();
}

function drawAxisArrow(context, start, end) {
  const angle = Math.atan2(end.y - start.y, end.x - start.x);
  const size = 9;
  context.beginPath();
  context.moveTo(end.x, end.y);
  context.lineTo(end.x - Math.cos(angle - Math.PI / 6) * size, end.y - Math.sin(angle - Math.PI / 6) * size);
  context.moveTo(end.x, end.y);
  context.lineTo(end.x - Math.cos(angle + Math.PI / 6) * size, end.y - Math.sin(angle + Math.PI / 6) * size);
  context.stroke();
}

function createBoxFaces(placement, latestAnimatedId = null) {
  const vertices = boxVertices(placement);
  const color = colorForBox(placement.box_id);
  const selected = placement.instance_id === state.selectedInstanceId;
  const hovered = placement.instance_id === state.hoveredInstanceId;
  const animated = placement.instance_id === latestAnimatedId;
  return [
    face([vertices.a, vertices.b, vertices.c, vertices.d], color, selected, hovered, animated, placement.instance_id, 0.52),
    face([vertices.e, vertices.f, vertices.g, vertices.h], color, selected, hovered, animated, placement.instance_id, 0.96),
    face([vertices.a, vertices.b, vertices.f, vertices.e], color, selected, hovered, animated, placement.instance_id, 0.78),
    face([vertices.b, vertices.c, vertices.g, vertices.f], color, selected, hovered, animated, placement.instance_id, 0.7),
    face([vertices.c, vertices.d, vertices.h, vertices.g], color, selected, hovered, animated, placement.instance_id, 0.62),
    face([vertices.d, vertices.a, vertices.e, vertices.h], color, selected, hovered, animated, placement.instance_id, 0.74),
  ];
}

function boxVertices(placement) {
  const x = Number(placement.x);
  const y = Number(placement.y);
  const z = Number(placement.z);
  const length = Number(placement.length);
  const width = Number(placement.width);
  const height = Number(placement.height);
  return {
    a: { x, y, z },
    b: { x: x + length, y, z },
    c: { x: x + length, y: y + width, z },
    d: { x, y: y + width, z },
    e: { x, y, z: z + height },
    f: { x: x + length, y, z: z + height },
    g: { x: x + length, y: y + width, z: z + height },
    h: { x, y: y + width, z: z + height },
  };
}

function boxEdges(vertices) {
  return [
    [vertices.a, vertices.b],
    [vertices.b, vertices.c],
    [vertices.c, vertices.d],
    [vertices.d, vertices.a],
    [vertices.e, vertices.f],
    [vertices.f, vertices.g],
    [vertices.g, vertices.h],
    [vertices.h, vertices.e],
    [vertices.a, vertices.e],
    [vertices.b, vertices.f],
    [vertices.c, vertices.g],
    [vertices.d, vertices.h],
  ];
}

function face(points, color, selected, hovered, animated, instanceId, alpha) {
  const style = boxFaceStyle(color, selected || animated, hovered, alpha);
  return {
    points,
    instanceId,
    selected,
    hovered,
    animated,
    ...style,
  };
}

function boxFaceStyle(color, selected, hovered, alpha) {
  if (selected) {
    const selectedColor = lightenColor(color, 0.1);
    return {
      fill: rgbaColor(selectedColor, 0.98),
      stroke: "#fef08a",
      lineWidth: 3.4,
      shadow: "rgba(254, 240, 138, 0.55)",
    };
  }
  if (hovered) {
    const hoveredColor = lightenColor(color, 0.16);
    return {
      fill: rgbaColor(hoveredColor, 0.92),
      stroke: rgbaColor(lightenColor(color, 0.62), 1),
      lineWidth: 2.4,
      shadow: "rgba(226, 232, 240, 0.35)",
    };
  }
  return {
    fill: rgbaColor(color, alpha),
    stroke: rgbaColor(lightenColor(color, 0.38), 0.98),
    lineWidth: 1.45,
    shadow: "",
  };
}

function drawBoxWireframes(context, placements, projector, latestAnimatedId) {
  const mutedStroke = placements.length > 220 ? "rgba(15, 23, 42, 0.46)" : "rgba(15, 23, 42, 0.72)";
  context.save();
  context.lineJoin = "round";
  context.lineCap = "round";
  placements.forEach((placement) => {
    drawBoxWireframe(context, placement, projector, latestAnimatedId, mutedStroke);
  });
  context.restore();
}

function drawBoxWireframe(context, placement, projector, latestAnimatedId, mutedStroke) {
  const vertices = boxVertices(placement);
  const highlighted =
    placement.instance_id === state.selectedInstanceId ||
    placement.instance_id === state.hoveredInstanceId ||
    placement.instance_id === latestAnimatedId;
  context.strokeStyle = highlighted ? "rgba(255, 255, 255, 0.88)" : mutedStroke;
  context.lineWidth = highlighted ? 2.2 : 0.75;
  boxEdges(vertices).forEach(([start, end]) => drawPolyline(context, [start, end], projector));
}

function currentAnimatedInstanceId(visiblePlacements) {
  if (state.animation.visibleCount === null || visiblePlacements.length === 0) {
    return null;
  }
  return visiblePlacements[visiblePlacements.length - 1].instance_id;
}

function drawFaces(context, faces, projector, hitRegions = null) {
  const projectedFaces = faces.map((item) => {
    const projected = item.points.map(projector);
    return {
      ...item,
      projected,
      depth: projected.reduce((total, point) => total + point.depth, 0) / projected.length,
    };
  });

  projectedFaces.sort((first, second) => first.depth - second.depth);

  context.save();
  projectedFaces.forEach((item) => {
    context.beginPath();
    item.projected.forEach((point, index) => {
      if (index === 0) {
        context.moveTo(point.x, point.y);
      } else {
        context.lineTo(point.x, point.y);
      }
    });
    context.closePath();
    context.fillStyle = item.fill;
    context.strokeStyle = item.stroke;
    context.lineWidth = item.lineWidth ?? 1;
    context.shadowColor = item.shadow || "transparent";
    context.shadowBlur = item.shadow ? 12 : 0;
    context.fill();
    context.stroke();
    if (hitRegions && item.instanceId) {
      hitRegions.push({ instanceId: item.instanceId, polygon: item.projected, depth: item.depth });
    }
  });
  context.restore();
}

function drawPolyline(context, points, projector) {
  const projected = points.map(projector);
  context.beginPath();
  projected.forEach((point, index) => {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });
  context.stroke();
}

function colorForBox(id) {
  let hash = 0;
  for (const char of id) {
    hash = (hash * 31 + char.charCodeAt(0)) % 9973;
  }
  return BOX_COLOR_PALETTE[hash % BOX_COLOR_PALETTE.length];
}

function lightenColor(color, ratio) {
  return {
    r: Math.round(color.r + (255 - color.r) * ratio),
    g: Math.round(color.g + (255 - color.g) * ratio),
    b: Math.round(color.b + (255 - color.b) * ratio),
  };
}

function rgbaColor(color, alpha) {
  return `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
}

function selectPlacement(instanceId, options = {}) {
  const activeResult = getActiveResult();
  const placement = activeResult?.placements.find((item) => item.instance_id === instanceId);
  if (!instanceId || !placement) {
    return;
  }
  state.selectedInstanceId = instanceId;
  if (options.focusSameBoxType) {
    setSceneBoxFocus(placement.box_id);
  } else {
    clearSceneBoxFocus();
  }
  if (options.syncSlice) {
    syncSliceToSelectedPlacement();
  }
  renderSelectedBoxDetails();
  updateSelectedRow();
  drawAllViews();
}

function setSceneBoxFocus(boxId) {
  state.focusedBoxId = boxId;
  resetAnimationState({ showFull: true });
}

function clearSceneBoxFocus() {
  state.focusedBoxId = null;
}

function syncSliceToSelectedPlacement() {
  const placement = getSelectedPlacement();
  const activeInput = getActiveProfileInput();
  if (!placement || !activeInput) {
    return;
  }
  state.sliceX = clamp(placement.x + placement.length / 2, 0, Number(activeInput.uld.length));
  elements.sliceSlider.value = String(Math.round(state.sliceX));
  state.sliceX = Number(elements.sliceSlider.value);
  updateSliceValue();
}

function renderSelectedBoxDetails() {
  const placement = getSelectedPlacement();
  if (!placement) {
    elements.selectedBoxDetails.classList.add("muted-text");
    elements.selectedBoxDetails.textContent = "点击 3D 视图、三视图或坐标表中的箱子查看位置范围。";
    return;
  }
  elements.selectedBoxDetails.classList.remove("muted-text");
  elements.selectedBoxDetails.innerHTML = `
    <strong>${escapeHtml(placement.instance_id)}</strong>
    <div>类型：<code>${escapeHtml(placement.box_id)}</code></div>
    ${state.focusedBoxId === placement.box_id ? `<div>3D 聚焦同类箱子：<code>${escapeHtml(placement.box_id)}</code></div>` : ""}
    <div>x：<code>${formatNumber(placement.x)} ~ ${formatNumber(placement.x + placement.length)}</code></div>
    <div>y：<code>${formatNumber(placement.y)} ~ ${formatNumber(placement.y + placement.width)}</code></div>
    <div>z：<code>${formatNumber(placement.z)} ~ ${formatNumber(placement.z + placement.height)}</code></div>
    <div>尺寸：<code>${formatNumber(placement.length)} × ${formatNumber(placement.width)} × ${formatNumber(placement.height)}</code></div>
  `;
}

function updateSelectedRow() {
  elements.placementsTableBody.querySelectorAll("tr").forEach((row) => {
    row.classList.toggle("selected-row", row.dataset.instanceId === state.selectedInstanceId);
  });
}

function getSelectedPlacement() {
  return getActiveResult()?.placements.find((placement) => placement.instance_id === state.selectedInstanceId) ?? null;
}

function selectScenePlacementAtPointer(event) {
  if (state.pointer.moved) {
    return;
  }
  const match = sceneMatchAtPoint(event);
  if (match) {
    selectPlacement(match.instanceId, { syncSlice: true });
  }
}

function updateHoveredScenePlacement(event) {
  const match = sceneMatchAtPoint(event);
  const nextInstanceId = match?.instanceId ?? null;
  if (!nextInstanceId) {
    clearHoveredScenePlacement();
    return;
  }

  const placement = placementByInstanceId(nextInstanceId);
  if (state.hoveredInstanceId !== nextInstanceId) {
    state.hoveredInstanceId = nextInstanceId;
    drawScene();
  }
  renderSceneTooltip(event, placement);
}

function clearHoveredScenePlacement() {
  if (state.hoveredInstanceId) {
    state.hoveredInstanceId = null;
    drawScene();
  }
  hideSceneTooltip();
}

function sceneMatchAtPoint(event) {
  const point = canvasPoint(event, elements.canvas);
  return [...state.hitRegions.scene]
    .sort((first, second) => second.depth - first.depth)
    .find((region) => pointInPolygon2D(point, region.polygon));
}

function placementByInstanceId(instanceId) {
  return getActiveResult()?.placements.find((placement) => placement.instance_id === instanceId) ?? null;
}

function renderSceneTooltip(event, placement) {
  if (!placement) {
    hideSceneTooltip();
    return;
  }
  elements.sceneTooltip.innerHTML = `
    <strong>${escapeHtml(placement.instance_id)}</strong>
    <div>类型：${escapeHtml(placement.box_id)}</div>
    <div>尺寸：${formatNumber(placement.length)} × ${formatNumber(placement.width)} × ${formatNumber(placement.height)}</div>
    <div>坐标：x ${formatNumber(placement.x)}，y ${formatNumber(placement.y)}，z ${formatNumber(placement.z)}</div>
  `;
  elements.sceneTooltip.classList.add("visible");

  const stageRect = elements.sceneStage.getBoundingClientRect();
  const tooltipRect = elements.sceneTooltip.getBoundingClientRect();
  const maxLeft = Math.max(8, stageRect.width - tooltipRect.width - 8);
  const maxTop = Math.max(8, stageRect.height - tooltipRect.height - 8);
  const left = clamp(event.clientX - stageRect.left + 14, 8, maxLeft);
  const top = clamp(event.clientY - stageRect.top + 14, 8, maxTop);
  elements.sceneTooltip.style.left = `${left}px`;
  elements.sceneTooltip.style.top = `${top}px`;
}

function hideSceneTooltip() {
  elements.sceneTooltip?.classList.remove("visible");
}

function selectProjectionPlacementAtPointer(event, viewKey) {
  const point = canvasPoint(event, event.currentTarget);
  const match = [...state.hitRegions[viewKey]].reverse().find((region) => pointInRect(point, region.rect));
  if (match) {
    selectPlacement(match.instanceId, { syncSlice: viewKey !== "section" });
  }
}

function focusProjectionCameraView(event, viewKey) {
  setCameraView(viewKey);
  selectProjectionPlacementAtPointer(event, viewKey);
}

function canvasPoint(event, canvas) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function pointInRect(point, rect) {
  return point.x >= rect.x && point.x <= rect.x + rect.width && point.y >= rect.y && point.y <= rect.y + rect.height;
}

function pointInPolygon2D(point, polygon) {
  let inside = false;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
    const currentPoint = polygon[index];
    const previousPoint = polygon[previous];
    const crosses = currentPoint.y > point.y !== previousPoint.y > point.y;
    if (crosses) {
      const intersectionX = ((previousPoint.x - currentPoint.x) * (point.y - currentPoint.y)) / (previousPoint.y - currentPoint.y) + currentPoint.x;
      if (point.x < intersectionX) {
        inside = !inside;
      }
    }
  }
  return inside;
}

function setCameraView(view) {
  const views = {
    isometric: { yaw: -0.72, pitch: 0.58 },
    top: { yaw: 0, pitch: 1.5708 },
    side: { yaw: 0, pitch: 0 },
    section: { yaw: -1.5708, pitch: 0 },
  };
  const next = views[view] ?? views.isometric;
  state.camera.yaw = next.yaw;
  state.camera.pitch = next.pitch;
  state.camera.panX = 0;
  state.camera.panY = 10;
  drawAllViews();
}

function startPointerDrag(event) {
  elements.canvas.setPointerCapture(event.pointerId);
  state.pointer.active = true;
  state.pointer.mode = event.shiftKey || event.button === 2 ? "pan" : "rotate";
  state.pointer.x = event.clientX;
  state.pointer.y = event.clientY;
  state.pointer.moved = false;
  hideSceneTooltip();
}

function movePointerDrag(event) {
  if (!state.pointer.active) {
    updateHoveredScenePlacement(event);
    return;
  }
  const deltaX = event.clientX - state.pointer.x;
  const deltaY = event.clientY - state.pointer.y;
  state.pointer.x = event.clientX;
  state.pointer.y = event.clientY;

  if (Math.abs(deltaX) + Math.abs(deltaY) > 2) {
    state.pointer.moved = true;
  }

  if (state.pointer.mode === "pan") {
    state.camera.panX += deltaX;
    state.camera.panY += deltaY;
  } else {
    state.camera.yaw += deltaX * 0.008;
    state.camera.pitch += deltaY * 0.008;
  }
  drawScene();
}

function endPointerDrag(event) {
  if (!state.pointer.active) {
    return;
  }
  state.pointer.active = false;
  if (event.pointerId !== undefined && elements.canvas.hasPointerCapture(event.pointerId)) {
    elements.canvas.releasePointerCapture(event.pointerId);
  }
}

function zoomScene(event) {
  event.preventDefault();
  const nextZoom = state.camera.zoom * (event.deltaY > 0 ? 0.9 : 1.1);
  state.camera.zoom = Math.min(4, Math.max(0.25, nextZoom));
  drawScene();
}

function resetView() {
  state.camera.yaw = -0.72;
  state.camera.pitch = 0.58;
  state.camera.zoom = 1;
  state.camera.panX = 0;
  state.camera.panY = 10;
}

function setBusy(isBusy) {
  elements.calculateButton.disabled = isBusy;
  elements.calculateButton.textContent = isBusy ? "计算中..." : "计算装箱";
}

function showError(message) {
  elements.errorMessage.textContent = message;
}

function clearError() {
  elements.errorMessage.textContent = "";
}

function formatNumber(value) {
  return Number(value).toFixed(0);
}

function formatPercent(value) {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

function formatSpeed(value) {
  return Number(value).toFixed(1).replace(".0", "");
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value)));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

function escapeXmlText(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeXmlAttribute(value) {
  return escapeXmlText(value).replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}
