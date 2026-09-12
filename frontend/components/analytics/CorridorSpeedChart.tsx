"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CorridorSpeed } from "@/types/analytics";

export function CorridorSpeedChart({ data }: { data: CorridorSpeed[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="from_node"
          stroke="rgba(255,255,255,0.35)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value, i) => `${value}→${data[i]?.to_node ?? ""}`}
        />
        <YAxis stroke="rgba(255,255,255,0.35)" fontSize={12} tickLine={false} axisLine={false} />
        <Tooltip
          cursor={{ fill: "rgba(245,158,11,0.06)" }}
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "var(--foreground)" }}
        />
        <Bar dataKey="avg_speed_kmh" fill="var(--tracker)" radius={[4, 4, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
