import { NextResponse } from "next/server";

export function redirectSeeOther(path: string): NextResponse {
  return new NextResponse(null, {
    status: 303,
    headers: { Location: path },
  });
}
