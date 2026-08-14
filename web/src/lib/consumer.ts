import { auth } from "@/lib/auth";
import { sql } from "@/lib/db";

export async function deleteConsumerAccount(userId: string): Promise<void> {
  if (!sql) {
    throw new Error("database unconfigured");
  }
  await sql`select privacyradar_delete_consumer(${userId})`;
}

export async function signOutRequest(request: Request): Promise<void> {
  await auth.api.signOut({ headers: request.headers });
}
