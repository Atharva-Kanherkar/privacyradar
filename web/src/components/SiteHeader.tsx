import Link from "next/link";
import { Radar } from "lucide-react";
import { AuthNav } from "./AuthNav";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/companies", label: "Companies" },
  { href: "/compare", label: "Compare" },
  { href: "/changes", label: "Changes" },
  { href: "/methodology", label: "How it works" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--rule)] bg-[var(--surface)]">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="mx-auto flex max-w-6xl min-w-0 flex-wrap items-center justify-between gap-x-6 gap-y-3 px-6 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent)] text-[var(--accent-contrast)]">
            <Radar size={20} aria-hidden="true" />
          </span>
          <span className="text-lg font-semibold tracking-tight">
            PrivacyRadar
          </span>
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 sm:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-[var(--muted)] transition-colors hover:bg-[var(--panel)] hover:text-[var(--ink)]"
            >
              {link.label}
            </Link>
          ))}
          <ThemeToggle />
          <AuthNav />
        </nav>
        <details className="sm:hidden">
          <summary className="inline-flex min-h-11 min-w-11 cursor-pointer items-center text-sm font-medium">
            Menu
          </summary>
          <nav aria-label="Primary" className="mt-2 flex flex-col">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="inline-flex min-h-11 items-center text-sm font-medium"
              >
                {link.label}
              </Link>
            ))}
            <div className="flex items-center gap-1">
              <ThemeToggle />
              <AuthNav />
            </div>
          </nav>
        </details>
      </div>
    </header>
  );
}
