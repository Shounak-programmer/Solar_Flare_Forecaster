/**
 * SuryaSetuApp — Main Application Orchestrator & Integration Controller
 * 
 * Production-quality 3D Scientific Visualization for ISRO / Hackathon / HOD demonstration.
 */

import { SYSTEM_PARAMETERS } from "./data/systemParameters.js";
import { CoordinateTransformer } from "./physics/coordinates.js";
import { SceneManager } from "./main/SceneManager.js";
import { LightingManager } from "./main/LightingManager.js";
import { CameraManager } from "./main/CameraManager.js";
import { RendererManager } from "./main/RendererManager.js";
import { Sun } from "./celestial/Sun.js";
import { Earth } from "./celestial/Earth.js";
import { AdityaL1 } from "./spacecraft/AdityaL1.js";
import { OrbitManager } from "./orbits/OrbitManager.js";
import { MeasurementManager } from "./measurements/MeasurementManager.js";
import { SignalManager } from "./signals/SignalManager.js";
import { SolarFlare } from "./solar/SolarFlare.js";
import { PresentationController } from "./presentation/PresentationController.js";
import { HUD } from "./ui/HUD.js";

export class SuryaSetuApp {
  constructor(containerElement) {
    this.container = containerElement;
    this.params = SYSTEM_PARAMETERS;
    this.coords = new CoordinateTransformer(this.params);

    this.simTimeDays = 0; // Simulation time in orbital days
    this.simSpeed = 1.0;
    this.isPaused = false;
    this.lastFrameTime = performance.now();

    this.selectedObjectId = "aditya_l1";
    this.hoveredObjectId = null;

    this.positions = {
      sci: {
        sun: () => this.coords.getScientificSunPosition(),
        earth: () => this.coords.getScientificEarthPosition(0),
        adityaL1: () => this.coords.getScientificAdityaL1Position(this.simTimeDays, 0)
      },
      vis: {
        sun: () => this.coords.getVisualSunPosition(),
        earth: () => this.coords.getVisualEarthPosition(0),
        l1Nominal: () => this.coords.getVisualL1NominalPosition(0),
        adityaL1: () => this.coords.getVisualAdityaL1Position(this.simTimeDays, 0)
      }
    };

    this._initThree();
    this._initEntities();
    this._initManagers();
    this._initHUD();
    this._initEvents();

    this.presentation = new PresentationController(this);

    // Initial camera position & selection
    this.cameraManager.focusOverview();
    this.selectObject("aditya_l1");

    this._animate = this._animate.bind(this);
    requestAnimationFrame(this._animate);
  }

  _initThree() {
    // Canvas wrapper
    this.canvasWrapper = document.createElement("div");
    this.canvasWrapper.className = "suryasetu-canvas-wrapper";
    this.container.appendChild(this.canvasWrapper);

    this.sceneManager = new SceneManager();
    this.scene = this.sceneManager.scene;

    // Perspective Camera: 45° FOV, near 0.1, far 2000
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || (window.innerHeight - 80);
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.5, 2500);
    this.camera.position.set(70, 115, 185);

