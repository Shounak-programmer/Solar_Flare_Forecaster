/**
 * Electromagnetic Radiation (X-Ray / EUV) Propagation System
 * 
 * Physics:
 * - Speed = c = 299,792.458 km/s
 * - Sun -> Earth: ~499.0 s (~8 min 19 s)
 * - Sun -> Aditya-L1: ~494.0 s (~8 min 14 s)
 * - Relative lead of Aditya-L1 over Earth: ~5.0 seconds
 * 
 * Visuals:
 * - Expanding luminous wavefront sphere / cone radiating outward at c
 * - Triggers detector arrival events at spacecraft
 */

export class EMPropagation {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.group.name = "EM_Propagation_Group";

    this.active = false;
    this.progress = 0.0; // 0 to 1
    this.durationSec = 4.8; // Visual duration to reach Earth/L2
    this.elapsedVisual = 0.0;

    this.callbacks = {
      onL1Reached: null,
      onEarthReached: null,
      onL2Reached: null,
      onL3Reached: null
    };

    this.reached = {
      l1: false,
      earth: false,
      l2: false,
      l3: false
    };

    this._createWavefrontMesh();
    this.scene.add(this.group);
  }

  _createWavefrontMesh() {
    // Glowing expanding spherical wavefront shell (smooth, non-wireframe)
    const shellGeo = new THREE.SphereGeometry(1, 48, 32, 0, Math.PI * 2, 0, Math.PI);
    this.shellMat = new THREE.MeshBasicMaterial({
      color: 0x00ffff,
      transparent: true,
      opacity: 0.0,
      wireframe: false,
      side: THREE.BackSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.shellMesh = new THREE.Mesh(shellGeo, this.shellMat);
    this.group.add(this.shellMesh);

    // High-intensity leading edge ring towards Earth direction (+X)
    const ringGeo = new THREE.RingGeometry(0.95, 1.05, 48);
    this.ringMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending
    });
    this.ringMesh = new THREE.Mesh(ringGeo, this.ringMat);
    this.ringMesh.rotation.y = Math.PI / 2;
    this.group.add(this.ringMesh);
  }

  trigger(callbacks = {}) {
    this.active = true;
    this.progress = 0.0;
    this.elapsedVisual = 0.0;
    this.callbacks = callbacks;
    this.reached = { l1: false, earth: false, l2: false, l3: false };
    this.shellMesh.scale.set(0.1, 0.1, 0.1);
    this.ringMesh.scale.set(0.1, 0.1, 0.1);
  }

  update(delta, positions) {
    if (!this.active) return;

    this.elapsedVisual += delta;
    this.progress = Math.min(1.0, this.elapsedVisual / this.durationSec);

    // Current visual wave radius expanding from Sun (0 to ~125 units)
    const maxRadius = 122;
    const currentRadius = Math.max(0.5, this.progress * maxRadius);

    this.shellMesh.scale.set(currentRadius, currentRadius, currentRadius);
    this.ringMesh.scale.set(currentRadius, currentRadius, currentRadius);

    // Opacity fades gracefully near boundary
    const alpha = Math.sin(this.progress * Math.PI) * 0.75;
    this.shellMat.opacity = alpha * 0.45;
    this.ringMat.opacity = alpha * 0.85;

    // Check arrival at Aditya-L1 (visual dist ~84)
    if (!this.reached.l1 && currentRadius >= 84) {
      this.reached.l1 = true;
      if (this.callbacks.onL1Reached) this.callbacks.onL1Reached();
    }

    // Check arrival at Earth (visual dist ~100)
    if (!this.reached.earth && currentRadius >= 100) {
      this.reached.earth = true;
      if (this.callbacks.onEarthReached) this.callbacks.onEarthReached();
    }

    // Check arrival at L2 (visual dist ~116)
    if (!this.reached.l2 && currentRadius >= 116) {
      this.reached.l2 = true;
      if (this.callbacks.onL2Reached) this.callbacks.onL2Reached();
    }

    // Check arrival at L3 (visual dist ~98 on opposite side)
    if (!this.reached.l3 && currentRadius >= 98) {
      this.reached.l3 = true;
      if (this.callbacks.onL3Reached) this.callbacks.onL3Reached();
    }

    if (this.progress >= 1.0) {
      this.active = false;
      this.shellMat.opacity = 0;
      this.ringMat.opacity = 0;
    }
  }

  reset() {
    this.active = false;
    this.progress = 0;
    this.shellMat.opacity = 0;
    this.ringMat.opacity = 0;
  }
}
