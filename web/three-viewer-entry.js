import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
import { LineSegments2 } from "three/examples/jsm/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/examples/jsm/lines/LineSegmentsGeometry.js";

const ALL_BOXES_OPACITY = 0.78;
const SELECTED_OUTLINE_COLOR = 0xef4444;
const HOVERED_OUTLINE_COLOR = 0xf87171;
const ANIMATED_EMISSIVE_COLOR = 0xef4444;
const HIGHLIGHT_LINE_WIDTH = 3.2;
const SHELL_COLOR = 0x64b5f6;
const SHELL_EDGE_COLOR = 0x1976d2;
const GRID_COLOR = 0x78909c;
const FLOOR_GRID_OPACITY = 0.45;
const AXIS_EXTENSION_FACTOR = 1.2;
const AXIS_LABEL_OFFSET_FACTOR = 0.04;
const AXIS_LABEL_SIZE_FACTOR = 0.06;
const AXIS_COLORS = {
  x: 0xe53935,
  y: 0x43a047,
  z: 0x1e88e5,
};

class ThreeSceneViewer {
  constructor({ canvas, getBoxColor, onHover, onSelect, onViewChange } = {}) {
    if (!canvas) {
      throw new Error("ThreeSceneViewer requires a canvas");
    }

    this.canvas = canvas;
    this.getBoxColor = getBoxColor ?? (() => 0x4f76ad);
    this.onHover = onHover ?? (() => {});
    this.onSelect = onSelect ?? (() => {});
    this.onViewChange = onViewChange ?? (() => {});
    this.displayMode = "visible";
    this.selectedInstanceId = null;
    this.hoveredInstanceId = null;
    this.animatedInstanceId = null;
    this.currentPlacements = null;
    this.currentUldKey = "";
    this.currentView = "isometric";
    this.boxMeshes = [];
    this.sceneDimensions = null;
    this.sceneCenter = new THREE.Vector3();
    this.sceneDiagonal = 500;
    this.viewHeight = 650;
    this.pointerDown = null;

    this.scene = new THREE.Scene();
    this.sceneRoot = new THREE.Group();
    this.scene.add(this.sceneRoot);
    const ambientLight = new THREE.AmbientLight(0xf0f4f8, 0.5);
    const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0x5a6c7d, 1.5);
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
    keyLight.position.set(420, 620, 520);
    const fillLight = new THREE.DirectionalLight(0xa8c5e0, 1.1);
    fillLight.position.set(-360, 220, -460);
    const rimLight = new THREE.DirectionalLight(0xe8f1f8, 0.7);
    rimLight.position.set(100, 50, -400);
    this.scene.add(ambientLight, hemisphereLight, keyLight, fillLight, rimLight);
    this.boxRoot = new THREE.Group();
    this.shellRoot = new THREE.Group();
    this.floorRoot = new THREE.Group();
    this.axisRoot = new THREE.Group();
    this.sceneRoot.add(this.floorRoot, this.shellRoot, this.boxRoot, this.axisRoot);

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
    this.renderer.setClearColor(0x000000, 0);
    if ("outputColorSpace" in this.renderer) {
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }

    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100000);
    this.camera.up.set(0, 1, 0);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = false;
    this.controls.enablePan = true;
    this.controls.screenSpacePanning = true;
    this.controls.minZoom = 0.35;
    this.controls.maxZoom = 8;
    this.controls.minPolarAngle = 0.12;
    this.controls.maxPolarAngle = Math.PI - 0.12;
    this.controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    this.controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    this.controls.touches.ONE = THREE.TOUCH.ROTATE;
    this.controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
    this.controls.addEventListener("change", () => this.render());

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.bindEvents();
    this.resize();
  }

  bindEvents() {
    this.handlePointerDown = (event) => {
      this.pointerDown = { x: event.clientX, y: event.clientY };
      this.hoveredInstanceId = null;
      this.onHover(null, event);
    };
    this.handlePointerMove = (event) => {
      // OrbitControls uses this gesture to rotate/pan. Do not run picking while
      // the pointer is held down, otherwise the rotating scene can trigger hover
      // highlights and tooltips as the ray moves across different boxes.
      if (this.pointerDown) {
        return;
      }
      const hit = this.pick(event);
      const placement = hit?.userData?.placement ?? null;
      this.hoveredInstanceId = placement?.instance_id ?? null;
      this.onHover(placement, event);
    };
    this.handlePointerUp = (event) => {
      if (!this.pointerDown) {
        return;
      }
      const distance = Math.hypot(event.clientX - this.pointerDown.x, event.clientY - this.pointerDown.y);
      this.pointerDown = null;
      if (distance > 5) {
        this.hoveredInstanceId = null;
        this.onHover(null, event);
        return;
      }
      const hit = this.pick(event);
      const placement = hit?.userData?.placement ?? null;
      if (placement) {
        this.onSelect(placement, event);
      }
    };
    this.handlePointerLeave = (event) => {
      this.pointerDown = null;
      this.hoveredInstanceId = null;
      this.onHover(null, event);
    };
    this.handleDoubleClick = () => this.resetView();
    this.handleContextMenu = (event) => event.preventDefault();

    this.canvas.addEventListener("pointerdown", this.handlePointerDown);
    this.canvas.addEventListener("pointermove", this.handlePointerMove);
    this.canvas.addEventListener("pointerup", this.handlePointerUp);
    this.canvas.addEventListener("pointercancel", this.handlePointerLeave);
    this.canvas.addEventListener("pointerleave", this.handlePointerLeave);
    this.canvas.addEventListener("dblclick", this.handleDoubleClick);
    this.canvas.addEventListener("contextmenu", this.handleContextMenu);
  }

  setScene({
    input,
    placements = [],
    visiblePlacements = placements,
    selectedInstanceId = null,
    hoveredInstanceId = null,
    latestAnimatedId = null,
    displayMode = "visible",
  } = {}) {
    if (!input?.uld) {
      this.clearScene();
      return;
    }

    const uldKey = `${input.uld.id}|${input.uld.length}|${JSON.stringify(input.uld.cross_section)}`;
    if (this.currentPlacements !== placements || this.currentUldKey !== uldKey) {
      this.rebuildScene(input.uld, placements);
      this.currentPlacements = placements;
      this.currentUldKey = uldKey;
      this.fitCamera("isometric");
    }

    this.displayMode = displayMode === "visible" ? "visible" : "all";
    this.selectedInstanceId = selectedInstanceId;
    this.hoveredInstanceId = hoveredInstanceId;
    this.animatedInstanceId = latestAnimatedId;
    this.updatePlacementVisibility(visiblePlacements);
    this.updateMaterialMode();
    this.updateHighlights();
    this.render();
  }

  clearScene() {
    this.disposeGroup(this.boxRoot);
    this.disposeGroup(this.shellRoot);
    this.disposeGroup(this.floorRoot);
    this.disposeGroup(this.axisRoot);
    this.boxRoot = new THREE.Group();
    this.shellRoot = new THREE.Group();
    this.floorRoot = new THREE.Group();
    this.axisRoot = new THREE.Group();
    this.sceneRoot.add(this.floorRoot, this.shellRoot, this.boxRoot, this.axisRoot);
    this.boxMeshes = [];
    this.currentPlacements = null;
    this.currentUldKey = "";
    this.sceneDimensions = null;
    this.render();
  }

  rebuildScene(uld, placements) {
    this.disposeGroup(this.boxRoot);
    this.disposeGroup(this.shellRoot);
    this.disposeGroup(this.floorRoot);
    this.disposeGroup(this.axisRoot);
    this.boxRoot = new THREE.Group();
    this.shellRoot = new THREE.Group();
    this.floorRoot = new THREE.Group();
    this.axisRoot = new THREE.Group();
    this.sceneRoot.add(this.floorRoot, this.shellRoot, this.boxRoot, this.axisRoot);
    this.boxMeshes = [];

    this.sceneDimensions = sceneDimensions(uld);
    this.sceneCenter.set(
      this.sceneDimensions.length / 2,
      this.sceneDimensions.maxZ / 2,
      this.sceneDimensions.maxY / 2,
    );
    this.sceneDiagonal = Math.max(
      1,
      Math.hypot(this.sceneDimensions.length, this.sceneDimensions.maxY, this.sceneDimensions.maxZ),
    );

    this.buildFloor(this.sceneDimensions);
    this.buildShell(uld);
    this.buildAxes(this.sceneDimensions);

    const geometryCache = new Map();
    const materialCache = new Map();
    const edgeMaterialCache = new Map();
    placements.forEach((placement) => {
      const length = Number(placement.length);
      const width = Number(placement.width);
      const height = Number(placement.height);
      const geometryKey = `${length}|${width}|${height}`;
      let geometry = geometryCache.get(geometryKey);
      if (!geometry) {
        geometry = new THREE.BoxGeometry(length, height, width);
        geometryCache.set(geometryKey, geometry);
      }

      const color = normalizeColor(this.getBoxColor(placement));
      const materialKey = color.getHexString();
      let material = materialCache.get(materialKey);
      if (!material) {
        material = new THREE.MeshStandardMaterial({
          color,
          transparent: true,
          opacity: ALL_BOXES_OPACITY,
          metalness: 0.1,
          roughness: 0.6,
        });
        materialCache.set(materialKey, material);
      }

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(
        Number(placement.x) + length / 2,
        Number(placement.z) + height / 2,
        Number(placement.y) + width / 2,
      );
      mesh.userData.placement = placement;
      mesh.userData.baseMaterial = material;
      mesh.userData.highlightMaterial = null;
      let edgeMaterial = edgeMaterialCache.get(materialKey);
      if (!edgeMaterial) {
        edgeMaterial = new THREE.LineBasicMaterial({
          color: 0x1a1a1a,
          transparent: true,
          opacity: 0.85,
          depthWrite: true,
          depthTest: true,
          linewidth: 1,
        });
        edgeMaterialCache.set(materialKey, edgeMaterial);
      }
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), edgeMaterial);
      edges.renderOrder = 1;
      mesh.userData.edgeObject = edges;
      mesh.userData.baseEdgeMaterial = edgeMaterial;
      mesh.userData.highlightEdgeMaterial = null;
      mesh.userData.hoverOutline = null;
      mesh.userData.selectOutline = null;
      mesh.add(edges);
      this.boxRoot.add(mesh);
      this.boxMeshes.push(mesh);
    });
  }

  updatePlacementVisibility(visiblePlacements = []) {
    const visibleIds = new Set(visiblePlacements.map((placement) => placement.instance_id));
    this.boxMeshes.forEach((mesh) => {
      mesh.visible = visibleIds.has(mesh.userData.placement.instance_id);
    });
  }

  buildFloor(dimensions) {
    const size = Math.max(dimensions.length, dimensions.maxY, 1);
    const divisions = Math.max(8, Math.min(16, Math.round(size / 35)));
    const grid = new THREE.GridHelper(size, divisions, GRID_COLOR, GRID_COLOR);
    grid.position.set(dimensions.length / 2, 0.5, dimensions.maxY / 2);
    grid.scale.set(dimensions.length / size, 1, dimensions.maxY / size);
    setMaterialVisibility(grid.material, { opacity: FLOOR_GRID_OPACITY, transparent: true, depthWrite: false, depthTest: false });
    this.floorRoot.add(grid);
  }

  buildShell(uld) {
    const geometry = createUldGeometry(uld);
    const shellMaterial = new THREE.MeshBasicMaterial({
      color: SHELL_COLOR,
      transparent: true,
      opacity: 0.12,
      depthWrite: false,
      depthTest: false,
      side: THREE.DoubleSide,
    });
    const shell = new THREE.Mesh(geometry, shellMaterial);
    this.shellRoot.add(shell);

    const edgeGeometry = new THREE.EdgesGeometry(geometry, 18);
    const edgeMaterial = new THREE.LineBasicMaterial({
      color: SHELL_EDGE_COLOR,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
      depthTest: false,
      linewidth: 1.5,
    });
    const edges = new THREE.LineSegments(edgeGeometry, edgeMaterial);
    this.shellRoot.add(edges);
  }

  buildAxes(dimensions) {
    const origin = new THREE.Vector3(0, 0, 0);
    const labelOffset = Math.max(8, this.sceneDiagonal * AXIS_LABEL_OFFSET_FACTOR);
    const labelSize = Math.max(10, Math.min(24, this.sceneDiagonal * AXIS_LABEL_SIZE_FACTOR));
    const axes = [
      { name: "x", direction: new THREE.Vector3(1, 0, 0), length: dimensions.length * AXIS_EXTENSION_FACTOR, color: AXIS_COLORS.x },
      { name: "y", direction: new THREE.Vector3(0, 0, 1), length: dimensions.maxY * AXIS_EXTENSION_FACTOR, color: AXIS_COLORS.y },
      { name: "z", direction: new THREE.Vector3(0, 1, 0), length: dimensions.maxZ * AXIS_EXTENSION_FACTOR, color: AXIS_COLORS.z },
    ];
    axes.forEach(({ name, direction, length, color }) => {
      const axisLength = Math.max(length, 1);
      const arrow = new THREE.ArrowHelper(direction, origin, axisLength, color, 12, 7);
      arrow.renderOrder = 20;
      setMaterialVisibility(arrow.line.material, { depthWrite: false, depthTest: false });
      setMaterialVisibility(arrow.cone.material, { depthWrite: false, depthTest: false });
      this.axisRoot.add(arrow);

      const label = createAxisLabelSprite(name, color, labelSize);
      label.position.copy(origin).addScaledVector(direction, axisLength + labelOffset);
      this.axisRoot.add(label);
    });
  }

  updateMaterialMode() {
    const visibleOnly = this.displayMode === "visible";
    const opacity = visibleOnly ? 1 : ALL_BOXES_OPACITY;
    const transparent = !visibleOnly;
    const depthTest = visibleOnly;
    const depthWrite = visibleOnly;
    const baseMaterials = new Set(this.boxMeshes.map((mesh) => mesh.userData.baseMaterial));
    const highlightMaterials = new Set();
    this.boxMeshes.forEach((mesh) => {
      if (mesh.userData.highlightMaterial) {
        highlightMaterials.add(mesh.userData.highlightMaterial);
      }
    });

    baseMaterials.forEach((material) => {
      material.transparent = transparent;
      material.opacity = opacity;
      material.depthTest = depthTest;
      material.depthWrite = depthWrite;
      material.needsUpdate = true;
    });
    highlightMaterials.forEach((material) => {
      material.transparent = transparent;
      material.opacity = visibleOnly ? 1 : 0.92;
      material.depthTest = depthTest;
      material.depthWrite = depthWrite;
      material.needsUpdate = true;
    });

    this.shellRoot.traverse((object) => {
      const material = object.material;
      if (!material) {
        return;
      }
      material.depthTest = visibleOnly && object.isLineSegments;
      material.needsUpdate = true;
    });

    this.boxMeshes.forEach((mesh) => {
      const edgeObject = mesh.userData.edgeObject;
      if (!edgeObject?.material) {
        return;
      }
      const isHighlighted = edgeObject.material === mesh.userData.highlightEdgeMaterial;
      edgeObject.material.depthTest = visibleOnly;
      edgeObject.material.depthWrite = visibleOnly;
      edgeObject.material.opacity = isHighlighted ? 1.0 : (visibleOnly ? 0.85 : 0.7);
      edgeObject.material.needsUpdate = true;

      // 高亮轮廓始终置于最上层，完整框出箱体的前后边线。
      [mesh.userData.hoverOutline, mesh.userData.selectOutline].forEach((outline) => {
        if (outline) {
          outline.traverse((child) => {
            if (child.material) {
              child.material.depthTest = false;
              child.material.depthWrite = false;
              child.material.needsUpdate = true;
            }
          });
        }
      });
    });
  }

  createHighlightOutline(geometry, color, opacity = 1) {
    const material = new LineMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
      depthTest: false,
      linewidth: HIGHLIGHT_LINE_WIDTH,
      worldUnits: false,
    });
    const edgeGeometry = new THREE.EdgesGeometry(geometry);
    const wideGeometry = new LineSegmentsGeometry().setPositions(
      Array.from(edgeGeometry.getAttribute("position").array),
    );
    edgeGeometry.dispose();
    const outline = new LineSegments2(wideGeometry, material);
    outline.renderOrder = 100;
    outline.scale.setScalar(1.018);
    return outline;
  }

  updateHighlights() {
    this.boxMeshes.forEach((mesh) => {
      const placement = mesh.userData.placement;
      const kind = this.animatedInstanceId
        ? placement.instance_id === this.animatedInstanceId
          ? "animated"
          : null
        : placement.instance_id === this.selectedInstanceId
          ? "selected"
          : placement.instance_id === this.hoveredInstanceId
            ? "hovered"
            : null;
      const currentKind = mesh.userData.highlightKind ?? null;
      if (currentKind === kind) {
        return;
      }
      if (mesh.userData.highlightMaterial) {
        mesh.userData.highlightMaterial.dispose();
        mesh.userData.highlightMaterial = null;
      }
      if (mesh.userData.highlightEdgeMaterial) {
        mesh.userData.highlightEdgeMaterial.dispose();
        mesh.userData.highlightEdgeMaterial = null;
      }
      if (mesh.userData.hoverOutline) {
        mesh.remove(mesh.userData.hoverOutline);
        mesh.userData.hoverOutline.traverse((child) => {
          child.geometry?.dispose();
          child.material?.dispose();
        });
        mesh.userData.hoverOutline = null;
      }
      if (mesh.userData.selectOutline) {
        mesh.remove(mesh.userData.selectOutline);
        mesh.userData.selectOutline.traverse((child) => {
          child.geometry?.dispose();
          child.material?.dispose();
        });
        mesh.userData.selectOutline = null;
      }
      mesh.userData.highlightKind = kind;
      if (!kind) {
        mesh.material = mesh.userData.baseMaterial;
        if (mesh.userData.edgeObject) {
          mesh.userData.edgeObject.material = mesh.userData.baseEdgeMaterial;
        }
        return;
      }

      if (kind === "hovered") {
        // 悬停：轻微提亮 + 单层亮红色粗轮廓。
        const material = mesh.userData.baseMaterial.clone();
        material.color = mesh.userData.baseMaterial.color.clone().lerp(new THREE.Color(0xffffff), 0.18);
        material.opacity = this.displayMode === "visible" ? 1 : 0.92;
        material.emissive = new THREE.Color(HOVERED_OUTLINE_COLOR);
        material.emissiveIntensity = 0.07;
        mesh.userData.highlightMaterial = material;
        mesh.material = material;

        const outline = this.createHighlightOutline(mesh.geometry, HOVERED_OUTLINE_COLOR, 0.92);
        mesh.userData.hoverOutline = outline;
        mesh.add(outline);
      } else if (kind === "selected") {
        // 选中：箱体提亮 + 单层高亮红色粗轮廓。
        const material = mesh.userData.baseMaterial.clone();
        material.color = mesh.userData.baseMaterial.color.clone().lerp(new THREE.Color(0xffffff), 0.26);
        material.opacity = this.displayMode === "visible" ? 1 : 0.92;
        material.emissive = new THREE.Color(SELECTED_OUTLINE_COLOR);
        material.emissiveIntensity = 0.12;
        mesh.userData.highlightMaterial = material;
        mesh.material = material;

        const outline = this.createHighlightOutline(mesh.geometry, SELECTED_OUTLINE_COLOR, 0.95);
        mesh.userData.selectOutline = outline;
        mesh.add(outline);
      } else {
        // 动画：当前刚出现的箱体使用同一层醒目的红色高亮。
        const material = mesh.userData.baseMaterial.clone();
        material.color = mesh.userData.baseMaterial.color.clone().lerp(new THREE.Color(0xffffff), 0.34);
        material.opacity = this.displayMode === "visible" ? 1 : 0.92;
        material.emissive = new THREE.Color(ANIMATED_EMISSIVE_COLOR);
        material.emissiveIntensity = 0.2;
        mesh.userData.highlightMaterial = material;
        mesh.material = material;

        const outline = this.createHighlightOutline(mesh.geometry, SELECTED_OUTLINE_COLOR, 0.95);
        mesh.userData.selectOutline = outline;
        mesh.add(outline);
      }
    });
    this.updateMaterialMode();
  }

  pick(event) {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return null;
    }
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects(this.boxMeshes.filter((mesh) => mesh.visible), false)[0]?.object ?? null;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = Math.max(1, rect.width || this.canvas.clientWidth || 1);
    const height = Math.max(1, rect.height || this.canvas.clientHeight || 1);
    this.renderer.setSize(width, height, false);
    const aspect = width / height;
    this.camera.left = (-this.viewHeight * aspect) / 2;
    this.camera.right = (this.viewHeight * aspect) / 2;
    this.camera.top = this.viewHeight / 2;
    this.camera.bottom = -this.viewHeight / 2;
    this.camera.updateProjectionMatrix();
    this.render();
  }

  fitCamera(view = "isometric") {
    if (!this.sceneDimensions) {
      return;
    }
    this.viewHeight = this.sceneDiagonal * 1.5;
    this.camera.near = 0.1;
    this.camera.far = this.sceneDiagonal * 20;
    this.camera.zoom = 1;
    this.resize();
    this.setView(view);
  }

  setView(view = "isometric") {
    const viewKey = ["isometric", "top", "side", "section"].includes(view) ? view : "isometric";
    const distance = this.sceneDiagonal * 2.7;
    const center = this.sceneCenter;
    this.camera.up.set(0, 1, 0);
    if (viewKey === "top") {
      this.camera.position.copy(center).add(new THREE.Vector3(0, distance, 0));
      this.camera.up.set(0, 0, -1);
    } else if (viewKey === "side") {
      this.camera.position.copy(center).add(new THREE.Vector3(0, 0, distance));
    } else if (viewKey === "section") {
      this.camera.position.copy(center).add(new THREE.Vector3(distance, 0, 0));
    } else {
      this.camera.position.copy(center).add(new THREE.Vector3(distance * 0.9, distance * 0.72, distance));
    }
    this.controls.target.copy(center);
    this.camera.lookAt(center);
    this.controls.update();
    this.currentView = viewKey;
    this.onViewChange(viewKey);
    this.render();
  }

  resetView() {
    this.fitCamera("isometric");
  }

  render() {
    this.renderer.render(this.scene, this.camera);
  }

  disposeGroup(group) {
    group.traverse((object) => {
      object.geometry?.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.filter(Boolean).forEach((material) => {
        material.map?.dispose();
        material.dispose();
      });
    });
    // 清理发光外边框
    this.boxMeshes.forEach((mesh) => {
      if (mesh.userData.hoverOutline) {
        mesh.userData.hoverOutline.traverse((child) => {
          child.geometry?.dispose();
          child.material?.dispose();
        });
      }
      if (mesh.userData.selectOutline) {
        mesh.userData.selectOutline.traverse((child) => {
          child.geometry?.dispose();
          child.material?.dispose();
        });
      }
    });
    this.sceneRoot.remove(group);
  }

  dispose() {
    this.canvas.removeEventListener("pointerdown", this.handlePointerDown);
    this.canvas.removeEventListener("pointermove", this.handlePointerMove);
    this.canvas.removeEventListener("pointerup", this.handlePointerUp);
    this.canvas.removeEventListener("pointercancel", this.handlePointerLeave);
    this.canvas.removeEventListener("pointerleave", this.handlePointerLeave);
    this.canvas.removeEventListener("dblclick", this.handleDoubleClick);
    this.canvas.removeEventListener("contextmenu", this.handleContextMenu);
    this.controls.dispose();
    this.clearScene();
    this.renderer.dispose();
  }
}

