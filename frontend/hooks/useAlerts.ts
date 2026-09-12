import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { apiFetch } from "@/lib/api";
import type { AlertEvent } from "@/types/tracking";

// Single shared poller per TEAM.md ("both roles; poll every 10s, NO WebSocket")
// and CLAUDE.md ("one shared hook per resource, not a poller per component").
export function useAlerts() {
  const sinceRef = useRef<string>(new Date(0).toISOString());

  return useQuery({
    queryKey: ["alerts"],
    queryFn: async () => {
      const events = await apiFetch<AlertEvent[]>(
        `/alerts?since=${encodeURIComponent(sinceRef.current)}`,
      );
      if (events.length > 0) {
        sinceRef.current = events[events.length - 1]!.ts;
      }
      return events;
    },
    refetchInterval: 10_000,
  });
}
