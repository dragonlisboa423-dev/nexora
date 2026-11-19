import { useEffect, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import {
  Vector2,
  CustomBlending,
  OneFactor,
  ZeroFactor,
  AddEquation,
} from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
function Pipeline({
  element,
}: {
  element: React.RefObject<HTMLDivElement | null>;
}) {
  const { gl, scene, camera, size } = useThree();
  const pipeline = useMemo(() => {
    const composer = new EffectComposer(gl);
    const render = new RenderPass(scene, camera);
    const bloom = new UnrealBloomPass(new Vector2(1, 1), 0.22, 0.35, 0.65);
    // Add RGB light while preserving the scene alpha; otherwise additive bloom
    // writes alpha=1 across the full canvas and produces an opaque rectangle.
    Object.assign(bloom.blendMaterial, {
      blending: CustomBlending,
      blendEquation: AddEquation,
      blendSrc: OneFactor,
      blendDst: OneFactor,
      blendEquationAlpha: AddEquation,
      blendSrcAlpha: ZeroFactor,
      blendDstAlpha: OneFactor,
    });
    const alpha = new ShaderPass({
      uniforms: { tDiffuse: { value: null } },
      vertexShader:
        "varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",
      fragmentShader:
        "uniform sampler2D tDiffuse;varying vec2 vUv;void main(){vec4 c=texture2D(tDiffuse,vUv);gl_FragColor=vec4(c.rgb,max(c.a,min(1.,max(c.r,max(c.g,c.b)))));}",
    });
    composer.addPass(render);
    composer.addPass(bloom);
    composer.addPass(alpha);
    return { composer, render, bloom, alpha };
  }, [gl, scene, camera]);
  useEffect(() => {
    pipeline.composer.setSize(size.width, size.height);
  }, [pipeline, size]);
  useEffect(() => {
    if (element.current) element.current.dataset.bloom = "enabled";
    return () => {
      pipeline.composer.dispose();
      pipeline.render.dispose();
      pipeline.bloom.dispose();
      pipeline.alpha.dispose();
      if (element.current) element.current.dataset.bloom = "disabled";
    };
  }, [pipeline, element]);
  useFrame((_, delta) => pipeline.composer.render(delta), 1);
  return null;
}
export function Bloom(props: {
  element: React.RefObject<HTMLDivElement | null>;
}) {
  const gl = useThree((s) => s.gl);
  return gl.extensions.has("EXT_color_buffer_float") ? (
    <Pipeline {...props} />
  ) : null;
}
