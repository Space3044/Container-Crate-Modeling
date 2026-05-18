const fallbackInput = {
  containers: [
    {
      id: "ULD-A",
      length: 300,
      quantity: 1,
      cross_section: [
        [0, 0],
        [220, 0],
        [220, 110],
        [170, 160],
        [0, 160],
      ],
    },
  ],
  boxes: [
    { id: "BOX-A", length: 60, width: 40, height: 30, quantity: 10, rotatable: true },
  ],
  objective: "maximize_volume",
};

const AXIS_EXTENSION_FACTOR = 1.18;
const BOX_ANIMATION_INTERVAL_MS = 320;
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

const state = {
  input: structuredClone(fallbackInput),
  result: null,
  selectedContainerId: null,
  selectedInstanceId: null,
  hoveredInstanceId: null,
  focusedBoxId: null,
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
  bindEvents();
  await loadSample();
  await calculatePacking();
  window.addEventListener("resize", drawAllViews);
}

function cacheElements() {
  elements.containerTableBody = document.getElementById("containerTableBody");
  elements.addContainerButton = document.getElementById("addContainerButton");
  elements.containerSelector = document.getElementById("containerSelector");
  elements.boxTableBody = document.getElementById("boxTableBody");
  elements.addBoxButton = document.getElementById("addBoxButton");
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
  elements.calculateButton.addEventListener("click", calculatePacking);
  elements.containerSelector.addEventListener("change", () => selectContainer(elements.containerSelector.value));
  elements.loadSampleButton.addEventListener("click", async () => {
    await loadSample();
    await calculatePacking();
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
        quantity: Number(container.quantity ?? 1),
        cross_section: container.cross_section.map(([y, z]) => [Number(y), Number(z)]),
      })),
      boxes: input.boxes ?? [],
      objective: input.objective ?? "maximize_volume",
    };
  }
  if (input?.uld) {
    return {
      containers: [
        {
          id: input.uld.id,
          length: input.uld.length,
          quantity: 1,
          cross_section: input.uld.cross_section,
        },
      ],
      boxes: input.boxes ?? [],
      objective: input.objective ?? "maximize_volume",
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
    <td><input class="container-quantity" type="number" min="1" step="1" value="${container.quantity ?? 1}" aria-label="ULD 数量" /></td>
    <td><textarea class="container-cross-section" rows="3" aria-label="ULD y-z 截面点">${escapeHtml(JSON.stringify(crossSection))}</textarea></td>
    <td><button class="icon-button" type="button" aria-label="删除 ULD">×</button></td>
  `;
  row.querySelector("button").addEventListener("click", () => row.remove());
  elements.containerTableBody.appendChild(row);
}

function addBoxRow(box = {}) {
  const row = document.createElement("tr");
  const id = box.id ?? nextAlphabeticId("BOX", ".box-id");
  row.innerHTML = `
    <td><input class="box-id" type="text" value="${escapeAttribute(id)}" aria-label="箱子 ID" /></td>
    <td><input class="box-length" type="number" min="1" step="1" value="${box.length ?? 60}" aria-label="箱子长度" /></td>
    <td><input class="box-width" type="number" min="1" step="1" value="${box.width ?? 40}" aria-label="箱子宽度" /></td>
    <td><input class="box-height" type="number" min="1" step="1" value="${box.height ?? 30}" aria-label="箱子高度" /></td>
    <td><input class="box-quantity" type="number" min="0" step="1" value="${box.quantity ?? 1}" aria-label="箱子数量" /></td>
    <td><input class="box-rotatable" type="checkbox" ${box.rotatable ?? true ? "checked" : ""} aria-label="允许长宽互换" /></td>
    <td><button class="icon-button" type="button" aria-label="删除箱子">×</button></td>
  `;
  row.querySelector("button").addEventListener("click", () => row.remove());
  elements.boxTableBody.appendChild(row);
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

async function calculatePacking() {
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

function readInputFromForm() {
  return {
    containers: readContainersFromForm(),
    boxes: readBoxesFromForm(),
    objective: "maximize_volume",
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
      quantity: readPositiveInteger(row.querySelector(".container-quantity").value, `${id} 数量`),
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
    return {
      id,
      length: readPositiveNumber(row.querySelector(".box-length").value, `${id} 长度`),
      width: readPositiveNumber(row.querySelector(".box-width").value, `${id} 宽度`),
      height: readPositiveNumber(row.querySelector(".box-height").value, `${id} 高度`),
      quantity: readNonNegativeInteger(row.querySelector(".box-quantity").value, `${id} 数量`),
      rotatable: row.querySelector(".box-rotatable").checked,
    };
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

  renderLoadedList(result);
  renderUnloadedList(result);
  renderActiveContainerDetails();
}

function renderActiveContainerDetails() {
  const activeResult = getActiveResult();
  renderActiveContainerStats(activeResult);
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
    elements.activeContainerStats.textContent = "选择 ULD 后显示单个 ULD 装载率。";
    return;
  }

  elements.activeContainerStats.classList.remove("muted-text");
  elements.activeContainerStats.innerHTML = `
    <div><span>单个 ULD 装载率</span><strong>${formatPercent(activeResult.volume_utilization)}</strong></div>
    <div><span>已装箱</span><strong>${activeResult.loaded_count ?? 0}</strong></div>
    <div><span>已用体积</span><strong>${formatNumber(activeResult.used_volume ?? 0)} / ${formatNumber(activeResult.uld_volume ?? 0)}</strong></div>
  `;
}

function renderLoadedList(result) {
  const loaded = result.loaded ?? loadedSummaryFromPlacements(result.placements);
  if (loaded.length === 0) {
    elements.loadedList.textContent = "暂无";
    elements.loadedList.classList.add("muted-text");
    return;
  }

  elements.loadedList.classList.remove("muted-text");
  elements.loadedList.innerHTML = loaded
    .map((item) => `<div>${escapeHtml(item.box_id)} × ${item.quantity}</div>`)
    .join("");
}

function renderUnloadedList(result) {
  const unloaded = result.unloaded ?? [];
  if (unloaded.length === 0) {
    elements.unloadedList.textContent = "暂无";
    elements.unloadedList.classList.add("muted-text");
    return;
  }

  elements.unloadedList.classList.remove("muted-text");
  elements.unloadedList.innerHTML = unloaded
    .map((item) => `<div>${escapeHtml(item.box_id)} × ${item.quantity}：${escapeHtml(item.reason)}</div>`)
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
  const scale = getSceneScale(rect, dimensions);
  const projector = (point) => projectPoint(point, dimensions, scale, rect);
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
  context.fillStyle = "rgba(226, 232, 240, 0.76)";
  context.font = "12px system-ui, sans-serif";
  context.fillText(horizontalLabel, rect.width - 80, rect.height - 12);
  context.fillText(verticalLabel, 12, 18);
  context.restore();
}

function drawProjectionUldRect(context, mapper, width, height) {
  const rect = mapper.rectToScreen(0, 0, width, height);
  context.save();
  context.strokeStyle = "rgba(186, 230, 253, 0.75)";
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
  const maxDimension = Math.max(dimensions.length, dimensions.maxY, dimensions.maxZ);
  return (Math.min(rect.width, rect.height) * 0.72 * state.camera.zoom) / maxDimension;
}

function projectPoint(point, dimensions, scale, rect) {
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
    x: rect.width / 2 + state.camera.panX + x1 * scale,
    y: rect.height / 2 + state.camera.panY - z2 * scale,
    depth: y2,
  };
}

function drawBackgroundText(context, rect) {
  context.save();
  context.fillStyle = "rgba(2, 6, 23, 0.72)";
  context.fillRect(14, rect.height - 39, 268, 26);
  context.strokeStyle = "rgba(125, 211, 252, 0.22)";
  context.strokeRect(14, rect.height - 39, 268, 26);
  context.fillStyle = "rgba(226, 232, 240, 0.88)";
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
  context.fillStyle = "rgba(15, 23, 42, 0.72)";
  context.fillRect(b.x + 3, b.y - 22, labelWidth, 22);
  context.strokeStyle = "rgba(255, 255, 255, 0.22)";
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
