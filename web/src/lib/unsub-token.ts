import { createHmac, timingSafeEqual } from "node:crypto";

function secret(): string {
  return process.env.AUTH_SECRET || process.env.NOTIFY_SIGNING_KEY || "";
}

export function signUnsubToken(
  userId: string,
  purpose = "unsub",
  exp = Math.floor(Date.now() / 1000) + 90 * 24 * 3600,
): string {
  const payload = `${userId}|${purpose}|${exp}`;
  const body = Buffer.from(payload, "utf8").toString("base64url");
  const sig = createHmac("sha256", secret()).update(body).digest("hex");
  return `${body}.${sig}`;
}

export function verifyUnsubToken(
  token: string,
): { userId: string; purpose: string } | null {
  const key = secret();
  if (!key || token.split(".").length !== 2) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const expected = createHmac("sha256", key).update(body).digest("hex");
  const a = Buffer.from(expected, "hex");
  const b = Buffer.from(sig, "hex");
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  let payload: string;
  try {
    payload = Buffer.from(body, "base64url").toString("utf8");
  } catch {
    return null;
  }
  const parts = payload.split("|");
  if (parts.length !== 3) return null;
  const [userId, purpose, expRaw] = parts;
  const exp = Number(expRaw);
  if (!userId || !purpose || !Number.isFinite(exp) || exp < Date.now() / 1000) {
    return null;
  }
  if (purpose !== "unsub" && !purpose.startsWith("mute:")) return null;
  return { userId, purpose };
}
