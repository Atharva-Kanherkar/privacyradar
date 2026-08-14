import { Search } from "lucide-react";

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
      <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-[var(--rule)] bg-[var(--surface)] p-1.5 shadow-sm focus-within:border-[var(--accent)]">
        <Search size={18} aria-hidden="true" className="ml-2 shrink-0 text-[var(--muted)]" />
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
        <button
          type="submit"
          className="min-h-11 shrink-0 rounded-xl bg-[var(--ink)] px-5 text-sm font-medium text-white"
        >
          Search
        </button>
      </div>
    </form>
  );
}
