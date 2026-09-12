import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CorridorSpeed, DensityPoint, HeatmapPoint } from "@/types/analytics";

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
