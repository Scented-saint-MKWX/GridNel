"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { motion } from "motion/react";
import { ShieldCheck, ScanSearch, LoaderCircle, Radar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/providers/AuthProvider";
import { AmbientBackground } from "@/components/layout/AmbientBackground";
import { SystemStatus } from "@/components/layout/SystemStatus";
import { MockBanner } from "@/components/layout/MockBanner";
import { apiFetch } from "@/lib/api";
import type { Role } from "@/types/auth";

const loginSchema = z.object({
  username: z.string().min(1, "Required"),
  password: z.string().min(1, "Required"),
});
type LoginForm = z.infer<typeof loginSchema>;

const roles: { role: Role; label: string; icon: typeof ScanSearch }[] = [
  { role: "tracker", label: "Tracker", icon: ScanSearch },
  { role: "analyst", label: "Analyst", icon: ShieldCheck },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [selectedRole, setSelectedRole] = useState<Role>("analyst");
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setError(null);
    try {
      const res = await apiFetch<{ token: string }>("/login", {
        method: "POST",
        body: values,
      });
      login(res.token);
      // Never auto-route to /tracking, even for a tracker login — see
      // FRONTEND_BLUEPRINT.md §5, /login section.
      router.push("/analytics");
    } catch {
      setError("Invalid credentials.");
    }
  }

  const glowClass =
    selectedRole === "tracker"
      ? "border-tracker/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.14),0_0_0_1px_rgba(217,126,44,0.15),0_8px_30px_-4px_rgba(217,126,44,0.4),0_30px_80px_-20px_rgba(0,0,0,0.8)]"
      : "border-analyst/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.14),0_0_0_1px_rgba(56,189,248,0.15),0_8px_30px_-4px_rgba(56,189,248,0.4),0_30px_80px_-20px_rgba(0,0,0,0.8)]";

  return (
    <div className="relative flex min-h-screen flex-col">
      <MockBanner />
      <AmbientBackground variant="login" />
      <div className="relative flex flex-1 flex-col items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={`glass-raised w-full max-w-md rounded-2xl border p-8 transition-all duration-500 ${glowClass}`}
        >
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex size-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
              <Radar className="size-5 text-analyst" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">SentinelGrid</h1>
            <p className="mt-1 text-sm text-muted-foreground">Traffic operations console</p>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-2">
            {roles.map(({ role, label, icon: Icon }) => {
              const active = selectedRole === role;
              return (
                <motion.button
                  key={role}
                  type="button"
                  onClick={() => setSelectedRole(role)}
                  whileTap={{ scale: 0.94 }}
                  animate={active ? { scale: [1, 1.04, 1] } : { scale: 1 }}
                  transition={{ duration: 0.28, ease: "easeOut" }}
                  className={`flex flex-col items-center gap-2 rounded-xl border px-4 py-3 text-sm transition-colors duration-300 ${
                    active
                      ? role === "tracker"
                        ? "border-tracker/60 bg-tracker/10 text-tracker shadow-[0_0_20px_-4px_rgba(217,126,44,0.4)]"
                        : "border-analyst/60 bg-analyst/10 text-analyst shadow-[0_0_20px_-4px_rgba(56,189,248,0.4)]"
                      : "border-white/10 bg-white/[0.02] text-muted-foreground hover:bg-white/[0.05] hover:-translate-y-0.5"
                  }`}
                >
                  <Icon className="size-4" />
                  {label}
                </motion.button>
              );
            })}
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input id="username" autoComplete="username" {...register("username")} />
              {errors.username && (
                <p className="text-xs text-destructive">{errors.username.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting && <LoaderCircle className="size-4 animate-spin" />}
              Sign in
            </Button>
          </form>
        </motion.div>

        <div className="absolute bottom-10 left-1/2 -translate-x-1/2">
          <SystemStatus />
        </div>
      </div>
    </div>
  );
}
