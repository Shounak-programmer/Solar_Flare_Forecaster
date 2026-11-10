/**
 * HUD & Mission Control Overlay for SURYASETU
  
 * Professional aerospace mission-control styling:
 * - Restrained typography and high legibility
 * - System status, telemetry telemetry cards, measurement tables
 * - Interactive mode selectors, camera presets, speed controls
 * - Solar flare timeline & presentation controller interface
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class HUD {
  constructor(container, app) {
    this.container = container;
    this.app = app;
    this.params = SYSTEM_PARAMETERS;

    this._createDOM();
    this._attachEventListeners();
  }

  _createDOM() {
    this.hudRoot = document.createElement("div");
    this.hudRoot.className = "suryasetu-hud";

    this.hudRoot.innerHTML = `
      <!-- TOP CONTROL & TITLE BAR -->
      <div class="ss-header">
        <div class="ss-branding">
          <div class="ss-title-row">
            <span class="ss-badge-live">MISSION 3D</span>
            <span class="ss-title">SURYASETU</span>
            <span class="ss-version">v2.4 / PS-15</span>
          </div>
          <div class="ss-subtitle">Proposed Multi-Point Solar Observation &amp; Space Weather Architecture</div>
        </div>

        <div class="ss-mode-bar">
          <button class="ss-mode-btn active" data-mode="OVERVIEW">Overview</button>
          <button class="ss-mode-btn" data-mode="DISTANCES">Distances</button>
          <button class="ss-mode-btn" data-mode="ANGLES">Angles</button>
          <button class="ss-mode-btn" data-mode="SIGNALS">Signals</button>
          <button class="ss-mode-btn ss-flare-btn" data-mode="SOLAR_EVENT">Simulate Flare</button>
        </div>

        <div class="ss-presentation-launch">
          <button class="ss-pres-btn" id="ssStartPresentation">
            <span class="ss-pres-icon">▶</span> START PRESENTATION
          </button>
        </div>
      </div>

      <!-- PRESENTATION CONTROL BANNER (Active during presentation mode) -->
      <div class="ss-pres-bar" id="ssPresBar" style="display: none;">
        <div class="ss-pres-info">
          <div class="ss-pres-badge">HOD / HACKATHON BRIEFING</div>
          <div class="ss-pres-title" id="ssPresTitle">1. Heliocentric Overview</div>
          <div class="ss-pres-desc" id="ssPresDesc">Overview of Sun, Earth, Lagrange regions, and orbital geometry.</div>
        </div>
        <div class="ss-pres-controls">
          <span class="ss-pres-counter" id="ssPresCounter">1 / 10</span>
          <button class="ss-btn-sm" id="ssPresPrev">◀ Prev</button>
          <button class="ss-btn-sm" id="ssPresNext">Next ▶</button>
          <button class="ss-btn-sm danger" id="ssPresExit">Exit</button>
        </div>
      </div>

      <!-- FLOATING SIDEBAR TOGGLE BUTTONS -->
      <button class="ss-tab-toggle left" id="ssToggleLeft" title="Toggle Controls">◀ Controls</button>
      <button class="ss-tab-toggle right" id="ssToggleRight" title="Toggle Telemetry">Telemetry ▶</button>

      <!-- LEFT SIDEBAR: CAMERA & SIMULATION CONTROLS -->
      <div class="ss-sidebar-left" id="ssSidebarLeft">
        <div class="ss-panel-box">
          <div class="ss-box-header">
            <span>Camera Targets</span>
            <button class="ss-panel-hide-btn" data-target="ssSidebarLeft" title="Hide panel">✕</button>
          </div>
          <div class="ss-cam-grid">
            <button class="ss-cam-btn" data-cam="reset">Reset</button>
            <button class="ss-cam-btn" data-cam="sun">Sun</button>
            <button class="ss-cam-btn" data-cam="earth">Earth</button>
            <button class="ss-cam-btn primary-aditya" data-cam="l1">Aditya-L1</button>
          </div>
        </div>

        <div class="ss-panel-box">
          <div class="ss-box-header">Layers &amp; Orbits</div>
          <div class="ss-toggle-list">
            <label class="ss-chk-lbl"><input type="checkbox" id="chkEarthOrbit" checked> Earth Orbit (1 AU)</label>
            <label class="ss-chk-lbl"><input type="checkbox" id="chkL1Halo" checked> Aditya-L1 3D Halo Orbit</label>
            <label class="ss-chk-lbl"><input type="checkbox" id="chkLagrange" checked> L1 Point — Reference</label>
            <label class="ss-chk-lbl"><input type="checkbox" id="chkParkerSpiral" checked> Parker Spiral / Magnetic Field</label>
            <label class="ss-chk-lbl"><input type="checkbox" id="chkDistLines" checked> Distance Rays</label>
            <label class="ss-chk-lbl"><input type="checkbox" id="chkCommLinks" checked> Communication Links</label>
          </div>
        </div>

        <div class="ss-panel-box">
          <div class="ss-box-header">Simulation Speed</div>
          <div class="ss-speed-row">
            <button class="ss-spd-btn" data-spd="0.25">0.25×</button>
            <button class="ss-spd-btn" data-spd="0.5">0.5×</button>
            <button class="ss-spd-btn active" data-spd="1.0">1×</button>
            <button class="ss-spd-btn" data-spd="2.0">2×</button>
            <button class="ss-spd-btn" data-spd="5.0">5×</button>
            <button class="ss-spd-btn" data-spd="10.0">10×</button>
          </div>
          <div class="ss-playpause-row">
            <button class="ss-btn-wide" id="ssPlayPause">❚❚ Pause Simulation</button>
          </div>
        </div>

        <!-- VISUAL LEGEND -->
        <div class="ss-panel-box ss-legend-box">
          <div class="ss-box-header">Visual Legend</div>
          <div class="ss-legend-item"><span class="ss-leg-line earth"></span> Earth Orbit (1 AU)</div>
          <div class="ss-legend-item"><span class="ss-leg-line halo"></span> Aditya-L1 Halo Orbit</div>
          <div class="ss-legend-item"><span class="ss-leg-dot l1-ref"></span> L1 Point — Reference</div>
          <div class="ss-legend-item"><span class="ss-leg-dot oper"></span> Aditya-L1 — Operational (ISRO)</div>
          <div class="ss-legend-item"><span class="ss-leg-line cme"></span> CME / Expanding Shock Front</div>
          <div class="ss-legend-item"><span class="ss-leg-line em"></span> Solar Flare / X-ray Pulse (c)</div>
          <div class="ss-legend-item"><span class="ss-leg-line sep"></span> SEP Particle Stream</div>
          <div class="ss-legend-item"><span class="ss-leg-line parker"></span> Parker Spiral / Magnetic Field</div>
          <div class="ss-legend-item"><span class="ss-leg-line comm"></span> Interplanetary Telemetry Link</div>
        </div>
      </div>

      <!-- RIGHT SIDEBAR: TELEMETRY & MEASUREMENT READOUTS -->
      <div class="ss-sidebar-right" id="ssSidebarRight">
        <!-- OBJECT TELEMETRY CARD -->
        <div class="ss-panel-box" id="ssTelemetryCard">
          <div class="ss-box-header">
            <span id="ssTelemTitle">Object Telemetry</span>
            <span class="ss-badge-status oper" id="ssTelemStatus">OPERATIONAL</span>
            <button class="ss-panel-hide-btn" data-target="ssSidebarRight" title="Hide panel">✕</button>
          </div>
          <div class="ss-telem-body" id="ssTelemBody">
            <div class="ss-telem-prop"><span class="lbl">Mission</span><span class="val" id="telMission">Aditya-L1 (ISRO)</span></div>
            <div class="ss-telem-prop"><span class="lbl">Location</span><span class="val" id="telLocation">Sun–Earth L1 Halo Region (~1.5M km from Earth)</span></div>
            <div class="ss-telem-prop"><span class="lbl">Orbit</span><span class="val" id="telOrbit">3D Halo Orbit around Sun–Earth L1</span></div>
            <div class="ss-telem-prop"><span class="lbl">Light Time from Sun</span><span class="val" id="telLightTime">~494.0 s (~8 min 14 s)</span></div>
            <div class="ss-telem-prop highlight"><span class="lbl">EM Advantage over Earth</span><span class="val" id="telAdvantage">~5.00 s (range 2.7–7.3 s)</span></div>
            <div class="ss-telem-desc" id="telDesc">Continuous solar observation in a 3D periodic halo orbit around the Sun–Earth L1 reference point. Features SoLEXS (2–22 keV) and HEL1OS (10–150 keV).</div>
          </div>
        </div>

        <!-- REAL-TIME SYSTEM GEOMETRY & DISTANCE TABLE -->
        <div class="ss-panel-box" id="ssDistancesCard">
          <div class="ss-box-header">Calculated System Geometry</div>
          <div class="ss-dist-table" id="ssDistTable">
            <!-- Dynamically populated from DistanceCalculator -->
          </div>
        </div>

        <!-- PHYSICS INFORMATION BOX -->
        <div class="ss-panel-box ss-physics-box">
          <div class="ss-box-header">Physics &amp; Propagation Principles</div>
          <div class="ss-physics-text">
            <b>X-Rays &amp; EUV:</b> Electromagnetic radiation traveling at <i>c</i>. Reaches Earth in ~499 s; Aditya-L1 detects ~5 s earlier. Drives HF radio blackouts.<br><br>
            <b>SEPs:</b> Charged protons/electrons guided along interplanetary Parker spiral lines. Speeds 0.15–0.5c; arrival in 20 min to hours.<br><br>
            <b>CME:</b> Bulk magnetized plasma cloud (400–2200 km/s). Typical transit: ~1–4 days. Triggers geomagnetic storms (G1–G5).
          </div>
        </div>
      </div>

      <!-- BOTTOM BAR: SOLAR FLARE SIMULATION TIMELINE & NARRATIVE (CENTERED & COMPACT) -->
      <div class="ss-timeline-bar" id="ssTimelineBar">
        <div class="ss-tl-header">
          <span class="ss-tl-tag">EVENT SEQUENCE</span>
          <span class="ss-tl-narrative" id="ssTimelineNarrative">Standby. Click "Simulate Flare" to trigger multi-point detection sequence.</span>
          <div class="ss-dual-clock">
            <div class="ss-clock-item">
              <span class="clk-lbl">PHYSICAL TIME</span>
              <span class="clk-val" id="ssPhysicalClock">00:00.0</span>
            </div>
            <div class="ss-clock-item">
              <span class="clk-lbl">STATUS</span>
              <span class="clk-val state-quiet" id="ssEventState">IDLE</span>
            </div>
          </div>
          <button class="ss-tl-min-btn" id="ssTimelineMinBtn" title="Minimize / Expand Timeline">▾</button>
        </div>
        <div class="ss-tl-progress-track" id="ssTimelineTrack">
          <div class="ss-tl-step s1" title="T+00:00 Flare Onset"><span>T+0</span>Flare</div>
          <div class="ss-tl-step s2" title="T+494s Aditya-L1 Detection"><span>T+494s</span>L1 Detection</div>
          <div class="ss-tl-step s3" title="T+499s Earth Detection"><span>T+499s</span>Earth (5s Lead)</div>
          <div class="ss-tl-step s4" title="T+30m SEP Stream"><span>T+30m</span>SEPs</div>
          <div class="ss-tl-step s5" title="T+2d CME Shock"><span>T+2d</span>CME Shock</div>
          <div class="ss-tl-bar-fill" id="ssTimelineFill"></div>
        </div>
      </div>

      <!-- SCIENTIFIC DISCLAIMER FOOTER -->
      <div class="ss-disclaimer">
        Conceptual visualization — distances and spacecraft sizes are visually exaggerated for clarity. Aditya-L1 operates in a 3D periodic halo orbit continuously traveling around the Sun–Earth L1 reference point (~1.5M km from Earth).
      </div>
    `;

    this.container.appendChild(this.hudRoot);
  }

  _attachEventListeners() {
    // Mode Buttons
    this.hudRoot.querySelectorAll(".ss-mode-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const mode = btn.dataset.mode;
        this.hudRoot.querySelectorAll(".ss-mode-btn").forEach(b => b.classList.toggle("active", b === btn));
        this.app.setMode(mode);
      });
    });

    // Camera Focus Buttons
    this.hudRoot.querySelectorAll(".ss-cam-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const cam = btn.dataset.cam;
        this.app.focusCamera(cam);
      });
    });

    // Layer Checkboxes
    const bindChk = (id, fn) => {
      const el = this.hudRoot.querySelector(`#${id}`);
      if (el) el.addEventListener("change", e => fn(e.target.checked));
    };
    bindChk("chkEarthOrbit", c => this.app.orbitManager.setOrbitVisibility("earth", c));
    bindChk("chkL1Halo", c => this.app.orbitManager.setOrbitVisibility("l1Halo", c));
    bindChk("chkLagrange", c => this.app.orbitManager.setOrbitVisibility("lagrangePoints", c));
    bindChk("chkParkerSpiral", c => this.app.signalManager.setParkerSpiralVisible(c));
    bindChk("chkDistLines", c => this.app.measurementManager.setDistancesVisible(c));
    bindChk("chkCommLinks", c => this.app.signalManager.setCommLinksVisible(c));

    // Speed Multipliers
    this.hudRoot.querySelectorAll(".ss-spd-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const spd = parseFloat(btn.dataset.spd);
        this.hudRoot.querySelectorAll(".ss-spd-btn").forEach(b => b.classList.toggle("active", b === btn));
        this.app.setSimSpeed(spd);
      });
    });

    // Play / Pause
    const playPauseBtn = this.hudRoot.querySelector("#ssPlayPause");
    if (playPauseBtn) {
      playPauseBtn.addEventListener("click", () => {
        const isPaused = this.app.togglePlayPause();
        playPauseBtn.textContent = isPaused ? "▶ Resume Simulation" : "❚❚ Pause Simulation";
      });
    }

    // Presentation Mode Buttons
    const presStart = this.hudRoot.querySelector("#ssStartPresentation");
    if (presStart) presStart.addEventListener("click", () => this.app.presentation.start());

    const presPrev = this.hudRoot.querySelector("#ssPresPrev");
    if (presPrev) presPrev.addEventListener("click", () => this.app.presentation.prev());

    const presNext = this.hudRoot.querySelector("#ssPresNext");
    if (presNext) presNext.addEventListener("click", () => this.app.presentation.next());

    const presExit = this.hudRoot.querySelector("#ssPresExit");
    if (presExit) presExit.addEventListener("click", () => this.app.presentation.stop());

    // Sidebar collapse & floating toggle tabs
    const sbLeft = this.hudRoot.querySelector("#ssSidebarLeft");
    const sbRight = this.hudRoot.querySelector("#ssSidebarRight");
    const togLeft = this.hudRoot.querySelector("#ssToggleLeft");
    const togRight = this.hudRoot.querySelector("#ssToggleRight");

    const toggleSidebar = (sb, btn) => {
      const isHidden = sb.classList.toggle("collapsed");
      if (btn) btn.classList.toggle("active", isHidden);
    };

    if (togLeft) togLeft.addEventListener("click", () => toggleSidebar(sbLeft, togLeft));
    if (togRight) togRight.addEventListener("click", () => toggleSidebar(sbRight, togRight));

    this.hudRoot.querySelectorAll(".ss-panel-hide-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.target;
        const targetEl = this.hudRoot.querySelector(`#${targetId}`);
        const togBtn = targetId === "ssSidebarLeft" ? togLeft : togRight;
        if (targetEl) toggleSidebar(targetEl, togBtn);
      });
    });

    // Timeline bar minimize / expand
    const tlBar = this.hudRoot.querySelector("#ssTimelineBar");
    const tlMinBtn = this.hudRoot.querySelector("#ssTimelineMinBtn");
    if (tlMinBtn && tlBar) {
      tlMinBtn.addEventListener("click", () => {
        const isMin = tlBar.classList.toggle("minimized");
        tlMinBtn.textContent = isMin ? "▴" : "▾";
      });
    }
  }

  updatePresentationUI(active, scene, current, total) {
    const bar = this.hudRoot.querySelector("#ssPresBar");
    const launchBtn = this.hudRoot.querySelector("#ssStartPresentation");

    if (active && scene) {
      bar.style.display = "flex";
      launchBtn.style.display = "none";
      this.hudRoot.querySelector("#ssPresTitle").textContent = scene.title;
      this.hudRoot.querySelector("#ssPresDesc").textContent = scene.desc;
      this.hudRoot.querySelector("#ssPresCounter").textContent = `${current} / ${total}`;
    } else {
      bar.style.display = "none";
      launchBtn.style.display = "flex";
    }
  }

  updateTelemetry(objId) {
    const card = this.hudRoot.querySelector("#ssTelemetryCard");
    const title = this.hudRoot.querySelector("#ssTelemTitle");
    const status = this.hudRoot.querySelector("#ssTelemStatus");
    const mission = this.hudRoot.querySelector("#telMission");
    const loc = this.hudRoot.querySelector("#telLocation");
    const orbit = this.hudRoot.querySelector("#telOrbit");
    const lightTime = this.hudRoot.querySelector("#telLightTime");
    const adv = this.hudRoot.querySelector("#telAdvantage");
    const desc = this.hudRoot.querySelector("#telDesc");

    if (objId === "aditya_l1") {
      title.textContent = "Aditya-L1";
      status.textContent = "OPERATIONAL (ISRO)";
      status.className = "ss-badge-status oper";
      mission.textContent = "ISRO Operational Solar Observatory";
      loc.textContent = "Sun–Earth L1 Halo Region (~1.5M km from Earth)";
      orbit.textContent = "3D Halo Orbit around Sun–Earth L1";
      lightTime.textContent = "~494.0 s (~8 min 14 s)";
      adv.textContent = "~5.00 s lead time over Earth (range 2.7–7.3s)";
      desc.textContent = "Continuous solar observation in a 3D periodic halo orbit around the Sun–Earth L1 reference point (Ay ≈ 670,000 km, T ≈ 177.8 days). Features SoLEXS and HEL1OS for solar flare forecasting.";
    } else if (objId === "l1_point" || objId === "l1_nominal") {
      title.textContent = "L1 Point (Reference)";
      status.textContent = "REFERENCE";
      status.className = "ss-badge-status";
      mission.textContent = "Sun–Earth Collinear Lagrange Point 1";
      loc.textContent = "~1.50 million km Sunward of Earth";
      orbit.textContent = "Dynamical Reference Point (Not a Spacecraft)";
      lightTime.textContent = "~494.0 s (~8 min 14 s)";
      adv.textContent = "~5.00 s (Geometric Reference Plane)";
      desc.textContent = "Stationary dynamical equilibrium reference point between Sun and Earth. Aditya-L1 does not sit stationary here; it operates in a 3D periodic halo orbit around this reference point.";
    } else if (objId === "earth") {
      title.textContent = "Earth";
      status.textContent = "1.00 AU";
      status.className = "ss-badge-status";
      mission.textContent = "Terrestrial System & Space Weather Assets";
      loc.textContent = "1 AU (~149,597,870 km from Sun)";
      orbit.textContent = "Heliocentric 1-year orbit (e = 0.0167)";
      lightTime.textContent = "499.0 s (~8 min 19 s)";
      adv.textContent = "0.0 s (Baseline reference observer)";
      desc.textContent = "Target for space weather operations: HF radio blackouts, geomagnetically induced currents (GICs), auroral electrojets, and satellite telemetry links.";
    } else if (objId === "sun") {
      title.textContent = "Sun";
      status.textContent = "SOLAR CORE";
      status.className = "ss-badge-status warning";
      mission.textContent = "G2V Main Sequence Star";
      loc.textContent = "Solar System Barycenter / Origin (0,0,0)";
      orbit.textContent = "Differential rotation (~25 days equator)";
      lightTime.textContent = "0.0 s (Source of all flare emissions)";
      adv.textContent = "Origin of radiation and coronal mass ejections";
      desc.textContent = "Source of solar flares, magnetic reconnection loops, soft/hard X-rays, solar energetic particles (SEPs), and Coronal Mass Ejections (CMEs).";
    } else if (objId === "l2_observatory" || objId === "l3_observatory" || objId === "relay_orbiter") {
      // These objects are no longer part of the scene; no-op.
    }
  }

  updateDistancesTable(metrics) {
    const table = this.hudRoot.querySelector("#ssDistTable");
    if (!table || !metrics || metrics.length === 0) return;

    let html = `
      <div class="ss-tbl-row header">
        <span>Path</span>
        <span>Distance (km)</span>
        <span>AU</span>
        <span>Light Travel</span>
      </div>
    `;

    for (const m of metrics) {
      html += `
        <div class="ss-tbl-row">
          <span class="path">${m.label}</span>
          <span class="km">${m.distanceFormatted}</span>
          <span class="au">${m.auFormatted}</span>
          <span class="time">${m.lightTimeFormatted}</span>
        </div>
      `;
    }
    table.innerHTML = html;
  }

  updateFlareNarrative(narrative, physicalSeconds) {
    const elNarrative = this.hudRoot.querySelector("#ssTimelineNarrative");
    const elClock = this.hudRoot.querySelector("#ssPhysicalClock");
    const elState = this.hudRoot.querySelector("#ssEventState");
    const elFill = this.hudRoot.querySelector("#ssTimelineFill");

    if (elNarrative) elNarrative.textContent = narrative;

    if (elClock && physicalSeconds !== undefined) {
      const mins = Math.floor(physicalSeconds / 60);
      const secs = physicalSeconds % 60;
      elClock.textContent = `${String(mins).padStart(2, "0")}:${secs.toFixed(1).padStart(4, "0")}`;
    }

    if (elState) {
      if (physicalSeconds === 0) {
        elState.textContent = "FLARE ONSET";
        elState.className = "clk-val state-warn";
      } else if (physicalSeconds <= 494) {
        elState.textContent = "L1 DETECTION";
        elState.className = "clk-val state-watch";
      } else if (physicalSeconds <= 499) {
        elState.textContent = "EARTH EM IMPACT";
        elState.className = "clk-val state-warn";
      } else {
        elState.textContent = "PARTICLES / CME";
        elState.className = "clk-val state-watch";
      }
    }

    if (elFill && physicalSeconds !== undefined) {
      const pct = Math.min(100, Math.max(0, (physicalSeconds / 499) * 55));
      elFill.style.width = `${pct}%`;
    }
  }

  // Hook to integrate with Solar Flare Forecaster ML predictions
  setOperationalForecasterState(stateData) {
    const elState = this.hudRoot.querySelector("#ssEventState");
    const elNarrative = this.hudRoot.querySelector("#ssTimelineNarrative");

    if (stateData && stateData.riskLevel) {
      if (elState) {
        elState.textContent = stateData.riskLevel.toUpperCase();
        elState.className = `clk-val state-${stateData.riskLevel.toLowerCase()}`;
      }
      if (elNarrative && stateData.message) {
        elNarrative.textContent = stateData.message;
      }
    }
  }
}
