"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ShieldCheck, ScanSearch, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/providers/AuthProvider";
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

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="glass-raised w-full max-w-md rounded-2xl p-8">
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold tracking-tight text-foreground">SentinelGrid</h1>
          <p className="mt-1 text-sm text-muted-foreground">Traffic operations console</p>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-2">
          {roles.map(({ role, label, icon: Icon }) => {
            const active = selectedRole === role;
            return (
              <button
                key={role}
                type="button"
                onClick={() => setSelectedRole(role)}
                className={`flex flex-col items-center gap-2 rounded-xl border px-4 py-3 text-sm transition-colors ${
                  active
                    ? role === "tracker"
                      ? "border-tracker/60 bg-tracker/10 text-tracker"
                      : "border-analyst/60 bg-analyst/10 text-analyst"
                    : "border-white/10 bg-white/[0.02] text-muted-foreground hover:bg-white/[0.05]"
                }`}
              >
                <Icon className="size-4" />
                {label}
              </button>
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
      </div>
    </div>
  );
}
