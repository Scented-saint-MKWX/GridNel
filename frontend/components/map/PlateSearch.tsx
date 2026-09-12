"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Search, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Indian plate format, permissive enough for demo plates like MH12AB1284.
// Validated + normalized to uppercase before it ever reaches
// /track/<text>/bridged — CLAUDE.md hard security rule (zod + URL-encode).
const plateSchema = z.object({
  plate: z
    .string()
    .trim()
    .min(4, "Too short")
    .max(15, "Too long")
    .regex(/^[A-Za-z0-9]+$/, "Letters and digits only"),
});
type PlateForm = z.infer<typeof plateSchema>;

interface PlateSearchProps {
  onSearch: (plateText: string) => void;
  isLoading?: boolean;
}

export function PlateSearch({ onSearch, isLoading }: PlateSearchProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PlateForm>({ resolver: zodResolver(plateSchema) });

  function onSubmit(values: PlateForm) {
    onSearch(values.plate.toUpperCase());
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-1.5">
      <div className="flex gap-2">
        <Input
          placeholder="MH12AB1284"
          className="data-mono uppercase"
          autoComplete="off"
          spellCheck={false}
          {...register("plate")}
        />
        <Button type="submit" size="icon" disabled={isLoading} aria-label="Search plate">
          {isLoading ? (
            <LoaderCircle className="size-4 animate-spin" />
          ) : (
            <Search className="size-4" />
          )}
        </Button>
      </div>
      {errors.plate && <p className="text-xs text-destructive">{errors.plate.message}</p>}
    </form>
  );
}
