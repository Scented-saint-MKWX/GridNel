import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Trajectory } from "@/types/tracking";

// plateText must already be validated (zod) and is URL-encoded here before
// touching /track/<text>/bridged — CLAUDE.md hard security rule.
export function useTrajectory(plateText: string | null) {
  return useQuery({
    queryKey: ["trajectory", plateText],
    queryFn: () =>
      apiFetch<Trajectory>(`/track/${encodeURIComponent(plateText!)}/bridged`),
    enabled: Boolean(plateText),
  });
}
