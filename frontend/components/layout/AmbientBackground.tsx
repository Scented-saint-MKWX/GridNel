"use client";

import { motion } from "motion/react";

// Shared ambient depth treatment — near-black base + several independently
// drifting cyan/amber/violet blobs at different speeds, sizes and opacities,
// plus grain. Used behind /login and the protected shell so neither reads as
// a flat bg-neutral-950 fill or a single static glow. See CLAUDE.md "Design
// bar" §1 (background depth) and §5 (motion must be visible) — a single blob
// doesn't read as alive, several moving at different rates does.
export function AmbientBackground({ variant = "default" }: { variant?: "default" | "login" }) {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-surface">
      <motion.div
        className="absolute -left-1/4 top-[-20%] size-[70vmax] rounded-full bg-analyst/[0.16] blur-[110px]"
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-1/4 bottom-[-20%] size-[65vmax] rounded-full bg-tracker/[0.13] blur-[110px]"
        animate={{ x: [0, -30, 0], y: [0, -25, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute right-[5%] top-[5%] size-[38vmax] rounded-full bg-healed/[0.08] blur-[100px]"
        animate={{ x: [0, -20, 10, 0], y: [0, 25, 10, 0] }}
        transition={{ duration: 34, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-1/4 left-[10%] size-[45vmax] rounded-full bg-analyst/[0.07] blur-[90px]"
        animate={{ x: [0, 35, -15, 0], y: [0, -20, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      {variant === "login" && (
        <motion.div
          className="absolute left-1/2 top-1/2 size-[40vmax] -translate-x-1/2 -translate-y-1/2 rounded-full bg-analyst/[0.1] blur-[90px]"
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      <div
        className="absolute inset-0 opacity-[0.03] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}
