import { attributeMeta, SENSITIVE } from "@/lib/data-categories";
import { DataTypeIcon } from "./DataTypeIcon";

export function DataTypeChip({ attribute }: { attribute: string }) {
  const sensitive = attribute in SENSITIVE;
  const meta = attributeMeta(sensitive ? "sensitive" : "data_collected", attribute);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${
        sensitive
          ? "bg-[var(--danger-soft)] text-[var(--danger)]"
          : "bg-muted text-muted-foreground"
      }`}
    >
      <DataTypeIcon attribute={attribute} size={12} />
      {meta.label}
    </span>
  );
}
