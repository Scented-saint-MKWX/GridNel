import { useQuery } from "@tanstack/react-query";
import type { ApiCamera } from "@/types/cameras";

// Cameras are served through the Next.js /api/cameras route (app/api/cameras/
// route.ts), which wraps lib/cameras.ts's MOCK_MODE-aware fetch — not
// apiFetch/lib/api.ts, since this data isn't behind the backend's auth at
// all (cameras aren't privileged). Same TanStack Query convention as every
// other hook regardless.
export function useCameras() {
  return useQuery({
    queryKey: ["cameras"],
    queryFn: () => fetch("/api/cameras").then((res) => res.json() as Promise<ApiCamera[]>),
    staleTime: Infinity,
  });
}
