"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Segment } from "@/types/analytics";

// Redriven from the real GET /analytics/segments (Nawfal, 2026-09-13,
// TEAM.md §4) — richer than the old corridor-speeds shape (per-edge node
// speed only). Renders average_speed_kmh per camera-pair segment; congestion
// still shown via the map layer's color coding (SegmentsLayer), not
// duplicated here as a redundant color dimension on the same bar.
export function CorridorSpeedChart({ data }: { data: Segment[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="from_camera"
          stroke="rgba(255,255,255,0.35)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value, i) => `${value}→${data[i]?.to_camera ?? ""}`}
        />
        <YAxis stroke="rgba(255,255,255,0.35)" fontSize={12} tickLine={false} axisLine={false} />
        <Tooltip
          cursor={{ fill: "rgba(217, 126, 44,0.06)" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "var(--foreground)" }}
          formatter={(value: number, name, item) => [
            `${value} km/h · ${item.payload.average_travel_time_sec}s avg`,
            "avg speed",
          ]}
        />
        <Bar dataKey="average_speed_kmh" fill="var(--tracker)" radius={[4, 4, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