function sceneDimensions(uld) {
  const crossSection = uld.cross_section ?? [];
  return {
    length: Number(uld.length) || 1,
    maxY: Math.max(1, ...crossSection.map(([y]) => Number(y) || 0)),
    maxZ: Math.max(1, ...crossSection.map(([, z]) => Number(z) || 0)),
  };
}

function createUldGeometry(uld) {
  const crossSection = uld.cross_section ?? [];
  const shape = new THREE.Shape();
  crossSection.forEach(([y, z], index) => {
    if (index === 0) {
      shape.moveTo(Number(y), Number(z));
    } else {
      shape.lineTo(Number(y), Number(z));
    }
  });
  shape.closePath();

  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: Number(uld.length) || 1,
    bevelEnabled: false,
    steps: 1,
  });
  const position = geometry.getAttribute("position");
  for (let index = 0; index < position.count; index += 1) {
    const dataY = position.getX(index);
    const dataZ = position.getY(index);
    const dataX = position.getZ(index);
    position.setXYZ(index, dataX, dataZ, dataY);
  }
  position.needsUpdate = true;
  geometry.computeVertexNormals();
  return geometry;
}

function normalizeColor(value) {
  if (value instanceof THREE.Color) {
    return value.clone();
  }
  if (typeof value === "number") {
    return new THREE.Color(value);
  }
  if (value && typeof value === "object") {
    return new THREE.Color((Number(value.r) << 16) | (Number(value.g) << 8) | Number(value.b));
  }
  return new THREE.Color(0x4f76ad);
}

