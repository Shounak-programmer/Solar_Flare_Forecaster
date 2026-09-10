/**
 * Procedural Sun with Granulation, Corona Glow & Solar Active Regions
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class Sun {
  constructor(scene, params = SYSTEM_PARAMETERS) {
    this.scene = scene;
    this.params = params;
    this.radius = params.visual.sunRadius;

    this.group = new THREE.Group();
    this.group.name = "SunGroup";

    this.flareIntensity = 0.0;
    this.isFlaring = false;

    this._createCore();
    this._createCorona();
    this._createActiveRegions();

    this.scene.add(this.group);
  }

  _generateSunTexture() {
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    // Base fiery solar gradient
    const grad = ctx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0, "#fff5d0");
    grad.addColorStop(0.2, "#ffaa20");
    grad.addColorStop(0.5, "#e65100");
    grad.addColorStop(0.8, "#ff9800");
    grad.addColorStop(1, "#fff5d0");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 512);

    // Procedural solar granules and convective cells
    for (let i = 0; i < 2000; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 512;
      const r = 2 + Math.random() * 8;
      const opacity = 0.15 + Math.random() * 0.35;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = Math.random() > 0.4 ? `rgba(255,235,140,${opacity})` : `rgba(180,40,0,${opacity})`;
      ctx.fill();
    }

    // Active region sunspot belts (latitudes ~15-30 deg N/S)
    const drawSpotBelt = (baseY) => {
      for (let s = 0; s < 12; s++) {
        const sx = 100 + s * 75 + (Math.random() * 30 - 15);
        const sy = baseY + (Math.random() * 30 - 15);
        // Penumbra
        ctx.beginPath();
        ctx.ellipse(sx, sy, 12, 7, Math.random() * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(180, 50, 0, 0.75)";
        ctx.fill();
        // Umbra (dark core)
        ctx.beginPath();
        ctx.ellipse(sx, sy, 6, 3.5, Math.random() * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(45, 10, 0, 0.95)";
        ctx.fill();
      }
    };
    drawSpotBelt(200); // North active belt
    drawSpotBelt(312); // South active belt

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  _createCore() {
    const geometry = new THREE.SphereGeometry(this.radius, 48, 48);
    const texture = this._generateSunTexture();

    this.material = new THREE.MeshBasicMaterial({
      map: texture,
      color: 0xfff0aa
    });

    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.userData = { id: "sun", name: "Sun", type: "celestial" };
    this.group.add(this.mesh);
  }

  _createCorona() {
    // Inner vibrant glow
    const innerGeo = new THREE.SphereGeometry(this.radius * 1.05, 32, 32);
    this.innerGlowMat = new THREE.MeshBasicMaterial({
      color: 0xffaa00,
      transparent: true,
      opacity: 0.38,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    this.innerGlow = new THREE.Mesh(innerGeo, this.innerGlowMat);
    this.group.add(this.innerGlow);

    // Outer subtle coronal halo
    const outerGeo = new THREE.SphereGeometry(this.radius * 1.25, 32, 32);
    this.outerGlowMat = new THREE.MeshBasicMaterial({
      color: 0xff7700,
      transparent: true,
      opacity: 0.18,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    this.outerGlow = new THREE.Mesh(outerGeo, this.outerGlowMat);
    this.group.add(this.outerGlow);
  }

  _createActiveRegions() {
    // Flaring active region marker facing Earth direction (+X)
    const arGeo = new THREE.RingGeometry(0.6, 1.3, 24);
    this.arMat = new THREE.MeshBasicMaterial({
      color: 0xffffaa,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending
    });
    this.activeRegion = new THREE.Mesh(arGeo, this.arMat);
    // Position on Sun surface towards +X direction with slight inclination
    this.activeRegion.position.set(this.radius * 0.99, 1.8, 1.2);
    this.activeRegion.lookAt(new THREE.Vector3(50, 1.8, 1.2));
    this.group.add(this.activeRegion);
  }

  triggerFlareFlash() {
    this.isFlaring = true;
    this.flareIntensity = 1.0;
  }

  update(delta, time) {
    // Subtle rotation of the Sun
    this.mesh.rotation.y += delta * 0.05;

    // Pulse active region
    if (this.isFlaring) {
      this.flareIntensity -= delta * 0.25;
      if (this.flareIntensity <= 0) {
        this.flareIntensity = 0;
        this.isFlaring = false;
      }
      const flareBoost = this.flareIntensity * 1.5;
      this.innerGlowMat.opacity = 0.38 + flareBoost * 0.45;
      this.outerGlowMat.opacity = 0.18 + flareBoost * 0.35;
      this.arMat.opacity = 0.85 + flareBoost;
      const s = 1.0 + flareBoost * 1.2;
      this.activeRegion.scale.set(s, s, s);
    } else {
      // Normal breathing glow
      const breathe = Math.sin(time * 1.5) * 0.04;
      this.innerGlowMat.opacity = 0.38 + breathe;
      this.arMat.opacity = 0.75 + Math.sin(time * 3.0) * 0.2;
    }
  }

  getPosition() {
    return this.group.position;
  }
}
