import { NextResponse } from "next/server";

// Intentional passthrough — do not "fix" this by adding a cookie.
//
// The JWT lives in memory (React Context) only, per CLAUDE.md's hard security
// rules. Middleware runs at the edge/server and structurally cannot read
// in-memory client state, so there is nothing here to decode a role claim from.
// Real UX-level gating lives in app/(protected)/layout.tsx as a hydration guard,
// with a repeated check in tracking/page.tsx as defense-in-depth. The API's 403
// is the actual security boundary regardless of what this file does.
//
// If edge-level redirects are wanted later, the correct upgrade is an httpOnly
// Secure SameSite=Strict JWT cookie from P5 alongside /login's existing JSON body
// — a team decision, not something to add unilaterally here.
export function middleware() {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
