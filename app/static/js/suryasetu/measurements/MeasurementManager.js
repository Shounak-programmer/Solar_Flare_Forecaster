/**
 * MeasurementManager — Orchestrates distance lines, angle arcs, and HUD metrics
 */

import { DistanceMeasurement } from "./DistanceMeasurement.js";
import { AngleMeasurement } from "./AngleMeasurement.js";

export class MeasurementManager {
  constructor(scene, getPositions) {
    this.scene = scene;
    this.getPositions = getPositions;

    this.distances = [];
    this.angles = [];

    this.mode = "ALL"; // "ALL", "SUN_EARTH", "L1", "OFF"
    this.showDistances = true;
    this.showAngles = false;

    this._initDistances();
    this._initAngles();
  }

  _initDistances() {
    const p = this.getPositions;

    const addDist = (id, labelA, labelB, getSciA, getSciB, getVisA, getVisB) => {
      const dm = new DistanceMeasurement(this.scene, labelA, labelB, getSciA, getSciB, getVisA, getVisB);
      dm.id = id;
      this.distances.push(dm);
    };

    // Sun - Earth
    addDist("sun_earth", "Sun", "Earth", () => p.sci.sun(), () => p.sci.earth(), () => p.vis.sun(), () => p.vis.earth());
    // Sun - Aditya-L1
    addDist("sun_l1", "Sun", "Aditya-L1", () => p.sci.sun(), () => p.sci.adityaL1(), () => p.vis.sun(), () => p.vis.adityaL1());
    // Earth - Aditya-L1
    addDist("earth_l1", "Earth", "Aditya-L1", () => p.sci.earth(), () => p.sci.adityaL1(), () => p.vis.earth(), () => p.vis.adityaL1());
  }

  _initAngles() {
    // No angle measurements required for the Sun-Earth-L1 configuration.
  }

  update(delta) {
    if (this.showDistances) {
      for (const d of this.distances) {
        d.update(delta);
      }
    }
    if (this.showAngles) {
      for (const a of this.angles) {
        a.update();
      }
    }
  }

  setDistancesVisible(visible) {
    this.showDistances = visible;
    for (const d of this.distances) {
      d.setVisible(visible);
    }
  }

  setAnglesVisible(visible) {
    this.showAngles = visible;
    for (const a of this.angles) {
      a.setVisible(visible);
    }
  }

  getActiveDistanceMetrics() {
    return this.distances.map(d => d.getMetrics());
  }

  getActiveAngleMetrics() {
    return this.angles.map(a => a.getMetrics());
  }
}
