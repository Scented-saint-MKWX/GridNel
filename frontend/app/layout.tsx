import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { AuthProvider } from "@/components/providers/AuthProvider";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  title: "SentinelGrid",
  description: "Unified ANPR tracking, analytics, and alerting for city traffic operations.",
};

// MockBanner is intentionally NOT rendered here. It used to be `fixed
// inset-x-0 top-0` at the document root while Navbar/AlertConsole were
// independently `sticky top-0`/`sticky top-14` inside (protected)/layout.tsx
// — nothing reconciled the fixed banner's height with those hardcoded sticky
// offsets, so the banner overlapped the navbar whenever MOCK_MODE was on
// (worse if its text wrapped to two lines). See DECISIONS.md / CLAUDE.md
// master-prompt Fix 2. MockBanner now renders as an in-flow sticky sibling of
// Navbar/AlertConsole inside (protected)/layout.tsx, and separately at the
// top of /login's own flow — one source of truth per surface, no hardcoded
// pixel offsets anywhere.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${sans.variable} ${mono.variable}`}>
      <body className="bg-background text-foreground antialiased font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
