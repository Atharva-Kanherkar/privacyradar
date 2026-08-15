import { queryCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

const base = process.env.PUBLIC_BASE_URL ?? "https://privacyradar.local";

export default async function sitemap() {
  let companies: Awaited<ReturnType<typeof queryCompanies>> = [];
  try {
    companies = await queryCompanies();
  } catch {
    companies = [];
  }
  const staticPaths = ["", "/companies", "/changes", "/methodology", "/corrections"].map(
    (path) => ({
      url: `${base}${path || "/"}`,
    }),
  );
  return [
    ...staticPaths,
    ...companies.map((company) => ({
      url: `${base}/companies/${company.slug}`,
    })),
  ];
}
