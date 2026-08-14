import Link from "next/link";
import { AuthNav } from "./AuthNav";

const LINKS = [
  { href: "/companies", label: "Companies" },
  { href: "/compare", label: "Compare" },
  { href: "/changes", label: "Changes" },
  { href: "/methodology", label: "Methodology" },
  { href: "/feed.xml", label: "RSS" },
];

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--rule)]">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="mx-auto flex max-w-5xl min-w-0 flex-wrap items-center justify-between gap-x-6 gap-y-3 px-6 py-4">
        <Link href="/" className="font-serif text-2xl tracking-tight">
          PrivacyRadar
        </Link>
        <nav aria-label="Primary" className="hidden gap-1 sm:flex">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="inline-flex min-h-11 items-center px-3 font-sans text-sm hover:underline"
            >
              {link.label}
            </Link>
          ))}
          <AuthNav />
        </nav>
        <details className="sm:hidden">
          <summary className="inline-flex min-h-11 min-w-11 cursor-pointer items-center font-sans text-sm">
            Menu
          </summary>
          <nav aria-label="Primary" className="mt-2 flex flex-col">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="inline-flex min-h-11 items-center font-sans text-sm hover:underline"
              >
                {link.label}
              </Link>
            ))}
            <AuthNav />
          </nav>
        </details>
      </div>
    </header>
  );
}
