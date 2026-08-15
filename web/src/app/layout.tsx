import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import { Geist, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const baseUrl = process.env.PUBLIC_BASE_URL ?? "https://privacyradar.local";

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

// Stamps the theme before first paint: stored choice, else system preference.
const themeInit = `try{var t=localStorage.getItem("theme");if(t!=="dark"&&t!=="light"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.setAttribute("data-theme",t)}catch(e){}`;

const description =
  "PrivacyRadar reads privacy policies so you don't have to. See exactly what data each company collects (your voice, location, messages) with the receipts, and get alerted when it changes.";

export const metadata: Metadata = {
  title: {
    default: "PrivacyRadar: see what companies take from you",
    template: "%s · PrivacyRadar",
  },
  description,
  metadataBase: new URL(baseUrl),
  applicationName: "PrivacyRadar",
  openGraph: {
    type: "website",
    siteName: "PrivacyRadar",
    title: "PrivacyRadar: see what companies take from you",
    description,
    url: "/",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "PrivacyRadar: see what companies take from you",
    description,
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geist.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <Analytics />
        <footer className="border-t border-border bg-card">
          <p className="mx-auto max-w-6xl px-6 py-5 text-xs text-muted-foreground">
            Not legal advice. We report what companies disclose in captured
            policies, with quotes. A missing fetch is not an empty policy.
          </p>
        </footer>
      </body>
    </html>
  );
}
