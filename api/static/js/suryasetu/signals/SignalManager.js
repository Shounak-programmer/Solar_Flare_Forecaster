/**
 * SignalManager — Orchestrates EM, SEP, CME waves, and Interplanetary Communication Links
 */

import { EMPropagation } from "./EMPropagation.js";
import { SEPPropagation } from "./SEPPropagation.js";
import { CMEPropagation } from "./CMEPropagation.js";
import { TimingEngine } from "../physics/timing.js";

export class SignalManager {
  constructor(scene, getPositions) {
    this.scene = scene;
    this.getPositions = getPositions;
    this.timing = new TimingEngine();

    this.em = new EMPropagation(scene);
    this.sep = new SEPPropagation(scene);
    this.cme = new CMEPropagation(scene);

    this.group = new THREE.Group();
    this.group.name = "SignalManager_Group";

    this.showEM = true;
    this.showSEP = true;
    this.showCME = true;
    this.showCommLinks = true;

    this.simulationState = "IDLE"; // "IDLE", "FLARING", "EM_PROPAGATING", "SEP_PROPAGATING", "CME_PROPAGATING", "COMPLETED"
    this.stepNarrative = "System standby. Ready for solar flare simulation.";

    this._createCommLinks();
    this.scene.add(this.group);
  }

  _createCommLinks() {
    this.commLinkGroup = new THREE.Group();
    this.commLinks = [];

    const makeLink = (id, labelFrom, labelTo, getFrom, getTo, color = 0x00e5ff) => {
      const geo = new THREE.BufferGeometry();
      const mat = new THREE.LineDashedMaterial({
        color,
        transparent: true,
        opacity: 0.6,
        dashSize: 1.5,
        gapSize: 1.0
      });
      const line = new THREE.Line(geo, mat);

      // Moving data packet pulse
      const pktGeo = new THREE.SphereGeometry(0.35, 8, 8);
      const pktMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const pkt = new THREE.Mesh(pktGeo, pktMat);

      this.commLinkGroup.add(line);
      this.commLinkGroup.add(pkt);

      this.commLinks.push({
        id,
        getFrom,
        getTo,
        line,
        geo,
        pkt,
        t: Math.random(),
        speed: 0.6 + Math.random() * 0.4
      });
    };

    const p = this.getPositions.vis;

    // Aditya-L1 -> Earth direct DSN link
    makeLink("aditya_earth", "Aditya-L1", "Earth", () => p.adityaL1(), () => p.earth(), 0x00e5ff);

    this.group.add(this.commLinkGroup);
  }

  triggerSolarFlareSimulation(spacecraftRefs, onStepUpdate) {
    this.simulationState = "FLARING";
    this.stepNarrative = "T+00:00.0 — Solar flare impulsive phase triggered! Soft X-ray flux rising sharply.";
    if (onStepUpdate) onStepUpdate(this.stepNarrative, 0);

    // 1. Trigger EM speed-of-light wave
    this.em.trigger({
      onL1Reached: () => {
        if (spacecraftRefs.adityaL1) spacecraftRefs.adityaL1.triggerDetection();
        this.stepNarrative = "T+494.0 s — ADITYA-L1 DETECTS EVENT! SoLEXS & HEL1OS observe hard X-ray impulsive peak.";
        if (onStepUpdate) onStepUpdate(this.stepNarrative, 494);
      },
      onEarthReached: () => {
        this.stepNarrative = "T+499.0 s — EARTH RECEIVES X-RAY SIGNAL! Aditya-L1 provided ~5.0 s electromagnetic lead time.";
        if (onStepUpdate) onStepUpdate(this.stepNarrative, 499);
      }
    });

    // 2. Trigger SEP particle stream along Parker spiral
    setTimeout(() => {
      this.sep.trigger();
      this.stepNarrative = "T+25 to 60 min — Solar Energetic Particles (SEPs) arrive along the Parker Spiral magnetic field lines.";
      if (onStepUpdate) onStepUpdate(this.stepNarrative, 1800);
    }, 4500);

    // 3. Trigger CME bulk plasma propagation
    setTimeout(() => {
      this.cme.trigger({
        onL1Passage: () => {
          this.stepNarrative = "T+1.7 days (~41 hours) — CME shock front reaches Sun-Earth L1 region. Aditya-L1 in-situ payloads (ASPEX, PAPA, MAG) record shock passage.";
          if (onStepUpdate) onStepUpdate(this.stepNarrative, 147600);
        },
        onEarthImpact: () => {
          this.stepNarrative = "T+1.8 days (~43 hours) — CME shock front impacts Earth magnetosphere. Geomagnetic storm warning active.";
          if (onStepUpdate) onStepUpdate(this.stepNarrative, 154800);
        }
      });
    }, 6000);
  }

  update(delta) {
    if (this.showEM) this.em.update(delta);
    if (this.showSEP) this.sep.update(delta);
    if (this.showCME) this.cme.update(delta);

    // Update communication link pulses
    if (this.showCommLinks) {
      for (const link of this.commLinks) {
        const from = link.getFrom();
        const to = link.getTo();
        if (from && to) {
          const pA = new THREE.Vector3(from.x, from.y, from.z);
          const pB = new THREE.Vector3(to.x, to.y, to.z);
          link.geo.setFromPoints([pA, pB]);
          link.line.computeLineDistances();

          link.t = (link.t + delta * link.speed) % 1.0;
          link.pkt.position.lerpVectors(pA, pB, link.t);
        }
      }
    }
  }

  setParkerSpiralVisible(visible) {
    if (this.sep) {
      this.sep.setSpiralVisible(visible);
    }
  }

  setCommLinksVisible(visible) {
    this.showCommLinks = visible;
    this.commLinkGroup.visible = visible;
  }

  resetAll() {
    this.em.reset();
    this.sep.reset();
    this.cme.reset();
    this.simulationState = "IDLE";
    this.stepNarrative = "System standby. Ready for solar flare simulation.";
  }
}
