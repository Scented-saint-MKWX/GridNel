"use client";

import { useAuth } from "@/components/providers/AuthProvider";

// Privileged surface. app/(protected)/layout.tsx already redirects a
// non-tracker role away from here — this is defense-in-depth in case that
// guard is ever bypassed or refactored around (CLAUDE.md "Auth gating
// implementation"). The real boundary is still the API's 403 on /track*.
export default function TrackingPage() {
  const { payload } = useAuth();

  if (payload?.role !== "tracker") {
    return null;
  }

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold tracking-tight">Vehicle Tracking</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Plate search, bridged trajectory map, and camera markers land here.
      </p>
    </div>
  );
}
