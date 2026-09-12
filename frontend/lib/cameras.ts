import "server-only";
import { readFile } from "fs/promises";
import path from "path";

export interface Camera {
  camera_id: string;
  lat: number;
  lon: number;
  zone: string;
  road_node_id: string;
}

// Reads the shared, frozen seed at db/cameras.json — nobody hardcodes camera
// positions (CLAUDE.md, TEAM.md §4.3). That file is owned by P3 and may not be
// populated yet; callers must handle an empty array, not assume six cameras exist.
let cache: Camera[] | null = null;

export async function getCameras(): Promise<Camera[]> {
  if (cache) return cache;
  const filePath = path.join(process.cwd(), "..", "db", "cameras.json");
  try {
    const raw = await readFile(filePath, "utf-8");
    if (!raw.trim()) {
      cache = [];
      return cache;
    }
    const parsed = JSON.parse(raw) as Camera[];
    cache = parsed;
    return cache;
  } catch {
    cache = [];
    return cache;
  }
}
