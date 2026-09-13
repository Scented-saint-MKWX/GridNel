"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { AlertConsole } from "@/components/alerts/AlertConsole";
import { AmbientBackground } from "@/components/layout/AmbientBackground";
import { MockBanner } from "@/components/layout/MockBanner";
import { useAuth } from "@/components/providers/AuthProvider";
import { isExpired } from "@/lib/auth";

// Real UX-level role gating lives here, not in middleware.ts — see CLAUDE.md
// "Auth gating implementation". Renders nothing but a skeleton until the
// in-memory session has been checked, so no privileged markup or data fetch
// ever starts before the redirect decision is made.
// Derives the gating decision synchronously, during render — not from a
// useState flipped inside a useEffect. The previous version used
// `const [checked, setChecked] = useState(false)` plus an effect that set
// it true/false: React commits the render that triggered a navigation
// *before* running effects, so on a /tracking -> /analytics navigation the
// very first render after the URL changed still saw the previous render's
// `checked=true` and mounted `children` (the new page, with its own
// data-fetching hooks) — firing every analytics query and hitting real
// 403s — a full render (and its effects, including data fetches) before
// the redirect effect even ran. That's a real, reproduced race, not a
// theoretical one: confirmed via real 403s in the browser console this
// session. Computing the decision inline from `payload`/`pathname` (both
// already correct on the very first render after a navigation) closes the
// window entirely — there is no render where `children` can mount under a
// stale decision, because there is no stale state to read.
type GateDecision = { kind: "redirect"; to: string } | { kind: "ok" };

function computeGate(payload: ReturnType<typeof useAuth>["payload"], pathname: string | null): GateDecision {
  if (!payload || isExpired(payload)) return { kind: "redirect", to: "/login" };
  if (payload.role !== "tracker" && pathname?.startsWith("/tracking")) {
    return { kind: "redirect", to: "/analytics" };
  }
  // Every /analytics/* route is require_role("analyst") only
  // (api/analytics.py, TEAM.md §4) — a tracker reaching /analytics (a
  // stale bookmark, manually typing the URL, or clicking the nav link)
  // got a wall of real 403s with every panel stuck in its empty/error
  // state instead of a redirect. The API's 403 was always the real
  // security boundary per CLAUDE.md; this is the same UX-politeness guard
  // CLAUDE.md's "definition of done" already required the other
  // direction for, just missing here until this session.
  if (payload.role === "tracker" && pathname?.startsWith("/analytics")) {
    return { kind: "redirect", to: "/tracking" };
  }
  return { kind: "ok" };
}

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { payload } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const gate = computeGate(payload, pathname);

  useEffect(() => {
    if (gate.kind === "redirect") {
      router.replace(gate.to);
    }
  });

  if (gate.kind !== "ok") {
    return (
      <div className="relative flex min-h-dvh items-center justify-center">
        <AmbientBackground />
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-analyst" />
      </div>
    );
  }

  // min-h-dvh (dynamic viewport height), not min-h-screen (100vh): 100vh is
  // computed against the browser's outer window, not the actually-visible
  // viewport — with any browser chrome eating vertical space (an infobar,
  // a Chrome extension banner, mobile address bar), 100vh renders taller
  // than the real client area, tripping a vertical scrollbar that then eats
  // ~15-17px from the right edge only, visibly shifting centered content
  // left of true screen-center. Reproduced this session against a real
  // Chrome window with an active infobar; confirmed via computed
  // scrollHeight > clientHeight. dvh tracks the real visible viewport.
  return (
    <div className="relative min-h-dvh">
      <AmbientBackground />
      {/* MockBanner, Navbar, and AlertConsole are consecutive `sticky top-0`
          siblings in normal flow — each one's sticky offset resolves against
          where the previous one currently sits, so nothing here hardcodes a
          pixel offset that breaks if the banner's height changes (e.g. its
          text wrapping to two lines at a narrow viewport). See CLAUDE.md
          master-prompt Fix 2. */}
      <MockBanner />
      <Navbar />
      <AlertConsole />
      <main>{children}</main>
    </div>
  );
}
