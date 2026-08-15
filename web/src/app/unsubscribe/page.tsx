import Link from "next/link";
import { StatePanel } from "@/components/StatePanel";
import { verifyUnsubToken } from "@/lib/unsub-token";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function UnsubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  const parsed = token ? verifyUnsubToken(token) : null;
  if (!parsed) {
    return (
      <main id="main" className="mx-auto max-w-xl px-6 py-12">
        <StatePanel title="This unsubscribe link is not valid">
          The link is missing, expired, or was altered. Sign in to manage alerts
          from your account instead.
        </StatePanel>
        <p className="mt-6 font-sans text-sm">
          <Link href="/radar/settings" className="underline">
            Alert settings
          </Link>
        </p>
      </main>
    );
  }
  const companyMute = parsed.purpose.startsWith("mute:");
  return (
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Unsubscribe</h1>
      <p className="mt-3 text-muted-foreground">
        {companyMute
          ? "This will mute alerts for one company. You can still watch it on My Radar."
          : "This will stop transactional change emails for this address."}
      </p>
      <form action="/unsubscribe/confirm" method="post" className="mt-8">
        <input type="hidden" name="token" value={token} />
        <button
          type="submit"
          className="min-h-11 border border-foreground px-4 font-sans text-sm"
        >
          Confirm unsubscribe
        </button>
      </form>
    </main>
  );
}
