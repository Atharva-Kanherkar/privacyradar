import { toNextJsHandler } from "better-auth/next-js";
import { NextRequest } from "next/server";
import { auth } from "@/lib/auth";
import { safeCallbackURL } from "@/lib/callback-url";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const handler = toNextJsHandler(auth);

const CALLBACK_KEYS = [
  "callbackURL",
  "errorCallbackURL",
  "newUserCallbackURL",
] as const;

function sanitizeAuthRequest(request: Request): Request {
  const url = new URL(request.url);
  if (!url.pathname.includes("/magic-link/verify")) {
    return request;
  }
  for (const key of CALLBACK_KEYS) {
    if (url.searchParams.has(key)) {
      url.searchParams.set(key, safeCallbackURL(url.searchParams.get(key)));
    }
  }
  return new Request(url, request);
}

export async function GET(request: NextRequest) {
  return handler.GET(sanitizeAuthRequest(request));
}

export async function POST(request: NextRequest) {
  return handler.POST(request);
}
