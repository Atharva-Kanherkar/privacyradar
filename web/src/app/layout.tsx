import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const baseUrl = process.env.PUBLIC_BASE_URL ?? "https://privacyradar.local";

export const metadata: Metadata = {
  title: {
    default: "PrivacyRadar: see what companies take from you",
    template: "%s · PrivacyRadar",
  },
  description:
    "PrivacyRadar reads privacy policies so you don't have to. See exactly what data each company collects (your voice, location, messages) with the receipts, and get alerted when it changes.",
  metadataBase: new URL(baseUrl),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-[var(--paper)] text-[var(--ink)]">
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <footer className="border-t border-[var(--rule)] bg-[var(--surface)]">
          <p className="mx-auto max-w-6xl px-6 py-5 text-xs text-[var(--muted)]">
            Not legal advice. We report what companies disclose in captured
            policies, with quotes. A missing fetch is not an empty policy.
          </p>
        </footer>
      </body>
    </html>
  );
}
