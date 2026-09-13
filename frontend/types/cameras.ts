// Real contract from Nawfal (P4), 2026-09-13 — see TEAM.md §4 and
// DECISIONS.md #6. Supersedes the old cameras.json-only camera shape as the
// app's live/mock source; db/cameras.json is now only the fixture backing
// the mock /cameras handler, not read directly by the app (see lib/cameras.ts).
export interface ApiCamera {
  camera_id: string;
  latitude: number;
  longitude: number;
  road_id: string;
}

export interface CamerasResponse {
  cameras: ApiCamera[];
}
