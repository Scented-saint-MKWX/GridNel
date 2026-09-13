import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AnalyticsSummary, HeatmapPoint, OdFlow, Route, Segment } from "@/types/analytics";

// Real contract from Nawfal (P4), 2026-09-13 — see TEAM.md §4 and
// DECISIONS.md #6. Supersedes useDensity/useCorridorSpeeds, which queried the
// now-gone /analytics/density and /analytics/corridor-speeds endpoints.

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: () => apiFetch<AnalyticsSummary>("/analytics/summary"),
  });
}

export function useSegments() {
  return useQuery({
    queryKey: ["analytics", "segments"],
    queryFn: () => apiFetch<{ segments: Segment[] }>("/analytics/segments").then((r) => r.segments),
  });
}

export function useHeatmap(hours: number = 1) {
  return useQuery({
    queryKey: ["analytics", "heatmap", hours],
    queryFn: () =>
      apiFetch<{ points: HeatmapPoint[] }>(`/analytics/heatmap?hours=${hours}`).then(
        (r) => r.points,
      ),
  });
}

export function useOdFlows() {
  return useQuery({
    queryKey: ["analytics", "od"],
    queryFn: () => apiFetch<{ flows: OdFlow[] }>("/analytics/od").then((r) => r.flows),
  });
}

export function useRoutes() {
  return useQuery({
    queryKey: ["analytics", "routes"],
    queryFn: () => apiFetch<{ routes: Route[] }>("/analytics/routes").then((r) => r.routes),
  });
}
