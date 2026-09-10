/**
 * L2 Proposed Solar / Magnetotail Observatory
 * 
 * Concept: Proposed deep-space space weather observatory situated at Sun-Earth L2.
 * Distinct aesthetic: Multi-layer sunshield, deep-space antenna, secondary particle detector.
 */

import { SpacecraftBase } from "./SpacecraftBase.js";

export class L2Observatory extends SpacecraftBase {
  constructor(scene) {
    super(scene, "l2_observatory", "L2 Observatory", "Proposed Multi-Point Sentinel", "PROPOSED");
    this._buildModel();
  }

  _buildModel() {
    this.modelGroup = new THREE.Group();

    // 1. Multi-layer Sunshield (silver/aluminum protective shield facing Sun)
    const shieldGeo = new THREE.BoxGeometry(0.1, 2.6, 2.2);
    const shieldMat = new THREE.MeshStandardMaterial({
      color: 0xdde5ee,
      metalness: 0.9,
      roughness: 0.15
    });
    const shield = new THREE.Mesh(shieldGeo, shieldMat);
    shield.position.set(-0.7, 0, 0);
    this.modelGroup.add(shield);

    // 2. Central Science Bus (silver/titanium box behind shield)
    const busGeo = new THREE.BoxGeometry(1.0, 1.1, 1.1);
    const busMat = new THREE.MeshStandardMaterial({
      color: 0x8899aa,
      metalness: 0.7,
      roughness: 0.3
    });
    this.busMesh = new THREE.Mesh(busGeo, busMat);
    this.busMesh.userData = { id: "l2_observatory", name: "L2 Observatory (Proposed)", type: "spacecraft" };
    this.modelGroup.add(this.busMesh);

    // 3. High-gain parabolic antenna (facing back towards Earth)
    const dishGeo = new THREE.CylinderGeometry(0.55, 0.1, 0.25, 24, 1, true);
    const dishMat = new THREE.MeshStandardMaterial({ color: 0xeeeeee, metalness: 0.8, roughness: 0.2, side: THREE.DoubleSide });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.rotation.z = Math.PI / 2;
    dish.position.set(0.65, 0.2, 0);
    this.modelGroup.add(dish);

    // 4. Solar Wings (outspread along Y axis)
    const wingGeo = new THREE.BoxGeometry(0.04, 1.8, 0.7);
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x112244, metalness: 0.5, roughness: 0.3 });
    const leftWing = new THREE.Mesh(wingGeo, wingMat);
    leftWing.position.set(0, 1.6, 0);
    this.modelGroup.add(leftWing);

    const rightWing = new THREE.Mesh(wingGeo, wingMat);
    rightWing.position.set(0, -1.6, 0);
    this.modelGroup.add(rightWing);

    this.group.add(this.modelGroup);
  }

  update(delta, time, visualPosition, earthPos, camera) {
    if (visualPosition) {
      this.group.position.set(visualPosition.x, visualPosition.y, visualPosition.z);
    }
    // Shield points toward Sun (negative X direction)
    this.modelGroup.rotation.y = 0;
    this.updateBase(delta, time, camera);
  }
}
