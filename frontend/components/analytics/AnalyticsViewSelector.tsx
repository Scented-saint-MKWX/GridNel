"use client";

import { useId } from "react";
import { BarChart3, Flame, Gauge } from "lucide-react";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

// PS vocabulary, exact: Traffic Density / Heatmap / Corridor Speeds — see
// TEAM.md §8 (P2 spec) and CLAUDE.md. Restyled from Watermelon's select-1
// block (ui.watermelon.sh) onto the theme's NativeSelect primitive, per
// CLAUDE.md "restyle its tokens to the role-accent system."
export type AnalyticsView = "density" | "heatmap" | "corridor-speeds";

const VIEWS: { value: AnalyticsView; label: string; icon: typeof BarChart3 }[] = [
  { value: "density", label: "Traffic Density", icon: BarChart3 },
  { value: "heatmap", label: "Heatmap", icon: Flame },
  { value: "corridor-speeds", label: "Corridor Speeds", icon: Gauge },
];

export function AnalyticsViewSelector({
  value,
  onChange,
}: {
  value: AnalyticsView;
  onChange: (view: AnalyticsView) => void;
}) {
  const id = useId();
  const active = VIEWS.find((v) => v.value === value) ?? VIEWS[0]!;
  const Icon = active.icon;

  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={id} className="sr-only">
        Analytics view
      </Label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-analyst" />
        <NativeSelect
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value as AnalyticsView)}
          className="glass min-w-56 rounded-xl border-white/10 pl-8 shadow-[0_0_20px_-8px_rgba(56,189,248,0.3)] transition-shadow hover:shadow-[0_0_24px_-6px_rgba(56,189,248,0.4)]"
        >
          {VIEWS.map((v) => (
            <option key={v.value} value={v.value}>
              {v.label}
            </option>
          ))}
        </NativeSelect>
      </div>
    </div>
  );
}
