import Link from "next/link";
import { accountsEnabled } from "@/lib/flags";
import { AuthNav } from "./AuthNav";
import { GitHubIcon } from "./GitHubIcon";
import { MobileNav } from "./MobileNav";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/companies", label: "Companies" },
  { href: "/compare", label: "Compare" },
  { href: "/changes", label: "Changes" },
  { href: "/methodology", label: "How it works" },
];

export function SiteHeader() {
  const accounts = accountsEnabled();
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="relative mx-auto flex max-w-6xl min-w-0 items-center justify-between gap-x-6 px-4 py-3 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2.5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" width={36} height={36} />
          <span className="truncate text-lg font-semibold tracking-tight">
            PrivacyRadar
          </span>
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 sm:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://github.com/Atharva-Kanherkar/privacyradar"
            target="_blank"
            rel="noreferrer"
            aria-label="Source code on GitHub"
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <GitHubIcon />
          </a>
          <ThemeToggle />
          {accounts ? (
            <AuthNav />
          ) : (
            <span className="ml-1 inline-flex min-h-10 items-center rounded-md bg-muted px-4 text-sm font-medium text-muted-foreground">
              Sign in coming soon
            </span>
          )}
        </nav>
        <MobileNav links={LINKS} accounts={accounts} />
      </div>
    </header>
  );
}
