export function safeCallbackURL(raw: string | null | undefined): string {
  const fallback = "/account";
  if (!raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//")) return fallback;
  if (raw.includes("://") || raw.includes("\\") || raw.includes("@")) return fallback;
  return raw;
}
