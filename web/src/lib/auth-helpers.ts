import { createHash } from "node:crypto";
import { safeCallbackURL } from "./callback-url";

export { safeCallbackURL };

export function emailHash(email: string): string {
  return createHash("sha256").update(email.trim().toLowerCase()).digest("hex");
}
