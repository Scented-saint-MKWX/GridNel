"use client";

import { useState } from "react";
import { LoaderCircle, ScanSearch } from "lucide-react";
import { useAuth } from "@/components/providers/AuthProvider";
import { CityMap } from "@/components/map/CityMap";
import { TrajectoryLayer } from "@/components/map/TrajectoryLayer";
import { PlateSearch } from "@/components/map/PlateSearch";
import { useTrajectory } from "@/hooks/useTrajectory";
import { useDebugHash } from "@/hooks/useDebugHash";
import { ApiError } from "@/lib/api";

// Privileged surface. app/(protected)/layout.tsx already redirects a
// non-tracker role away from here — this is defense-in-depth in case that
// guard is ever bypassed or refactored around (CLAUDE.md "Auth gating
// implementation"). The real boundary is still the API's 403 on /track*.
export default function TrackingPage() {
  const { payload } = useAuth();
  const [plateText, setPlateText] = useState<string | null>(null);

  const trajectoryQuery = useTrajectory(plateText);
  const debugHashQuery = useDebugHash(plateText);

  if (payload?.role !== "tracker") {
    return null;
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <div className="relative z-10 flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-white/10 bg-surface/60 p-4 backdrop-blur-xl">
        <div>
          <h1 className="flex items-center gap-2 text-sm font-semibold tracking-tight text-tracker">
            <ScanSearch className="size-4" />
            Vehicle Tracking
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Search a plate to reconstruct its route, including A*-bridged blind spots.
          </p>
        </div>

        <PlateSearch onSearch={setPlateText} isLoading={trajectoryQuery.isFetching} />

        {plateText && debugHashQuery.data && (
          <div className="glass rounded-lg p-2.5 text-xs">
            <div className="text-muted-foreground">/debug/hash lookup</div>
            <div className="data-mono mt-1 break-all text-analyst">
              {debugHashQuery.data.plate_hash}
            </div>
          </div>
        )}

        {trajectoryQuery.isFetching && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <LoaderCircle className="size-3.5 animate-spin" />
            Querying trajectory…
          </div>
        )}

        {trajectoryQuery.isError && (
          <p className="text-xs text-destructive">
            {trajectoryQuery.error instanceof ApiError
              ? trajectoryQuery.error.message
              : "Lookup failed."}
          </p>
        )}

        {trajectoryQuery.data && (
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">
              <span className="data-mono text-foreground">{trajectoryQuery.data.plate}</span> —{" "}
              {trajectoryQuery.data.segments.length} segments
            </div>
            <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="h-0.5 w-3 rounded bg-tracker" /> observed
              </span>
              <span className="flex items-center gap-1">
                <span className="h-0.5 w-3 rounded border-b border-dashed border-healed" />{" "}
                inferred
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="relative flex-1">
        <CityMap>
          {trajectoryQuery.data && <TrajectoryLayer trajectory={trajectoryQuery.data} />}
        </CityMap>
      </div>
    </div>
  );
}
