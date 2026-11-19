import { readCoreMotion } from "./CoreMotion";
import {
  Component,
  Suspense,
  lazy,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { SalyState } from "./api";
import { stateLabels } from "./state_labels";
export type CoreProps = {
  state: SalyState;
  level: React.MutableRefObject<number>;
  quality: string;
  pulse: number;
  speechSignal?: React.MutableRefObject<boolean>;
  motion?: { intensity: number; speed: number };
};
const BotanicalCanvas = lazy(() => import("./BotanicalCanvas"));
function BotanicalFlat({ state }: { state: SalyState }) {
  return (
    <div
      className={`flat-core restored-fluid-flat ${state}`}
      aria-hidden="true"
    >
      <i />
      <i />
      <i />
      <b />
    </div>
  );
}
class Boundary extends Component<
  { children: ReactNode; fallback: ReactNode; onFailure: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onFailure();
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
export function Core(props: CoreProps) {
  const [failed, setFailed] = useState(false);
  const [motion, setMotion] = useState(readCoreMotion);
  useEffect(() => {
    const update = () => setMotion(readCoreMotion());
    window.addEventListener("saly-core-motion", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("saly-core-motion", update);
      window.removeEventListener("storage", update);
    };
  }, []);
  const container = useRef<HTMLDivElement>(null),
    [visible, setVisible] = useState(true),
    [reduced, setReduced] = useState(
      matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
    [small, setSmall] = useState(matchMedia("(max-width:760px)").matches);
  useEffect(() => {
    const motion = matchMedia("(prefers-reduced-motion: reduce)"),
      mobile = matchMedia("(max-width:760px)"),
      change = () => {
        setReduced(motion.matches);
        setSmall(mobile.matches);
      };
    motion.addEventListener("change", change);
    mobile.addEventListener("change", change);
    return () => {
      motion.removeEventListener("change", change);
      mobile.removeEventListener("change", change);
    };
  }, []);
  useEffect(() => {
    let intersecting = true;
    const refresh = () => setVisible(intersecting && !document.hidden);
    const observer = new IntersectionObserver((entries) => {
      intersecting = entries[0]?.isIntersecting ?? false;
      refresh();
    });
    if (container.current) observer.observe(container.current);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);
  const webgl = useMemo(() => {
    try {
      const canvas = document.createElement("canvas"),
        gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      const exists = !!gl;
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
      return exists;
    } catch {
      return false;
    }
  }, []);
  const quality =
    props.quality === "auto"
      ? small || navigator.hardwareConcurrency <= 4
        ? "low"
        : "balanced"
      : props.quality;
  const flat = quality === "2d" || !webgl || failed;
  useEffect(() => {
    let frame = 0;
    const active =
      props.state === "listening" ||
      (props.state === "speaking" && props.speechSignal?.current);
    if (!flat || !visible || reduced || !active) {
      container.current?.style.setProperty("--audio-energy", "0");
      return;
    }
    const update = () => {
      container.current?.style.setProperty(
        "--audio-energy",
        String(props.level.current),
      );
      frame = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(frame);
  }, [flat, visible, reduced, props.state]);
  const fallback = <BotanicalFlat state={props.state} />;
  return (
    <div
      ref={container}
      className={`core botanical-core ${props.state} ${!visible ? "dormant" : ""}`}
      data-core-renderer={flat ? "css-fallback" : "webgl"}
      data-core-quality={quality}
      data-core-active={visible ? "true" : "false"}
      data-motion={reduced ? "reduced" : "animated"}
      data-speech-signal={props.speechSignal?.current ? "pcm" : "events"}
      role="img"
      aria-label={`Coração vegetal da Saly: ${stateLabels[props.state]}`}
    >
      {flat ? (
        fallback
      ) : (
        <Boundary fallback={fallback} onFailure={() => setFailed(true)}>
          <Suspense fallback={fallback}>
            <BotanicalCanvas
              {...props}
              motion={motion}
              quality={quality}
              reduced={reduced}
              visible={visible}
              element={container}
              onFailure={() => setFailed(true)}
            />
          </Suspense>
        </Boundary>
      )}
    </div>
  );
}
