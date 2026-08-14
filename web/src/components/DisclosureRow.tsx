import { EvidenceQuote } from "./EvidenceQuote";

const POLARITY: Record<string, string> = {
  disclosed: "disclosed",
  negated: "not disclosed",
  unspecified: "unspecified in the captured policy",
};

export function DisclosureRow({
  claimKey,
  category,
  attribute,
  polarity,
  quote,
  snapshotId,
  revisionN,
  region,
}: {
  claimKey: string;
  category: string;
  attribute: string;
  polarity: string;
  quote: string;
  snapshotId: string;
  revisionN: number;
  region: string | null;
}) {
  const label = `${category.replaceAll("_", " ")} · ${attribute.replaceAll("_", " ")}`;
  return (
    <li id={`claim-${claimKey}`} className="border border-[var(--rule)] bg-[var(--surface)] p-5">
      <p className="font-sans text-sm uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-lg">
        We found: {POLARITY[polarity] ?? polarity}
      </p>
      <EvidenceQuote
        quote={quote}
        snapshotId={snapshotId}
        revisionN={revisionN}
        region={region}
      />
      <details className="mt-3">
        <summary className="min-h-11 cursor-pointer font-sans text-sm underline">
          Evidence details
        </summary>
        <p className="mt-2 font-mono text-xs text-[var(--muted)]">
          claim {claimKey}
        </p>
      </details>
    </li>
  );
}
