/**
 * Orbital Calculations & Curve Generators
 * 
 * Generates mathematically continuous 3D path curves for:
 * - Earth's Orbit (1 AU)
 * - Aditya-L1 3D Halo Orbit around L1 nominal point
 * - Proposed L2 Lissajous / Halo Orbit
 * - Proposed L3 Trajectory
 * - Proposed Communication Relay Eccentric Inclined Orbit
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class OrbitalCalculations {
  constructor(params = SYSTEM_PARAMETERS) {
    this.params = params;
  }

  /**
   * Generate 3D vertices for Earth's Orbit circle
   * @param {number} segments 
   * @returns {Array<{x: number, y: number, z: number}>}
   */
  generateEarthOrbitPath(segments = 128) {
    const r = this.params.visual.earthOrbitRadius;
    const points = [];
    for (let i = 0; i <= segments; i++) {
      const theta = (2 * Math.PI * i) / segments;
      points.push({
        x: r * Math.cos(theta),
        y: 0,
        z: r * Math.sin(theta)
      });
    }
    return points;
  }

  /**
   * Generate 3D vertices for Aditya-L1's Halo Orbit around Sun-Earth L1 nominal point
   * Using authentic 3D halo parametric geometry:
   * x(phi) = -Ax * cos(phi)  (sunward/earthward along Sun-Earth axis)
   * y(phi) =  Az * cos(phi)  (out-of-plane above/below ecliptic)
   * z(phi) =  Ay * sin(phi)  (in-plane cross-track perpendicular to Sun-Earth axis)
   * @param {{x: number, y: number, z: number}} l1NominalVisualPos 
   * @param {number} segments 
   */
  generateL1HaloOrbitPath(l1NominalVisualPos, segments = 128) {
    const halo = this.params.adityaHalo;
    const visualScale = 3.2 / halo.Ay_km;
    const ax = halo.Ax_km * visualScale;
    const ay = halo.Ay_km * visualScale;
    const az = halo.Az_km * visualScale;

    const points = [];
    for (let i = 0; i <= segments; i++) {
      const phi = (2 * Math.PI * i) / segments;
      points.push({
        x: l1NominalVisualPos.x - ax * Math.cos(phi),
        y: l1NominalVisualPos.y + az * Math.cos(phi),
        z: l1NominalVisualPos.z + ay * Math.sin(phi)
      });
    }
    return points;
  }

  /**
   * Generate 3D vertices for L2 Proposed Observatory halo orbit
   */
  generateL2OrbitPath(l2NominalVisualPos, segments = 96) {
    const ax = 1.5;
    const ay = 3.0;
    const az = 2.0;

    const points = [];
    for (let i = 0; i <= segments; i++) {
      const phi = (2 * Math.PI * i) / segments;
      points.push({
        x: l2NominalVisualPos.x + ax * Math.cos(phi),
        y: l2NominalVisualPos.y + az * Math.sin(phi),
        z: l2NominalVisualPos.z + ay * Math.sin(phi)
      });
    }
    return points;
  }

  /**
   * Generate 3D arc path for L3 Proposed Observatory around Sun-Earth L3 region
   */
  generateL3OrbitPath(segments = 48) {
    const r = this.params.visual.l3VisualRadius;
    const points = [];
    // Arc spanning ±35 degrees around 180°
    const spanRad = (35 * Math.PI) / 180;
    for (let i = 0; i <= segments; i++) {
      const t = -spanRad + (2 * spanRad * i) / segments;
      const angle = Math.PI + t;
      points.push({
        x: r * Math.cos(angle),
        y: 0,
        z: r * Math.sin(angle)
      });
    }
    return points;
  }

  /**
   * Generate 3D path for Communication Relay Orbiter's inclined orbit
   */
  generateRelayOrbitPath(segments = 120) {
    const a = 68;
    const b = 58;
    const inc = 0.42; // ~24° inclination
    const points = [];

    for (let i = 0; i <= segments; i++) {
      const phi = (2 * Math.PI * i) / segments;
      const xOrb = a * Math.cos(phi);
      const zOrb = b * Math.sin(phi);
      points.push({
        x: xOrb,
        y: zOrb * Math.sin(inc),
        z: zOrb * Math.cos(inc)
      });
    }
    return points;
  }
}
