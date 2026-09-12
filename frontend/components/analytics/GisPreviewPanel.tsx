"use client";

import { useState } from "react";
import { Waypoints, Route as RouteIcon } from "lucide-react";
import { CityMap } from "@/components/map/CityMap";
import { SegmentsLayer } from "@/components/map/SegmentsLayer";
import { RoutesLayer } from "@/components/map/RoutesLayer";
import { PrototypeBanner } from "@/components/layout/PrototypeBanner";
import { mockRoadSegments, mockRoutes } from "@/lib/gis-prototype/fixtures";
import { CONGESTION_COLORS } from "@/lib/gis-prototype/adapter";

type GisSubView = "segments" | "routes";

const SUB_VIEWS: { value: GisSubView; label: string; icon: typeof Waypoints }[] = [
  { value: "segments", label: "Segments", icon: Waypoints },
  { value: "routes", label: "Busiest Routes", icon: RouteIcon },
];

// GIS feature expansion, Part 2 of the design-escalation master prompt — see
// DECISIONS.md #4. Fixtures only (no real /analytics/segments or /analytics/
// routes endpoint exists in TEAM.md §4.4). OD used to live here as a third
// preview sub-tab; it was promoted to a first-class AnalyticsViewSelector
// view on 2026-09-13 (confirmed in-scope, authorized by Wahid) — see
// components/map/ODFlowLayer.tsx and DECISIONS.md #4. Segments and Routes
// remain prototypes, unaffected by that authorization.
export function GisPreviewPanel() {
  const [subView, setSubView] = useState<GisSubView>("segments");
  const segments = mockRoadSegments();
  const routes = mockRoutes();

  return (
    <div className="space-y-3">
      <PrototypeBanner label="This GIS preview" />

      <div className="flex flex-wrap items-center gap-2">
        {SUB_VIEWS.map(({ value, label, icon: Icon }) => {
          const active = subView === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setSubView(value)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "border-healed/50 bg-healed/10 text-healed"
                  : "border-white/10 bg-white/[0.02] text-muted-foreground hover:bg-white/[0.05]"
              }`}
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          );
        })}
      </div>

      <div className="relative h-[420px] overflow-hidden rounded-xl">
        <CityMap>
          {subView === "segments" && <SegmentsLayer segments={segments} />}
          {subView === "routes" && <RoutesLayer routes={routes} />}
        </CityMap>
      </div>

      {subView === "segments" && (
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          {(Object.keys(CONGESTION_COLORS) as (keyof typeof CONGESTION_COLORS)[]).map((level) => (
            <span key={level} className="flex items-center gap-1.5 capitalize">
              <span
                className="h-0.5 w-4 rounded"
                style={{ backgroundColor: CONGESTION_COLORS[level] }}
              />
              {level}
            </span>
          ))}
        </div>
      )}

      {subView === "routes" && (
        <div className="space-y-1 text-xs text-muted-foreground">
          {routes.map((r) => (
            <div key={r.route_id} className="flex items-center gap-2">
              <span className="data-mono text-foreground">#{r.rank}</span>
              <span>{r.node_path.join(" → ")}</span>
              <span className="data-mono">{r.vehicle_count} vehicles</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
