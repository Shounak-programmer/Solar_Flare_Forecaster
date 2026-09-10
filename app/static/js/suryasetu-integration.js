/**
 * SURYASETU Integration Bridge
 * 
 * Bridges the Three.js 3D Scientific Visualization system into the
 * Aditya-L1 Solar Flare Forecaster dashboard.
 */

import { SuryaSetuApp } from "./suryasetu/SuryaSetuApp.js";

let suryaSetuInstance = null;

function initSuryaSetu() {
  const container = document.getElementById("suryasetuViewport");
  if (!container) return;

  if (!suryaSetuInstance) {
    suryaSetuInstance = new SuryaSetuApp(container);
    window.SURYASETU_APP = suryaSetuInstance;
    console.log("[SURYASETU] 3D Visualization System initialized successfully.");
  } else {
    suryaSetuInstance.handleResize();
  }
}

// Listen for tab switching
window.addEventListener("tabchange", (e) => {
  if (e.detail === "suryasetu") {
    requestAnimationFrame(() => {
      initSuryaSetu();
      if (suryaSetuInstance) suryaSetuInstance.handleResize();
    });
    setTimeout(() => {
      initSuryaSetu();
      if (suryaSetuInstance) suryaSetuInstance.handleResize();
    }, 60);
    setTimeout(() => {
      if (suryaSetuInstance) suryaSetuInstance.handleResize();
    }, 220);
  }
});

// Auto-initialize if already on the 3D tab
document.addEventListener("DOMContentLoaded", () => {
  const activeTab = document.querySelector(".tabpane.active");
  if (activeTab && activeTab.id === "tab-suryasetu") {
    initSuryaSetu();
  }
});

// Bridge to existing replay events
window.addEventListener("suryasetu_flare_event", (e) => {
  if (suryaSetuInstance && e.detail) {
    suryaSetuInstance.updateSolarEvent(e.detail);
  }
});

window.addEventListener("suryasetu_prediction_update", (e) => {
  if (suryaSetuInstance && e.detail) {
    suryaSetuInstance.updatePrediction(e.detail);
  }
});

export { initSuryaSetu, suryaSetuInstance };
