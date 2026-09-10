/**
 * L3 Proposed Far-Side Solar Sentinel
 * 
 * Concept: Proposed deep-space observatory positioned in the Sun-Earth L3 region
 * (~180° opposite Earth with respect to Sun) to detect active regions 1-2 weeks
 * before solar rotation brings them into Earth's field of view.
 */

import { SpacecraftBase } from "./SpacecraftBase.js";

export class L3Observatory extends SpacecraftBase {
  constructor(scene) {
    super(scene, "l3_observatory", "L3 Observatory", "Proposed Far-Side Sentinel", "PROPOSED");
    this._buildModel();
  }

  _buildModel() {
    this.modelGroup = new THREE.Group();

    // 1. Main Octagonal/Cylindrical Bus
    const busGeo = new THREE.CylinderGeometry(0.7, 0.7, 1.3, 8);
    const busMat = new THREE.MeshStandardMaterial({
      color: 0x99aab8,
      metalness: 0.8,
      roughness: 0.25
    });
    this.busMesh = new THREE.Mesh(busGeo, busMat);
    this.busMesh.userData = { id: "l3_observatory", name: "L3 Observatory (Proposed)", type: "spacecraft" };
    this.modelGroup.add(this.busMesh);

    // 2. Far-Side Solar Telescope Apertures (pointing toward Sun at 0,0,0)
    const scopeGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.5, 16);
    const scopeMat = new THREE.MeshStandardMaterial({ color: 0x111111, metalness: 0.9, roughness: 0.1 });
    const scope1 = new THREE.Mesh(scopeGeo, scopeMat);
    scope1.rotation.z = Math.PI / 2;
    scope1.position.set(0.75, 0.3, 0.2);
    this.modelGroup.add(scope1);

    const scope2 = new THREE.Mesh(scopeGeo, scopeMat);
    scope2.rotation.z = Math.PI / 2;
    scope2.position.set(0.75, -0.25, -0.2);
    this.modelGroup.add(scope2);

    // 3. High-Gain Gimballed Antenna (for relay link)
    const dishGeo = new THREE.CylinderGeometry(0.65, 0.12, 0.28, 24, 1, true);
    const dishMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.7, roughness: 0.2, side: THREE.DoubleSide });
    this.dish = new THREE.Mesh(dishGeo, dishMat);
    this.dish.rotation.x = Math.PI / 3;
    this.dish.position.set(-0.6, 0.8, 0);
    this.modelGroup.add(this.dish);

    // 4. Large Far-side Solar Wings
    const wingGeo = new THREE.BoxGeometry(0.05, 0.8, 2.8);
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x0a1a33, metalness: 0.6, roughness: 0.3 });
    const wings = new THREE.Mesh(wingGeo, wingMat);
    wings.position.set(0, 0, 0);
    this.modelGroup.add(wings);

    this.group.add(this.modelGroup);
  }

  update(delta, time, visualPosition, sunPos, relayPos, camera) {
    if (visualPosition) {
      this.group.position.set(visualPosition.x, visualPosition.y, visualPosition.z);
    }
    // Telescopes point towards Sun
    if (sunPos) {
      this.modelGroup.lookAt(sunPos.x, sunPos.y, sunPos.z);
    }
    // Antenna articulates towards relay position
    if (relayPos && this.dish) {
      this.dish.lookAt(relayPos.x, relayPos.y, relayPos.z);
    }
    this.updateBase(delta, time, camera);
  }
}
