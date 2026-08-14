import { redirect } from "next/navigation";
import { sql } from "@/lib/db";
import { REGIONS } from "@/lib/regions";
import { getSessionFromCookies } from "@/lib/session";
import { StatePanel } from "@/components/StatePanel";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function AccountPage() {
  const session = await getSessionFromCookies();
  if (!session?.user) {
    redirect("/login");
  }
  if (!sql) {
    return (
      <main id="main" className="mx-auto max-w-xl px-6 py-12">
        <StatePanel title="Account unavailable">
          We could not load your account.
        </StatePanel>
      </main>
    );
  }
  const profiles = await sql<{ region: string }[]>`
    select region from consumer_profiles where user_id = ${session.user.id}
  `;
  const region = profiles[0]?.region ?? "unspecified";

  return (
    <main id="main" className="mx-auto max-w-xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Account</h1>
      {region === "unspecified" ? (
        <p className="mt-3" role="status">
          Choose a policy region before other account settings. This is the
          region you want us to emphasize. It is not legal advice and is not
          inferred from your IP address.
        </p>
      ) : (
        <p className="mt-3 text-[var(--muted)]">
          Region is the policy region you want us to emphasize. It is not legal
          advice and is not inferred from your IP address.
        </p>
      )}
      <form action="/account/region" method="post" className="mt-8">
        <label htmlFor="region" className="font-sans text-sm">
          Policy region
        </label>
        <select
          id="region"
          name="region"
          defaultValue={region}
          className="mt-1 min-h-11 w-full border border-[var(--rule)] bg-[var(--surface)] px-3"
        >
          {REGIONS.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="mt-4 min-h-11 border border-[var(--ink)] px-4 font-sans text-sm"
        >
          Save region
        </button>
      </form>
      <form action="/account/sign-out" method="post" className="mt-8">
        <button
          type="submit"
          className="min-h-11 border border-[var(--rule)] px-4 font-sans text-sm"
        >
          Sign out
        </button>
      </form>
      <p className="mt-8 font-sans text-sm">
        <a href="/account/export" className="underline">
          Download account export (JSON)
        </a>
      </p>
      <p className="mt-6 text-[var(--muted)]">
        Passkeys are optional later. A magic link is enough to sign in.
      </p>
      <form action="/account/delete" method="post" className="mt-10">
        <label htmlFor="confirm" className="font-sans text-sm">
          Type DELETE to remove this account
        </label>
        <input
          id="confirm"
          name="confirm"
          className="mt-1 min-h-11 w-full border border-[var(--rule)] bg-[var(--surface)] px-3"
        />
        <button
          type="submit"
          className="mt-4 min-h-11 border border-[var(--important)] px-4 font-sans text-sm text-[var(--important)]"
        >
          Delete account
        </button>
      </form>
    </main>
  );
}