    this.rendererManager = new RendererManager(this.canvasWrapper);
    this.lightingManager = new LightingManager(this.scene);
    this.cameraManager = new CameraManager(this.camera, this.rendererManager.getDomElement());
  }

  _initEntities() {
    this.sun = new Sun(this.scene, this.params);
    this.earth = new Earth(this.scene, this.params);
    this.adityaL1 = new AdityaL1(this.scene);
    this.solarFlare = new SolarFlare(this.scene, new THREE.Vector3(0, 0, 0), this.params.visual.sunRadius);

    this.spacecraftMap = {
      aditya_l1: this.adityaL1
    };

    this.selectableMeshes = [
      this.sun.mesh,
      this.earth.earthMesh,
      this.adityaL1.busMesh
    ];
  }

  _initManagers() {
    this.orbitManager = new OrbitManager(this.scene, this.params);
    this.measurementManager = new MeasurementManager(this.scene, this.positions);
    this.signalManager = new SignalManager(this.scene, this.positions);

    if (this.orbitManager.l1MarkerClickMesh) {
      this.selectableMeshes.push(this.orbitManager.l1MarkerClickMesh);
    }
  }

  _initHUD() {
    this.hud = new HUD(this.container, this);
  }

  _initEvents() {
    const dom = this.rendererManager.getDomElement();

    window.addEventListener("resize", () => {
      this.handleResize();
    });

    dom.addEventListener("pointerdown", (e) => {
      const hit = this.sceneManager.raycast(e, this.camera, dom, this.selectableMeshes);
      if (hit && hit.id) {
        this.selectObject(hit.id);
      }
    });

    dom.addEventListener("pointermove", (e) => {
      const hit = this.sceneManager.raycast(e, this.camera, dom, this.selectableMeshes);
      if (hit && hit.id) {
        dom.style.cursor = "pointer";
        if (this.hoveredObjectId !== hit.id) {
          if (this.spacecraftMap[this.hoveredObjectId]) {
            this.spacecraftMap[this.hoveredObjectId].setHovered(false);
          }
          this.hoveredObjectId = hit.id;
          if (this.spacecraftMap[hit.id]) {
            this.spacecraftMap[hit.id].setHovered(true);
          }
        }
      } else {
        dom.style.cursor = "default";
        if (this.hoveredObjectId && this.spacecraftMap[this.hoveredObjectId]) {
          this.spacecraftMap[this.hoveredObjectId].setHovered(false);
          this.hoveredObjectId = null;
        }
      }
    });
  }

  selectObject(id) {
    this.selectedObjectId = id;

    // Clear previous spacecraft reticles
    for (const scId in this.spacecraftMap) {
      this.spacecraftMap[scId].setSelected(scId === id);
    }

    // Update HUD telemetry card
    this.hud.updateTelemetry(id);

    // Camera auto-focus on selection
    if (id === "sun") this.cameraManager.focusSun();
    else if (id === "earth") this.cameraManager.focusEarth(this.positions.vis.earth());
    else if (id === "aditya_l1" || id === "l1_point" || id === "l1_nominal") {
      this.cameraManager.focusAdityaL1(this.positions.vis.l1Nominal());
    }
  }

  focusCamera(target) {
    if (target === "reset") this.cameraManager.focusOverview();
    else if (target === "sun") this.cameraManager.focusSun();
    else if (target === "earth") this.cameraManager.focusEarth(this.positions.vis.earth());
    else if (target === "l1") {
      this.cameraManager.focusAdityaL1(this.positions.vis.l1Nominal());
      this.selectObject("aditya_l1");
    }
  }

  setMode(mode) {
    if (mode === "OVERVIEW") {
      this.cameraManager.focusOverview();
      this.measurementManager.setDistancesVisible(false);
      this.measurementManager.setAnglesVisible(false);
    } else if (mode === "DISTANCES") {
      this.cameraManager.focusOverview();
      this.measurementManager.setDistancesVisible(true);
      this.measurementManager.setAnglesVisible(false);
    } else if (mode === "ANGLES") {
      this.measurementManager.setDistancesVisible(false);
      this.measurementManager.setAnglesVisible(true);
    } else if (mode === "SIGNALS") {
      this.measurementManager.setDistancesVisible(true);
      this.signalManager.setCommLinksVisible(true);
    } else if (mode === "SOLAR_EVENT") {
      this.triggerSolarFlare();
    }
  }

  triggerSolarFlare() {
    this.sun.triggerFlareFlash();
    this.solarFlare.trigger();
    this.signalManager.triggerSolarFlareSimulation({
      adityaL1: this.adityaL1
    }, (narrative, time) => {
      this.hud.updateFlareNarrative(narrative, time);
    });
  }

  setSimSpeed(speed) {
    this.simSpeed = speed;
  }

  togglePlayPause() {
    this.isPaused = !this.isPaused;
    return this.isPaused;
  }

  handleResize() {
    const { width, height, aspect } = this.rendererManager.handleResize();
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  _animate(now) {
    requestAnimationFrame(this._animate);

    // Guard: only simulate and render when the 3D tab is actually visible and has geometry
    const pane = document.getElementById("tab-suryasetu");
    if (!pane || !pane.classList.contains("active") || pane.style.display === "none") {
      return;
    }
    if (!this.container || this.container.clientWidth === 0 || this.container.clientHeight === 0) {
      return;
    }

    const delta = Math.min((now - this.lastFrameTime) / 1000, 0.1);
    this.lastFrameTime = now;

    const effDelta = this.isPaused ? 0 : delta * this.simSpeed;
    const simDaysPerSec = 177.8 / 24.0; // ~24s full 3D halo orbit loop at 1x speed
    this.simTimeDays += effDelta * simDaysPerSec;

    // 1. Update entities
    const vSun = this.positions.vis.sun();
    const vEarth = this.positions.vis.earth();
    const vL1Nominal = this.positions.vis.l1Nominal();
    const vAditya = this.positions.vis.adityaL1();

    this.sun.update(effDelta, this.simTimeDays * 0.1);
    this.earth.update(effDelta, this.simTimeDays, vEarth);
    this.adityaL1.update(effDelta, this.simTimeDays, vAditya, vSun, this.camera);
    this.solarFlare.update(effDelta);

    // 2. Update orbits
    this.orbitManager.updateL1HaloOrbit(vL1Nominal);

    // 3. Update measurements & signals
    this.measurementManager.update(effDelta);
    this.signalManager.update(effDelta);

    // 4. Update HUD measurement table (throttled at ~2 Hz)
    if (!this._lastTableUpdate || now - this._lastTableUpdate > 500) {
      this._lastTableUpdate = now;
      this.hud.updateDistancesTable(this.measurementManager.getActiveDistanceMetrics());
    }

    // 5. Update Camera & Render
    this.cameraManager.update(delta);
    this.rendererManager.render(this.scene, this.camera);
  }

  // ── Integration API for Solar Flare Forecaster ──────────────────────────
  updateSolarEvent(event) {
    if (event && event.active) {
      this.triggerSolarFlare();
    }
  }

  updatePrediction(prediction) {
    if (!prediction) return;
    const prob15 = prediction.prob_15 || prediction.prob || 0;
    let riskLevel = "QUIET";
    let message = "Background solar activity nominal. Low flare risk.";

    if (prob15 >= 0.2006) {
      riskLevel = "WARN";
      message = `High flare risk (${(prob15 * 100).toFixed(1)}%). Impulsive phase expected within 15 min.`;
    } else if (prob15 >= 0.0961) {
      riskLevel = "WATCH";
      message = `Elevated solar activity (${(prob15 * 100).toFixed(1)}%). Monitoring active regions.`;
    }

    this.hud.setOperationalForecasterState({ riskLevel, message });
  }

  updateInstrumentData(data) {
    // React to real-time telemetry updates from SoLEXS / HEL1OS
    if (data && data.flareDetected) {
      this.adityaL1.triggerDetection();
    }
  }

  updateSatelliteState(state) {
    if (state && state.selectedSpacecraft) {
      this.selectObject(state.selectedSpacecraft);
    }
  }
}
