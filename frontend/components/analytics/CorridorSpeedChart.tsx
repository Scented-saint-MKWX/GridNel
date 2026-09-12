"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CorridorSpeed } from "@/types/analytics";

export function CorridorSpeedChart({ data }: { data: CorridorSpeed[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
        <XAxis
          dataKey="from_node"
          stroke="rgba(255,255,255,0.4)"
          fontSize={12}
          tickFormatter={(value, i) => `${value}→${data[i]?.to_node ?? ""}`}
        />
        <YAxis stroke="rgba(255,255,255,0.4)" fontSize={12} />
        <Tooltip
          contentStyle={{ background: "#10151d", border: "1px solid rgba(255,255,255,0.1)" }}
        />
        <Bar dataKey="avg_speed_kmh" fill="#f59e0b" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
