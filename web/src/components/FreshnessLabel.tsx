export function FreshnessLabel({
  lastCheckedAt,
  health,
}: {
  lastCheckedAt: string | null;
  health: "pending" | "healthy" | "degraded" | "quarantined" | null;
}) {
  const checked = lastCheckedAt
    ? `last checked ${new Date(lastCheckedAt).toLocaleDateString("en-US")}`
    : "not yet checked";
  let status = "pending";
  if (health === "healthy") status = "healthy";
  if (health === "degraded" || health === "quarantined") status = "check delayed";
  return (
    <span className="font-sans text-sm text-[var(--muted)]">
      <span className="font-mono text-xs">{checked}</span>
      <span className="mx-2" aria-hidden="true">
        ·
      </span>
      <span>{status}</span>
    </span>
  );
}
