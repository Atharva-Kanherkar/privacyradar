import { attributeMeta, SENSITIVE } from "@/lib/data-categories";
import { DataTypeIcon } from "./DataTypeIcon";

export function DataTypeChip({ attribute }: { attribute: string }) {
  const sensitive = attribute in SENSITIVE;
  const meta = attributeMeta(sensitive ? "sensitive" : "data_collected", attribute);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        sensitive
          ? "bg-[var(--danger-soft)] text-[var(--danger)]"
          : "bg-[var(--panel)] text-[var(--muted)]"
      }`}
    >
      <DataTypeIcon attribute={attribute} size={12} />
      {meta.label}
    </span>
  );
}
