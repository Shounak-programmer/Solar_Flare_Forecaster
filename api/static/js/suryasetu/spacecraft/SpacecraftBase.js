/**
 * SpacecraftBase — Base class for aerospace spacecraft representations
 * 
 * Provides:
 * - 3D scene group & transform management
 * - Selection, hover, and highlight visual states
 * - Detection trigger flash (when solar flare / wave arrives)
 * - Reticle and status indicators
 */

export class SpacecraftBase {
  constructor(scene, id, name, subtitle, status) {
    this.scene = scene;
    this.id = id;
    this.name = name;
    this.subtitle = subtitle;
    this.status = status; // "OPERATIONAL" or "PROPOSED"

    this.group = new THREE.Group();
    this.group.name = `Spacecraft_${id}`;

    this.isSelected = false;
    this.isHovered = false;
    this.isDetecting = false;
    this.detectionFlash = 0.0;

    this._createReticle();
    this.scene.add(this.group);
  }

  _createReticle() {
    // Holographic targeting ring
    const ringGeo = new THREE.RingGeometry(1.6, 1.85, 32);
    this.reticleMat = new THREE.MeshBasicMaterial({
      color: this.status === "OPERATIONAL" ? 0x00e5ff : 0xff9900,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide
    });
    this.reticle = new THREE.Mesh(ringGeo, this.reticleMat);
    this.reticle.rotation.x = Math.PI / 2;
    this.group.add(this.reticle);
  }

  triggerDetection(duration = 3.0) {
    this.isDetecting = true;
    this.detectionFlash = 1.0;
  }

  setSelected(selected) {
    this.isSelected = selected;
    this.reticleMat.opacity = selected ? 0.95 : (this.isHovered ? 0.75 : 0.45);
    const scale = selected ? 1.4 : 1.0;
    this.reticle.scale.set(scale, scale, scale);
  }

  setHovered(hovered) {
    this.isHovered = hovered;
    if (!this.isSelected) {
      this.reticleMat.opacity = hovered ? 0.75 : 0.45;
    }
  }

  updateBase(delta, time, camera) {
    // Orient reticle towards camera for clean HUD appearance
    if (camera) {
      this.reticle.lookAt(camera.position);
    }

    // Handle detection flash
    if (this.isDetecting) {
      this.detectionFlash -= delta * 0.4;
      if (this.detectionFlash <= 0) {
        this.detectionFlash = 0;
        this.isDetecting = false;
      }
      this.reticleMat.color.setHex(0xffffff);
      this.reticleMat.opacity = 0.95;
    } else {
      const defaultColor = this.status === "OPERATIONAL" ? 0x00e5ff : 0xff9900;
      this.reticleMat.color.setHex(defaultColor);
      if (!this.isSelected && !this.isHovered) {
        // Gentle operational beacon pulse
        this.reticleMat.opacity = 0.35 + Math.sin(time * 2.5) * 0.15;
      }
    }
  }

  getPosition() {
    return this.group.position;
  }
}
