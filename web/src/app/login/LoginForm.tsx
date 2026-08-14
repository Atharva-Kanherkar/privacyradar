"use client";

import { FormEvent, useState } from "react";

export const MAGIC_LINK_PUBLIC_COPY =
  "If that address can be used, we sent a link.";

export function LoginForm({ next }: { next: string }) {
  const [status, setStatus] = useState<"idle" | "sent">("idle");
  const callbackURL = next;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    try {
      await fetch("/api/auth/sign-in/magic-link", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, callbackURL }),
      });
    } finally {
      setStatus("sent");
    }
  }

  return (
    <>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label htmlFor="email" className="font-sans text-sm">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          className="mt-1 min-h-11 w-full border border-[var(--rule)] bg-[var(--surface)] px-3"
        />
        <button
          type="submit"
          className="min-h-11 border border-[var(--ink)] bg-[var(--ink)] px-4 font-sans text-sm text-[var(--paper)]"
        >
          Email me a link
        </button>
      </form>
      {status === "sent" ? (
        <p className="mt-6" role="status">
          {MAGIC_LINK_PUBLIC_COPY}
        </p>
      ) : null}
    </>
  );
}
