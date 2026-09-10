/**
 * Earth Celestial Body with Continents, Clouds, Night-Side Shading & Atmospheric Glow
 */

import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class Earth {
  constructor(scene, params = SYSTEM_PARAMETERS) {
    this.scene = scene;
    this.params = params;
    this.radius = params.visual.earthRadius;
    this.orbitRadius = params.visual.earthOrbitRadius;

    this.group = new THREE.Group();
    this.group.name = "EarthGroup";

    this._createEarth();
    this._createAtmosphere();

    this.scene.add(this.group);
  }

  _generateEarthTexture() {
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    // Deep ocean blue
    ctx.fillStyle = "#0c2b4d";
    ctx.fillRect(0, 0, 1024, 512);

    // Continents (procedural geographical landmasses: Eurasia, Africa, Americas, Antarctica, Australia)
    ctx.fillStyle = "#2d5e38";

    // Africa & Europe
    ctx.beginPath();
    ctx.ellipse(520, 240, 75, 110, 0.1, 0, Math.PI * 2);
    ctx.fill();

    // Asia & India
    ctx.beginPath();
    ctx.ellipse(680, 190, 120, 80, -0.1, 0, Math.PI * 2);
    ctx.fill();
    // Indian subcontinent peninsula
    ctx.beginPath();
    ctx.moveTo(670, 220);
    ctx.lineTo(720, 230);
    ctx.lineTo(690, 290);
    ctx.closePath();
    ctx.fillStyle = "#3e6e38";
    ctx.fill();

    // Americas
    ctx.fillStyle = "#2d5e38";
    ctx.beginPath();
    ctx.ellipse(250, 170, 65, 80, -0.2, 0, Math.PI * 2); // North America
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(310, 320, 50, 95, 0.25, 0, Math.PI * 2); // South America
    ctx.fill();

    // Australia
    ctx.beginPath();
    ctx.ellipse(820, 330, 45, 35, 0, 0, Math.PI * 2);
    ctx.fill();

    // Polar ice caps
    ctx.fillStyle = "#e8f4f8";
    ctx.fillRect(0, 0, 1024, 30);
    ctx.fillRect(0, 485, 1024, 27);

    // Swirling atmospheric clouds
    ctx.fillStyle = "rgba(255, 255, 255, 0.38)";
    for (let i = 0; i < 70; i++) {
      const cx = (i * 37) % 1024;
      const cy = 60 + ((i * 53) % 390);
      const rw = 40 + (i % 5) * 18;
      const rh = 8 + (i % 3) * 6;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rw, rh, (i * 0.1) % 0.6 - 0.3, 0, Math.PI * 2);
      ctx.fill();
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  _createEarth() {
    const geometry = new THREE.SphereGeometry(this.radius, 36, 36);
    const texture = this._generateEarthTexture();

    this.material = new THREE.MeshLambertMaterial({
      map: texture,
      color: 0xffffff
    });

    this.earthMesh = new THREE.Mesh(geometry, this.material);
    // 23.44° axial tilt
    this.earthMesh.rotation.z = (23.44 * Math.PI) / 180;
    this.earthMesh.userData = { id: "earth", name: "Earth", type: "celestial" };

    this.group.add(this.earthMesh);
  }

  _createAtmosphere() {
    // Subtle atmospheric glow rim
    const atmoGeo = new THREE.SphereGeometry(this.radius * 1.08, 32, 32);
    this.atmoMat = new THREE.MeshBasicMaterial({
      color: 0x4da6ff,
      transparent: true,
      opacity: 0.28,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    this.atmoMesh = new THREE.Mesh(atmoGeo, this.atmoMat);
    this.group.add(this.atmoMesh);
  }

  update(delta, time, earthVisualPos) {
    if (earthVisualPos) {
      this.group.position.set(earthVisualPos.x, earthVisualPos.y, earthVisualPos.z);
    }
    // Axial diurnal rotation
    this.earthMesh.rotation.y += delta * 0.2;
  }

  getPosition() {
    return this.group.position;
  }
}
