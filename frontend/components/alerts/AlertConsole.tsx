"use client";

import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle } from "lucide-react";
import { useAlerts } from "@/hooks/useAlerts";

// Global blacklist-hit banner — mounted once in (protected)/layout.tsx so it's
// visible from any page, per FRONTEND_BLUEPRINT.md §5 ("must not be tucked away
// on a sub-page"). Camera-flash-on-map behavior wires in once CityMap exists
// (hour 3-12 per the blueprint's hour plan); this is the hour-0-3 stub.
export function AlertConsole() {
  const { data: alerts } = useAlerts();
  const latest = alerts?.[alerts.length - 1];

  return (
    <AnimatePresence>
      {latest && (
        <motion.div
          key={`${latest.type}-${latest.camera_id}-${latest.ts}`}
          role="alert"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="sticky top-14 z-40 flex items-center justify-center gap-2 border-b border-alert/40 bg-alert/15 px-4 py-2 text-sm text-alert shadow-[0_4px_40px_-8px_rgba(239,68,68,0.45)] backdrop-blur-xl"
        >
          <AlertTriangle className="size-4 shrink-0 animate-pulse" />
          <span className="data-mono">{latest.type}</span>
          <span className="text-alert/70">·</span>
          <span className="data-mono">{latest.camera_id}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
