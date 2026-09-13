"use client";

import { useMemo, useState } from "react";
import { BarChart3, Flame, Gauge, GitBranch, Waypoints, Route as RouteIcon } from "lucide-react";
import { AnalyticsViewSelector, type AnalyticsView } from "@/components/analytics/AnalyticsViewSelector";
import { DensityChart } from "@/components/analytics/DensityChart";
import { CorridorSpeedChart } from "@/components/analytics/CorridorSpeedChart";
import { SummaryStats } from "@/components/analytics/SummaryStats";
import { HeatmapLayer } from "@/components/map/HeatmapLayer";
import { ODFlowLayer } from "@/components/map/ODFlowLayer";
import { SegmentsLayer } from "@/components/map/SegmentsLayer";
import { RoutesLayer } from "@/components/map/RoutesLayer";
import { CityMap } from "@/components/map/CityMap";
import { RadarSweep } from "@/components/layout/RadarSweep";
import { Skeleton } from "@/components/layout/Skeleton";
import {
  useAnalyticsSummary,
  useHeatmap,
  useOdFlows,
  useSegments,
  useRoutes,
} from "@/hooks/useAnalytics";
import { useCameras } from "@/hooks/useCameras";
import { useFlashingCamera } from "@/hooks/useFlashingCamera";
import { buildRoadCoordinateIndex } from "@/lib/roads";
import { CONGESTION_COLORS } from "@/lib/colors";
import type { CongestionLevel } from "@/types/analytics";

