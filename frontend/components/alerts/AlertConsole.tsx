"use client";

import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useAlerts } from "@/hooks/useAlerts";

// Global blacklist-hit banner — mounted once in (protected)/layout.tsx so it's
// visible from any page, per FRONTEND_BLUEPRINT.md §5 ("must not be tucked away
// on a sub-page"). Camera-flash-on-map behavior wires in once CityMap exists
// (hour 3-12 per the blueprint's hour plan); this is the hour-0-3 stub.
//
// No-alerts is the common case with the backend unwired, so it gets its own
// deliberate "monitoring, no hits" state instead of rendering nothing — see
// CLAUDE.md "Design bar" empty-state requirement.
export function AlertConsole() {
  const { data: alerts, dataUpdatedAt } = useAlerts();
  const latest = alerts?.[alerts.length - 1];
  const [dismissedKey, setDismissedKey] = useState<string | null>(null);

  const latestKey = latest ? `${latest.type}-${latest.camera_id}-${latest.ts}` : null;
  const showBanner = latest && latestKey !== dismissedKey;

  return (
    <AnimatePresence mode="wait">
      {showBanner ? (
        <motion.div
          key={latestKey}
          role="alert"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="sticky top-14 z-40 flex items-center justify-center gap-2 border-b border-alert/40 bg-alert/15 px-4 py-2 text-sm text-alert shadow-[0_4px_40px_-8px_rgba(239,68,68,0.45)] backdrop-blur-xl"
        >
          <AlertTriangle className="size-4 shrink-0 animate-pulse" />
          <span className="data-mono">{latest!.type}</span>
          <span className="text-alert/70">·</span>
          <span className="data-mono">{latest!.camera_id}</span>
          <button
            type="button"
            onClick={() => setDismissedKey(latestKey)}
            className="ml-2 text-alert/60 transition-colors hover:text-alert"
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </motion.div>
      ) : (
        <motion.div
          key="standing-by"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
          className="sticky top-14 z-30 flex items-center justify-center gap-2 border-b border-white/5 bg-surface/40 px-4 py-1.5 text-xs text-muted-foreground/70 backdrop-blur-xl"
        >
          <span className="relative flex size-1.5">
            <motion.span
              className="absolute inline-flex size-full rounded-full bg-analyst"
              animate={{ scale: [1, 2.4], opacity: [0.6, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
            />
            <span className="relative inline-flex size-1.5 rounded-full bg-analyst" />
          </span>
          <ShieldCheck className="size-3.5 text-analyst/70" />
          Monitoring — no blacklist hits
          {dataUpdatedAt > 0 && <span className="text-muted-foreground/40">· polling every 10s</span>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
