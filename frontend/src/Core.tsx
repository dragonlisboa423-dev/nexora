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

const vertex = `varying vec3 p; varying vec3 vNormal; varying vec3 vView; uniform float t; uniform float energy;
float fluid(vec3 q){return sin(q.x*2.8+t*.38)*cos(q.y*3.4-t*.29)*sin(q.z*2.6+t*.23)+.45*sin(q.y*5.+q.x*3.-t*.42);}
void main(){float displacement=fluid(position)*(.12+energy*.09);vec3 v=position*(1.+displacement);p=v;vNormal=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(v,1.);vView=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}`;
const fragment = `varying vec3 p;varying vec3 vNormal;varying vec3 vView;uniform float t;uniform float energy;
void main(){float fresnel=pow(1.-abs(dot(normalize(vNormal),vView)),2.2);float folds=sin(p.y*5.+sin(p.x*4.+t*.3)*1.3+sin(p.z*5.-t*.28));float vein=pow(.5+.5*sin(folds*3.+p.z*2.),5.);float caustic=pow(.5+.5*sin(p.x*5.+p.y*3.+sin(p.z*4.+t*.2)),12.);vec3 deep=vec3(.015,.12,.18);vec3 cyan=vec3(.12,.78,.78);vec3 light=vec3(.54,1.,.86);vec3 color=mix(deep,cyan,.2+vein*.48);color+=light*(fresnel*.75+caustic*.32)*(1.+energy*.6);gl_FragColor=vec4(color,.65+fresnel*.3);}`;
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
          : [
                "thinking",
                "searching",
                "executing_tool",
                "reading_document",
                "transcribing",
              ].includes(state)
            ? 0.25
            : state === "responding"
              ? 0.2
              : 0.02;
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
      const boost = pulse
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
