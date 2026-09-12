export type FusionOutcome =
  | "agreement"
  | "engine_preferred"
  | "vendor_preferred"
  | "single_channel"
  | "low_confidence";

export interface ObservedSegment {
  type: "observed";
  camera_id: string;
  ts: string;
  lat: number;
  lon: number;
  outcome?: FusionOutcome;
  healed?: boolean;
}

export interface InferredSegment {
  type: "inferred";
  from: string;
  to: string;
  ts_start: string;
  ts_end: string;
  path: [number, number][];
  algorithm: "astar_speed_prior";
}

export type TrajectorySegment = ObservedSegment | InferredSegment;

export interface Trajectory {
  plate: string;
  segments: TrajectorySegment[];
}

export interface BlacklistRequest {
  plate_text: string;
  reason: string;
}

// NOT in TEAM.md §4 verbatim — shape inferred from db schema's alert_events table
// (TEAM.md §8 P3 spec) and /debug/hash's stated purpose. Confirm with P4 before
// relying on field names beyond what's used here.
export interface DebugHashResponse {
  plate_text: string;
  plate_hash: string;
}

export interface AlertEvent {
  id: string;
  type: string;
  plate_hash: string;
  camera_id: string;
  ts: string;
  detail: Record<string, unknown>;
}
