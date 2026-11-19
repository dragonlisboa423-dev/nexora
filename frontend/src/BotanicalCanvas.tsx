import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { SalyState } from "./api";
import type { CoreProps as Props } from "./Core";
// Restored selectively from f03426b:frontend/src/Core.tsx.
const vertex = `varying vec3 p; varying vec3 vNormal; varying vec3 vView; uniform float t; uniform float energy;
float fluid(vec3 q){return sin(q.x*2.8+t*.38)*cos(q.y*3.4-t*.29)*sin(q.z*2.6+t*.23)+.45*sin(q.y*5.+q.x*3.-t*.42);}
void main(){float displacement=fluid(position)*(.12+energy*.09);vec3 v=position*(1.+displacement);p=v;vNormal=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(v,1.);vView=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}`;
const fragment = `varying vec3 p;varying vec3 vNormal;varying vec3 vView;uniform float t;uniform float energy;uniform float stress;
void main(){float fresnel=pow(1.-abs(dot(normalize(vNormal),vView)),2.2);float folds=sin(p.y*5.+sin(p.x*4.+t*.3)*1.3+sin(p.z*5.-t*.28));float vein=pow(.5+.5*sin(folds*3.+p.z*2.),5.);float caustic=pow(.5+.5*sin(p.x*5.+p.y*3.+sin(p.z*4.+t*.2)),12.);vec3 deep=vec3(.015,.12,.09);vec3 cyan=vec3(.12,.68,.43);vec3 light=vec3(.64,1.,.72);vec3 color=mix(deep,cyan,.2+vein*.48);color+=light*(fresnel*.75+caustic*.32)*(1.+energy*.6);color=mix(color,vec3(.5,.39,.22),stress*.16);gl_FragColor=vec4(color,.65+fresnel*.3);}`;
function Organic({
  state,
  level,
  quality,
  reduced,
  pulse,
  speechSignal,
  element,
}: {
  element: React.RefObject<HTMLDivElement | null>;
  state: SalyState;
  level: React.MutableRefObject<number>;
  quality: string;
  reduced: boolean;
  pulse: number;
  speechSignal?: React.MutableRefObject<boolean>;
}) {
  const group = useRef<THREE.Group>(null!);
  const errorStart = useRef(0);
  useEffect(() => {
    if (state === "error") errorStart.current = performance.now();
  }, [state]);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          t: { value: 0 },
          energy: { value: 0 },
          stress: { value: 0 },
        },
        vertexShader: vertex,
        fragmentShader: fragment,
        transparent: true,
        wireframe: false,
      }),
    [],
  );
  const points = useMemo(() => {
    const count = quality === "low" ? 120 : 550;
    const a = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const theta = Math.PI * (3 - Math.sqrt(5)) * i;
      a.set(
        [Math.cos(theta) * r * 1.35, y * 1.35, Math.sin(theta) * r * 1.35],
        i * 3,
      );
    }
    return a;
  }, [quality]);
  const stats = useRef({ frames: 0, last: 0, total: 0 });
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    invalidate();
  }, [state, reduced, quality, invalidate]);
  useEffect(() => () => material.dispose(), [material]);
  useFrame(({ clock, gl }, delta) => {
    stats.current.frames++;
    stats.current.total += delta;
    if (element.current) {
      const signal =
        state === "listening" || (state === "speaking" && speechSignal?.current)
          ? level.current
          : 0;
      element.current.style.setProperty("--audio-energy", String(signal));
      if (clock.elapsedTime - stats.current.last > 1) {
        Object.assign(element.current.dataset, {
          frames: String(stats.current.frames),
          drawCalls: String(gl.info.render.calls),
          triangles: String(gl.info.render.triangles),
          frameMs: (
            (1000 * stats.current.total) /
            stats.current.frames
          ).toFixed(2),
        });
        stats.current.last = clock.elapsedTime;
      }
    }
    const t = clock.getElapsedTime();
    const energy =
      state === "listening"
        ? level.current
        : state === "speaking"
          ? speechSignal?.current
            ? level.current
            : 0.12
          : [
                "thinking",
                "executing",
                "synthesizing",
                "searching",
                "executing_tool",
                "reading_document",
                "transcribing",
              ].includes(state)
            ? 0.25
            : state === "responding"
              ? 0.2
              : 0.02;
    material.uniforms.stress.value =
      state === "error"
        ? reduced
          ? 1
          : Math.max(0, 1 - (performance.now() - errorStart.current) / 3500)
        : 0;
    material.uniforms.energy.value = THREE.MathUtils.lerp(
      material.uniforms.energy.value,
      energy,
      0.13,
    );
    material.uniforms.t.value = reduced
      ? 0
      : state === "offline"
        ? t * 0.08
        : t;
    if (group.current) {
      group.current.rotation.y = reduced ? 0 : t * 0.08;
      const boost =
        pulse && !reduced
          ? Math.max(0, 1 - (performance.now() - pulse) / 1100) * 0.1
          : 0;
      group.current.scale.setScalar(1 + energy * 0.06 + boost);
    }
  });
  return (
    <group ref={group}>
      <mesh
        material={material}
        onAfterRender={(renderer) => {
          renderer.domElement.dataset.salyRendered = "true";
        }}
      >
        <sphereGeometry
          args={[1, quality === "low" ? 32 : 72, quality === "low" ? 24 : 64]}
        />
      </mesh>
      <Fibres materialTime={material} quality={quality} />
      <mesh rotation={[0.4, 0, 0.5]}>
        <icosahedronGeometry args={[0.81, 2]} />
        <meshBasicMaterial
          color="#58cfce"
          wireframe
          transparent
          opacity={0.035}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.44, 24, 24]} />
        <meshBasicMaterial color="#87fff0" transparent opacity={0.14} />
      </mesh>
      {[0, 1, 2].map((i) => (
        <mesh
          key={i}
          rotation={[Math.PI / 2 + i * 0.3, 0.15 + i * 0.4, i * 0.5]}
        >
          <torusGeometry args={[1.12 + i * 0.09, 0.004, 6, 128]} />
          <meshBasicMaterial color="#67dacc" transparent opacity={0.07} />
        </mesh>
      ))}
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[points, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color="#8bffea"
          size={0.012}
          transparent
          opacity={0.5}
        />
      </points>
    </group>
  );
}

