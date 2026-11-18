import {
  Component,
  Suspense,
  lazy,
  useEffect,
  useId,
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
};
const BotanicalCanvas = lazy(() => import("./BotanicalCanvas"));
function BotanicalFlat({ state }: { state: SalyState }) {
  const id = useId().replace(/:/g, "");
  return (
    <div className={`flat-core botanical-flat ${state}`} aria-hidden="true">
      <svg viewBox="0 0 380 440">
        <defs>
          <radialGradient id={`tissue-${id}`} cx="35%" cy="32%" r="80%">
            <stop stopColor="#adc66c" />
            <stop offset=".42" stopColor="#486a34" />
            <stop offset="1" stopColor="#182e1e" />
          </radialGradient>
          <linearGradient id={`vein-${id}`} x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#d4e59c" stopOpacity=".75" />
            <stop offset="1" stopColor="#63864c" stopOpacity=".25" />
          </linearGradient>
        </defs>
        <g
          className="botanical-tissue"
          fill={`url(#tissue-${id})`}
          stroke="#8dab6833"
        >
          <path d="M190 331C95 303 91 231 119 172C143 118 161 93 170 55C203 107 221 133 245 177C286 253 263 312 190 331Z" />
          <path d="M181 328C99 275 130 195 151 159C175 119 182 85 197 47C244 120 271 179 258 237C248 284 219 309 181 328Z" />
          <path d="M182 326C132 275 153 217 182 170C203 132 210 97 214 75C254 171 237 255 182 326Z" />
          <path d="M183 325C94 275 105 200 115 154C133 207 154 217 168 244C185 273 188 303 183 325Z" />
        </g>
        <g fill="none" stroke={`url(#vein-${id})`} strokeLinecap="round">
          <path
            strokeWidth="2"
            d="M183 329Q165 231 196 77M181 327Q120 255 121 175M190 325Q242 246 226 151"
          />
          <path d="M177 273Q143 254 133 222M177 240Q161 219 157 191M180 209Q206 185 211 159M183 179Q171 167 171 148M229 226Q246 207 242 190M219 266Q205 249 203 233" />
          <path
            className="botanical-root"
            strokeWidth="2"
            d="M181 325Q174 356 155 376T135 410M188 329Q204 354 196 374T209 415M186 333Q180 374 168 398M197 356Q220 364 234 391M158 374Q142 376 130 391"
          />
        </g>
      </svg>
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
      data-core-renderer={flat ? "vector" : "webgl"}
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
