import { redirectSeeOther } from "@/lib/http";
import { canonicalComparePath, parseCompanySlugs } from "@/lib/compare";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const form = await request.formData();
  const selected = form.getAll("c").map((value) => String(value));
  const { slugs } = parseCompanySlugs(selected);
  return redirectSeeOther(canonicalComparePath(slugs));
}
