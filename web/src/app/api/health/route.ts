import { sql } from "@/lib/db";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type HealthBody = {
  status: "ok" | "degraded";
  database: "connected" | "unavailable" | "unconfigured";
};

export async function GET() {
  if (!sql) {
    const body: HealthBody = { status: "ok", database: "unconfigured" };
    return NextResponse.json(body, { status: 200 });
  }

  try {
    await sql`select 1 as ok`;
    const body: HealthBody = { status: "ok", database: "connected" };
    return NextResponse.json(body, { status: 200 });
  } catch {
    const body: HealthBody = { status: "degraded", database: "unavailable" };
    return NextResponse.json(body, { status: 503 });
  }
}
