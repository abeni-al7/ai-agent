import { useMemo } from "react";
import type { Tier } from "./api";

/**
 * Guilloche seal: interlaced hypotrochoid rosettes, the linework of certificates and banknotes.
 * Printed once when Wekil completes a review; lobe count and line density encode the risk tier.
 */
const TIER = {
  low: { lobes: 7, rings: 3, ink: "var(--clear)" },
  medium: { lobes: 11, rings: 4, ink: "var(--hold)" },
  high: { lobes: 17, rings: 5, ink: "var(--block)" },
  prohibited: { lobes: 23, rings: 6, ink: "var(--block)" },
} as const;

function rosette(R: number, lobes: number, d: number, phase: number, steps = 720) {
  const r = R / lobes;
  const k = (R - r) / r;
  let path = "";
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * Math.PI * 2;
    const x = (R - r) * Math.cos(t + phase) + d * Math.cos(k * t + phase);
    const y = (R - r) * Math.sin(t + phase) - d * Math.sin(k * t + phase);
    path += `${i ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }
  return path;
}

export function Seal({ tier, size = 112, stamp, animate = true }: {
  tier: Tier; size?: number; stamp?: { outcome: string; date: string } | null; animate?: boolean;
}) {
  const spec = TIER[tier ?? "low"];
  const paths = useMemo(
    () => Array.from({ length: spec.rings }, (_, i) => rosette(44 - i * 5, spec.lobes, 14 + i * 2.5, (i * Math.PI) / spec.lobes)),
    [spec],
  );
  const label = tier ? `${tier} risk seal${stamp ? `, ${stamp.outcome}` : ""}` : "Not yet reviewed";
  return (
    <figure className={`seal ${animate ? "seal--print" : ""}`} style={{ width: size, height: size, color: spec.ink }} aria-label={label} role="img">
      <svg viewBox="-50 -50 100 100" aria-hidden="true">
        <circle r="48" className="seal__rim" />
        <circle r="46.5" className="seal__rim seal__rim--fine" />
        {paths.map((d, i) => (
          <path key={i} d={d} pathLength={1} className="seal__line" style={{ animationDelay: `${i * 140}ms` }} />
        ))}
      </svg>
      {stamp && (
        <figcaption className={`stamp stamp--${stamp.outcome}`}>
          <strong>{stamp.outcome}</strong>
          <span>{stamp.date}</span>
        </figcaption>
      )}
    </figure>
  );
}

/** Small mark for Wekil's own actions in timelines. */
export function WekilMark() {
  const d = useMemo(() => rosette(9, 5, 3.2, 0, 240), []);
  return (
    <svg className="mark mark--wekil" viewBox="-10 -10 20 20" aria-label="Wekil" role="img">
      <path d={d} />
    </svg>
  );
}

export function StampMark() {
  return (
    <svg className="mark mark--stamp" viewBox="-10 -10 20 20" aria-label="Analyst" role="img">
      <rect x="-8" y="-6" width="16" height="12" rx="2" transform="rotate(-8)" />
      <line x1="-5" y1="0" x2="5" y2="0" transform="rotate(-8)" />
    </svg>
  );
}
