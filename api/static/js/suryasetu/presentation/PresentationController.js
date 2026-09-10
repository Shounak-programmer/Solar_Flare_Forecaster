/**
 * PresentationController — 12-Scene Cinematic Demonstration for ISRO / HOD Pitch
 */

export class PresentationController {
  constructor(app) {
    this.app = app;
    this.active = false;
    this.currentSceneIndex = 0;
    this.autoPlay = true;
    this.timer = null;

    this.scenes = [
      {
        id: 1,
        title: "1. Heliocentric Overview",
        desc: "Solar observation architecture (SURYASETU). Overview of Sun, Earth, L1 region, and orbital geometry.",
        action: () => {
          this.app.cameraManager.focusOverview();
          this.app.measurementManager.setDistancesVisible(false);
          this.app.measurementManager.setAnglesVisible(false);
          this.app.signalManager.resetAll();
        },
        durationSec: 6.5
      },
      {
        id: 2,
        title: "2. Earth at 1.0 AU",
        desc: "Earth in heliocentric orbit at 1 AU (~149.6 million km). All terrestrial space weather impacts occur here.",
        action: () => {
          this.app.cameraManager.focusEarth(this.app.positions.vis.earth());
        },
        durationSec: 6.0
      },
      {
        id: 3,
        title: "3. Aditya-L1 Halo Orbit",
        desc: "India's operational solar observatory operating in a 3D periodic halo orbit around the Sun–Earth L1 reference point (~1.5M km sunward). Notice the 3D halo trajectory looping around the stationary L1 reference marker.",
        action: () => {
          this.app.cameraManager.focusAdityaL1(this.app.positions.vis.l1Nominal());
          this.app.selectObject("aditya_l1");
        },
        durationSec: 7.5
      },
      {
        id: 4,
        title: "4. System Geometry & Distances",
        desc: "Scientifically derived distances: Sun-Earth (149.6M km), Earth-L1 (1.5M km). Zero hard-coded coordinates.",
        action: () => {
          this.app.cameraManager.focusOverview();
          this.app.measurementManager.setDistancesVisible(true);
          this.app.measurementManager.setAnglesVisible(false);
        },
        durationSec: 6.5
      },
      {
        id: 5,
        title: "5. Solar Flare Eruption",
        desc: "Simulating an impulsive X-class solar flare! Active region flashes; magnetic reconnection loops expel coronal energy.",
        action: () => {
          this.app.cameraManager.focusSun();
          this.app.sun.triggerFlareFlash();
          this.app.solarFlare.trigger();
        },
        durationSec: 6.0
      },
      {
        id: 6,
        title: "6. Electromagnetic X-Ray Wavefront",
        desc: "Electromagnetic radiation travels at c (~300,000 km/s). Expanding spherical wavefront radiates outward through interplanetary space.",
        action: () => {
          this.app.cameraManager.focusOverview();
          this.app.signalManager.triggerSolarFlareSimulation({
            adityaL1: this.app.adityaL1
          }, (narrative, time) => {
            this.app.hud.updateFlareNarrative(narrative, time);
          });
        },
        durationSec: 7.0
      },
      {
        id: 7,
        title: "7. L1 vs Earth Timing Advantage",
        desc: "Physical Reality: Sun->L1 is ~494 s; Sun->Earth is ~499 s. Aditya-L1 gains ~5 seconds lead time over Earth (not 8 minutes!). Defensible science for ISRO presentation.",
        action: () => {
          this.app.cameraManager.focusAdityaL1(this.app.positions.vis.adityaL1());
        },
        durationSec: 7.5
      },
      {
        id: 8,
        title: "8. SEP & CME Propagation",
        desc: "Solar Energetic Particles arrive in 20-60 min along curved Parker spiral magnetic lines. Bulk CME plasma arrives in 1–4 days (~400-2000 km/s) driving geomagnetic storms.",
        action: () => {
          this.app.cameraManager.focusOverview();
        },
        durationSec: 7.5
      },
      {
        id: 9,
        title: "9. Communication Link",
        desc: "Aditya-L1 relays real-time solar telemetry directly to ISRO ground stations via deep space network (DSN) Ka-band link.",
        action: () => {
          this.app.cameraManager.focusOverview();
          this.app.measurementManager.setDistancesVisible(true);
          this.app.signalManager.setCommLinksVisible(true);
        },
        durationSec: 7.0
      },
      {
        id: 10,
        title: "10. Integrated Space Weather Architecture",
        desc: "SURYASETU combines real Aditya-L1 data with AI/ML forecasting to protect communication satellites, astronauts, and power grids.",
        action: () => {
          this.app.cameraManager.focusOverview();
          this.app.measurementManager.setDistancesVisible(true);
          this.app.measurementManager.setAnglesVisible(false);
        },
        durationSec: 8.0
      }
    ];
  }

  start() {
    this.active = true;
    this.currentSceneIndex = 0;
    this._playScene(0);
  }

  stop() {
    this.active = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.app.hud.updatePresentationUI(false, null, 0, this.scenes.length);
  }

  next() {
    if (this.currentSceneIndex < this.scenes.length - 1) {
      this._playScene(this.currentSceneIndex + 1);
    } else {
      this.stop();
    }
  }

  prev() {
    if (this.currentSceneIndex > 0) {
      this._playScene(this.currentSceneIndex - 1);
    }
  }

  _playScene(index) {
    if (!this.active) return;
    this.currentSceneIndex = index;
    const scene = this.scenes[index];

    // Execute scene actions
    scene.action();

    // Update HUD
    this.app.hud.updatePresentationUI(true, scene, index + 1, this.scenes.length);

    if (this.timer) clearTimeout(this.timer);

    if (this.autoPlay) {
      this.timer = setTimeout(() => {
        if (this.active) {
          this.next();
        }
      }, scene.durationSec * 1000);
    }
  }
}
