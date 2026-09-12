import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CorridorSpeed, DensityPoint, HeatmapPoint, OdFlowPoint } from "@/types/analytics";

export function useDensity(hours: number = 1) {
  return useQuery({
    queryKey: ["analytics", "density", hours],
    queryFn: () => apiFetch<DensityPoint[]>(`/analytics/density?hours=${hours}`),
  });
}

export function useHeatmap(hours: number = 1) {
  return useQuery({
    queryKey: ["analytics", "heatmap", hours],
    queryFn: () => apiFetch<HeatmapPoint[]>(`/analytics/heatmap?hours=${hours}`),
  });
}

export function useCorridorSpeeds() {
  return useQuery({
    queryKey: ["analytics", "corridor-speeds"],
    queryFn: () => apiFetch<CorridorSpeed[]>("/analytics/corridor-speeds"),
  });
}

// OD confirmed in-scope 2026-09-13 (DECISIONS.md #4) — no real /analytics/od
// endpoint in TEAM.md §4.4 yet, mock-only until P4 wires it.
export function useOdFlows() {
  return useQuery({
    queryKey: ["analytics", "od"],
    queryFn: () => apiFetch<OdFlowPoint[]>("/analytics/od"),
  });
}
