"use client";

import { FormEvent, useState } from "react";

export const MAGIC_LINK_PUBLIC_COPY =
  "If that address can be used, we sent a link.";

type Mode = "sign-in" | "sign-up";

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { message?: string };
    if (payload?.message) return payload.message;
  } catch {
    // fall through to the generic message
  }
  return "Something went wrong. Please try again.";
}

export function LoginForm({ next }: { next: string }) {
  const [mode, setMode] = useState<Mode>("sign-in");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [magicStatus, setMagicStatus] = useState<"idle" | "sent">("idle");
  const callbackURL = next;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const name = String(form.get("name") ?? "").trim();
    try {
      const endpoint =
        mode === "sign-up" ? "/api/auth/sign-up/email" : "/api/auth/sign-in/email";
      const body =
        mode === "sign-up"
          ? { name: name || email.split("@")[0], email, password, callbackURL }
          : { email, password, callbackURL };
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setError(await readError(response));
        return;
      }
      window.location.assign(callbackURL || "/account");
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function onMagicSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("magic-email") ?? "");
    try {
      await fetch("/api/auth/sign-in/magic-link", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, callbackURL }),
      });
    } finally {
      setMagicStatus("sent");
    }
  }

  const inputClass =
    "mt-1 min-h-11 w-full rounded-lg border border-[var(--rule)] bg-[var(--surface)] px-3 text-base outline-none focus:border-[var(--accent)]";

  return (
    <>
      <div
        role="tablist"
        aria-label="Sign in or create account"
        className="mt-8 grid grid-cols-2 rounded-lg border border-[var(--rule)] bg-[var(--surface)] p-1 font-sans text-sm"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "sign-in"}
          onClick={() => {
            setMode("sign-in");
            setError(null);
          }}
          className={`min-h-10 rounded-md px-3 ${
            mode === "sign-in"
              ? "bg-[var(--ink)] text-white"
              : "text-[var(--muted)]"
          }`}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "sign-up"}
          onClick={() => {
            setMode("sign-up");
            setError(null);
          }}
          className={`min-h-10 rounded-md px-3 ${
            mode === "sign-up"
              ? "bg-[var(--ink)] text-white"
              : "text-[var(--muted)]"
          }`}
        >
          Create account
        </button>
      </div>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {mode === "sign-up" ? (
          <div>
            <label htmlFor="name" className="font-sans text-sm font-medium">
              Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              placeholder="How should we address you?"
              className={inputClass}
            />
          </div>
        ) : null}
        <div>
          <label htmlFor="email" className="font-sans text-sm font-medium">
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="password" className="font-sans text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
            className={inputClass}
          />
          {mode === "sign-up" ? (
            <p className="mt-1 font-sans text-xs text-[var(--muted)]">
              At least 8 characters.
            </p>
          ) : null}
        </div>
        {error ? (
          <p role="alert" className="font-sans text-sm text-[var(--danger)]">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="min-h-11 w-full rounded-lg bg-[var(--ink)] px-4 font-sans text-sm font-medium text-white disabled:opacity-60"
        >
          {pending
            ? "One moment…"
            : mode === "sign-up"
              ? "Create account"
              : "Sign in"}
        </button>
      </form>

      <details className="mt-8 border-t border-[var(--rule)] pt-4">
        <summary className="cursor-pointer font-sans text-sm text-[var(--muted)]">
          Prefer a single-use email link?
        </summary>
        <form onSubmit={onMagicSubmit} className="mt-4 space-y-3">
          <label htmlFor="magic-email" className="font-sans text-sm font-medium">
            Email
          </label>
          <input
            id="magic-email"
            name="magic-email"
            type="email"
            required
            autoComplete="email"
            className={inputClass}
          />
          <button
            type="submit"
            className="min-h-11 rounded-lg border border-[var(--ink)] px-4 font-sans text-sm"
          >
            Email me a link
          </button>
        </form>
        {magicStatus === "sent" ? (
          <p className="mt-4 font-sans text-sm" role="status">
            {MAGIC_LINK_PUBLIC_COPY}
          </p>
        ) : null}
      </details>
    </>
  );
}
