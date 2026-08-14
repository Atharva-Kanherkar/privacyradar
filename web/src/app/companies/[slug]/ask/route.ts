import { redirectSeeOther } from "@/lib/http";
import { askCompany, hashIdentity } from "@/lib/assistant";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  if (!/^[a-z0-9-]+$/.test(slug)) {
    return redirectSeeOther("/companies");
  }
  const form = await request.formData();
  const question = String(form.get("question") ?? "").slice(0, 500);
  const session = await getSessionFromCookies();
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const identity = hashIdentity(session?.user?.id ?? forwarded ?? "anonymous");
  const result = await askCompany(slug, question, identity);
  return redirectSeeOther(`/companies/${slug}?ask=${result.status}`);
}
