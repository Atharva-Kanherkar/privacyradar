import { redirect } from "next/navigation";
import Link from "next/link";
import { getSessionFromCookies } from "@/lib/session";
import { getPreference } from "@/lib/notify";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const FREQUENCIES = [
  { value: "immediate", label: "Email me when a published material change lands" },
  { value: "digest_weekly", label: "Weekly digest of published material changes" },
  { value: "unsubscribed", label: "Do not email me" },
] as const;

export default async function RadarSettingsPage() {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    redirect("/login?next=/radar/settings");
  }
  const pref = await getPreference(session.user.id);

  return (
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <p className="font-sans text-sm">
        <Link href="/radar" className="underline">
          My Radar
        </Link>
      </p>
      <h1 className="mt-2 font-serif text-4xl tracking-tight">Alert settings</h1>
      <p className="mt-3 text-muted-foreground">
        Alerts are transactional. We email only published material changes for
        companies you watch. Unpublished extraction never notifies you.
      </p>
      <form action="/radar/settings/update" method="post" className="mt-8 space-y-3">
        {FREQUENCIES.map((item) => (
          <label key={item.value} className="flex min-h-11 items-center gap-3">
            <input
              type="radio"
              name="frequency"
              value={item.value}
              defaultChecked={pref.frequency === item.value}
            />
            <span>{item.label}</span>
          </label>
        ))}
        <button
          type="submit"
          className="mt-4 min-h-11 border border-foreground px-4 font-sans text-sm"
        >
          Save alert settings
        </button>
      </form>
      {pref.muted_company_ids.length > 0 ? (
        <p className="mt-8 font-sans text-sm text-muted-foreground">
          {pref.muted_company_ids.length} companies muted via unsubscribe links.
        </p>
      ) : null}
    </main>
  );
}
