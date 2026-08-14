import { assistantEnabled } from "@/lib/assistant";

export async function AssistantPanel({
  slug,
  askStatus,
}: {
  slug: string;
  askStatus?: string;
}) {
  const on = await assistantEnabled();
  return (
    <section className="mt-12">
      <h2 className="font-serif text-xl">Ask about this policy</h2>
      {!on ? (
        <p className="mt-3 text-[var(--muted)]">
          The cited assistant is off. Read the published disclosures above.
          This is not legal advice.
        </p>
      ) : (
        <>
          {askStatus === "answered" ? (
            <p className="mt-3" role="status">
              We found published evidence. Open the claim quote above.
            </p>
          ) : null}
          {askStatus === "refused" ? (
            <p className="mt-3" role="status">
              PrivacyRadar does not have enough published evidence to answer
              that, or the question is out of scope for this company.
            </p>
          ) : null}
          {askStatus === "rate_limited" ? (
            <p className="mt-3" role="status">
              Daily assistant limit reached.
            </p>
          ) : null}
          {askStatus === "disabled" ? (
            <p className="mt-3" role="status">
              The cited assistant is off.
            </p>
          ) : null}
          <form action={`/companies/${slug}/ask`} method="post" className="mt-4">
            <label htmlFor="assistant-question" className="font-sans text-sm">
              Question about this company
            </label>
            <textarea
              id="assistant-question"
              name="question"
              required
              maxLength={500}
              className="mt-1 min-h-24 w-full border border-[var(--rule)] bg-[var(--surface)] px-3 py-2"
            />
            <button
              type="submit"
              className="mt-3 min-h-11 border border-[var(--ink)] px-4 font-sans text-sm"
            >
              Ask
            </button>
          </form>
        </>
      )}
    </section>
  );
}
