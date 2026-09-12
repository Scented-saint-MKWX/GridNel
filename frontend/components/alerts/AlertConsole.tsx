"use client";

import { AlertTriangle } from "lucide-react";
import { useAlerts } from "@/hooks/useAlerts";

// Global blacklist-hit banner — mounted once in (protected)/layout.tsx so it's
// visible from any page, per FRONTEND_BLUEPRINT.md §5 ("must not be tucked away
// on a sub-page"). Camera-flash-on-map behavior wires in once CityMap exists
// (hour 3-12 per the blueprint's hour plan); this is the hour-0-3 stub.
export function AlertConsole() {
  const { data: alerts } = useAlerts();
  const latest = alerts?.[alerts.length - 1];

  if (!latest) return null;

  return (
    <div
      role="alert"
      className="fixed inset-x-0 top-14 z-50 flex items-center justify-center gap-2 border-b border-alert/40 bg-alert/15 px-4 py-2 text-sm text-alert backdrop-blur-xl animate-in fade-in slide-in-from-top-2"
    >
      <AlertTriangle className="size-4 shrink-0 animate-pulse" />
      <span className="data-mono">{latest.type}</span>
      <span className="text-alert/70">·</span>
      <span className="data-mono">{latest.camera_id}</span>
    </div>
  );
}
