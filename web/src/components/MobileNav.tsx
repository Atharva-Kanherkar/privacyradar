"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { AuthNav } from "./AuthNav";
import { GitHubIcon } from "./GitHubIcon";
import { ThemeToggle } from "./ThemeToggle";

export function MobileNav({
  links,
}: {
  links: { href: string; label: string }[];
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="sm:hidden">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={open ? "Close menu" : "Open menu"}
        className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-foreground"
      >
        {open ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
      </button>
      {open ? (
        <div className="absolute left-0 right-0 top-full z-40 border-b border-border bg-card shadow-lg">
          <nav aria-label="Primary" className="flex flex-col px-4 py-2">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="inline-flex min-h-12 items-center rounded-lg px-2 text-base font-medium"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2 border-t border-border px-6 py-3">
            <a
              href="https://github.com/Atharva-Kanherkar/privacyradar"
              target="_blank"
              rel="noreferrer"
              aria-label="Source code on GitHub"
              className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground"
            >
              <GitHubIcon />
            </a>
            <ThemeToggle />
            <div className="ml-auto" onClick={() => setOpen(false)}>
              <AuthNav />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
