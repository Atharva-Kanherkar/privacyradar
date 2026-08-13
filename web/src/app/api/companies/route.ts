import { queryCompanies } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function publicCompany(row: Awaited<ReturnType<typeof queryCompanies>>[number]) {
  return {
    slug: row.slug,
    name: row.name,
    category: row.category,
    website: row.website,
    region: row.region,
    source_health: row.source_health ?? "pending",
    last_verified_at: row.last_verified_at,
    current_snapshot_id: row.current_snapshot_id,
  };
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  try {
    const rows = await queryCompanies(q);
    return NextResponse.json(rows.map(publicCompany));
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}