function createAxisLabelSprite(label, color, size) {
  const fontSize = 64;
  const horizontalPadding = 18;
  const verticalPadding = 12;
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2.5);
  const measureCanvas = document.createElement("canvas");
  const measureContext = measureCanvas.getContext("2d");
  measureContext.font = `700 ${fontSize}px Arial, sans-serif`;
  const textWidth = measureContext.measureText(label).width;
  const width = Math.ceil(textWidth + horizontalPadding * 2);
  const height = fontSize + verticalPadding * 2;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(width * pixelRatio);
  canvas.height = Math.ceil(height * pixelRatio);
  const context = canvas.getContext("2d");
  context.scale(pixelRatio, pixelRatio);
  context.font = `700 ${fontSize}px Arial, sans-serif`;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.lineJoin = "round";
  context.lineWidth = 10;
  context.strokeStyle = "rgba(255, 255, 255, 0.94)";
  context.shadowColor = "rgba(15, 23, 42, 0.28)";
  context.shadowBlur = 5;
  context.shadowOffsetY = 2;
  context.strokeText(label, width / 2, height / 2);
  context.shadowColor = "transparent";
  context.fillStyle = new THREE.Color(color).getStyle();
  context.fillText(label, width / 2, height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  if ("colorSpace" in texture) {
    texture.colorSpace = THREE.SRGBColorSpace;
  }
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(size * (width / height), size, 1);
  sprite.renderOrder = 30;
  return sprite;
}

function setMaterialVisibility(material, values) {
  const materials = Array.isArray(material) ? material : [material];
  materials.filter(Boolean).forEach((item) => {
    Object.assign(item, values);
    item.needsUpdate = true;
  });
}

window.ThreeSceneViewer = ThreeSceneViewer;
