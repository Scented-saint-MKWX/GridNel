"use client";

import { Car, ArrowLeftRight, Gauge, Timer, TrafficCone } from "lucide-react";
import type { AnalyticsSummary } from "@/types/analytics";

// Primary content of the repurposed "Traffic Density" view (Nawfal,
// 2026-09-13, TEAM.md §4) — /analytics/summary has no per-camera shape
// anymore, so this KPI row is now the headline, with the per-camera bar
// chart (DensityChart, re-sourced from /analytics/heatmap) as a secondary
// breakdown underneath. Congested/total segments renders as a labeled
// horizontal bar rather than a bare number, per Phase 3's structural
// inspiration from the reference dashboard's weighted-scoring bars.
export function SummaryStats({ summary }: { summary: AnalyticsSummary }) {
  const congestedRatio =
    summary.total_segments > 0 ? summary.congested_segments / summary.total_segments : 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          icon={<Car className="size-4" />}
          label="Vehicles analyzed"
          value={summary.vehicles_analyzed.toLocaleString()}
        />
        <StatTile
          icon={<ArrowLeftRight className="size-4" />}
          label="Transitions"
          value={summary.transitions_analyzed.toLocaleString()}
        />
        <StatTile
          icon={<Gauge className="size-4" />}
          label="Avg / median speed"
          value={`${summary.average_speed_kmh.toFixed(1)} / ${summary.median_speed_kmh.toFixed(1)} km/h`}
        />
        <StatTile
          icon={<Timer className="size-4" />}
          label="Avg travel time"
          value={`${summary.average_travel_time_sec.toFixed(0)}s`}
        />
      </div>

      <div className="glass rounded-xl border-white/10 p-3">
        <div className="mb-2 flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <TrafficCone className="size-3.5 text-congestion-high" />
            Congested segments
          </span>
          <span className="data-mono text-foreground">
            {summary.congested_segments} / {summary.total_segments}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-congestion-high transition-[width] duration-700 ease-out"
            style={{ width: `${Math.round(congestedRatio * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="glass rounded-xl border-white/10 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="text-analyst">{icon}</span>
        {label}
      </div>
      <div className="data-mono mt-1.5 text-lg font-semibold text-foreground">{value}</div>
    </div>
  );
}
