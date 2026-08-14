import { NextRequest, NextResponse } from "next/server";
import { redirectSeeOther } from "@/lib/http";
import { getSessionFromCookies } from "@/lib/session";
import { companyIdForSlug, unfollowCompany } from "@/lib/watches";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ slug: string }> },
) {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { slug } = await context.params;
  const companyId = await companyIdForSlug(slug);
  if (!companyId) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  await unfollowCompany(session.user.id, companyId);
  const contentType = request.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return NextResponse.json({ ok: true, slug });
  }
  const referer = request.headers.get("referer") ?? "";
  if (referer.includes("/radar")) {
    return redirectSeeOther("/radar/watching");
  }
  return redirectSeeOther(`/companies/${slug}`);
}
