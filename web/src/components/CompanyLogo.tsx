"use client";

import { useState } from "react";

function domainOf(website: string | null): string | null {
  if (!website) return null;
  try {
    return new URL(website).hostname;
  } catch {
    return null;
  }
}

/**
 * Real company logo via the site's own favicon (Google s2 service, no API
 * key). Falls back to an initial if the image fails, so we never show a
 * broken image or a made-up mark.
 */
export function CompanyLogo({
  name,
  website,
  size = 40,
  className = "",
}: {
  name: string;
  website: string | null;
  size?: number;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const domain = domainOf(website);
  const src = domain
    ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128`
    : null;

  if (!src || failed) {
    return (
      <span
        aria-hidden="true"
        style={{ width: size, height: size }}
        className={`flex shrink-0 items-center justify-center rounded-xl bg-[var(--panel)] text-sm font-semibold text-[var(--muted)] ${className}`}
      >
        {name.charAt(0).toUpperCase()}
      </span>
    );
  }

  return (
    <span
      style={{ width: size, height: size }}
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-[var(--rule)] bg-white ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        width={Math.round(size * 0.62)}
        height={Math.round(size * 0.62)}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </span>
  );
}
