/**
 * Distance Calculations and Light Travel Time
 * 
 * STRICT REQUIREMENT:
 * All measurements MUST be derived from coordinates rather than hard-coded strings.
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class DistanceCalculator {
  constructor(speedOfLight = SYSTEM_PARAMETERS.speedOfLightKmS, sunEarthKm = SYSTEM_PARAMETERS.sunEarthKm) {
    this.c = speedOfLight;
    this.oneAU = sunEarthKm;
  }

  /**
   * Euclidean distance between two 3D points
   * @param {{x: number, y: number, z: number}} a 
   * @param {{x: number, y: number, z: number}} b 
   * @returns {number} distance in kilometers
   */
  calculateDistance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    const dz = a.z - b.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  /**
   * Light travel time for electromagnetic radiation (speed = c)
   * @param {number} distanceKm 
   * @returns {number} travel time in seconds
   */
  calculateLightTravelTime(distanceKm) {
    if (this.c <= 0) return 0;
    return distanceKm / this.c;
  }

  /**
   * Relative timing delay between two observers receiving a flare from a source
   * Positive value means Observer A receives it BEFORE Observer B (lead time).
   * @param {number} distanceSourceToA_Km 
   * @param {number} distanceSourceToB_Km 
   * @returns {{delaySeconds: number, leadSeconds: number}}
   */
  calculateRelativeDelay(distanceSourceToA_Km, distanceSourceToB_Km) {
    const timeA = this.calculateLightTravelTime(distanceSourceToA_Km);
    const timeB = this.calculateLightTravelTime(distanceSourceToB_Km);
    const diff = timeB - timeA; // positive if A detects earlier than B
    return {
      timeA_sec: timeA,
      timeB_sec: timeB,
      delaySeconds: Math.abs(diff),
      leadSeconds: diff // > 0 means A leads B
    };
  }

  /**
   * Distance expressed in Astronomical Units (AU)
   * @param {number} distanceKm 
   * @returns {number} distance in AU
   */
  toAU(distanceKm) {
    return distanceKm / this.oneAU;
  }

  /**
   * Formatted string in human-readable scientific notation
   */
  formatDistanceKm(distanceKm) {
    if (distanceKm >= 1000000) {
      const millions = (distanceKm / 1000000).toFixed(2);
      return `${millions} million km`;
    }
    return `${Math.round(distanceKm).toLocaleString()} km`;
  }

  /**
   * Formatted distance in both km and AU
   */
  formatDistanceFull(distanceKm) {
    const kmStr = this.formatDistanceKm(distanceKm);
    const auVal = this.toAU(distanceKm).toFixed(3);
    return `${kmStr} (~${auVal} AU)`;
  }

  /**
   * Formatted light travel time (e.g. "494.0 s (~8 min 14 s)")
   */
  formatLightTime(seconds) {
    if (seconds < 60) {
      return `${seconds.toFixed(1)} s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${seconds.toFixed(1)} s (~${mins} min ${Math.round(secs)} s)`;
  }
}
