/**
 * Angle Calculations & Arc Geometry
 * 
 * STRICT REQUIREMENT:
 * The angle must be mathematically calculated from vectors.
 * Do NOT hard-code visual arcs.
 * The arc should update dynamically if the geometry changes.
 */

export class AngleCalculator {
  /**
   * Calculate angle in degrees between vector (A - Vertex) and vector (B - Vertex)
   * @param {{x: number, y: number, z: number}} a 
   * @param {{x: number, y: number, z: number}} vertex 
   * @param {{x: number, y: number, z: number}} b 
   * @returns {{radians: number, degrees: number, formatted: string}}
   */
  calculateAngle(a, vertex, b) {
    const u = {
      x: a.x - vertex.x,
      y: a.y - vertex.y,
      z: a.z - vertex.z
    };
    const v = {
      x: b.x - vertex.x,
      y: b.y - vertex.y,
      z: b.z - vertex.z
    };

    const magU = Math.sqrt(u.x * u.x + u.y * u.y + u.z * u.z);
    const magV = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);

    if (magU === 0 || magV === 0) {
      return { radians: 0, degrees: 0, formatted: "0.0°" };
    }

    const dot = u.x * v.x + u.y * v.y + u.z * v.z;
    // Clamp dot product to [-1, 1] to prevent NaN from floating point precision
    const cosTheta = Math.max(-1.0, Math.min(1.0, dot / (magU * magV)));
    const radians = Math.acos(cosTheta);
    const degrees = (radians * 180) / Math.PI;

    return {
      radians,
      degrees,
      formatted: `${degrees.toFixed(1)}°`
    };
  }

  /**
   * Generate points along a 3D arc between vector (A - Vertex) and (B - Vertex)
   * @param {{x: number, y: number, z: number}} a 
   * @param {{x: number, y: number, z: number}} vertex 
   * @param {{x: number, y: number, z: number}} b 
   * @param {number} arcRadius 
   * @param {number} segments 
   * @returns {Array<{x: number, y: number, z: number}>}
   */
  generateArcPoints(a, vertex, b, arcRadius = 10, segments = 32) {
    const u = {
      x: a.x - vertex.x,
      y: a.y - vertex.y,
      z: a.z - vertex.z
    };
    const v = {
      x: b.x - vertex.x,
      y: b.y - vertex.y,
      z: b.z - vertex.z
    };

    const magU = Math.sqrt(u.x * u.x + u.y * u.y + u.z * u.z);
    const magV = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);

    if (magU === 0 || magV === 0) return [];

    // Unit vectors
    const uHat = { x: u.x / magU, y: u.y / magU, z: u.z / magU };
    const vHat = { x: v.x / magV, y: v.y / magV, z: v.z / magV };

    // Normal vector to the plane of u and v: n = uHat x vHat
    let nx = uHat.y * vHat.z - uHat.z * vHat.y;
    let ny = uHat.z * vHat.x - uHat.x * vHat.z;
    let nz = uHat.x * vHat.y - uHat.y * vHat.x;
    let magN = Math.sqrt(nx * nx + ny * ny + nz * nz);

    if (magN === 0) {
      // Vectors are collinear; pick an arbitrary perpendicular vector
      nx = 0; ny = 1; nz = 0;
      magN = 1;
    }

    const nHat = { x: nx / magN, y: ny / magN, z: nz / magN };

    // Orthogonal vector in the plane: w = nHat x uHat
    const wHat = {
      x: nHat.y * uHat.z - nHat.z * uHat.y,
      y: nHat.z * uHat.x - nHat.x * uHat.z,
      z: nHat.x * uHat.y - nHat.y * uHat.x
    };

    const totalAngle = Math.acos(Math.max(-1.0, Math.min(1.0, uHat.x * vHat.x + uHat.y * vHat.y + uHat.z * vHat.z)));
    const points = [];

    for (let i = 0; i <= segments; i++) {
      const phi = (totalAngle * i) / segments;
      const cosPhi = Math.cos(phi);
      const sinPhi = Math.sin(phi);

      points.push({
        x: vertex.x + arcRadius * (cosPhi * uHat.x + sinPhi * wHat.x),
        y: vertex.y + arcRadius * (cosPhi * uHat.y + sinPhi * wHat.y),
        z: vertex.z + arcRadius * (cosPhi * uHat.z + sinPhi * wHat.z)
      });
    }

    return points;
  }
}
