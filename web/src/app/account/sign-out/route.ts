import { signOutRequest } from "@/lib/consumer";
import { redirectSeeOther } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  await signOutRequest(request);
  return redirectSeeOther("/login");
}
