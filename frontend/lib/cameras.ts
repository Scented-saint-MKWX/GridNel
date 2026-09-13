import "server-only";
import { readFile } from "fs/promises";
import path from "path";
import type { ApiCamera } from "@/types/cameras";

export type { ApiCamera as Camera };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === "true";

// Real contract: GET /cameras -> {cameras:[...]} (Nawfal, 2026-09-13, TEAM.md
// §4) — supersedes the old "read db/cameras.json directly" approach. In mock
// mode we still source fixture data FROM db/cameras.json when it's populated
// (falling back to lib/mock/fixtures.ts's MOCK_CAMERAS otherwise, since P3's
// seed file is empty as of this session) so the fixture stays realistic; in
// real mode this hits the live endpoint like every other data source in the
// app (see lib/api.ts's MOCK_MODE branch pattern).
let cache: ApiCamera[] | null = null;

async function readSeedFile(): Promise<ApiCamera[]> {
  const filePath = path.join(process.cwd(), "..", "db", "cameras.json");
  try {
    const raw = await readFile(filePath, "utf-8");
    if (!raw.trim()) return [];
    const parsed = JSON.parse(raw) as Array<{
      camera_id: string;
      lat: number;
      lon: number;
      road_node_id?: string;
      road_id?: string;
    }>;
    return parsed.map((c) => ({
      camera_id: c.camera_id,
      latitude: c.lat,
      longitude: c.lon,
      road_id: c.road_id ?? c.road_node_id ?? "",
    }));
  } catch {
    return [];
  }
}

export async function getCameras(): Promise<ApiCamera[]> {
  if (cache) return cache;

  if (MOCK_MODE) {
    const seeded = await readSeedFile();
    if (seeded.length > 0) {
      cache = seeded;
      return cache;
    }
    const { MOCK_CAMERAS } = await import("@/lib/mock/fixtures");
    cache = MOCK_CAMERAS.map((c) => ({
      camera_id: c.camera_id,
      latitude: c.lat,
      longitude: c.lon,
      road_id: c.road_node_id,
    }));
    return cache;
  }

  try {
    const res = await fetch(`${API_URL}/cameras`, { cache: "no-store" });
    if (!res.ok) {
      cache = [];
      return cache;
    }
    const data = (await res.json()) as { cameras: ApiCamera[] };
    cache = data.cameras;
    return cache;
  } catch {
    cache = [];
    return cache;
  }
}
