/**
 * Signal Timing & Animation Time Compression
 * 
 * STRICT SCIENTIFIC CONSTRAINTS:
 * 1. EM radiation travels at c (Sun-Earth ~499s, Sun-L1 ~494s, L1 lead ~5s).
 * 2. Visual animation cannot wait 499 real seconds in a presentation.
 * 3. We maintain two clocks: REAL PHYSICAL TIME and VISUAL TIME.
 * 4. Dual display explicitly shows both to prevent any audience confusion.
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class TimingEngine {
  constructor(params = SYSTEM_PARAMETERS) {
    this.params = params;
    this.c = params.speedOfLightKmS;

    // Visual compression targets (in visual seconds for nominal event)
    this.visualEmDurationSec = params.physics.em.visualTimeSec; // ~4.5 s
    this.visualSepDurationSec = params.physics.sep.visualTimeSec; // ~8.0 s
    this.visualCmeDurationSec = params.physics.cme.visualTimeSec; // ~12.0 s

    // Physical travel times for reference
    this.realEmSunToEarthSec = params.physics.em.sunToEarthSec; // ~499.0 s
    this.realEmSunToL1Sec = params.physics.em.sunToL1Sec; // ~494.0 s
    this.realEmLeadSec = params.physics.em.leadTimeSec; // ~5.0 s
  }

  /**
   * Calculate exact EM travel time from Sun to any distance in km
   */
  calculateEmTravelTimeSec(distanceKm) {
    return distanceKm / this.c;
  }

  /**
   * Convert visual animation progress [0, 1] for EM wave to real physical elapsed seconds
   */
  emVisualProgressToRealSec(progress) {
    return progress * this.realEmSunToEarthSec;
  }

  /**
   * Convert visual animation progress [0, 1] for SEP stream to real physical elapsed minutes
   */
  sepVisualProgressToRealMin(progress) {
    // 20 min to 90 min arrival window
    return 20 + progress * 70;
  }

  /**
   * Convert visual animation progress [0, 1] for CME wave to real physical elapsed hours/days
   */
  cmeVisualProgressToRealHours(progress) {
    // 18 hours to 72 hours (0.75 to 3.0 days)
    return progress * 48; // reaches Earth at 48 hours (~2.0 days)
  }

  /**
   * Format physical seconds into clean ISO-like or min:sec timer string
   * Example: 494.0 -> "08:14.0" (494.0 s)
   */
  formatTimerString(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const minStr = String(mins).padStart(2, "0");
    const secStr = secs.toFixed(1).padStart(4, "0");
    return `${minStr}:${secStr}`;
  }

  /**
   * Format hours into day/hour string
   */
  formatCmeTime(hours) {
    if (hours < 24) {
      return `${hours.toFixed(1)} hours`;
    }
    const days = (hours / 24).toFixed(1);
    return `${days} days (${hours.toFixed(1)} h)`;
  }
}
