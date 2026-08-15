import Link from "next/link";
import { Button } from "@/components/ui/button";

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
      <Button asChild className="min-h-11 px-5">
        <Link href={`/login?next=${encodeURIComponent(`/companies/${slug}/watch`)}`}>
          Watch
        </Link>
      </Button>
    );
  }
  if (watching) {
    return (
      <form action={`/api/watches/${slug}/unfollow`} method="post">
        <Button type="submit" variant="outline" className="min-h-11 px-5">
          Watching
        </Button>
      </form>
    );
  }
  return (
    <form action="/api/watches" method="post">
      <input type="hidden" name="slug" value={slug} />
      <input type="hidden" name="source" value="company_page" />
      <Button type="submit" className="min-h-11 px-5">
        Watch
      </Button>
    </form>
  );
}
