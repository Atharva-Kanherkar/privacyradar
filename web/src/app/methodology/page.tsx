export default function MethodologyPage() {
  return (
    <main id="main" className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="font-serif text-4xl tracking-tight">Methodology</h1>
      <div className="mt-6 space-y-4 text-muted-foreground">
        <p>
          PrivacyRadar captures public privacy-policy pages, hashes the cleaned
          text, and only then asks a model what the company discloses. If the
          hash matches the last successful capture, no model runs.
        </p>
        <p>
          Model output is untrusted. A claim becomes public only after a quote
          is found in the captured snapshot and an operator publishes a
          revision. Cosmetic date-stamp diffs stay off the public feed.
        </p>
        <p>
          We report disclosed practices, not proven behavior. “We have not found
          evidence” is not the same as “this never happens.” Failed or blocked
          fetches are not empty policies.
        </p>
        <p>
          Corrections supersede a publication. Prior revisions remain readable.
          This is not legal advice.
        </p>
      </div>
    </main>
  );
}
