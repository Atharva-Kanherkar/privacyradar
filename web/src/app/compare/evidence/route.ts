import { redirectSeeOther } from "@/lib/http";
import { recordCompareEvent } from "@/lib/compare";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug") ?? "";
  const claim = url.searchParams.get("claim") ?? "";
  if (!/^[a-z0-9-]+$/.test(slug) || !/^[a-f0-9]{64}$/.test(claim)) {
    return redirectSeeOther("/compare");
  }
  await recordCompareEvent("compare_evidence");
  return redirectSeeOther(`/companies/${slug}#claim-${claim}`);
}
