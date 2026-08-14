import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { CompanyRow } from "@/lib/db";
import { SENSITIVE } from "@/lib/data-categories";
import { CompanyLogo } from "./CompanyLogo";
import { DataTypeChip } from "./DataTypeChip";
import { FreshnessLabel } from "./FreshnessLabel";

const CHIP_LIMIT = 6;

function orderAttributes(attributes: string[]): string[] {
  // Sensitive categories first, then alphabetical, so the scary stuff is visible.
  return [...attributes].sort((a, b) => {
    const sa = a in SENSITIVE ? 0 : 1;
    const sb = b in SENSITIVE ? 0 : 1;
    if (sa !== sb) return sa - sb;
    return a.localeCompare(b);
  });
}

export function CompanyCard({
  company,
  dataTypes,
}: {
  company: Pick<
    CompanyRow,
    "slug" | "name" | "category" | "website" | "last_verified_at" | "source_health"
  >;
  /** null means the data-type lookup failed, which is not an empty review. */
  dataTypes: string[] | null;
}) {
  const ordered = orderAttributes(dataTypes ?? []);
  const shown = ordered.slice(0, CHIP_LIMIT);
  const extra = ordered.length - shown.length;
  return (
    <Link
      href={`/companies/${company.slug}`}
      className="group flex flex-col gap-3 rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <CompanyLogo name={company.name} website={company.website} size={40} />
          <div>
            <h3 className="text-lg font-semibold tracking-tight">{company.name}</h3>
            <p className="text-xs text-[var(--muted)]">{company.category}</p>
          </div>
        </div>
        <ArrowUpRight
          size={18}
          aria-hidden="true"
          className="shrink-0 text-[var(--muted)] transition-colors group-hover:text-[var(--accent)]"
        />
      </div>
      {shown.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {shown.map((attribute) => (
            <DataTypeChip key={attribute} attribute={attribute} />
          ))}
          {extra > 0 ? (
            <span className="inline-flex items-center rounded-full bg-[var(--panel)] px-2.5 py-1 text-xs font-medium text-[var(--muted)]">
              +{extra} more
            </span>
          ) : null}
        </div>
      ) : dataTypes === null ? (
        <p className="text-xs text-[var(--muted)]">
          Data summary unavailable right now.
        </p>
      ) : (
        <p className="text-xs text-[var(--muted)]">
          Policy captured. Evidence review in progress.
        </p>
      )}
      <p className="mt-auto pt-1">
        <FreshnessLabel
          lastCheckedAt={company.last_verified_at}
          health={company.source_health}
        />
      </p>
    </Link>
  );
}
