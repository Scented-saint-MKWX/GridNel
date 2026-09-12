import { AlertTriangle } from "lucide-react";
import { MOCK_MODE } from "@/lib/mock/router";

// Impossible-to-miss indicator whenever NEXT_PUBLIC_MOCK_MODE=true — so nobody,
// including future-us mid-rehearsal, mistakes mock fixtures for live data.
// Never rendered when the flag is unset (default/off, per CLAUDE.md).
export function MockBanner() {
  if (!MOCK_MODE) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-[999] flex items-center justify-center gap-2 bg-tracker px-3 py-1 text-xs font-semibold tracking-wide text-black">
      <AlertTriangle className="size-3.5" />
      MOCK DATA — NEXT_PUBLIC_MOCK_MODE is on, nothing here is live
    </div>
  );
}
