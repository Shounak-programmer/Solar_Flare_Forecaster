/**
 * Coordinates and Coordinate Transformations
 * 
 * Manages dual coordinate spaces:
 * 1. SCIENTIFIC COORDINATES (in kilometers and AU)
 * 2. VISUALIZATION COORDINATES (in Three.js scene units)
 * 
 * Displays strict notice: Real space is visually exaggerated for clarity,
 * but all scientific measurements are derived from scientific coordinates.
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class CoordinateTransformer {
  constructor(params = SYSTEM_PARAMETERS) {
    this.params = params;
  }

  /**
   * Scientific Sun position (Origin)
   */
  getScientificSunPosition() {
    return { x: 0, y: 0, z: 0, unit: "km" };
  }

  /**
   * Scientific Earth position at orbital true anomaly theta (default theta = 0)
   */
  getScientificEarthPosition(theta = 0) {
    const r = this.params.sunEarthKm;
    return {
      x: r * Math.cos(theta),
      y: 0,
      z: r * Math.sin(theta),
      unit: "km"
    };
  }

  /**
   * Scientific Sun-Earth L1 nominal point position
   */
  getScientificL1NominalPosition(theta = 0) {
    const r = this.params.sunEarthKm - this.params.earthL1Km;
    return {
      x: r * Math.cos(theta),
      y: 0,
      z: r * Math.sin(theta),
      unit: "km"
    };
  }

  /**
   * Scientific Aditya-L1 instantaneous position including 3D halo orbit offset
   * @param {number} t - time in days
   * @param {number} theta - Earth orbital angle (rad)
   */
  getScientificAdityaL1Position(t = 0, theta = 0) {
    const l1 = this.getScientificL1NominalPosition(theta);
    const halo = this.params.adityaHalo;
    const omega = (2 * Math.PI) / halo.periodDays;
    const phi = omega * t;
    
    // Halo orbit offsets in local frame (x toward Sun, y out of ecliptic plane, z in-plane cross-track)
    const dxLocal = -halo.Ax_km * Math.cos(phi);
    const dyLocal = halo.Az_km * Math.cos(phi); // km out of ecliptic plane
    const dzLocal = halo.Ay_km * Math.sin(phi); // km in-plane cross-track

    // Rotate local frame into heliocentric ecliptic frame
    const cosT = Math.cos(theta);
    const sinT = Math.sin(theta);
    const dx = dxLocal * cosT - dzLocal * sinT;
    const dy = dyLocal; // out of ecliptic plane
    const dz = dxLocal * sinT + dzLocal * cosT;

    return {
      x: l1.x + dx,
      y: l1.y + dy,
      z: l1.z + dz,
      unit: "km",
      haloOffsetKm: { dx: dxLocal, dy: dyLocal, dz: dzLocal }
    };
  }

  /**
   * Scientific L2 nominal position (~1.5M km anti-sunward)
   */
  getScientificL2NominalPosition(theta = 0) {
    const r = this.params.sunEarthKm + this.params.earthL2Km;
    return {
      x: r * Math.cos(theta),
      y: 0,
      z: r * Math.sin(theta),
      unit: "km"
    };
  }

  /**
   * Scientific L3 nominal position (~1 AU opposite Earth, slightly offset)
   */
  getScientificL3NominalPosition(theta = 0) {
    const r = this.params.sunEarthKm;
    const l3Theta = theta + Math.PI; // 180 degrees opposite
    return {
      x: r * Math.cos(l3Theta),
      y: 0,
      z: r * Math.sin(l3Theta),
      unit: "km"
    };
  }

  /**
   * Visual coordinate for Sun (always 0,0,0)
   */
  getVisualSunPosition() {
    return { x: 0, y: 0, z: 0 };
  }

  /**
   * Visual coordinate for Earth
   */
  getVisualEarthPosition(theta = 0) {
    const r = this.params.visual.earthOrbitRadius;
    return {
      x: r * Math.cos(theta),
      y: 0,
      z: r * Math.sin(theta)
    };
  }

  /**
   * Visual coordinate for L1 nominal point
   */
  getVisualL1NominalPosition(theta = 0) {
    const r = this.params.visual.earthOrbitRadius - this.params.visual.l1VisualDistFromEarth;
    return {
      x: r * Math.cos(theta),
      y: 0,
      z: r * Math.sin(theta)
    };
  }

  /**
   * Visual coordinate for Aditya-L1 including visually scaled halo orbit
   */
  getVisualAdityaL1Position(t = 0, theta = 0) {
    const l1 = this.getVisualL1NominalPosition(theta);
    const halo = this.params.adityaHalo;
    const omega = (2 * Math.PI) / halo.periodDays;
    const phi = omega * t;
    
    // Scale halo orbit visually so it is distinct from L1 nominal point (~3.2 units amplitude)
    const visualScale = 3.2 / halo.Ay_km;
    const ax = halo.Ax_km * visualScale;
    const ay = halo.Ay_km * visualScale;
    const az = halo.Az_km * visualScale;

    // Local frame: x along Sun-Earth axis, y out-of-plane, z in-plane cross-track
    const dxLocal = -ax * Math.cos(phi);
    const dyLocal = az * Math.cos(phi);
    const dzLocal = ay * Math.sin(phi);

    const cosT = Math.cos(theta);
    const sinT = Math.sin(theta);
    const dx = dxLocal * cosT - dzLocal * sinT;
    const dy = dyLocal;
    const dz = dxLocal * sinT + dzLocal * cosT;

    return {
      x: l1.x + dx,
      y: l1.y + dy,
      z: l1.z + dz
    };
  }

  /**
   * Visual coordinate for L2 proposed observatory
   */
  getVisualL2Position(t = 0, theta = 0) {
    const rNominal = this.params.visual.earthOrbitRadius + this.params.visual.l2VisualDistFromEarth;
    const omega = (2 * Math.PI) / 180;
    const dy = 2.0 * Math.sin(omega * t);
    const dxLocal = 1.5 * Math.cos(omega * t);

    const cosT = Math.cos(theta);
    const sinT = Math.sin(theta);
    const baseX = rNominal * cosT;
    const baseZ = rNominal * sinT;

    return {
      x: baseX + dxLocal * cosT,
      y: dy,
      z: baseZ + dxLocal * sinT
    };
  }

  /**
   * Visual coordinate for L3 proposed observatory
   */
  getVisualL3Position(theta = 0) {
    const r = this.params.visual.l3VisualRadius;
    const l3Theta = theta + Math.PI;
    return {
      x: r * Math.cos(l3Theta),
      y: 0,
      z: r * Math.sin(l3Theta)
    };
  }

  /**
   * Visual coordinate for Communication Relay Orbiter (Proposed)
   * High-inclination orbit around Sun enabling non-occulted LOS crosslinks
   */
  getVisualRelayPosition(t = 0) {
    const a = 68; // semi-major axis in visual units
    const b = 58;
    const inc = 0.42; // ~24 degree orbital inclination
    const omega = (2 * Math.PI) / 95; // orbit period in simulation units
    const angle = omega * t + 0.8;

    const xOrb = a * Math.cos(angle);
    const zOrb = b * Math.sin(angle);

    return {
      x: xOrb,
      y: zOrb * Math.sin(inc),
      z: zOrb * Math.cos(inc)
    };
  }
}
