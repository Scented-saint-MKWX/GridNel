import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { DebugHashResponse } from "@/types/tracking";

// Tracker-only demo helper (TEAM.md §4.4) so the frontend can show judges the
// plaintext -> hash link live. plateText must already be validated (zod) and
// is URL-encoded here — same rule as useTrajectory.
export function useDebugHash(plateText: string | null) {
  return useQuery({
    queryKey: ["debug-hash", plateText],
    queryFn: () =>
      apiFetch<DebugHashResponse>(`/debug/hash/${encodeURIComponent(plateText!)}`),
    enabled: Boolean(plateText),
  });
}
