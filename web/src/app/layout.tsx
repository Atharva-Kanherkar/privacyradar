import type { Metadata } from "next";
import { Newsreader, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const serif = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "privacyradar",
  description:
    "live inventory of what data companies take, and what just changed in their privacy policies.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${serif.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--paper)] text-[var(--ink)]">
        <header className="border-b border-[var(--rule)]">
          <div className="mx-auto flex max-w-5xl items-baseline justify-between gap-6 px-6 py-5">
            <Link href="/" className="font-serif text-2xl tracking-tight">
              privacyradar
            </Link>
            <nav className="flex gap-5 text-sm">
              <Link href="/companies" className="hover:underline">
                Companies
              </Link>
              <Link href="/about" className="hover:underline">
                About
              </Link>
              <Link href="/feed.xml" className="hover:underline">
                RSS
              </Link>
            </nav>
          </div>
        </header>
        <div className="flex-1">{children}</div>
        <footer className="border-t border-[var(--rule)]">
          <p className="mx-auto max-w-5xl px-6 py-4 text-xs text-[var(--muted)]">
            Not legal advice. Analysis of publicly posted policies, with quotes.
            Hash-first crawler. Models only run when the text actually changes.
          </p>
        </footer>
      </body>
    </html>
  );
}
