import { NextRequest, NextResponse } from "next/server";
import { redirectSeeOther } from "@/lib/http";
import { getSessionFromCookies } from "@/lib/session";
import { companyIdForSlug, followCompany, isWatchSource } from "@/lib/watches";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const contentType = request.headers.get("content-type") ?? "";
  let slug = "";
  let source = "company_page";
  if (contentType.includes("application/json")) {
    const body = (await request.json()) as Record<string, unknown>;
    if ("userId" in body || "user_id" in body) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    slug = String(body.slug ?? "");
    source = String(body.source ?? "company_page");
  } else {
    const form = await request.formData();
    if (form.has("userId") || form.has("user_id")) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    slug = String(form.get("slug") ?? "");
    source = String(form.get("source") ?? "company_page");
  }
  if (!isWatchSource(source)) {
    return NextResponse.json({ error: "invalid" }, { status: 400 });
  }
  const companyId = await companyIdForSlug(slug);
  if (!companyId) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  await followCompany(session.user.id, companyId, source);
  if (contentType.includes("application/json")) {
    return NextResponse.json({ ok: true, slug });
  }
  return redirectSeeOther(`/companies/${slug}`);
}