// Both roles reach this page (TEAM.md §4). Density is now a KPI summary view
// (/analytics/summary) with a secondary per-camera chart; Corridor Speeds,
// OD Flow, Segments, and Routes are all real, contracted views as of
// Nawfal's 2026-09-13 handoff (TEAM.md §4, DECISIONS.md #6) — none of them
// carry the old PROTOTYPE banner treatment anymore.
export default function AnalyticsPage() {
  const [view, setView] = useState<AnalyticsView>("density");

  const summaryQuery = useAnalyticsSummary();
  const heatmapQuery = useHeatmap();
  const odFlowQuery = useOdFlows();
  const segmentsQuery = useSegments();
  const routesQuery = useRoutes();
  const camerasQuery = useCameras();
  const flashingCameraId = useFlashingCamera();

  const roadCoordinateIndex = useMemo(
    () => buildRoadCoordinateIndex(camerasQuery.data ?? []),
    [camerasQuery.data],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-analyst">Traffic Analytics</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            City-wide flow, congestion, and corridor speed, aggregated — never plaintext.
          </p>
        </div>
        <AnalyticsViewSelector value={view} onChange={setView} />
      </div>

      {view === "density" && (
        <Panel
          icon={<BarChart3 className="size-4" />}
          title="Traffic Density"
          subtitle="City-wide summary, plus vehicle counts per camera"
        >
          {summaryQuery.isLoading ? (
            <SummarySkeleton />
          ) : !summaryQuery.data ? (
            <EmptyChart label="No summary data yet" sublabel="Waiting on ingested sightings" />
          ) : (
            <SummaryStats summary={summaryQuery.data} />
          )}

          <div className="mt-5 border-t border-white/10 pt-5">
            {heatmapQuery.isLoading ? (
              <ChartSkeleton />
            ) : !heatmapQuery.data || heatmapQuery.data.length === 0 ? (
              <EmptyChart label="No per-camera data yet" sublabel="Waiting on ingested sightings" />
            ) : (
              <DensityChart data={heatmapQuery.data} />
            )}
          </div>
        </Panel>
      )}

      {view === "heatmap" && (
        <Panel
          icon={<Flame className="size-4" />}
          title="Heatmap"
          subtitle="Sighting density across the city, last hour"
        >
          <div className="relative h-[420px] overflow-hidden rounded-xl">
            <CityMap flashingCameraId={flashingCameraId}>
              {heatmapQuery.data && heatmapQuery.data.length > 0 && (
                <HeatmapLayer points={heatmapQuery.data} />
              )}
            </CityMap>
            {heatmapQuery.isLoading && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-sm">
                <RadarSweep accent="analyst" label="Loading heatmap…" icon={<Flame className="size-4" />} />
              </div>
            )}
          </div>
        </Panel>
      )}

      {view === "corridor-speeds" && (
        <Panel
          icon={<Gauge className="size-4" />}
          title="Corridor Speeds"
          subtitle="Average implied speed per camera-pair segment"
        >
          {segmentsQuery.isLoading ? (
            <ChartSkeleton />
          ) : !segmentsQuery.data || segmentsQuery.data.length === 0 ? (
            <EmptyChart label="No segment data yet" sublabel="Needs at least two sightings per plate" />
          ) : (
            <CorridorSpeedChart data={segmentsQuery.data} />
          )}
        </Panel>
      )}

      {view === "od-flow" && (
        <Panel
          icon={<GitBranch className="size-4" />}
          title="OD Flow"
          subtitle="Origin→destination volume between roads, last hour"
        >
          <MapPanelBody
            isLoading={odFlowQuery.isLoading}
            hasData={Boolean(odFlowQuery.data && odFlowQuery.data.length > 0)}
            loadingLabel="Loading OD flows…"
            emptyLabel="No OD flow data yet"
            flashingCameraId={flashingCameraId}
            icon={<GitBranch className="size-4" />}
          >
            {odFlowQuery.data && odFlowQuery.data.length > 0 && (
              <ODFlowLayer flows={odFlowQuery.data} roadCoordinateIndex={roadCoordinateIndex} />
            )}
          </MapPanelBody>
        </Panel>
      )}

      {view === "segments" && (
        <Panel
          icon={<Waypoints className="size-4" />}
          title="Segments"
          subtitle="Road segments colored by congestion"
        >
          <MapPanelBody
            isLoading={segmentsQuery.isLoading}
            hasData={Boolean(segmentsQuery.data && segmentsQuery.data.length > 0)}
            loadingLabel="Loading segments…"
            emptyLabel="No segment data yet"
            flashingCameraId={flashingCameraId}
            icon={<Waypoints className="size-4" />}
          >
            {segmentsQuery.data && camerasQuery.data && (
              <SegmentsLayer segments={segmentsQuery.data} cameras={camerasQuery.data} />
            )}
          </MapPanelBody>
          {segmentsQuery.data && segmentsQuery.data.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              {(Object.keys(CONGESTION_COLORS) as CongestionLevel[]).map((level) => (
                <span key={level} className="flex items-center gap-1.5 capitalize">
                  <span className="h-0.5 w-4 rounded" style={{ backgroundColor: CONGESTION_COLORS[level] }} />
                  {level.toLowerCase()}
                </span>
              ))}
            </div>
          )}
        </Panel>
      )}

      {view === "routes" && (
        <Panel
          icon={<RouteIcon className="size-4" />}
          title="Busiest Routes"
          subtitle="Top routes ranked by vehicle volume"
        >
          <MapPanelBody
            isLoading={routesQuery.isLoading}
            hasData={Boolean(routesQuery.data && routesQuery.data.length > 0)}
            loadingLabel="Loading routes…"
            emptyLabel="No route data yet"
            flashingCameraId={flashingCameraId}
            icon={<RouteIcon className="size-4" />}
          >
            {routesQuery.data && (
              <RoutesLayer routes={routesQuery.data} roadCoordinateIndex={roadCoordinateIndex} />
            )}
          </MapPanelBody>
          {routesQuery.data && routesQuery.data.length > 0 && (
            <div className="mt-3 space-y-1 text-xs text-muted-foreground">
              {[...routesQuery.data]
                .sort((a, b) => b.vehicle_count - a.vehicle_count)
                .map((r, i) => (
                  <div key={r.route_id} className="flex items-center gap-2">
                    <span className="data-mono text-foreground">#{i + 1}</span>
                    <span>{r.road_sequence.join(" → ")}</span>
                    <span className="data-mono">{r.vehicle_count} vehicles</span>
                  </div>
                ))}
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}

function MapPanelBody({
  isLoading,
  hasData,
  loadingLabel,
  emptyLabel,
  flashingCameraId,
  icon,
  children,
}: {
  isLoading: boolean;
  hasData: boolean;
  loadingLabel: string;
  emptyLabel: string;
  flashingCameraId: string | null;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="relative h-[420px] overflow-hidden rounded-xl">
      <CityMap flashingCameraId={flashingCameraId}>{children}</CityMap>
      {isLoading && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-sm">
          <RadarSweep accent="analyst" label={loadingLabel} icon={icon} />
        </div>
      )}
      {!isLoading && !hasData && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-sm">
          <RadarSweep
            accent="analyst"
            label={emptyLabel}
            sublabel="Waiting on ingested sightings"
            icon={icon}
          />
        </div>
      )}
    </div>
  );
}

function Panel({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-raised rounded-2xl border border-white/10 p-5 shadow-[0_0_40px_-16px_rgba(56,189,248,0.25)]">
      <div className="mb-4 flex items-center gap-2 text-sm font-medium text-foreground">
        <span className="text-analyst">{icon}</span>
        {title}
        <span className="text-xs font-normal text-muted-foreground">— {subtitle}</span>
      </div>
      {children}
    </div>
  );
}

const SKELETON_BAR_HEIGHTS = ["55%", "80%", "40%", "95%", "65%", "70%"];

function ChartSkeleton() {
  return (
    <div className="flex h-[280px] items-end gap-3 px-2 pb-4">
      {SKELETON_BAR_HEIGHTS.map((height, i) => (
        <Skeleton key={i} className="flex-1" style={{ height }} />
      ))}
    </div>
  );
}

function SummarySkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {SKELETON_BAR_HEIGHTS.slice(0, 4).map((_, i) => (
        <Skeleton key={i} className="h-16 rounded-xl" />
      ))}
    </div>
  );
}

function EmptyChart({ label, sublabel }: { label: string; sublabel: string }) {
  return (
    <div className="flex h-[280px] items-center justify-center">
      <RadarSweep accent="analyst" label={label} sublabel={sublabel} icon={<BarChart3 className="size-4" />} />
    </div>
  );
}
