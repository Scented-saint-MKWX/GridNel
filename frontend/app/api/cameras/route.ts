import { NextResponse } from "next/server";
import { getCameras } from "@/lib/cameras";

export async function GET() {
  const cameras = await getCameras();
  return NextResponse.json(cameras);
}
