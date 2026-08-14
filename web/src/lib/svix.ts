import { createHmac, timingSafeEqual } from "node:crypto";

export function verifySvixSignature(opts: {
  secret: string;
  body: string;
  svixId: string;
  svixTimestamp: string;
  svixSignature: string;
  nowSeconds?: number;
}): boolean {
  const now = opts.nowSeconds ?? Math.floor(Date.now() / 1000);
  const ts = Number(opts.svixTimestamp);
  if (!Number.isFinite(ts) || Math.abs(now - ts) > 300) return false;
  let raw = opts.secret;
  if (raw.startsWith("whsec_")) raw = raw.slice("whsec_".length);
  let key: Buffer;
  try {
    key = Buffer.from(raw, "base64");
  } catch {
    key = Buffer.from(raw, "utf8");
  }
  const signed = Buffer.concat([
    Buffer.from(`${opts.svixId}.${opts.svixTimestamp}.`, "ascii"),
    Buffer.from(opts.body, "utf8"),
  ]);
  const digest = createHmac("sha256", key).update(signed).digest("base64");
  const candidates = opts.svixSignature.split(" ").map((part) => {
    const trimmed = part.trim();
    return trimmed.startsWith("v1,") ? trimmed.slice(3) : trimmed;
  });
  const expected = Buffer.from(digest);
  return candidates.some((item) => {
    const got = Buffer.from(item);
    return got.length === expected.length && timingSafeEqual(got, expected);
  });
}
