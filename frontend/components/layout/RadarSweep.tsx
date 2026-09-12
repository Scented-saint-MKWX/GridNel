"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

// Shared "system online, standing by" placeholder for genuinely-no-data
// states (no alerts yet, no cameras, no search run) — see CLAUDE.md "Design
// bar" empty-state requirement. A slow rotating conic-gradient sweep behind a
// short caption; fits a surveillance product directly rather than reading as
// decoration. Never use this for "about to have content" — that's a skeleton
// shimmer instead.
export function RadarSweep({
  label,
  sublabel,
  size = 96,
  accent = "analyst",
  icon,
}: {
  label: string;
  sublabel?: string;
  size?: number;
  accent?: "analyst" | "tracker";
  icon?: ReactNode;
}) {
  const accentColor = accent === "tracker" ? "var(--tracker)" : "var(--analyst)";

  return (
    <div className="flex flex-col items-center justify-center gap-3 text-center">
      <div className="relative" style={{ width: size, height: size }}>
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `conic-gradient(from 0deg, transparent 0%, ${accentColor}33 15%, transparent 30%)`,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 3.5, repeat: Infinity, ease: "linear" }}
        />
        <div
          className="absolute inset-[10%] rounded-full border"
          style={{ borderColor: `${accentColor}22` }}
        />
        <div
          className="absolute inset-[30%] rounded-full border"
          style={{ borderColor: `${accentColor}33` }}
        />
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground/70">
          {icon}
        </div>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        {sublabel && <p className="mt-0.5 text-xs text-muted-foreground/60">{sublabel}</p>}
      </div>
    </div>
  );
}
