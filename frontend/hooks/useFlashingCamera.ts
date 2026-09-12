import { useEffect, useState } from "react";
import { useAlerts } from "@/hooks/useAlerts";

const FLASH_DURATION_MS = 8000;

// Derives "which camera marker should currently be flashing" from the shared
// /alerts poll — CLAUDE.md Part 1 item 2: a blacklist hit must visibly flash
// the specific camera marker on whatever map is mounted, not just the banner.
// Independent of AlertConsole's own dismiss state: the map flash and the
// banner are two separate reactions to the same event, one time-boxed, one
// user-dismissed.
export function useFlashingCamera(): string | null {
  const { data: alerts } = useAlerts();
  const latest = alerts?.[alerts.length - 1];
  const [flashingCameraId, setFlashingCameraId] = useState<string | null>(null);

  useEffect(() => {
    if (!latest) return;
    setFlashingCameraId(latest.camera_id);
    const timer = setTimeout(() => setFlashingCameraId(null), FLASH_DURATION_MS);
    return () => clearTimeout(timer);
  }, [latest]);

  return flashingCameraId;
}
