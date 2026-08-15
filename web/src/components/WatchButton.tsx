import Link from "next/link";

export function WatchButton({
  slug,
  signedIn,
  watching,
}: {
  slug: string;
  signedIn: boolean;
  watching: boolean;
}) {
  if (!signedIn) {
    return (
      <Link
        href={`/login?next=${encodeURIComponent(`/companies/${slug}/watch`)}`}
        className="inline-flex min-h-11 items-center rounded-full bg-[var(--accent)] px-5 text-sm font-medium text-[var(--accent-contrast)] transition-opacity hover:opacity-90"
      >
        Watch
      </Link>
    );
  }
  if (watching) {
    return (
      <form action={`/api/watches/${slug}/unfollow`} method="post">
        <button
          type="submit"
          className="inline-flex min-h-11 items-center rounded-full border border-[var(--rule)] bg-[var(--surface)] px-5 text-sm font-medium text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--ink)]"
        >
          Watching
        </button>
      </form>
    );
  }
  return (
    <form action="/api/watches" method="post">
      <input type="hidden" name="slug" value={slug} />
      <input type="hidden" name="source" value="company_page" />
      <button
        type="submit"
        className="inline-flex min-h-11 items-center rounded-full bg-[var(--accent)] px-5 text-sm font-medium text-[var(--accent-contrast)] transition-opacity hover:opacity-90"
      >
        Watch
      </button>
    </form>
  );
}
