/**
 * SURYASETU — 3D Solar Flare Observation & Communication System
 * Centralized Scientific Constants and System Parameters.
 * 
 * STRICT SCIENTIFIC CONSTRAINTS:
 * - Speed of light c = 299,792.458 km/s
 * - 1 AU (Sun-Earth) = 149,597,870.7 km
 * - Earth-L1 distance = ~1,500,000 km
 * - Sun-L1 distance = ~148,097,870.7 km
 * - Sun-Earth EM light travel time = ~499.0 s (~8 min 19 s)
 * - Sun-Aditya-L1 EM light travel time = ~494.0 s (~8 min 14 s)
 * - Aditya-L1 EM timing advantage over Earth = ~5.0 s (range 2.7 - 7.3 s due to halo orbit semi-diameter)
 * - DO NOT display "8 minutes early warning from L1" - that is physically incorrect!
 * - SEP propagation: 0.1c - 0.5c (minutes to hours along Parker spiral)
 * - CME propagation: 300 - 3000 km/s (1 to 4 days transit to 1 AU)
 */

export const SYSTEM_PARAMETERS = {
  // Astronomical Constants
  speedOfLightKmS: 299792.458,
  sunEarthKm: 149597870.7, // 1 AU in km
  sunRadiusKm: 696340,
  earthRadiusKm: 6371,

  // Lagrange Points (km from Earth)
  earthL1Km: 1500000, // Sunward
  earthL2Km: 1500000, // Anti-sunward
  earthL3Km: 299195740, // Opposite side of Sun (~2 AU from Earth)

  // Aditya-L1 Halo Orbit Parameters (ISRO / Howell-Barden nominal)
  adityaHalo: {
    Ax_km: 250000,  // Sun-Earth direction semi-amplitude
    Ay_km: 670000,  // In-plane cross-track semi-amplitude (±2.2s timing delta)
    Az_km: 200000,  // Out-of-plane z-axis semi-amplitude
    periodDays: 177.8, // ~6 months halo orbit period
    nominalAdvantageSec: 5.004, // Nominal EM lead time over Earth
    minAdvantageSec: 2.7,
    maxAdvantageSec: 7.3,
  },

  // Spacecraft & Observatories Metadata
  spacecraft: {
    adityaL1: {
      id: "aditya_l1",
      name: "Aditya-L1",
      subtitle: "Operational Solar Observatory",
      status: "OPERATIONAL",
      agency: "ISRO",
      launchDate: "2 September 2023",
      insertionDate: "6 January 2024",
      orbitType: "3D Halo Orbit around Sun-Earth L1",
      payloads: [
        "SoLEXS (Soft X-ray Spectrometer 2–22 keV)",
        "HEL1OS (Hard X-ray Spectrometer 10–150 keV)",
        "VELC (Visible Emission Line Coronagraph)",
        "SUIT (Solar Ultraviolet Imaging Telescope)",
        "ASPEX (Aditya Solar Wind Particle Experiment)",
        "PAPA (Plasma Analyser Package for Aditya)",
        "Advanced Tri-axial High Resolution Digital Magnetometer"
      ],
      primaryRole: "Uninterrupted continuous solar disk observation without occultation/eclipse.",
      emTravelTimeFromSunSec: 494.00,
      nominalLeadOverEarthSec: 5.00
    },
    l2Observatory: {
      id: "l2_observatory",
      name: "L2 Observatory",
      subtitle: "Proposed Deep Space Observatory",
      status: "PROPOSED",
      agency: "ISRO / Conceptual Architecture",
      orbitType: "Lissajous / Halo Orbit around Sun-Earth L2",
      role: "Nightside shielding, magnetotail space weather monitoring, and stereoscopic solar wind correlation.",
      distanceFromEarthKm: 1500000,
      emTravelTimeFromSunSec: 504.01,
      emDelayBehindEarthSec: 5.00
    },
    l3Observatory: {
      id: "l3_observatory",
      name: "L3 Observatory",
      subtitle: "Proposed Far-Side Solar Sentinel",
      status: "PROPOSED",
      agency: "ISRO / Conceptual Architecture",
      orbitType: "Sun-Earth L3 Region (~180° opposite Earth)",
      role: "Far-side solar active region early detection 1–2 weeks before solar rotation brings them into Earth's view.",
      distanceFromEarthKm: 299195740,
      emTravelTimeFromSunSec: 499.00,
      emTravelTimeToEarthSec: 998.01
    },
    relayOrbiter: {
      id: "relay_orbiter",
      name: "Communication Relay Orbiter",
      subtitle: "Proposed Deep-Space Optical & RF Relay",
      status: "PROPOSED",
      agency: "SURYASETU Interplanetary Architecture",
      orbitType: "High-inclination eccentric solar transfer orbit",
      role: "Uninterrupted line-of-sight telemetry bridge routing L3, L2, and Aditya-L1 data to Earth Deep Space Network.",
      carrierBands: "Ka-Band RF (32 GHz) + Deep Space Optical Comm (1550 nm)"
    }
  },

  // Propagation Physics Properties
  physics: {
    em: {
      type: "Electromagnetic Radiation (X-rays, EUV, Radio)",
      speedKmS: 299792.458,
      sunToEarthSec: 499.005,
      sunToL1Sec: 494.001,
      leadTimeSec: 5.004,
      visualTimeSec: 4.5, // Presentation visual compression
      hazard: "Ionospheric heating, HF radio blackouts (R1–R5), satellite drag."
    },
    sep: {
      type: "Solar Energetic Particles (Protons, Electrons, Ions)",
      speedFactorC: [0.15, 0.50], // 0.15c to 0.5c
      travelTimeMin: [20, 180], // 20 mins to ~3 hours
      visualTimeSec: 8.0,
      pathGeometry: "Guided along Archimedean Parker Spiral magnetic field lines",
      hazard: "Radiation hazard to astronauts, solar panel degradation, single-event upsets (SEU) in avionics."
    },
    cme: {
      type: "Coronal Mass Ejection (Bulk Magnetized Plasma)",
      nominalSpeedKmS: 900,
      speedKmS: [400, 2200], // 400 km/s slow to >2000 km/s extreme
      angularWidthDeg: 60,   // Broad angular plasma cone
      direction: { x: 1, y: 0, z: 0 }, // Sun-to-Earth axis (+X)
      expansionRate: 0.38,   // Lateral expansion rate
      transitTimeDays: [1.0, 4.0], // 1 to 4 days to reach 1 AU
      visualTimeSec: 12.0,
      hazard: "Geomagnetic storms (G1–G5), geomagnetically induced currents (GIC) in power grids, auroral heating."
    }
  },

  // Visualization Coordinate System Transformation Constants
  visual: {
    sunRadius: 10,
    earthOrbitRadius: 100,
    earthRadius: 2.4,
    l1VisualDistFromEarth: 16,
    l2VisualDistFromEarth: 16,
    l3VisualRadius: 98,
    spacecraftScale: 1.0,
    disclaimer: "Conceptual visualization — distances and spacecraft sizes are visually exaggerated for clarity. L2/L3 observatories and relay spacecraft are proposed/illustrative components."
  }
};

if (typeof window !== "undefined") {
  window.SURYASETU_PARAMETERS = SYSTEM_PARAMETERS;
}
