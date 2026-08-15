import { ImageResponse } from "next/og";
import { attributeMeta, SENSITIVE } from "@/lib/data-categories";
import { listPublishedClaims, sql } from "@/lib/db";

export const runtime = "nodejs";
export const alt = "What this company's privacy policy discloses it collects";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const MARK = (
  <svg width="96" height="96" viewBox="0 0 512 512">
    <path
      d="M256 26 L282 44 C330 74 388 88 448 92 L448 268 C448 366 372 448 256 492 C140 448 64 366 64 268 L64 92 C124 88 182 74 230 44 Z"
      fill="#171E2C"
    />
    <circle cx="256" cy="276" r="148" fill="none" stroke="#FFFFFF" strokeWidth="24" />
    <path d="M256 276 L336 29 L472 131 Z" fill="#29DE8D" />
    <circle cx="380" cy="148" r="17" fill="none" stroke="#171E2C" strokeWidth="9" />
    <circle cx="256" cy="276" r="36" fill="#29DE8D" />
  </svg>
);

export default async function Image({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let name = "This company";
  let attributes: string[] = [];
  try {
    if (sql && /^[a-z0-9-]{1,80}$/.test(slug)) {
      const rows = await sql<{ id: string; name: string }[]>`
        select id, name from companies where slug = ${slug} limit 1
      `;
      if (rows[0]) {
        name = rows[0].name;
        const claims = await listPublishedClaims(rows[0].id);
        attributes = claims
          .filter(
            (claim) =>
              (claim.category === "data_collected" || claim.category === "sensitive") &&
              claim.polarity === "disclosed" &&
              claim.attribute !== "none_disclosed",
          )
          .sort((a, b) =>
            (a.attribute in SENSITIVE ? 0 : 1) - (b.attribute in SENSITIVE ? 0 : 1),
          )
          .map((claim) =>
            attributeMeta(
              claim.attribute in SENSITIVE ? "sensitive" : "data_collected",
              claim.attribute,
            ).label,
          );
        attributes = [...new Set(attributes)].slice(0, 8);
      }
    }
  } catch {
    // render the generic card if the database is unavailable
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: 72,
          backgroundColor: "#0a0a0a",
          color: "#ededed",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {MARK}
          <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: "-0.02em" }}>
            PrivacyRadar
          </div>
        </div>
        <div
          style={{
            marginTop: 40,
            fontSize: 62,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
            maxWidth: 1000,
          }}
        >
          {`What ${name} takes from you`}
        </div>
        {attributes.length > 0 ? (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
              marginTop: 36,
              maxWidth: 1040,
            }}
          >
            {attributes.map((label) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  padding: "10px 22px",
                  borderRadius: 10,
                  border: "1px solid #262626",
                  backgroundColor: "#1a1a1a",
                  color: "#ededed",
                  fontSize: 27,
                }}
              >
                {label}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: 36, fontSize: 30, color: "#a3a3a3" }}>
            Evidence-backed disclosures, straight from the captured policy.
          </div>
        )}
        <div style={{ marginTop: 44, fontSize: 26, color: "#a3a3a3" }}>
          Every claim backed by the exact policy quote
        </div>
      </div>
    ),
    size,
  );
}
