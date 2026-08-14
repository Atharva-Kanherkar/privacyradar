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
          className="inline-flex min-h-11 items-center px-3 font-sans text-sm hover:underline"
        >
          My Radar
        </Link>
      ) : null}
      <Link
        href={signedIn ? "/account" : "/login"}
        className="inline-flex min-h-11 items-center px-3 font-sans text-sm hover:underline"
      >
        {signedIn ? "Account" : "Sign in"}
      </Link>
    </>
  );
}
