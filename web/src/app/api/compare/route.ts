import { loadComparison, parseCompanySlugs, recordCompareEvent } from "@/lib/compare";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const { slugs, truncated } = parseCompanySlugs(
      request.nextUrl.searchParams.get("companies") ?? undefined,
    );
    const payload = await loadComparison(slugs, truncated);
    if (slugs.length >= 2) {
      await recordCompareEvent("compare_start");
      if (payload.status === "comparable") {
        await recordCompareEvent("compare_complete");
      }
    }
    return NextResponse.json(payload);
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}
