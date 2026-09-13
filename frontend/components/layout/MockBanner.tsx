import { AlertTriangle } from "lucide-react";
import { MOCK_MODE } from "@/lib/mock/router";

// Impossible-to-miss indicator whenever NEXT_PUBLIC_MOCK_MODE=true — so nobody,
// including future-us mid-rehearsal, mistakes mock fixtures for live data.
// Never rendered when the flag is unset (default/off, per CLAUDE.md).
//
// Deliberately NOT `fixed` — a fixed banner at the document root used to
// overlap Navbar/AlertConsole's independently-hardcoded `sticky top-N`
// offsets in (protected)/layout.tsx (worse when this text wraps to two lines
// on a narrow viewport). This renders as a normal-flow, `sticky top-0`
// sibling wherever it's mounted, so it pushes the elements after it down
// naturally instead of floating on top of them — see CLAUDE.md master-prompt
// Fix 2.
export function MockBanner() {
  if (!MOCK_MODE) return null;

  return (
    <div className="sticky top-0 z-[999] flex flex-wrap items-center justify-center gap-x-2 gap-y-0.5 bg-tracker px-3 py-1 text-center text-xs font-semibold tracking-wide text-black">
      <AlertTriangle className="size-3.5 shrink-0" />
      MOCK DATA — NEXT_PUBLIC_MOCK_MODE is on, nothing here is live
    </div>
  );
}
