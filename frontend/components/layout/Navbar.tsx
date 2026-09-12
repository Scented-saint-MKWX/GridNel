"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "motion/react";
import { LogOut, Radar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RoleBadge } from "@/components/layout/RoleBadge";
import { useAuth } from "@/components/providers/AuthProvider";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { payload, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const links = [
    { href: "/analytics", label: "Analytics" },
    // Hidden entirely for analysts — UX politeness on top of the layout guard
    // and the API's 403; see CLAUDE.md.
    ...(payload?.role === "tracker" ? [{ href: "/tracking", label: "Tracking" }] : []),
  ];

  const accentGlow =
    payload?.role === "tracker"
      ? "shadow-[0_1px_30px_-8px_rgba(245,158,11,0.35)]"
      : "shadow-[0_1px_30px_-8px_rgba(56,189,248,0.3)]";

  return (
    <header
      className={`glass sticky top-0 z-40 flex h-14 items-center justify-between px-6 ${accentGlow}`}
    >
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="relative flex size-4 items-center justify-center">
            <motion.span
              className="absolute inline-flex size-full rounded-full bg-analyst/60"
              animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
            />
            <Radar className="relative size-4 text-analyst" />
          </span>
          SentinelGrid
        </div>
        <nav className="flex items-center gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                pathname?.startsWith(link.href)
                  ? "bg-white/[0.08] text-foreground"
                  : "text-muted-foreground hover:bg-white/[0.05] hover:text-foreground"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        {payload && <RoleBadge role={payload.role} />}
        <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Log out">
          <LogOut className="size-4" />
        </Button>
      </div>
    </header>
  );
}
