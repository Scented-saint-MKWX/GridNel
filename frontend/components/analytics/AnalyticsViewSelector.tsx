"use client";

import { BarChart3, Flame, Gauge, GitBranch, FlaskConical } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// PS vocabulary, exact: Traffic Density / Heatmap / Corridor Speeds — see
// TEAM.md §8 (P2 spec) and CLAUDE.md. Built on Radix's Select (shadcn's real
// select.tsx) rather than a native <select> — a native popup renders with the
// OS's own UA styles (forced light bg/dark text on Windows/Chrome regardless
// of app theme) and can't be reliably restyled cross-browser. See DECISIONS.md
// #5 / CLAUDE.md master-prompt Fix 1.
//
// "od-flow" was confirmed in-scope 2026-09-13 (authorized by Wahid) and is
// now a real, first-class item alongside the three PS-vocabulary views —
// this deliberately deviates from TEAM.md/CLAUDE.md's "exact PS vocabulary"
// wording (see DECISIONS.md #4). "gis-preview" (Segments/Routes) remains an
// unconfirmed prototype, kept last and visually distinct so it's never
// mistaken for confirmed scope.
export type AnalyticsView = "density" | "heatmap" | "corridor-speeds" | "od-flow" | "gis-preview";

const VIEWS: { value: AnalyticsView; label: string; icon: typeof BarChart3 }[] = [
  { value: "density", label: "Traffic Density", icon: BarChart3 },
  { value: "heatmap", label: "Heatmap", icon: Flame },
  { value: "corridor-speeds", label: "Corridor Speeds", icon: Gauge },
  { value: "od-flow", label: "OD Flow", icon: GitBranch },
  { value: "gis-preview", label: "GIS Preview (prototype)", icon: FlaskConical },
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
