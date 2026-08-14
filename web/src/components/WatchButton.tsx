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
        className="inline-flex min-h-11 items-center border border-[var(--ink)] px-4 font-sans text-sm"
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
          className="inline-flex min-h-11 items-center border border-[var(--rule)] px-4 font-sans text-sm"
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
        className="inline-flex min-h-11 items-center border border-[var(--ink)] px-4 font-sans text-sm"
      >
        Watch
      </button>
    </form>
  );
}
