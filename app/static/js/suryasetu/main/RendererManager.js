/**
 * RendererManager — WebGL Renderer Lifecycle, Responsive Sizing, Tone Mapping & Context Safety
 */

export class RendererManager {
  constructor(container) {
    this.container = container;
    this.isContextLost = false;

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "default",
      preserveDrawingBuffer: true,
      alpha: false
    });

    this.renderer.setClearColor(0x060c14, 1.0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;

    const dom = this.renderer.domElement;
    dom.style.width = "100%";
    dom.style.height = "100%";
    dom.style.display = "block";
    dom.style.background = "#060c14";

    // WebGL Context Loss / Restoration Guards (mandatory per WebGL spec)
    dom.addEventListener("webglcontextlost", (e) => {
      e.preventDefault(); // Prevents browser from permanently killing context
      this.isContextLost = true;
      console.warn("[SURYASETU] WebGL context lost. Awaiting restoration...");
    }, false);

    dom.addEventListener("webglcontextrestored", () => {
      console.log("[SURYASETU] WebGL context restored successfully.");
      this.isContextLost = false;
      this.handleResize();
    }, false);

    this.container.appendChild(dom);
    this.handleResize();
  }

  handleResize() {
    let width = this.container.clientWidth;
    let height = this.container.clientHeight;

    if (!width || !height) {
      const parent = document.getElementById("tab-suryasetu");
      if (parent) {
        width = parent.clientWidth || window.innerWidth;
        height = window.innerHeight - 72;
      }
    }

    width = Math.max(width || window.innerWidth, 320);
    height = Math.max(height || (window.innerHeight - 72), 320);

    this.renderer.setSize(width, height, false); // false preserves CSS 100% bounds
    return { width, height, aspect: width / height };
  }

  render(scene, camera) {
    if (this.isContextLost) return;
    this.renderer.render(scene, camera);
  }

  getDomElement() {
    return this.renderer.domElement;
  }
}
