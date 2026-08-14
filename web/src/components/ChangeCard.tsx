import Link from "next/link";

const MATERIALITY: Record<string, { label: string; tone: string }> = {
  material: {
    label: "Important",
    tone: "bg-[var(--danger-soft)] text-[var(--danger)]",
  },
  unknown: {
    label: "Moderate",
    tone: "bg-[var(--warning-soft)] text-[var(--warning)]",
  },
  cosmetic: { label: "Minor", tone: "bg-[var(--panel)] text-[var(--muted)]" },
};

export function ChangeCard({
  id,
  companyName,
  companySlug,
  headline,
  summary,
  materiality,
  publishedAt,
  corrected = false,
}: {
  id: string;
  companyName: string;
  companySlug: string;
  headline: string;
  summary: string;
  materiality: string;
  publishedAt: string;
  corrected?: boolean;
}) {
  const when = new Date(publishedAt).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const badge = MATERIALITY[materiality] ?? {
    label: materiality,
    tone: "bg-[var(--panel)] text-[var(--muted)]",
  };
  return (
    <article className="rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-5 shadow-sm">
      <p className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted)]">
        <Link
          href={`/companies/${companySlug}`}
          className="font-medium text-[var(--ink)] hover:underline"
        >
          {companyName}
        </Link>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${badge.tone}`}
        >
          {badge.label}
        </span>
        {corrected ? <span className="text-xs">corrected</span> : null}
        <time dateTime={publishedAt} className="font-mono text-xs">
          {when}
        </time>
      </p>
      <h2 className="mt-2 text-xl font-semibold leading-snug tracking-tight">
        <Link href={`/changes/${id}`} className="hover:underline">
          {headline}
        </Link>
      </h2>
      <p className="mt-1.5 max-w-2xl text-sm text-[var(--muted)]">{summary}</p>
    </article>
  );
}
