/**
 * Coronal Mass Ejection (CME) Bulk Plasma Propagation System
 * 
 * Physics:
 * - Large-scale eruption of magnetized solar plasma expelled from the corona
 * - Broad expanding 3D shock front and plasma cloud (not a spiral or wireframe web)
 * - Originates at solar active region, detaches from Sun, and sweeps through interplanetary space
 * - Speed range: 400 - 2200 km/s (nominal ~900 km/s)
 * - Interplanetary transit time to 1 AU: 1 to 4 days (~24 to 96 hours)
 * - Arrives at Sun-Earth L1 region (~1.5M km sunward) prior to Earth impact
 * - Drives geomagnetic storms (G1-G5), ionospheric currents, and power grid GICs
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class CMEPropagation {
  constructor(scene, params = SYSTEM_PARAMETERS) {
    this.scene = scene;
    this.params = params;

    const cmePhys = (params.physics && params.physics.cme) || {};
    this.config = {
      speedKmS: cmePhys.nominalSpeedKmS || 900,
      angularWidthDeg: cmePhys.angularWidthDeg || 60,
      direction: new THREE.Vector3(1, 0, 0), // Sun-to-Earth axis (+X)
      expansionRate: cmePhys.expansionRate || 0.38,
      durationSec: cmePhys.visualTimeSec || 12.0,
      sunRadius: (params.visual && params.visual.sunRadius) || 10,
      earthDistance: (params.visual && params.visual.earthOrbitRadius) || 100,
      l1Distance: (params.visual && (params.visual.earthOrbitRadius - params.visual.l1VisualDistFromEarth)) || 84
    };

    this.active = false;
    this.elapsed = 0;
    this.visible = true;

    this.callbacks = {
      onL1Passage: null,
      onEarthImpact: null
    };

    this.reached = {
      l1: false,
      earth: false
    };

    this.group = new THREE.Group();
    this.group.name = "CME_Propagation_Group";

    this._buildCMEStructure();
    this.scene.add(this.group);
  }

  _buildCMEStructure() {
    // 1. Moving CME entity root (translates along Sun-Earth axis)
    this.cmeEntity = new THREE.Group();
    this.cmeEntity.name = "CME_Plasma_Entity";
    this.cmeEntity.position.set(this.config.sunRadius, 0, 0);

    // 2. Curved Bow Shock Front Shell (Smooth translucent cap, non-wireframe)
    // Spherical cap oriented so apex points forward along +X
    const shockGeo = new THREE.SphereGeometry(1.0, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.46);
    this.shockMat = new THREE.MeshBasicMaterial({
      color: 0xff8800,
      transparent: true,
      opacity: 0.0,
      wireframe: false,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.shockMesh = new THREE.Mesh(shockGeo, this.shockMat);
    // Rotate so apex of dome faces +X (towards Earth)
    this.shockMesh.rotation.z = -Math.PI / 2;
    this.cmeEntity.add(this.shockMesh);

    // 3. Shock Front Leading Edge Rim (Luminous shock crest boundary)
    const rimPoints = [];
    const segments = 48;
    for (let i = 0; i <= segments; i++) {
      const phi = (2 * Math.PI * i) / segments;
      // Perimeter circle in Y-Z plane at shock base
      rimPoints.push(new THREE.Vector3(0.08, Math.cos(phi), Math.sin(phi)));
    }
    const rimGeo = new THREE.BufferGeometry().setFromPoints(rimPoints);
    this.rimMat = new THREE.LineBasicMaterial({
      color: 0xffcc44,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending
    });
    this.rimLine = new THREE.Line(rimGeo, this.rimMat);
    this.cmeEntity.add(this.rimLine);

    // 4. Internal Magnetized Flux Rope Loops (subtle magnetic field lines inside cloud)
    this.fluxLoops = [];
    for (let i = 0; i < 3; i++) {
      const curve = new THREE.CubicBezierCurve3(
        new THREE.Vector3(-0.6, -0.4 + i * 0.4, -0.4),
        new THREE.Vector3(0.4, -0.2 + i * 0.2, -0.2),
        new THREE.Vector3(0.4, 0.2 - i * 0.2, 0.2),
        new THREE.Vector3(-0.6, 0.4 - i * 0.4, 0.4)
      );
      const loopGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(24));
      const loopMat = new THREE.LineBasicMaterial({
        color: 0xffaa33,
        transparent: true,
        opacity: 0.0,
        blending: THREE.AdditiveBlending
      });
      const loopLine = new THREE.Line(loopGeo, loopMat);
      this.cmeEntity.add(loopLine);
      this.fluxLoops.push({ line: loopLine, mat: loopMat });
    }

    // 5. Internal Plasma Core Cloud (Ionized dense core)
    const coreGeo = new THREE.SphereGeometry(0.75, 24, 16);
    this.coreMat = new THREE.MeshBasicMaterial({
      color: 0xff4400,
      transparent: true,
      opacity: 0.0,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.coreMesh = new THREE.Mesh(coreGeo, this.coreMat);
    this.coreMesh.position.set(-0.2, 0, 0);
    this.cmeEntity.add(this.coreMesh);

    // 6. Plasma Particles (Internal turbulent ion cluster)
    const particleCount = 60;
    this.particleGeo = new THREE.BufferGeometry();
    const posArray = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.cbrt(Math.random()) * 0.8;
      posArray[i * 3] = r * Math.sin(phi) * Math.cos(theta) - 0.1;
      posArray[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.7;
      posArray[i * 3 + 2] = r * Math.cos(phi) * 0.7;
    }
    this.particleGeo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
    this.particleMat = new THREE.PointsMaterial({
      color: 0xffaa33,
      size: 1.6,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending
    });
    this.particles = new THREE.Points(this.particleGeo, this.particleMat);
    this.cmeEntity.add(this.particles);

    this.group.add(this.cmeEntity);

    // 7. Transient Coronal Detachment Streamer (connects Sun to CME during early eruption)
    const streamerGeo = new THREE.CylinderGeometry(0.4, 1.2, 1.0, 16, 1, true);
    this.streamerMat = new THREE.MeshBasicMaterial({
      color: 0xff5500,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.streamerMesh = new THREE.Mesh(streamerGeo, this.streamerMat);
    this.streamerMesh.rotation.z = Math.PI / 2;
    this.group.add(this.streamerMesh);
  }

  trigger(callbacks = {}) {
    this.active = true;
    this.elapsed = 0;
    this.callbacks = callbacks;
    this.reached = { l1: false, earth: false };

    // Reset initial pose at solar limb
    this.cmeEntity.position.set(this.config.sunRadius, 0, 0);
    this.cmeEntity.scale.set(1, 1, 1);
  }

  update(delta) {
    if (!this.active) return;

    this.elapsed += delta;
    const progress = Math.min(1.0, this.elapsed / this.config.durationSec);

    // 1. Center Translation: Move outward away from Sun (+X toward Earth)
    const startX = this.config.sunRadius; // ~10
    const endX = this.config.earthDistance + 5; // ~105
    const currentCenterX = startX + progress * (endX - startX);
    this.cmeEntity.position.set(currentCenterX, 0, 0);

    // 2. Physical 3D Expansion: Broad conical/bubble expansion
    const radialLen = 2.5 + progress * 16.0;   // Length along X
    const lateralRadius = 2.0 + progress * 26.0; // Cross-track radius in Y and Z (60 deg cone)
    this.shockMesh.scale.set(radialLen, lateralRadius, lateralRadius);
    this.rimLine.scale.set(radialLen, lateralRadius, lateralRadius);
    this.coreMesh.scale.set(radialLen * 0.7, lateralRadius * 0.65, lateralRadius * 0.65);
    this.particles.scale.set(radialLen, lateralRadius, lateralRadius);

    // 3. Density / Opacity Curve: Expands into diffuse plasma (n ~ 1/r^2)
    const baseAlpha = Math.sin(progress * Math.PI) * (1.0 - progress * 0.4);
    this.shockMat.opacity = Math.max(0, baseAlpha * 0.42);
    this.rimMat.opacity = Math.max(0, baseAlpha * 0.70);
    this.coreMat.opacity = Math.max(0, baseAlpha * 0.28);
    this.particleMat.opacity = Math.max(0, baseAlpha * 0.55);
    for (const loop of this.fluxLoops) {
      loop.mat.opacity = Math.max(0, baseAlpha * 0.38);
    }

    // 4. Coronal Detachment: Streamer attaches Sun to CME during liftoff, then vanishes
    if (progress < 0.22) {
      const streamerLen = Math.max(0.1, currentCenterX - startX);
      this.streamerMesh.position.set(startX + streamerLen * 0.5, 0, 0);
      this.streamerMesh.scale.set(1.0, streamerLen, 1.0);
      const streamerAlpha = (1.0 - progress / 0.22) * 0.5;
      this.streamerMat.opacity = streamerAlpha;
      this.streamerMesh.visible = true;
    } else {
      this.streamerMat.opacity = 0;
      this.streamerMesh.visible = false;
    }

    // 5. Leading Shock Front Apex Detection
    const apexX = currentCenterX + radialLen * 0.85;

    // A. Passage through Sun-Earth L1 region (~84 units)
    if (!this.reached.l1 && apexX >= this.config.l1Distance) {
      this.reached.l1 = true;
      if (this.callbacks.onL1Passage) {
        this.callbacks.onL1Passage();
      }
    }

    // B. Impact at Earth magnetosphere (~100 units)
    if (!this.reached.earth && apexX >= this.config.earthDistance) {
      this.reached.earth = true;
      if (this.callbacks.onEarthImpact) {
        this.callbacks.onEarthImpact();
      }
    }

    // 6. Completion & Cleanup
    if (progress >= 1.0) {
      this.active = false;
      this.reset();
    }
  }

  setVisible(visible) {
    this.visible = visible;
    this.group.visible = visible;
  }

  reset() {
    this.active = false;
    this.elapsed = 0;
    this.shockMat.opacity = 0;
    this.rimMat.opacity = 0;
    this.coreMat.opacity = 0;
    this.particleMat.opacity = 0;
    this.streamerMat.opacity = 0;
    if (this.streamerMesh) this.streamerMesh.visible = false;
    for (const loop of this.fluxLoops) {
      loop.mat.opacity = 0;
    }
    this.cmeEntity.position.set(this.config.sunRadius, 0, 0);
  }
}
