import type { Role } from "@/types/auth";
import { ScanSearch, ShieldCheck } from "lucide-react";

const roleStyles: Record<Role, string> = {
  tracker: "border-tracker/40 bg-tracker/10 text-tracker",
  analyst: "border-analyst/40 bg-analyst/10 text-analyst",
};

const roleIcons: Record<Role, typeof ScanSearch> = {
  tracker: ScanSearch,
  analyst: ShieldCheck,
};

export function RoleBadge({ role }: { role: Role }) {
  const Icon = roleIcons[role];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium uppercase tracking-wide ${roleStyles[role]}`}
    >
      <Icon className="size-3.5" />
      {role}
    </span>
  );
}
