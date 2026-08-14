import { getSessionFromCookies } from "@/lib/session";
import { redirectSeeOther } from "@/lib/http";
import { companyIdForSlug, followCompany } from "@/lib/watches";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return redirectSeeOther(
      `/login?next=${encodeURIComponent(`/companies/${slug}/watch`)}`,
    );
  }
  const companyId = await companyIdForSlug(slug);
  if (!companyId) {
    return redirectSeeOther("/companies");
  }
  await followCompany(session.user.id, companyId, "resume");
  return redirectSeeOther(`/companies/${slug}`);
}
