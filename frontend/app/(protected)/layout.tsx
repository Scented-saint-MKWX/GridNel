"use client";

import { useEffect, useState } from "react";
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
export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { payload } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!payload || isExpired(payload)) {
      router.replace("/login");
      return;
    }
    if (payload.role !== "tracker" && pathname?.startsWith("/tracking")) {
      router.replace("/analytics");
      return;
    }
    setChecked(true);
  }, [payload, pathname, router]);

  if (!checked) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <AmbientBackground />
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-analyst" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
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
