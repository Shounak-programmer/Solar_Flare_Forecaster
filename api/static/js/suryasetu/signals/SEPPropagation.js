/**
 * Solar Energetic Particles (SEP) Propagation System
 * 
 * Physics:
 * - Particles travel slower than light (0.15c - 0.50c)
 * - Guided along the interplanetary magnetic field (Parker Spiral)
 * - Trajectory is curved, not a straight line
 * - Arrival time ranges from ~20 minutes to several hours
 * - Causes radiation hazards to spacecraft electronics (SEUs) and astronauts
 */

export class SEPPropagation {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.group.name = "SEP_Propagation_Group";

    this.active = false;
    this.particleCount = 180;
    this.durationSec = 8.5; // Visual presentation time
    this.elapsed = 0;

    this._createParkerSpiralStreams();
    this.scene.add(this.group);
  }

  _createParkerSpiralStreams() {
    // 1. Static guide lines showing the magnetic Parker Spiral topology
    this.spiralGuideGeo = new THREE.BufferGeometry();
    const spiralPoints = [];
    const a = 1.6; // spiral expansion rate
    // Archimedean spiral r = a * theta
    for (let t = 2.5; t <= 18.0; t += 0.2) {
      const r = a * t * 3.6;
      const theta = -t * 0.45; // solar rotation winding
      spiralPoints.push(new THREE.Vector3(r * Math.cos(theta), 0, r * Math.sin(theta)));
    }
    this.spiralGuideGeo.setFromPoints(spiralPoints);
    const spiralGuideMat = new THREE.LineDashedMaterial({
      color: 0x4a90e2, // Heliospheric magnetic field line (subtle blue)
      transparent: true,
      opacity: 0.35,
      dashSize: 1.5,
      gapSize: 1.0
    });
    this.spiralGuideLine = new THREE.Line(this.spiralGuideGeo, spiralGuideMat);
    this.spiralGuideLine.computeLineDistances();
    this.group.add(this.spiralGuideLine);

    // 2. High-energy charged particles flowing along the spiral
    this.particlesGeo = new THREE.BufferGeometry();
    this.particlePositions = new Float32Array(this.particleCount * 3);
    this.particleProgresses = new Float32Array(this.particleCount);
    this.particleSpeeds = new Float32Array(this.particleCount);

    for (let i = 0; i < this.particleCount; i++) {
      this.particleProgresses[i] = Math.random(); // staggered start along stream
      this.particleSpeeds[i] = 0.25 + Math.random() * 0.25; // velocity dispersion
      this.particlePositions[i * 3] = 0;
      this.particlePositions[i * 3 + 1] = 0;
      this.particlePositions[i * 3 + 2] = 0;
    }

    this.particlesGeo.setAttribute("position", new THREE.BufferAttribute(this.particlePositions, 3));

    const pMat = new THREE.PointsMaterial({
      color: 0x64d2ff, // High-energy charged solar protons (electric cyan)
      size: 1.8,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending
    });
    this.particleSystem = new THREE.Points(this.particlesGeo, pMat);
    this.group.add(this.particleSystem);
  }

  setSpiralVisible(visible) {
    if (this.spiralGuideLine) {
      this.spiralGuideLine.visible = visible;
    }
  }

  setVisible(visible) {
    this.group.visible = visible;
  }

  trigger() {
    this.active = true;
    this.elapsed = 0;
    this.particleSystem.material.opacity = 0.95;
    this.spiralGuideLine.material.opacity = 0.45;
  }

  update(delta) {
    if (!this.active) return;

    this.elapsed += delta;
    const overallProgress = Math.min(1.0, this.elapsed / this.durationSec);

    const positions = this.particlesGeo.attributes.position.array;
    const a = 1.6;

    for (let i = 0; i < this.particleCount; i++) {
      this.particleProgresses[i] += delta * this.particleSpeeds[i] * 0.8;
      if (this.particleProgresses[i] > 1.0) {
        this.particleProgresses[i] = 0.0;
      }

      const p = this.particleProgresses[i];
      const t = 2.5 + p * 15.5;
      const r = a * t * 3.6;
      const theta = -t * 0.45;

      // Slight dispersion perpendicular to magnetic line
      const jitterY = Math.sin(i * 99 + this.elapsed * 4) * 0.8;
      positions[i * 3] = r * Math.cos(theta);
      positions[i * 3 + 1] = jitterY;
      positions[i * 3 + 2] = r * Math.sin(theta);
    }

    this.particlesGeo.attributes.position.needsUpdate = true;

    if (overallProgress >= 1.0) {
      // Fade out
      this.particleSystem.material.opacity -= delta * 0.5;
      if (this.particleSystem.material.opacity <= 0) {
        this.active = false;
        this.particleSystem.material.opacity = 0;
        this.spiralGuideLine.material.opacity = 0.2;
      }
    }
  }

  reset() {
    this.active = false;
    this.elapsed = 0;
    this.particleSystem.material.opacity = 0;
  }
}
