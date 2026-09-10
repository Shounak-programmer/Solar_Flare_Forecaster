/**
 * CameraManager — Cinematic OrbitControls & Smooth Target Transitions
 */

export class CameraManager {
  constructor(camera, domElement) {
    this.camera = camera;
    this.domElement = domElement;

    this.controls = new THREE.OrbitControls(this.camera, this.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 600;
    this.controls.maxPolarAngle = Math.PI * 0.95;

    // Smooth transition state
    this.isTransitioning = false;
    this.transitionTime = 0;
    this.transitionDuration = 1.6; // seconds
    this.startCamPos = new THREE.Vector3();
    this.targetCamPos = new THREE.Vector3();
    this.startControlTarget = new THREE.Vector3();
    this.targetControlTarget = new THREE.Vector3();
  }

  update(delta) {
    if (this.isTransitioning) {
      this.transitionTime += delta;
      const t = Math.min(1.0, this.transitionTime / this.transitionDuration);
      // Smooth cubic ease-in-out
      const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

      this.camera.position.lerpVectors(this.startCamPos, this.targetCamPos, ease);
      this.controls.target.lerpVectors(this.startControlTarget, this.targetControlTarget, ease);

      if (t >= 1.0) {
        this.isTransitioning = false;
        this.camera.position.copy(this.targetCamPos);
        this.controls.target.copy(this.targetControlTarget);
      }
    }

    this.controls.update();
  }

  transitionTo(camPos, targetPos, duration = 1.6) {
    this.startCamPos.copy(this.camera.position);
    this.targetCamPos.copy(camPos);
    this.startControlTarget.copy(this.controls.target);
    this.targetControlTarget.copy(targetPos);
    this.transitionDuration = duration;
    this.transitionTime = 0;
    this.isTransitioning = true;
  }

  // Camera Focus Presets
  focusOverview() {
    this.transitionTo(new THREE.Vector3(70, 115, 185), new THREE.Vector3(0, 0, 0), 1.8);
  }

  focusSun() {
    this.transitionTo(new THREE.Vector3(22, 10, 32), new THREE.Vector3(0, 0, 0), 1.5);
  }

  focusEarth(earthVisualPos) {
    const pos = earthVisualPos || new THREE.Vector3(100, 0, 0);
    this.transitionTo(new THREE.Vector3(pos.x + 8, pos.y + 4, pos.z + 12), pos, 1.6);
  }

  focusAdityaL1(l1VisualPos) {
    const pos = l1VisualPos || new THREE.Vector3(84, 0, 0);
    // Smoothly frame the L1 region showing the stationary L1 reference marker,
    // the 3D halo orbit, the traveling Aditya-L1 spacecraft, and the clear Sun-Earth axis
    this.transitionTo(new THREE.Vector3(pos.x + 5.0, pos.y + 4.5, pos.z + 10.5), pos, 1.6);
  }

  focusL2(l2VisualPos) {
    const pos = l2VisualPos || new THREE.Vector3(116, 0, 0);
    this.transitionTo(new THREE.Vector3(pos.x + 6, pos.y + 3, pos.z + 8), pos, 1.6);
  }

  focusL3(l3VisualPos) {
    const pos = l3VisualPos || new THREE.Vector3(-98, 0, 0);
    this.transitionTo(new THREE.Vector3(pos.x + 8, pos.y + 4, pos.z + 10), pos, 1.8);
  }

  focusRelay(relayVisualPos) {
    const pos = relayVisualPos || new THREE.Vector3(50, 25, 45);
    this.transitionTo(new THREE.Vector3(pos.x + 7, pos.y + 4, pos.z + 9), pos, 1.6);
  }
}
