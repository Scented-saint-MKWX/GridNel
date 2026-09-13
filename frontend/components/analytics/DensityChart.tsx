"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HeatmapPoint } from "@/types/analytics";

// Re-sourced from /analytics/heatmap's per-camera vehicle_count (Nawfal,
// 2026-09-13, TEAM.md §4) — there's no more standalone per-camera density
// endpoint (see DECISIONS.md #6), so this reuses the heatmap points'
// counts as the secondary per-camera breakdown under the new
// /analytics/summary KPI row on the "Traffic Density" view. Same component,
// just re-sourced — not rebuilt.
export function DensityChart({ data }: { data: HeatmapPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="camera_id"
          stroke="rgba(255,255,255,0.35)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis stroke="rgba(255,255,255,0.35)" fontSize={12} tickLine={false} axisLine={false} />
        <Tooltip
          cursor={{ fill: "rgba(56,189,248,0.06)" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "var(--foreground)" }}
        />
        <Bar dataKey="vehicle_count" fill="var(--analyst)" radius={[4, 4, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
