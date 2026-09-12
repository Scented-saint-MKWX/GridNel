"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DensityPoint } from "@/types/analytics";

export function DensityChart({ data }: { data: DensityPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
        <XAxis dataKey="camera_id" stroke="rgba(255,255,255,0.4)" fontSize={12} />
        <YAxis stroke="rgba(255,255,255,0.4)" fontSize={12} />
        <Tooltip
          contentStyle={{ background: "#10151d", border: "1px solid rgba(255,255,255,0.1)" }}
        />
        <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
