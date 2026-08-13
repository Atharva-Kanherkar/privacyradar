export default function AboutPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">About</h1>
      <div className="mt-6 space-y-4 text-[var(--muted)]">
        <p>
          Privacy-policy update emails are long on purpose. privacyradar watches a
          fixed list of companies, strips the boilerplate, hashes the remaining
          text, and only then asks OpenAI what data they collect, share, and
          just changed.
        </p>
        <p>
          If the hash matches yesterday, no model runs. If the hash changes but
          the only delta is a date stamp, it is marked cosmetic and stays off
          the public feed.
        </p>
        <p>
          This is not legal advice, not a law firm, and not a complete archive
          of every policy on the internet. Quotes are taken from the public
          page at fetch time. Read the original if you need to make a decision.
        </p>
      </div>
    </main>
  );
}
