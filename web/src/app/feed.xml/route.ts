import { listEvents } from "@/lib/db";

export const revalidate = 60;

export async function GET() {
  const events = await listEvents(50);
  const items = events
    .map(
      (e) => `    <item>
      <title>${escapeXml(`${e.name}: ${e.headline}`)}</title>
      <link>https://privacyradar.local/companies/${e.slug}</link>
      <guid>${e.id}</guid>
      <pubDate>${new Date(e.published_at).toUTCString()}</pubDate>
      <description>${escapeXml(e.summary)}</description>
    </item>`,
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>privacyradar - material privacy changes</title>
    <link>https://privacyradar.local</link>
    <description>What data companies take, and what just changed.</description>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "s-maxage=60, stale-while-revalidate=300",
    },
  });
}

function escapeXml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
