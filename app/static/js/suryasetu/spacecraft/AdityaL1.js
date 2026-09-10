/**
 * Aditya-L1 Spacecraft Model (ISRO Operational Solar Observatory)
 * 
 * Features:
 * - Gold Multi-Layer Insulation (MLI) main bus
 * - Extended dual solar arrays (photovoltaic blue/indigo)
 * - Sun-facing scientific instrument deck (SoLEXS, HEL1OS, VELC)
 * - Deployable magnetometer boom
 * - Precise sun-pointing attitude orientation
 */

import { SpacecraftBase } from "./SpacecraftBase.js";

export class AdityaL1 extends SpacecraftBase {
  constructor(scene) {
    super(scene, "aditya_l1", "Aditya-L1", "Sun-Earth L1 Observatory", "OPERATIONAL");
    this._buildModel();
  }

  _buildModel() {
    this.modelGroup = new THREE.Group();

    // 1. Main Spacecraft Bus (Gold MLI Thermal Blanket finish)
    const busGeo = new THREE.BoxGeometry(1.2, 1.4, 1.2);
    const goldBusMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.85,
      roughness: 0.25,
      emissive: 0x332205
    });
    this.busMesh = new THREE.Mesh(busGeo, goldBusMat);
    this.busMesh.userData = { id: "aditya_l1", name: "Aditya-L1", type: "spacecraft" };
    this.modelGroup.add(this.busMesh);

    // 2. Solar Arrays (Left & Right Wings)
    const panelGeo = new THREE.BoxGeometry(2.2, 0.05, 0.85);
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x112244,
      metalness: 0.6,
      roughness: 0.3,
      emissive: 0x050c18
    });

    const leftWing = new THREE.Mesh(panelGeo, panelMat);
    leftWing.position.set(0, 0, -1.8);
    this.modelGroup.add(leftWing);

    const rightWing = new THREE.Mesh(panelGeo, panelMat);
    rightWing.position.set(0, 0, 1.8);
    this.modelGroup.add(rightWing);

    // Solar array yoke brackets
    const yokeGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.9, 8);
    const yokeMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.9, roughness: 0.2 });
    const leftYoke = new THREE.Mesh(yokeGeo, yokeMat);
    leftYoke.rotation.x = Math.PI / 2;
    leftYoke.position.set(0, 0, -1.0);
    this.modelGroup.add(leftYoke);

    const rightYoke = new THREE.Mesh(yokeGeo, yokeMat);
    rightYoke.rotation.x = Math.PI / 2;
    rightYoke.position.set(0, 0, 1.0);
    this.modelGroup.add(rightYoke);

    // 3. Sun-Facing Science Payload Deck (-X faces Sun)
    // SoLEXS (Soft X-ray Spectrometer collimator block)
    const solexsGeo = new THREE.BoxGeometry(0.35, 0.3, 0.35);
    const solexsMat = new THREE.MeshStandardMaterial({ color: 0x223344, metalness: 0.7, roughness: 0.3 });
    const solexs = new THREE.Mesh(solexsGeo, solexsMat);
    solexs.position.set(-0.65, 0.3, 0.25);
    this.modelGroup.add(solexs);

    // HEL1OS (Hard X-ray Spectrometer collimator tube)
    const hel1osGeo = new THREE.CylinderGeometry(0.14, 0.16, 0.45, 16);
    const hel1osMat = new THREE.MeshStandardMaterial({ color: 0xcc5500, metalness: 0.6, roughness: 0.4 });
    const hel1os = new THREE.Mesh(hel1osGeo, hel1osMat);
    hel1os.rotation.z = Math.PI / 2;
    hel1os.position.set(-0.7, -0.25, 0.25);
    this.modelGroup.add(hel1os);

    // VELC (Visible Emission Line Coronagraph main optical barrel)
    const velcGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.65, 16);
    const velcMat = new THREE.MeshStandardMaterial({ color: 0x111111, metalness: 0.9, roughness: 0.1 });
    const velc = new THREE.Mesh(velcGeo, velcMat);
    velc.rotation.z = Math.PI / 2;
    velc.position.set(-0.75, 0.15, -0.25);
    this.modelGroup.add(velc);

    // 4. Deployable Magnetometer Boom (+X / aft)
    const boomGeo = new THREE.CylinderGeometry(0.03, 0.03, 2.0, 8);
    const boomMat = new THREE.MeshStandardMaterial({ color: 0xaaaaaa, metalness: 0.8, roughness: 0.2 });
    const boom = new THREE.Mesh(boomGeo, boomMat);
    boom.rotation.z = Math.PI / 2;
    boom.position.set(1.4, -0.4, -0.3);
    this.modelGroup.add(boom);

    // Sensor ball at tip of magnetometer boom
    const magBallGeo = new THREE.SphereGeometry(0.1, 12, 12);
    const magBallMat = new THREE.MeshStandardMaterial({ color: 0xff3300, roughness: 0.5 });
    const magBall = new THREE.Mesh(magBallGeo, magBallMat);
    magBall.position.set(2.4, -0.4, -0.3);
    this.modelGroup.add(magBall);

    this.group.add(this.modelGroup);
  }

  update(delta, time, visualPosition, sunPos, camera) {
    if (visualPosition) {
      this.group.position.set(visualPosition.x, visualPosition.y, visualPosition.z);
    }
    // Maintain Sun-pointing attitude (payload deck faces Sun at 0,0,0)
    if (sunPos) {
      this.modelGroup.lookAt(sunPos.x, sunPos.y, sunPos.z);
    }
    this.updateBase(delta, time, camera);
  }
}
