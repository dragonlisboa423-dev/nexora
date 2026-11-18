import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { SalyState } from "./api";
import type { CoreProps as Props } from "./Core";
import { botanicalGeometry } from "./botanical_geometry";
// The original liquid deformation/clock/RMS engine evolves into anatomical surfaces.
const vertex = `varying vec3 p;varying vec3 n;varying vec3 view;varying vec2 tex;uniform float t;uniform float energy;
float fluid(vec3 q){return sin(q.x*2.8+t*.38)*cos(q.y*3.4-t*.29)*sin(q.z*2.6+t*.23)+.45*sin(q.y*5.+q.x*3.-t*.42);}
void main(){float f=fluid(position);vec3 v=position+normal*f*(.018+energy*.028);v.x+=sin(position.y*2.+t*.7)*.014;p=v;tex=uv;n=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(v,1.);view=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}`;
const fragment = `varying vec3 p;varying vec3 n;varying vec3 view;varying vec2 tex;uniform float t;uniform float energy;uniform float activity;uniform float stress;uniform float vascular;uniform float inner;
void main(){float rim=pow(1.-abs(dot(normalize(n),view)),2.);vec3 N=normalize(n)*(gl_FrontFacing?1.:-1.);vec3 L=normalize(vec3(-.5,.8,1.));float light=.28+.72*max(0.,dot(N,L));float sheen=pow(max(0.,dot(reflect(-L,N),view)),18.);float cells=.5+.5*sin(p.y*21.+sin(p.x*19.)+sin(p.z*16.));float flow=pow(.5+.5*sin(tex.x*9.-t*3.),7.)*activity;
vec3 deep=vec3(.075,.19,.09);vec3 tissue=vec3(.37,.54,.21);vec3 glow=vec3(.70,.84,.38);vec3 col=mix(deep,tissue,light*.62+rim*.25);col+=vec3(.28,.42,.12)*cells*.06;col+=glow*(rim*.19+energy*.13+inner*.20+sheen*.22);col=mix(col,vec3(.39,.55,.19)+glow*(flow*.75+energy*.3),vascular);col=mix(col,vec3(.48,.36,.17),stress*.25);gl_FragColor=vec4(col,vascular>.5?.80:.91);}`;
const working = new Set<SalyState>([
  "thinking",
  "searching",
  "executing",
  "executing_tool",
  "reading_document",
  "transcribing",
  "synthesizing",
]);

function Organic({
  state,
  level,
  quality,
  reduced,
  pulse,
  speechSignal,
  element,
}: {
  reduced: boolean;
  element: React.RefObject<HTMLDivElement | null>;
} & Props) {
  const group = useRef<THREE.Group>(null!),
    leaves = useRef<(THREE.Group | null)[]>([]),
    metrics = useRef({ elapsed: 0, frames: 0, last: 0 });
  const low = quality !== "high",
    anatomy = useMemo(() => botanicalGeometry(low), [low]);
  const materials = useMemo(
    () =>
      [0, 1, 2].map(
        (i) =>
          new THREE.ShaderMaterial({
            vertexShader: vertex,
            fragmentShader: fragment,
            side: THREE.DoubleSide,
            transparent: true,
            forceSinglePass: true,
            depthWrite: i !== 1,
            uniforms: {
              t: { value: 0 },
              energy: { value: 0 },
              activity: { value: 0 },
              stress: { value: 0 },
              vascular: { value: i === 1 ? 1 : 0 },
              inner: { value: i === 2 ? 1 : 0 },
            },
          }),
      ),
    [],
  );
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    invalidate();
  }, [state, reduced, quality, invalidate]);
  useEffect(
    () => () => {
      Object.values(anatomy).forEach((g) => g.dispose());
    },
    [anatomy],
  );
  useEffect(() => () => materials.forEach((m) => m.dispose()), [materials]);
  useFrame(({ clock, gl }, delta) => {
    const time = reduced
      ? 0
      : clock.getElapsedTime() * (state === "offline" ? 0.15 : 1);
    const signal =
      state === "listening" || (state === "speaking" && speechSignal?.current)
        ? Math.max(0, Math.min(1, level.current))
        : 0;
    if (element.current)
      element.current.style.setProperty("--audio-energy", String(signal));
    const activity = working.has(state)
      ? 0.65
      : state === "responding"
        ? 0.4
        : 0;
    const energy = signal || (state === "speaking" ? 0.07 : activity * 0.22);
    const smoothing = 1 - Math.exp(-Math.min(delta, 0.1) * 6);
    for (const m of materials) {
      m.uniforms.t.value = time;
      m.uniforms.energy.value = THREE.MathUtils.lerp(
        m.uniforms.energy.value,
        energy,
        smoothing,
      );
      m.uniforms.activity.value = activity;
      m.uniforms.stress.value = state === "error" ? 1 : 0;
    }
    if (group.current) {
      group.current.rotation.y =
        0.55 + (reduced ? 0 : Math.sin(time * 0.21) * 0.09);
      group.current.rotation.z = reduced
        ? -0.04
        : -0.04 + Math.sin(time * 0.28) * 0.018;
      const beat = reduced
        ? 0
        : Math.exp(-Math.pow((Math.sin(time * 1.6) - 0.87) * 9, 2)) * 0.014 +
          Math.sin(time * 0.8) * 0.007;
      const confirmed =
        pulse && !reduced
          ? Math.max(0, 1 - (performance.now() - pulse) / 1000) * 0.018
          : 0;
      group.current.scale.setScalar(1 + beat + energy * 0.035 + confirmed);
    }
    leaves.current.forEach((leaf, i) => {
      if (leaf)
        leaf.rotation.x = reduced
          ? 0
          : Math.sin(time * 0.6 + i) * 0.015 + signal * 0.025;
    });
    metrics.current.elapsed += delta;
    metrics.current.frames++;
    if (clock.elapsedTime - metrics.current.last > 1 && element.current) {
      element.current.dataset.drawCalls = String(gl.info.render.calls);
      element.current.dataset.triangles = String(gl.info.render.triangles);
      element.current.dataset.frames = String(metrics.current.frames);
      element.current.dataset.frameMs = (
        (1000 * metrics.current.elapsed) /
        metrics.current.frames
      ).toFixed(2);
      metrics.current.last = clock.elapsedTime;
    }
  });
  const count = quality === "high" ? 5 : 3;
  return (
    <group ref={group} rotation={[0, 0.55, -0.04]}>
      <mesh
        geometry={anatomy.pod}
        material={materials[2]}
        onAfterRender={(renderer) => {
          renderer.domElement.dataset.salyRendered = "true";
        }}
      />
      {Array.from({ length: count }, (_, i) => (
        <group
          key={i}
          rotation={[
            0,
            (i * Math.PI * 2) / count + 0.35,
            Math.sin(i * 2.3) * 0.13,
          ]}
          scale={[0.82 + (i % 2) * 0.12, 0.85 + (i % 3) * 0.13, 1]}
        >
          <group
            ref={(node) => {
              leaves.current[i] = node;
            }}
          >
            <mesh geometry={anatomy.leaf} material={materials[0]} />
            <mesh geometry={anatomy.vessels} material={materials[1]} />
          </group>
        </group>
      ))}
      <mesh geometry={anatomy.roots} material={materials[1]} />
    </group>
  );
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
      camera={{ position: [0, -0.05, 4.6], fov: 40 }}
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
