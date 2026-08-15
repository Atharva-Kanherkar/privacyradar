import Link from "next/link";

export const dynamic = "force-dynamic";

export default function UnsubscribeDonePage() {
  return (
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">You are unsubscribed</h1>
      <p className="mt-3 text-muted-foreground" role="status">
        We will not send further change alerts unless you opt back in from alert
        settings.
      </p>
      <p className="mt-6 font-sans text-sm">
        <Link href="/radar/settings" className="underline">
          Alert settings
        </Link>
      </p>
    </main>
  );
}
