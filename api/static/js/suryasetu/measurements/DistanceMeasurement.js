/**
 * Reusable 3D Distance Measurement Component
 * 
 * Computes:
 * - Scientific distance in km and AU
 * - Light travel time (d / c)
 * 
 * Renders:
 * - Line between object visual positions
 * - Endpoint ticks
 * - Animated measurement pulse
 * - 3D Text/Sprite Annotation showing exact scientific values
 */

import { DistanceCalculator } from "../physics/distances.js";

export class DistanceMeasurement {
  constructor(scene, labelA, labelB, getScientificPosA, getScientificPosB, getVisualPosA, getVisualPosB) {
    this.scene = scene;
    this.labelA = labelA;
    this.labelB = labelB;
    this.getScientificPosA = getScientificPosA;
    this.getScientificPosB = getScientificPosB;
    this.getVisualPosA = getVisualPosA;
    this.getVisualPosB = getVisualPosB;

    this.calculator = new DistanceCalculator();
    this.group = new THREE.Group();
    this.group.name = `Dist_${labelA}_${labelB}`;

    this.pulseT = 0;
    this._initVisuals();
    this.scene.add(this.group);
  }

  _initVisuals() {
    // 1. Measurement line
    this.lineGeo = new THREE.BufferGeometry();
    this.lineMat = new THREE.LineDashedMaterial({
      color: 0x00ffff,
      transparent: true,
      opacity: 0.85,
      dashSize: 1.5,
      gapSize: 1.0
    });
    this.line = new THREE.Line(this.lineGeo, this.lineMat);
    this.group.add(this.line);

    // 2. Pulse particle along measurement line
    const pulseGeo = new THREE.SphereGeometry(0.5, 12, 12);
    const pulseMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.95
    });
    this.pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    this.group.add(this.pulseMesh);

    // 3. Endpoint indicators
    const tickGeo = new THREE.RingGeometry(0.3, 0.6, 16);
    const tickMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, side: THREE.DoubleSide });
    this.tickA = new THREE.Mesh(tickGeo, tickMat);
    this.tickB = new THREE.Mesh(tickGeo, tickMat);
    this.group.add(this.tickA);
    this.group.add(this.tickB);
  }

  update(delta) {
    const visualA = this.getVisualPosA();
    const visualB = this.getVisualPosB();
    const sciA = this.getScientificPosA();
    const sciB = this.getScientificPosB();

    if (!visualA || !visualB || !sciA || !sciB) return;

    // Update line geometry
    const pts = [
      new THREE.Vector3(visualA.x, visualA.y, visualA.z),
      new THREE.Vector3(visualB.x, visualB.y, visualB.z)
    ];
    this.lineGeo.setFromPoints(pts);
    this.line.computeLineDistances();

    // Position ticks
    this.tickA.position.set(visualA.x, visualA.y, visualA.z);
    this.tickB.position.set(visualB.x, visualB.y, visualB.z);

    // Update pulse particle
    this.pulseT = (this.pulseT + delta * 0.4) % 1.0;
    this.pulseMesh.position.lerpVectors(pts[0], pts[1], this.pulseT);

    // Calculate real scientific numbers
    this.scientificDistanceKm = this.calculator.calculateDistance(sciA, sciB);
    this.scientificLightTimeSec = this.calculator.calculateLightTravelTime(this.scientificDistanceKm);
    this.au = this.calculator.toAU(this.scientificDistanceKm);
    this.midpointVisual = new THREE.Vector3().addVectors(pts[0], pts[1]).multiplyScalar(0.5);
  }

  getMetrics() {
    return {
      label: `${this.labelA} → ${this.labelB}`,
      distanceKm: this.scientificDistanceKm,
      distanceFormatted: this.calculator.formatDistanceKm(this.scientificDistanceKm),
      au: this.au,
      auFormatted: `${this.au.toFixed(3)} AU`,
      lightTimeSec: this.scientificLightTimeSec,
      lightTimeFormatted: this.calculator.formatLightTime(this.scientificLightTimeSec),
      midpoint: this.midpointVisual
    };
  }

  setVisible(visible) {
    this.group.visible = visible;
  }

  dispose() {
    this.scene.remove(this.group);
    this.lineGeo.dispose();
    this.lineMat.dispose();
  }
}
