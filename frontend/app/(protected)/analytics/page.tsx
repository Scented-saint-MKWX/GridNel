"use client";

import { useState } from "react";
import { BarChart3, Flame, Gauge, GitBranch } from "lucide-react";
import { AnalyticsViewSelector, type AnalyticsView } from "@/components/analytics/AnalyticsViewSelector";
import { DensityChart } from "@/components/analytics/DensityChart";
import { CorridorSpeedChart } from "@/components/analytics/CorridorSpeedChart";
import { GisPreviewPanel } from "@/components/analytics/GisPreviewPanel";
import { HeatmapLayer } from "@/components/map/HeatmapLayer";
import { ODFlowLayer } from "@/components/map/ODFlowLayer";
import { CityMap } from "@/components/map/CityMap";
import { RadarSweep } from "@/components/layout/RadarSweep";
import { Skeleton } from "@/components/layout/Skeleton";
import { useDensity, useHeatmap, useCorridorSpeeds, useOdFlows } from "@/hooks/useAnalytics";
import { useFlashingCamera } from "@/hooks/useFlashingCamera";

// Both roles reach this page (TEAM.md §4.4). Density + corridor-speeds render
// as Recharts bar charts inside a glass panel; heatmap is a real Mapbox layer,
// not a chart-library heatmap — per FRONTEND_BLUEPRINT.md §5.
export default function AnalyticsPage() {
  const [view, setView] = useState<AnalyticsView>("density");

  const densityQuery = useDensity();
  const heatmapQuery = useHeatmap();
  const corridorQuery = useCorridorSpeeds();
  const odFlowQuery = useOdFlows();
  const flashingCameraId = useFlashingCamera();

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
          subtitle="Vehicle counts per camera, last hour"
        >
          {densityQuery.isLoading ? (
            <ChartSkeleton />
          ) : !densityQuery.data || densityQuery.data.length === 0 ? (
            <EmptyChart label="No density data yet" sublabel="Waiting on ingested sightings" />
          ) : (
            <DensityChart data={densityQuery.data} />
          )}
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
          subtitle="Average implied speed per road edge"
        >
          {corridorQuery.isLoading ? (
            <ChartSkeleton />
          ) : !corridorQuery.data || corridorQuery.data.length === 0 ? (
            <EmptyChart label="No corridor speed data yet" sublabel="Needs at least two sightings per plate" />
          ) : (
            <CorridorSpeedChart data={corridorQuery.data} />
          )}
        </Panel>
      )}

      {view === "od-flow" && (
        <Panel
          icon={<GitBranch className="size-4" />}
          title="OD Flow"
          subtitle="Origin→destination volume between zone centroids, last hour"
        >
          <div className="relative h-[420px] overflow-hidden rounded-xl">
            <CityMap flashingCameraId={flashingCameraId}>
              {odFlowQuery.data && odFlowQuery.data.length > 0 && (
                <ODFlowLayer flows={odFlowQuery.data} />
              )}
            </CityMap>
            {odFlowQuery.isLoading && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-sm">
                <RadarSweep accent="analyst" label="Loading OD flows…" icon={<GitBranch className="size-4" />} />
              </div>
            )}
            {!odFlowQuery.isLoading && (!odFlowQuery.data || odFlowQuery.data.length === 0) && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-sm">
                <RadarSweep
                  accent="analyst"
                  label="No OD flow data yet"
                  sublabel="Waiting on ingested sightings"
                  icon={<GitBranch className="size-4" />}
                />
              </div>
            )}
          </div>
        </Panel>
      )}

      {view === "gis-preview" && <GisPreviewPanel />}
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

function EmptyChart({ label, sublabel }: { label: string; sublabel: string }) {
  return (
    <div className="flex h-[280px] items-center justify-center">
      <RadarSweep accent="analyst" label={label} sublabel={sublabel} icon={<BarChart3 className="size-4" />} />
    </div>
  );
}
