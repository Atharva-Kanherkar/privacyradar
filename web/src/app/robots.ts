import type { MetadataRoute } from "next";

const base = process.env.PUBLIC_BASE_URL ?? "https://privacyradar.local";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${base}/sitemap.xml`,
  };
}
