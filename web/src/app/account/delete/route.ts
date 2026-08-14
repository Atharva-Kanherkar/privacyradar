import { deleteConsumerAccount, signOutRequest } from "@/lib/consumer";
import { redirectSeeOther } from "@/lib/http";
import { getSessionFromCookies } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    return redirectSeeOther("/login");
  }
  const form = await request.formData();
  if (String(form.get("confirm") ?? "") !== "DELETE") {
    return redirectSeeOther("/account");
  }
  await deleteConsumerAccount(session.user.id);
  await signOutRequest(request);
  return redirectSeeOther("/login");
}
