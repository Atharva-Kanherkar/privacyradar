import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SearchForm({
  defaultQuery = "",
  autofocus = false,
  label = "Search companies",
}: {
  defaultQuery?: string;
  autofocus?: boolean;
  label?: string;
}) {
  return (
    <form action="/companies" method="get" role="search" className="mt-6 w-full max-w-xl">
      <label htmlFor="company-search" className="sr-only">
        {label}
      </label>
      <div className="flex min-w-0 items-center gap-2 rounded-lg border border-border bg-card p-1.5 focus-within:border-foreground">
        <Search size={18} aria-hidden="true" className="ml-2 shrink-0 text-muted-foreground" />
        <input
          id="company-search"
          name="q"
          type="search"
          defaultValue={defaultQuery}
          autoFocus={autofocus}
          autoComplete="off"
          placeholder="Try Google, Spotify, or Signal…"
          className="min-h-11 min-w-0 flex-1 bg-transparent text-base outline-none"
        />
        <Button type="submit" className="min-h-11 shrink-0 px-6">
          Search
        </Button>
      </div>
    </form>
  );
}
