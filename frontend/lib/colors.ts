import type { CongestionLevel } from "@/types/analytics";

// Single JS-side source for semantic colors that need a raw hex value (Mapbox
// paint expressions, inline styles) rather than a CSS var — Mapbox GL layers
// cannot resolve `var(--congestion-high)` in paint properties. Values must
// stay byte-identical to app/globals.css's --congestion-*/--status-* tokens;
// there is intentionally only one other place these hexes appear (Phase 3,
// "one shared token set, not per-component color choices").
export const CONGESTION_COLORS: Record<CongestionLevel, string> = {
  HIGH: "#ef4444",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
};

export const STATUS_COLORS = {
  live: "#22c55e",
  warning: "#eab308",
} as const;

// Continuous green -> yellow -> orange -> red congestion ramp, keyed by a
// 0..1 "load" ratio (e.g. 1 - avg_speed/speed_limit, or vehicle_count over
// some local max) rather than the flat 3-bucket HIGH/MEDIUM/LOW match used
// elsewhere. Same four hues TomTom/Mapbox Traffic/ArcGIS use (already the
// house convention, DECISIONS.md #4) as anchor stops, interpolated between
// them via MapLibre's own ["interpolate"] expression — see
// SegmentsLayer.tsx for the consuming paint expression. Byte-identical
// anchor hexes to CONGESTION_COLORS.LOW/MEDIUM/HIGH plus one added
// "orange" stop between medium and high.
export const CONGESTION_GRADIENT_STOPS: [number, string][] = [
  [0, "#22c55e"], // low
  [0.45, "#eab308"], // medium
  [0.72, "#f97316"], // heavy (new intermediate stop)
  [1, "#ef4444"], // severe
];

// Routes (Busiest Routes view) rank scale — violet/blue, distinct from
// congestion and from OD's teal below. Mirrors --route-rank-* in
// globals.css; kept here too since Mapbox/MapLibre paint expressions can't
// resolve a CSS var() at runtime. Rank 1 is brightest/most saturated; the
// scale fades toward --route-rank-low as rank drops, so width+opacity+hue
// all reinforce "less busy" together instead of hue alone doing the work.
export const ROUTE_RANK_COLORS = {
  top: "#8b5cf6",
  mid: "#6d5bd0",
  low: "#4c4a7a",
} as const;

// OD Flow volume scale — teal/cyan, distinct from Routes' violet and from
// the analyst role-accent cyan (--analyst) used elsewhere as a UI role
// color, not a data-volume encoding. Mirrors --flow-high/--flow-low.
export const FLOW_VOLUME_COLORS = {
  high: "#2dd4bf",
  low: "#155e63",
} as const;
