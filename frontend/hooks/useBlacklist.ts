import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { BlacklistRequest } from "@/types/tracking";

// Tracker-only mutations (TEAM.md §4.4: POST /blacklist, DELETE
// /blacklist/<plate_hash>) — plate_text is zod-validated at the form layer
// before it ever reaches this hook, same rule as useTrajectory/PlateSearch.
export function useAddBlacklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: BlacklistRequest) =>
      apiFetch<void>("/blacklist", { method: "POST", body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

// plateHash is a hash, not plaintext — still URL-encoded defensively, same
// treatment as any path segment carrying user-influenced data.
export function useRemoveBlacklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plateHash: string) =>
      apiFetch<void>(`/blacklist/${encodeURIComponent(plateHash)}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}
