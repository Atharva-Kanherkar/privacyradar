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
      <label htmlFor="company-search" className="font-sans text-sm text-[var(--muted)]">
        {label}
      </label>
      <div className="mt-2 flex min-w-0 gap-2">
        <input
          id="company-search"
          name="q"
          type="search"
          defaultValue={defaultQuery}
          autoFocus={autofocus}
          autoComplete="off"
          placeholder="Signal, a company name, or slug"
          className="min-h-11 min-w-0 flex-1 border border-[var(--rule)] bg-[var(--surface)] px-3 font-sans text-base"
        />
        <button
          type="submit"
          className="min-h-11 min-w-11 border border-[var(--ink)] bg-[var(--ink)] px-4 font-sans text-sm text-[var(--paper)]"
        >
          Search
        </button>
      </div>
    </form>
  );
}
