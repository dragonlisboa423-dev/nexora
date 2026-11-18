import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

function surface(
  rows: number,
  columns: number,
  point: (u: number, v: number) => THREE.Vector3,
) {
  const positions: number[] = [],
    uv: number[] = [],
    indices: number[] = [];
  for (let y = 0; y <= rows; y++)
    for (let x = 0; x <= columns; x++) {
      const p = point(x / columns, y / rows);
      positions.push(p.x, p.y, p.z);
      uv.push(x / columns, y / rows);
    }
  for (let y = 0; y < rows; y++)
    for (let x = 0; x < columns; x++) {
      const a = y * (columns + 1) + x,
        b = a + columns + 1;
      indices.push(a, b, a + 1, b, b + 1, a + 1);
    }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}
export function leafPoint(t: number, s: number) {
  const bell = Math.pow(Math.sin(Math.PI * t), 0.78);
  return new THREE.Vector3(
    s * 0.44 * bell + 0.12 * t * t,
    -0.84 + 1.98 * t + 0.06 * s * s * bell,
    0.17 + 0.36 * Math.sin(Math.PI * t) - 0.12 * t + 0.15 * s * s * bell,
  );
}
function tube(points: THREE.Vector3[], radius: number, low: boolean) {
  return new THREE.TubeGeometry(
    new THREE.CatmullRomCurve3(points),
    low ? 9 : 17,
    radius,
    low ? 4 : 5,
    false,
  );
}
function combine(parts: THREE.BufferGeometry[]) {
  const merged = mergeGeometries(parts)!;
  parts.forEach((p) => p.dispose());
  return merged;
}
export function botanicalGeometry(low = false) {
  const leaf = surface(low ? 15 : 30, low ? 8 : 16, (u, v) =>
    leafPoint(v, 2 * u - 1),
  );
  const pod = surface(low ? 24 : 42, low ? 32 : 56, (u, v) => {
    const angle = u * Math.PI * 2,
      ring = Math.pow(Math.sin(Math.PI * v), 0.63);
    const radius =
      ring * (0.34 + 0.09 * (1 - v) + 0.045 * Math.sin(angle * 5 + v * 3.7));
    return new THREE.Vector3(
      Math.cos(angle) * radius + 0.08 * Math.sin(v * 3.5),
      -0.78 + 1.72 * v,
      Math.sin(angle) * radius,
    );
  });
  const vesselParts: THREE.BufferGeometry[] = [];
  vesselParts.push(
    tube(
      Array.from({ length: 12 }, (_, i) =>
        leafPoint(0.03 + (i * 0.93) / 11, 0).add(
          new THREE.Vector3(0, 0, 0.012),
        ),
      ),
      0.012,
      low,
    ),
  );
  const levels = low ? [0.27, 0.49, 0.7] : [0.22, 0.37, 0.52, 0.67, 0.8];
  for (const t of levels)
    for (const side of [-1, 1]) {
      const points = Array.from({ length: 6 }, (_, i) =>
        leafPoint(t + (0.13 * i) / 5, (side * 0.88 * i) / 5).add(
          new THREE.Vector3(0, 0, 0.012),
        ),
      );
      vesselParts.push(tube(points, 0.0055, low));
    }
  const rootParts: THREE.BufferGeometry[] = [];
  for (let i = 0; i < (low ? 3 : 5); i++) {
    const a = i * 2.4 + 0.3,
      dx = Math.cos(a),
      dz = Math.sin(a),
      length = 1.43 + (i % 2) * 0.15;
    rootParts.push(
      tube(
        [
          new THREE.Vector3(dx * 0.1, -0.68, dz * 0.1),
          new THREE.Vector3(dx * 0.16, -1.02, dz * 0.16),
          new THREE.Vector3(dx * 0.35, -1.27, dz * 0.28),
          new THREE.Vector3(dx * 0.38, -length, dz * 0.34),
        ],
        0.014 - (i % 2) * 0.003,
        low,
      ),
    );
    rootParts.push(
      tube(
        [
          new THREE.Vector3(dx * 0.28, -1.18, dz * 0.25),
          new THREE.Vector3(dx * 0.42 + 0.08, -1.32, dz * 0.3),
          new THREE.Vector3(dx * 0.48 + 0.11, -1.42, dz * 0.36),
        ],
        0.005,
        low,
      ),
    );
  }
  return {
    leaf,
    pod,
    vessels: combine(vesselParts),
    roots: combine(rootParts),
  };
}