// Delicate branching fibres remain INSIDE the recovered fluid surface (radius < .9).
function Fibres({
  materialTime,
  quality,
}: {
  materialTime: THREE.ShaderMaterial;
  quality: string;
}) {
  const geometry = useMemo(() => {
    const pieces: THREE.BufferGeometry[] = [];
    const count = quality === "low" ? 4 : 7;
    for (let i = 0; i < count; i++) {
      const phase = i * 2.399;
      const point = (t: number, offset = 0) => {
        const y = -0.72 + 1.44 * t;
        const radius = Math.sqrt(1 - y * y) * (0.74 + offset);
        const angle = phase + t * 1.5;
        return new THREE.Vector3(
          Math.cos(angle) * radius,
          y,
          Math.sin(angle) * radius,
        );
      };
      pieces.push(
        new THREE.TubeGeometry(
          new THREE.CatmullRomCurve3(
            Array.from({ length: 16 }, (_, j) => point(j / 15)),
          ),
          24,
          0.004,
          4,
          false,
        ),
      );
      for (const t of [0.3, 0.57])
        pieces.push(
          new THREE.TubeGeometry(
            new THREE.CatmullRomCurve3([
              point(t),
              point(t + 0.08, -0.09),
              point(t + 0.19, -0.2),
            ]),
            9,
            0.0025,
            3,
            false,
          ),
        );
    }
    const merged = mergeGeometries(pieces)!;
    pieces.forEach((g) => g.dispose());
    return merged;
  }, [quality]);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: vertex,
        fragmentShader: `varying vec3 p;uniform float t;uniform float energy;void main(){float flow=pow(.5+.5*sin(p.y*7.-t*1.2),5.);gl_FragColor=vec4(.44,.88,.54,.12+flow*(.08+energy*.25));}`,
        uniforms: materialTime.uniforms,
        transparent: true,
        depthWrite: false,
      }),
    [materialTime],
  );
  useEffect(
    () => () => {
      geometry.dispose();
      material.dispose();
    },
    [geometry, material],
  );
  return <mesh geometry={geometry} material={material} renderOrder={-1} />;
}
export default function BotanicalCanvas(
  props: Props & {
    reduced: boolean;
    visible: boolean;
    element: React.RefObject<HTMLDivElement | null>;
    onFailure: () => void;
  },
) {
  const { visible, reduced, quality } = props;
  return (
    <Canvas
      frameloop={!visible ? "never" : reduced ? "demand" : "always"}
      camera={{ position: [0, 0, 3.8], fov: 42 }}
      dpr={quality === "high" ? [1, 1.7] : quality === "low" ? 1 : [1, 1.25]}
      gl={{
        alpha: true,
        antialias: quality !== "low",
        powerPreference: quality === "low" ? "low-power" : "default",
      }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener(
          "webglcontextlost",
          (event) => {
            event.preventDefault();
            props.onFailure();
          },
          { once: true },
        );
      }}
    >
      <Organic {...props} />
    </Canvas>
  );
}
