/**
 * OrbitManager — Manages orbital tracks, halo trajectories, and Lagrange markers
 */

import { OrbitalCalculations } from "../physics/orbitalCalculations.js";
import { SYSTEM_PARAMETERS } from "../data/systemParameters.js";

export class OrbitManager {
  constructor(scene, params = SYSTEM_PARAMETERS) {
    this.scene = scene;
    this.params = params;
    this.calculator = new OrbitalCalculations(params);

    this.group = new THREE.Group();
    this.group.name = "OrbitsGroup";

    this.visible = {
      earth: true,
      l1Halo: true,
      lagrangePoints: true
    };

    this._initOrbits();
    this.scene.add(this.group);
  }

  _initOrbits() {
    this._createEarthOrbit();
    this._createL1HaloOrbit();
    this._createLagrangeMarkers();
  }

  _createEarthOrbit() {
    const points = this.calculator.generateEarthOrbitPath(128);
    const geometry = new THREE.BufferGeometry().setFromPoints(
      points.map(p => new THREE.Vector3(p.x, p.y, p.z))
    );
    const material = new THREE.LineBasicMaterial({
      color: 0x3a6a99,
      transparent: true,
      opacity: 0.45
    });
    this.earthOrbitLine = new THREE.Line(geometry, material);
    this.group.add(this.earthOrbitLine);
  }

  _createL1HaloOrbit() {
    const l1Nominal = this.params.visual ? {
      x: this.params.visual.earthOrbitRadius - this.params.visual.l1VisualDistFromEarth,
      y: 0,
      z: 0
    } : { x: 84, y: 0, z: 0 };

    this._lastHaloCenter = { ...l1Nominal };
    const points = this.calculator.generateL1HaloOrbitPath(l1Nominal, 128);
    const geometry = new THREE.BufferGeometry().setFromPoints(
      points.map(p => new THREE.Vector3(p.x, p.y, p.z))
    );
    const material = new THREE.LineBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.85
    });
    this.l1HaloLine = new THREE.Line(geometry, material);
    this.group.add(this.l1HaloLine);
  }

  _createTextSprite(text, subtitle = "") {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");

    // Dark high-tech pill background
    ctx.fillStyle = "rgba(6, 16, 28, 0.85)";
    ctx.beginPath();
    ctx.roundRect(16, 16, 480, 96, 20);
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.75)";
    ctx.stroke();

    // Primary Text
    ctx.fillStyle = "#00e5ff";
    ctx.font = "bold 32px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 256, subtitle ? 52 : 64);

    // Subtitle
    if (subtitle) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 20px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx.fillText(subtitle, 256, 84);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false
    });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(4.2, 1.05, 1.0);
    return sprite;
  }

  _createLagrangeMarkers() {
    this.lagrangeGroup = new THREE.Group();
    this.lagrangeGroup.name = "LagrangeMarkers";

    const l1Nominal = this.params.visual ? {
      x: this.params.visual.earthOrbitRadius - this.params.visual.l1VisualDistFromEarth,
      y: 0,
      z: 0
    } : { x: 84, y: 0, z: 0 };

    this.l1Marker = new THREE.Group();
    this.l1Marker.name = "L1_Point_Reference";
    this.l1Marker.userData = { id: "l1_point", name: "L1 Point (Reference)", type: "lagrange_point" };
    this.l1Marker.position.set(l1Nominal.x, l1Nominal.y, l1Nominal.z);

    // 1. Central reference sphere
    const dotGeo = new THREE.SphereGeometry(0.35, 16, 16);
    const dotMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
    const dot = new THREE.Mesh(dotGeo, dotMat);
    this.l1Marker.add(dot);

    // 2. Concentric reference rings
    const ringGeo = new THREE.RingGeometry(0.75, 0.95, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    this.l1Marker.add(ring);

    // 3. Precision 3D crosshair lines
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-1.6, 0, 0), new THREE.Vector3(1.6, 0, 0),
      new THREE.Vector3(0, 0, -1.6), new THREE.Vector3(0, 0, 1.6),
      new THREE.Vector3(0, -1.2, 0), new THREE.Vector3(0, 1.2, 0)
    ]);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.7 });
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    this.l1Marker.add(lines);

    // 4. Interactive click/hover sphere
    const hitGeo = new THREE.SphereGeometry(1.6, 8, 8);
    const hitMat = new THREE.MeshBasicMaterial({ visible: false });
    this.l1MarkerClickMesh = new THREE.Mesh(hitGeo, hitMat);
    this.l1MarkerClickMesh.userData = { id: "l1_point", name: "L1 Point (Reference)", type: "lagrange_point" };
    this.l1Marker.add(this.l1MarkerClickMesh);

    // 5. Billboard text label: "L1 Point (Reference)"
    this.l1LabelSprite = this._createTextSprite("L1 Point (Reference)", "Mathematical Reference");
    this.l1LabelSprite.position.set(0, 2.0, 0);
    this.l1Marker.add(this.l1LabelSprite);

    this.lagrangeGroup.add(this.l1Marker);
    this.group.add(this.lagrangeGroup);
  }

  updateL1HaloOrbit(l1NominalVisualPos) {
    if (!l1NominalVisualPos) return;

    if (this.l1Marker) {
      this.l1Marker.position.set(l1NominalVisualPos.x, l1NominalVisualPos.y, l1NominalVisualPos.z);
    }

    // Only rebuild orbit if center has actually shifted
    if (
      !this._lastHaloCenter ||
      Math.abs(this._lastHaloCenter.x - l1NominalVisualPos.x) > 0.001 ||
      Math.abs(this._lastHaloCenter.y - l1NominalVisualPos.y) > 0.001 ||
      Math.abs(this._lastHaloCenter.z - l1NominalVisualPos.z) > 0.001
    ) {
      this._lastHaloCenter = { ...l1NominalVisualPos };
      if (this.l1HaloLine) {
        this.group.remove(this.l1HaloLine);
        this.l1HaloLine.geometry.dispose();
      }
      const points = this.calculator.generateL1HaloOrbitPath(l1NominalVisualPos, 128);
      const geometry = new THREE.BufferGeometry().setFromPoints(
        points.map(p => new THREE.Vector3(p.x, p.y, p.z))
      );
      const material = new THREE.LineBasicMaterial({
        color: 0x00e5ff,
        transparent: true,
        opacity: 0.85
      });
      this.l1HaloLine = new THREE.Line(geometry, material);
      this.group.add(this.l1HaloLine);
    }
  }

  setOrbitVisibility(key, visible) {
    this.visible[key] = visible;
    if (key === "earth" && this.earthOrbitLine) this.earthOrbitLine.visible = visible;
    if (key === "l1Halo" && this.l1HaloLine) this.l1HaloLine.visible = visible;
    if (key === "lagrangePoints" && this.lagrangeGroup) this.lagrangeGroup.visible = visible;
  }
}
