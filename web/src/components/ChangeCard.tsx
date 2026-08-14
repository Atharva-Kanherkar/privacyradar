import Link from "next/link";

const MATERIALITY: Record<string, string> = {
  material: "Important",
  unknown: "Moderate",
  cosmetic: "Minor",
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
  return (
    <article className="py-6">
      <p className="font-sans text-sm text-[var(--muted)]">
        <Link href={`/companies/${companySlug}`} className="hover:underline">
          {companyName}
        </Link>
        <span className="mx-2" aria-hidden="true">
          ·
        </span>
        <span>{MATERIALITY[materiality] ?? materiality}</span>
        {corrected ? <span> · corrected</span> : null}
        <span className="mx-2" aria-hidden="true">
          ·
        </span>
        <time dateTime={publishedAt} className="font-mono text-xs">
          {when}
        </time>
      </p>
      <h2 className="mt-2 text-2xl leading-snug">
        <Link href={`/changes/${id}`}>{headline}</Link>
      </h2>
      <p className="mt-2 max-w-2xl text-[var(--muted)]">{summary}</p>
    </article>
  );
}
