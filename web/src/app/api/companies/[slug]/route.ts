import { queryCompany } from "@/lib/db";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  try {
    const data = await queryCompany(slug);
    if (!data) {
      return NextResponse.json({ error: "not_found" }, { status: 404 });
    }
    const { company, document_changes } = data;
    return NextResponse.json({
      slug: company.slug,
      name: company.name,
      category: company.category,
      website: company.website,
      region: company.region,
      privacy_url: company.privacy_url,
      source_health: company.source_health ?? "pending",
      last_verified_at: company.last_verified_at,
      current_snapshot_id: company.current_snapshot_id,
      current_observation_id: company.current_observation_id,
      normalizer_version: company.normalizer_version,
      document_changes,
    });
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}
