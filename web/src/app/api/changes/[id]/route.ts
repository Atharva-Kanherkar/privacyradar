import { queryDocumentChange } from "@/lib/db";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  try {
    const change = await queryDocumentChange(id);
    if (!change) {
      return NextResponse.json({ error: "not_found" }, { status: 404 });
    }
    return NextResponse.json(change);
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 503 });
  }
}
