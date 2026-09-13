"use client";

import { useId, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ShieldBan, LoaderCircle, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAddBlacklist, useRemoveBlacklist } from "@/hooks/useBlacklist";
import { ApiError } from "@/lib/api";

// Tracker-only privileged mutation UI (TEAM.md §4.4: POST /blacklist, DELETE
// /blacklist/<plate_hash>) — same defense-in-depth pattern as the rest of
// /tracking: this panel only ever mounts inside the tracker-gated page, and
// the API's 403 remains the real boundary if that guard is ever bypassed.
const addSchema = z.object({
  plate: z
    .string()
    .trim()
    .min(4, "Too short")
    .max(15, "Too long")
    .regex(/^[A-Za-z0-9]+$/, "Letters and digits only"),
  reason: z.string().trim().min(3, "Give a reason (min 3 chars)").max(200, "Too long"),
});
type AddForm = z.infer<typeof addSchema>;

const removeSchema = z.object({
  plateHash: z.string().trim().min(1, "Required"),
});
type RemoveForm = z.infer<typeof removeSchema>;

export function BlacklistPanel() {
  const addId = useId();
  const removeId = useId();
  const [addSuccess, setAddSuccess] = useState(false);
  const [removeSuccess, setRemoveSuccess] = useState(false);

  const addMutation = useAddBlacklist();
  const removeMutation = useRemoveBlacklist();

  const {
    register: registerAdd,
    handleSubmit: handleAddSubmit,
    reset: resetAdd,
    formState: { errors: addErrors },
  } = useForm<AddForm>({ resolver: zodResolver(addSchema) });

  const {
    register: registerRemove,
    handleSubmit: handleRemoveSubmit,
    reset: resetRemove,
    formState: { errors: removeErrors },
  } = useForm<RemoveForm>({ resolver: zodResolver(removeSchema) });

  function onAdd(values: AddForm) {
    setAddSuccess(false);
    addMutation.mutate(
      { plate_text: values.plate.toUpperCase(), reason: values.reason },
      {
        onSuccess: () => {
          setAddSuccess(true);
          resetAdd();
        },
      },
    );
  }

  function onRemove(values: RemoveForm) {
    setRemoveSuccess(false);
    removeMutation.mutate(values.plateHash, {
      onSuccess: () => {
        setRemoveSuccess(true);
        resetRemove();
      },
    });
  }

  return (
    <div className="glass space-y-4 rounded-xl border-white/10 p-3 shadow-[0_0_20px_-8px_rgba(217,126,44,0.3)]">
      <h2 className="flex items-center gap-2 text-sm font-semibold tracking-tight text-tracker">
        <ShieldBan className="size-4" />
        Blacklist
      </h2>

      <form onSubmit={handleAddSubmit(onAdd)} className="space-y-2">
        <div className="space-y-1">
          <Label htmlFor={`${addId}-plate`} className="text-xs text-muted-foreground">
            Plate
          </Label>
          <Input
            id={`${addId}-plate`}
            placeholder="MH12AB1284"
            className="data-mono uppercase"
            autoComplete="off"
            spellCheck={false}
            {...registerAdd("plate")}
          />
          {addErrors.plate && (
            <p className="text-xs text-destructive">{addErrors.plate.message}</p>
          )}
        </div>
        <div className="space-y-1">
          <Label htmlFor={`${addId}-reason`} className="text-xs text-muted-foreground">
            Reason
          </Label>
          <textarea
            id={`${addId}-reason`}
            placeholder="Stolen vehicle report"
            rows={2}
            className="w-full min-w-0 resize-none rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30 dark:hover:bg-input/50"
            {...registerAdd("reason")}
          />
          {addErrors.reason && (
            <p className="text-xs text-destructive">{addErrors.reason.message}</p>
          )}
        </div>
        <Button type="submit" size="sm" disabled={addMutation.isPending} className="w-full">
          {addMutation.isPending && <LoaderCircle className="size-3.5 animate-spin" />}
          Add to blacklist
        </Button>
        {addMutation.isError && (
          <p className="text-xs text-destructive">
            {addMutation.error instanceof ApiError
              ? addMutation.error.message
              : "Failed to add plate."}
          </p>
        )}
        {addSuccess && !addMutation.isError && (
          <p className="text-xs text-analyst">Added.</p>
        )}
      </form>

      <div className="h-px bg-white/10" />

      <form onSubmit={handleRemoveSubmit(onRemove)} className="space-y-2">
        <div className="space-y-1">
          <Label htmlFor={removeId} className="text-xs text-muted-foreground">
            Remove by plate hash
          </Label>
          <Input
            id={removeId}
            placeholder="a9f3c1..."
            className="data-mono"
            autoComplete="off"
            spellCheck={false}
            {...registerRemove("plateHash")}
          />
          {removeErrors.plateHash && (
            <p className="text-xs text-destructive">{removeErrors.plateHash.message}</p>
          )}
        </div>
        <Button
          type="submit"
          size="sm"
          variant="destructive"
          disabled={removeMutation.isPending}
          className="w-full"
        >
          {removeMutation.isPending ? (
            <LoaderCircle className="size-3.5 animate-spin" />
          ) : (
            <Trash2 className="size-3.5" />
          )}
          Remove
        </Button>
        {removeMutation.isError && (
          <p className="text-xs text-destructive">
            {removeMutation.error instanceof ApiError
              ? removeMutation.error.message
              : "Failed to remove plate."}
          </p>
        )}
        {removeSuccess && !removeMutation.isError && (
          <p className="text-xs text-analyst">Removed.</p>
        )}
      </form>
    </div>
  );
}
