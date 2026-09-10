/**
 * Reusable 3D Angle Measurement Component
 * 
 * Supports: angle(A, vertex, B)
 * Computes:
 * - Mathematical angle from vectors (zero hard-coding)
 * Renders:
 * - Two vector rays from vertex to A and B
 * - 3D Arc spanning the angle
 * - Degrees readout
 */

import { AngleCalculator } from "../physics/angles.js";

export class AngleMeasurement {
  constructor(scene, labelA, labelVertex, labelB, getVisualPosA, getVisualPosVertex, getVisualPosB, arcRadius = 12) {
    this.scene = scene;
    this.labelA = labelA;
    this.labelVertex = labelVertex;
    this.labelB = labelB;
    this.getVisualPosA = getVisualPosA;
    this.getVisualPosVertex = getVisualPosVertex;
    this.getVisualPosB = getVisualPosB;
    this.arcRadius = arcRadius;

    this.calculator = new AngleCalculator();
    this.group = new THREE.Group();
    this.group.name = `Angle_${labelA}_${labelVertex}_${labelB}`;

    this._initVisuals();
    this.scene.add(this.group);
  }

  _initVisuals() {
    // 1. Ray from vertex to A
    this.rayAGeo = new THREE.BufferGeometry();
    this.rayBGeo = new THREE.BufferGeometry();
    const rayMat = new THREE.LineBasicMaterial({
      color: 0xffaa00,
      transparent: true,
      opacity: 0.65
    });
    this.rayA = new THREE.Line(this.rayAGeo, rayMat);
    this.rayB = new THREE.Line(this.rayBGeo, rayMat);
    this.group.add(this.rayA);
    this.group.add(this.rayB);

    // 2. Arc curve
    this.arcGeo = new THREE.BufferGeometry();
    const arcMat = new THREE.LineBasicMaterial({
      color: 0xffd54f,
      linewidth: 2,
      transparent: true,
      opacity: 0.95
    });
    this.arcLine = new THREE.Line(this.arcGeo, arcMat);
    this.group.add(this.arcLine);
  }

  update() {
    const vA = this.getVisualPosA();
    const vV = this.getVisualPosVertex();
    const vB = this.getVisualPosB();

    if (!vA || !vV || !vB) return;

    // Ray lines
    this.rayAGeo.setFromPoints([
      new THREE.Vector3(vV.x, vV.y, vV.z),
      new THREE.Vector3(vA.x, vA.y, vA.z)
    ]);
    this.rayBGeo.setFromPoints([
      new THREE.Vector3(vV.x, vV.y, vV.z),
      new THREE.Vector3(vB.x, vB.y, vB.z)
    ]);

    // Arc geometry
    const arcPts = this.calculator.generateArcPoints(vA, vV, vB, this.arcRadius, 32);
    if (arcPts && arcPts.length > 1) {
      this.arcGeo.setFromPoints(arcPts.map(p => new THREE.Vector3(p.x, p.y, p.z)));
      this.arcMidpoint = arcPts[Math.floor(arcPts.length / 2)];
    }

    // Mathematical angle calculation
    this.angleData = this.calculator.calculateAngle(vA, vV, vB);
  }

  getMetrics() {
    return {
      label: `∠(${this.labelA}, ${this.labelVertex}, ${this.labelB})`,
      degrees: this.angleData ? this.angleData.degrees : 0,
      formatted: this.angleData ? this.angleData.formatted : "0.0°",
      vertex: this.labelVertex,
      midpoint: this.arcMidpoint
    };
  }

  setVisible(visible) {
    this.group.visible = visible;
  }

  dispose() {
    this.scene.remove(this.group);
    this.rayAGeo.dispose();
    this.rayBGeo.dispose();
    this.arcGeo.dispose();
  }
}
