import type { Metadata } from "next";
import { Newsreader, Geist_Mono, Source_Sans_3 } from "next/font/google";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const serif = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
});

const sans = Source_Sans_3({
  variable: "--font-source-sans",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "PrivacyRadar",
    template: "%s · PrivacyRadar",
  },
  description:
    "Evidence-backed disclosed privacy practices and material policy changes. Dated. Correctable.",
  metadataBase: new URL("https://privacyradar.local"),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${serif.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-[var(--paper)] text-[var(--ink)]">
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <footer className="border-t border-[var(--rule)]">
          <p className="mx-auto max-w-5xl px-6 py-4 font-sans text-xs text-[var(--muted)]">
            Not legal advice. We report what companies disclose in captured
            policies, with quotes. A missing fetch is not an empty policy.
          </p>
        </footer>
      </body>
    </html>
  );
}
