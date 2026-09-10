/**
 * LightingManager — Heliocentric Sun Point Light, Ambient Fill & Flare Illumination
 */

export class LightingManager {
  constructor(scene) {
    this.scene = scene;

    // 1. Central Sun Light (Point Light at origin radiating into solar system)
    this.sunLight = new THREE.PointLight(0xfff5e0, 2.2, 800, 0.4);
    this.sunLight.position.set(0, 0, 0);
    this.scene.add(this.sunLight);

    // 2. Space ambient fill light (cool deep navy tone to avoid pitch-black unreadable surfaces)
    this.ambientLight = new THREE.AmbientLight(0x203550, 0.85);
    this.scene.add(this.ambientLight);

    // 3. Subtle directional rim light from ecliptic north
    this.rimLight = new THREE.DirectionalLight(0x7799bb, 0.35);
    this.rimLight.position.set(0, 50, 0);
    this.scene.add(this.rimLight);
  }

  setFlareBoost(intensity) {
    this.sunLight.intensity = 2.2 + intensity * 2.5;
    this.sunLight.color.setHex(intensity > 0.5 ? 0xfffae6 : 0xfff5e0);
  }
}
