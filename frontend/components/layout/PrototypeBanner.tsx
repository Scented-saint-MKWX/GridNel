import { FlaskConical } from "lucide-react";

// Same visual weight as MockBanner (impossible to miss) but a distinct
// message and color, so a GIS prototype view is never confused with either
// "this is live" or "this is mock-but-confirmed-shape" data. Per the master
// prompt Part 2: "build it visibly flagged ... same visual treatment as the
// mock-mode banner — impossible to mistake for a confirmed, shipped feature."
// See DECISIONS.md #4 — the underlying data shape itself is unconfirmed with
// the team, not just unwired.
export function PrototypeBanner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-healed/30 bg-healed/10 px-3 py-2 text-xs font-medium text-healed">
      <FlaskConical className="size-3.5 shrink-0" />
      <span>
        PROTOTYPE — {label} uses an unconfirmed data contract (see DECISIONS.md #4), not the
        frozen API shape. Not a shipped feature.
      </span>
    </div>
  );
}
