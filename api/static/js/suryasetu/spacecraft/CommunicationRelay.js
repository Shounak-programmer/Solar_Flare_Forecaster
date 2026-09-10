/**
 * Communication Relay Orbiter (Proposed)
 * 
 * Interplanetary communications bridge operating in an inclined transfer orbit.
 * Routes telemetry, high-cadence X-ray spectra, and space weather warnings
 * between L3 far-side, Aditya-L1, L2, and Earth Deep Space Network ground stations.
 */

import { SpacecraftBase } from "./SpacecraftBase.js";

export class CommunicationRelay extends SpacecraftBase {
  constructor(scene) {
    super(scene, "relay_orbiter", "Communication Relay Orbiter", "Proposed Interplanetary Relay", "PROPOSED");
    this._buildModel();
  }

  _buildModel() {
    this.modelGroup = new THREE.Group();

    // 1. Sleek aerospace relay bus
    const busGeo = new THREE.CylinderGeometry(0.5, 0.65, 1.2, 6);
    const busMat = new THREE.MeshStandardMaterial({
      color: 0xccddee,
      metalness: 0.9,
      roughness: 0.2
    });
    this.busMesh = new THREE.Mesh(busGeo, busMat);
    this.busMesh.userData = { id: "relay_orbiter", name: "Communication Relay Orbiter (Proposed)", type: "spacecraft" };
    this.modelGroup.add(this.busMesh);

    // 2. Large Primary Ka-Band Parabolic Reflector
    const dishGeo = new THREE.CylinderGeometry(0.85, 0.15, 0.35, 32, 1, true);
    const dishMat = new THREE.MeshStandardMaterial({
      color: 0xf5f8fa,
      metalness: 0.85,
      roughness: 0.15,
      side: THREE.DoubleSide
    });
    this.dishMesh = new THREE.Mesh(dishGeo, dishMat);
    this.dishMesh.rotation.x = -Math.PI / 3;
    this.dishMesh.position.set(0, 0.9, 0.3);
    this.modelGroup.add(this.dishMesh);

    // Antenna feed tripod and sub-reflector
    const tripodGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.6, 6);
    const tripodMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.8 });
    const feed = new THREE.Mesh(tripodGeo, tripodMat);
    feed.position.set(0, 1.35, 0.55);
    feed.rotation.x = -Math.PI / 3;
    this.modelGroup.add(feed);

    // 3. Deep Space Optical Communication (DSOC) Laser Turret
    const laserGeo = new THREE.SphereGeometry(0.22, 16, 16);
    const laserMat = new THREE.MeshStandardMaterial({ color: 0x223355, metalness: 0.9, roughness: 0.2 });
    this.laserTurret = new THREE.Mesh(laserGeo, laserMat);
    this.laserTurret.position.set(0, -0.65, 0.4);
    this.modelGroup.add(this.laserTurret);

    // Laser aperture lens
    const lensGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.1, 16);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });
    const lens = new THREE.Mesh(lensGeo, lensMat);
    lens.rotation.x = Math.PI / 2;
    lens.position.set(0, 0, 0.2);
    this.laserTurret.add(lens);

    // 4. Photovoltaic solar array wings (tracking)
    const wingGeo = new THREE.BoxGeometry(0.05, 0.65, 2.4);
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x112255, metalness: 0.7, roughness: 0.3 });
    const wings = new THREE.Mesh(wingGeo, wingMat);
    wings.position.set(0, 0, 0);
    this.modelGroup.add(wings);

    // 5. Active Transponder Status LED Indicator
    const ledGeo = new THREE.SphereGeometry(0.08, 8, 8);
    this.ledMat = new THREE.MeshBasicMaterial({ color: 0x00ff88 });
    this.led = new THREE.Mesh(ledGeo, this.ledMat);
    this.led.position.set(0.55, 0.4, 0);
    this.modelGroup.add(this.led);

    this.group.add(this.modelGroup);
  }

  update(delta, time, visualPosition, earthPos, camera) {
    if (visualPosition) {
      this.group.position.set(visualPosition.x, visualPosition.y, visualPosition.z);
    }
    // High-gain dish tracks Earth position
    if (earthPos && this.dishMesh) {
      this.dishMesh.lookAt(earthPos.x, earthPos.y, earthPos.z);
    }
    // Transponder LED heartbeat blink (1 Hz operational cadence)
    const blink = Math.sin(time * 6.0) > 0.2 ? 0x00ff88 : 0x004422;
    this.ledMat.color.setHex(blink);

    this.updateBase(delta, time, camera);
  }
}
