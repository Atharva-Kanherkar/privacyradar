import type { PublishedClaimRow } from "@/lib/db";
import { attributeMeta } from "@/lib/data-categories";
import { DataTypeIcon } from "./DataTypeIcon";

type Tone = "neutral" | "danger" | "good" | "unclear";

function toneFor(claim: PublishedClaimRow): Tone {
  if (claim.polarity === "negated") return "good";
  if (claim.polarity === "unspecified") return "unclear";
  if (claim.category === "retention" && claim.attribute === "unspecified") {
    return "unclear";
  }
  if (claim.category === "sensitive") return "danger";
  if (claim.category === "sharing" && claim.attribute !== "none_disclosed") {
    return "danger";
  }
  if (claim.category === "purpose" && claim.attribute === "ai_training") {
    return "danger";
  }
  if (claim.category === "control" && claim.attribute !== "none_disclosed") {
    return "good";
  }
  return "neutral";
}

const BADGE: Record<Tone, { text: string; className: string }> = {
  neutral: { text: "Collected", className: "bg-[var(--panel)] text-[var(--muted)]" },
  danger: { text: "Disclosed", className: "bg-[var(--danger-soft)] text-[var(--danger)]" },
  good: { text: "Good sign", className: "bg-[var(--good-soft)] text-[var(--good)]" },
  unclear: { text: "Unclear", className: "bg-[var(--warning-soft)] text-[var(--warning)]" },
};

function badgeText(claim: PublishedClaimRow, tone: Tone): string {
  if (claim.polarity === "negated") return "Says no";
  if (claim.polarity === "unspecified" || tone === "unclear") return "Unclear";
  if (claim.category === "data_collected") return "Collected";
  if (claim.category === "purpose") return "Yes";
  if (claim.category === "sharing" || claim.category === "retention") {
    return "Disclosed";
  }
  if (claim.category === "control") return "Good sign";
  return BADGE[tone].text;
}

export function ClaimCard({ claim }: { claim: PublishedClaimRow }) {
  const tone = toneFor(claim);
  const meta = attributeMeta(claim.category, claim.attribute);
  const iconTone =
    tone === "danger"
      ? "bg-[var(--danger-soft)] text-[var(--danger)]"
      : tone === "good"
        ? "bg-[var(--good-soft)] text-[var(--good)]"
        : "bg-[var(--panel)] text-[var(--muted)]";
  return (
    <details
      className="group rounded-2xl border border-[var(--rule)] bg-[var(--surface)] open:border-[var(--accent)]"
    >
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-3 p-4 [&::-webkit-details-marker]:hidden">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconTone}`}
        >
          <DataTypeIcon attribute={claim.attribute} size={18} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold">{meta.label}</span>
          {meta.plain ? (
            <span className="block truncate text-xs text-[var(--muted)]">
              {meta.plain}
            </span>
          ) : null}
        </span>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${BADGE[tone].className}`}
        >
          {badgeText(claim, tone)}
        </span>
      </summary>
      <div className="border-t border-[var(--rule)] px-4 py-3">
        <blockquote className="border-l border-[var(--accent)] pl-3 text-sm italic text-[var(--muted)]">
          &ldquo;{claim.quote}&rdquo;
        </blockquote>
        <p className="mt-2 font-mono text-[0.65rem] text-[var(--muted)]">
          snapshot {claim.snapshot_id} · revision {claim.revision_n}
        </p>
      </div>
    </details>
  );
}
