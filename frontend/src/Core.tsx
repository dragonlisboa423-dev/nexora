import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { SalyState } from "./api";

const vertex = `varying vec3 p; uniform float t; uniform float energy;
void main(){p=position; float wave=sin(position.y*9.+t)*cos(position.x*7.-t*.7)*.025;
vec3 v=position+normal*wave*(1.+energy*4.);gl_Position=projectionMatrix*modelViewMatrix*vec4(v,1.);}`;
const fragment = `varying vec3 p;uniform float t;uniform float energy;
void main(){float f=pow(abs(sin(p.y*18.+sin(p.x*8.+t)*1.5+t*.4)),14.);
float edge=pow(1.-abs(p.z),2.);vec3 c=mix(vec3(.02,.22,.29),vec3(.2,.95,.87),f*.7+edge*.4);
gl_FragColor=vec4(c*(.65+energy*.8),.48+f*.38);}`;
function Organic({
  state,
  level,
  quality,
  reduced,
  pulse,
}: {
  state: SalyState;
  level: React.MutableRefObject<number>;
  quality: string;
  reduced: boolean;
  pulse: number;
}) {
  const group = useRef<THREE.Group>(null!);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { t: { value: 0 }, energy: { value: 0 } },
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
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const energy =
      state === "listening"
        ? level.current
        : state === "speaking"
          ? 0.3 + Math.abs(Math.sin(t * 5)) * 0.3
          : state === "thinking"
            ? 0.25
            : state === "responding"
              ? 0.2
              : 0.02;
    material.uniforms.energy.value = THREE.MathUtils.lerp(
      material.uniforms.energy.value,
      energy,
      0.13,
    );
    material.uniforms.t.value = reduced ? 0 : t;
    if (group.current) {
      group.current.rotation.y = reduced ? 0 : t * 0.08;
      const boost = pulse
        ? Math.max(0, 1 - (performance.now() - pulse) / 1100) * 0.1
        : 0;
      group.current.scale.setScalar(1 + energy * 0.06 + boost);
    }
  });
  return (
    <group ref={group}>
      <mesh material={material}>
        <sphereGeometry
          args={[1, quality === "low" ? 32 : 72, quality === "low" ? 24 : 64]}
        />
      </mesh>
      <mesh rotation={[0.4, 0, 0.5]}>
        <icosahedronGeometry args={[0.81, 2]} />
        <meshBasicMaterial
          color="#58cfce"
          wireframe
          transparent
          opacity={0.13}
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
          <meshBasicMaterial color="#67dacc" transparent opacity={0.25} />
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
class Boundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
export function Core(props: {
  state: SalyState;
  level: React.MutableRefObject<number>;
  quality: string;
  pulse: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let frame = 0;
    function update() {
      container.current?.style.setProperty(
        "--audio-energy",
        String(props.state === "listening" ? props.level.current : 0),
      );
      frame = requestAnimationFrame(update);
    }
    update();
    return () => cancelAnimationFrame(frame);
  }, [props.state]);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const flat = (
    <div className={`flat-core ${props.state}`} aria-hidden="true">
      <i />
      <i />
      <i />
      <b />
    </div>
  );
  const webgl = useMemo(() => {
    try {
      const c = document.createElement("canvas");
      return !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch {
      return false;
    }
  }, []);
  return (
    <div
      ref={container}
      className={`core ${props.state}`}
      role="img"
      aria-label={`Núcleo Saly: ${props.state}`}
    >
      {props.quality === "2d" || !webgl ? (
        flat
      ) : (
        <Boundary fallback={flat}>
          <Suspense fallback={flat}>
            <Canvas
              camera={{ position: [0, 0, 3.8], fov: 42 }}
              dpr={props.quality === "high" ? [1, 1.8] : [1, 1.2]}
              gl={{ alpha: true, antialias: props.quality !== "low" }}
            >
              <Organic {...props} reduced={reduced} />
            </Canvas>
          </Suspense>
        </Boundary>
      )}
      {props.pulse > 0 && <div key={props.pulse} className="response-pulse" />}
      {props.state === "speaking" && (
        <div className="speech-waves">
          <i />
          <i />
          <i />
        </div>
      )}
      <div className="core-orbit" />
      <div className="core-caption">
        NÚCLEO SALY <span>01 / INTERFACE COGNITIVA</span>
      </div>
    </div>
  );
}
