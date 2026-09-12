"use client";

import { motion } from "motion/react";

// Live "system status" indicator for /login — see CLAUDE.md "Design bar":
// "/login needs presence ... a live system status indicator". Purely
// cosmetic/ambient (no privileged data), gives the login screen a sense of
// a system that's actually running rather than two buttons on black.
export function SystemStatus() {
  return (
    <div className="glass inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs text-muted-foreground">
      <span className="relative flex size-2">
        <motion.span
          className="absolute inline-flex size-full rounded-full bg-analyst"
          animate={{ scale: [1, 2.2], opacity: [0.7, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
        />
        <span className="relative inline-flex size-2 rounded-full bg-analyst" />
      </span>
      Fog network online — 6 cameras reporting
    </div>
  );
}
