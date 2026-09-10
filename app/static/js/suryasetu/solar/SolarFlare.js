/**
 * SolarFlare — Active Region Eruption & Coronal Magnetic Loops
 */

export class SolarFlare {
  constructor(scene, sunPos = new THREE.Vector3(0, 0, 0), sunRadius = 10) {
    this.scene = scene;
    this.sunPos = sunPos;
    this.sunRadius = sunRadius;

    this.group = new THREE.Group();
    this.group.name = "SolarFlare_Group";

    this.active = false;
    this.intensity = 0.0;

    this._createMagneticLoops();
    this.scene.add(this.group);
  }

  _createMagneticLoops() {
    this.loops = [];
    const loopCount = 5;

    for (let i = 0; i < loopCount; i++) {
      const curve = new THREE.CubicBezierCurve3(
        new THREE.Vector3(this.sunRadius * 0.98, 1.2 - i * 0.4, 0.6 + i * 0.3),
        new THREE.Vector3(this.sunRadius * 1.35 + i * 0.3, 2.5 + i * 0.5, 0.8),
        new THREE.Vector3(this.sunRadius * 1.35 + i * 0.3, -1.0 - i * 0.3, 1.5),
        new THREE.Vector3(this.sunRadius * 0.98, -1.5, 1.2)
      );

      const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(32));
      const mat = new THREE.LineBasicMaterial({
        color: 0xffeedd,
        transparent: true,
        opacity: 0.0,
        blending: THREE.AdditiveBlending
      });
      const line = new THREE.Line(geo, mat);
      this.group.add(line);
      this.loops.push({ line, mat });
    }

    // Flash burst sphere
    const burstGeo = new THREE.SphereGeometry(1.2, 16, 16);
    this.burstMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending
    });
    this.burst = new THREE.Mesh(burstGeo, this.burstMat);
    this.burst.position.set(this.sunRadius * 0.98, 1.0, 1.0);
    this.group.add(this.burst);
  }

  trigger() {
    this.active = true;
    this.intensity = 1.0;
  }

  update(delta) {
    if (!this.active) return;

    this.intensity -= delta * 0.22;
    if (this.intensity <= 0) {
      this.intensity = 0;
      this.active = false;
    }

    // Flash dynamics
    this.burstMat.opacity = this.intensity * 0.9;
    const s = 1.0 + (1.0 - this.intensity) * 3.5;
    this.burst.scale.set(s, s, s);

    // Magnetic loops glow
    for (let i = 0; i < this.loops.length; i++) {
      this.loops[i].mat.opacity = this.intensity * (0.8 - i * 0.1);
    }
  }

  reset() {
    this.active = false;
    this.intensity = 0;
    this.burstMat.opacity = 0;
    for (const loop of this.loops) {
      loop.mat.opacity = 0;
    }
  }
}
