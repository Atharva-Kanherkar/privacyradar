"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function AuthNav() {
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    void fetch("/api/auth/get-session", { credentials: "include" })
      .then((res) => res.json())
      .then((payload: { user?: { id?: string } } | null) => {
        setSignedIn(Boolean(payload?.user?.id));
      })
      .catch(() => {
        setSignedIn(false);
      });
  }, []);

  return (
    <>
      {signedIn ? (
        <Link
          href="/radar"
          className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-[var(--muted)] transition-colors hover:bg-[var(--panel)] hover:text-[var(--ink)]"
        >
          My Radar
        </Link>
      ) : null}
      <Link
        href={signedIn ? "/account" : "/login"}
        className={
          signedIn
            ? "inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-[var(--muted)] transition-colors hover:bg-[var(--panel)] hover:text-[var(--ink)]"
            : "ml-1 inline-flex min-h-10 items-center rounded-full bg-[var(--ink)] px-5 text-sm font-medium text-[var(--ink-contrast)] transition-opacity hover:opacity-90"
        }
      >
        {signedIn ? "Account" : "Sign in"}
      </Link>
    </>
  );
}
