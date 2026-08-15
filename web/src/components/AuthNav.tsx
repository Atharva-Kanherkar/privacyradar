"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

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
          className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          My Radar
        </Link>
      ) : null}
      {signedIn ? (
        <Link
          href="/account"
          className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          Account
        </Link>
      ) : (
        <Button asChild className="ml-1 min-h-10 px-5">
          <Link href="/login">Sign in</Link>
        </Button>
      )}
    </>
  );
}
