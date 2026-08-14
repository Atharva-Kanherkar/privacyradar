export const REGIONS = ["US", "EU", "UK", "other", "unspecified"] as const;

export type PolicyRegion = (typeof REGIONS)[number];

export function isPolicyRegion(value: string): value is PolicyRegion {
  return (REGIONS as readonly string[]).includes(value);
}
