export function EvidenceQuote({
  quote,
  snapshotId,
  revisionN,
  region,
}: {
  quote: string;
  snapshotId: string;
  revisionN: number;
  region: string | null;
}) {
  return (
    <figure className="mt-3 border-l border-[var(--important)] pl-3">
      <blockquote className="text-sm italic text-[var(--muted)]">“{quote}”</blockquote>
      <figcaption className="mt-2 font-mono text-xs text-[var(--muted)]">
        snapshot {snapshotId} · revision {revisionN}
        {region ? ` · source region ${region}` : " · source region not labeled"}
      </figcaption>
    </figure>
  );
}
