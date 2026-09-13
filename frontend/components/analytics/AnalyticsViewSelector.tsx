"use client";

import { BarChart3, Flame, Gauge, GitBranch, Waypoints, Route as RouteIcon } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Vocabulary has materially diverged from TEAM.md/CLAUDE.md's original
// "exact PS vocabulary" instruction (Traffic Density / Heatmap / Corridor
// Speeds) across three sessions now — Density is a summary KPI view,
// Corridor Speeds is segment-driven, OD/Segments/Routes are all real,
// first-class views. Deliberate, flagged, logged in DECISIONS.md #6 — not a
// silent drift. Built on Radix's Select (shadcn's real select.tsx) rather
// than a native <select> — see DECISIONS.md #5.
//
// Segments, OD, and Routes were all promoted out of prototype status
// 2026-09-13 once Nawfal's real /analytics/segments, /analytics/od, and
// /analytics/routes endpoints landed (TEAM.md §4, DECISIONS.md #6) — no more
// "gis-preview"/PrototypeBanner treatment; these are shipped features now.
export type AnalyticsView = "density" | "heatmap" | "corridor-speeds" | "od-flow" | "segments" | "routes";

const VIEWS: { value: AnalyticsView; label: string; icon: typeof BarChart3 }[] = [
  { value: "density", label: "Traffic Density", icon: BarChart3 },
  { value: "heatmap", label: "Heatmap", icon: Flame },
  { value: "corridor-speeds", label: "Corridor Speeds", icon: Gauge },
  { value: "od-flow", label: "OD Flow", icon: GitBranch },
  { value: "segments", label: "Segments", icon: Waypoints },
  { value: "routes", label: "Busiest Routes", icon: RouteIcon },
];

export function AnalyticsViewSelector({
  value,
  onChange,
}: {
  value: AnalyticsView;
  onChange: (view: AnalyticsView) => void;
}) {
  const active = VIEWS.find((v) => v.value === value) ?? VIEWS[0]!;
  const ActiveIcon = active.icon;

  return (
    <Select value={value} onValueChange={(v) => onChange(v as AnalyticsView)}>
      <SelectTrigger
        className="glass min-w-56 rounded-xl border-white/10 shadow-[0_0_20px_-8px_rgba(56,189,248,0.3)] transition-shadow hover:shadow-[0_0_24px_-6px_rgba(56,189,248,0.4)]"
        aria-label="Analytics view"
      >
        <ActiveIcon className="size-4 text-analyst" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {VIEWS.map((v) => {
          const Icon = v.icon;
          return (
            <SelectItem key={v.value} value={v.value}>
              <Icon className="size-4" />
              {v.label}
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
