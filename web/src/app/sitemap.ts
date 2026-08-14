import { queryCompanies } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function sitemap() {
  let companies: Awaited<ReturnType<typeof queryCompanies>> = [];
  try {
    companies = await queryCompanies();
  } catch {
    companies = [];
  }
  const staticPaths = ["", "/companies", "/changes", "/methodology", "/corrections"].map(
    (path) => ({
      url: `https://privacyradar.local${path || "/"}`,
    }),
  );
  return [
    ...staticPaths,
    ...companies.map((company) => ({
      url: `https://privacyradar.local/companies/${company.slug}`,
    })),
  ];
}
