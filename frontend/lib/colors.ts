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
