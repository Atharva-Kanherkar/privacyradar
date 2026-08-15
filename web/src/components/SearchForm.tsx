"use client";

import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CompanyLogo } from "./CompanyLogo";

type Result = {
  slug: string;
  name: string;
  category: string;
  website: string | null;
};

export function SearchForm({
  defaultQuery = "",
  autofocus = false,
  label = "Search companies",
}: {
  defaultQuery?: string;
  autofocus?: boolean;
  label?: string;
}) {
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState(defaultQuery);
  const [results, setResults] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const [failed, setFailed] = useState(false);
  const rootRef = useRef<HTMLFormElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, []);

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    },
    [],
  );

  function search(value: string) {
    setQuery(value);
    setHighlighted(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = value.trim();
    if (!trimmed) {
      abortRef.current?.abort();
      setResults([]);
      setOpen(false);
      setFailed(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const response = await fetch(
          `/api/companies?q=${encodeURIComponent(trimmed)}`,
          { signal: controller.signal },
        );
        if (!response.ok) {
          setResults([]);
          setFailed(true);
          setOpen(true);
          return;
        }
        const rows = (await response.json()) as Result[];
        setResults(rows.slice(0, 8));
        setFailed(false);
        setOpen(true);
      } catch (cause) {
        if ((cause as Error).name !== "AbortError") {
          setResults([]);
          setFailed(true);
          setOpen(true);
        }
      }
    }, 150);
  }

  function go(slug: string) {
    setOpen(false);
    router.push(`/companies/${slug}`);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (open && highlighted >= 0 && results[highlighted]) {
      go(results[highlighted].slug);
      return;
    }
    setOpen(false);
    router.push(`/companies?q=${encodeURIComponent(query.trim())}`);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) {
      if (event.key === "Escape") setOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((index) => (index <= 0 ? results.length - 1 : index - 1));
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <form
      ref={rootRef}
      onSubmit={onSubmit}
      action="/companies"
      method="get"
      role="search"
      className="relative mt-6 w-full max-w-xl"
    >
      <label htmlFor="company-search" className="sr-only">
        {label}
      </label>
      <div className="flex min-w-0 items-center gap-2 rounded-lg border border-border bg-card p-1.5 focus-within:border-foreground">
        <Search size={18} aria-hidden="true" className="ml-2 shrink-0 text-muted-foreground" />
        <input
          id="company-search"
          name="q"
          type="search"
          value={query}
          onChange={(event) => search(event.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => {
            if (results.length > 0 || failed) setOpen(true);
          }}
          autoFocus={autofocus}
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            highlighted >= 0 ? `${listId}-${highlighted}` : undefined
          }
          placeholder="Search a company…"
          className="min-h-11 min-w-0 flex-1 bg-transparent text-base outline-none"
        />
        <Button type="submit" className="min-h-11 shrink-0 px-4 sm:px-6">
          Search
        </Button>
      </div>

      {open ? (
        <div
          id={listId}
          role="listbox"
          aria-label="Matching companies"
          className="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-lg border border-border bg-popover shadow-lg"
        >
          {failed ? (
            <p className="px-4 py-3 text-sm text-muted-foreground">
              Search is unavailable right now. Press Enter to browse the catalog.
            </p>
          ) : results.length === 0 ? (
            <p className="px-4 py-3 text-sm text-muted-foreground">
              No matching company yet. Press Enter to browse the catalog.
            </p>
          ) : (
            <>
              <ul>
                {results.map((company, index) => (
                  <li key={company.slug}>
                    <button
                      type="button"
                      id={`${listId}-${index}`}
                      role="option"
                      aria-selected={index === highlighted}
                      onMouseEnter={() => setHighlighted(index)}
                      onClick={() => go(company.slug)}
                      className={`flex min-h-12 w-full items-center gap-3 px-3 text-left ${
                        index === highlighted ? "bg-muted" : ""
                      }`}
                    >
                      <CompanyLogo
                        name={company.name}
                        website={company.website}
                        size={30}
                      />
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">
                        {company.name}
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {company.category}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <Link
                href={`/companies?q=${encodeURIComponent(query.trim())}`}
                onClick={() => setOpen(false)}
                className="block border-t border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                See all results
              </Link>
            </>
          )}
        </div>
      ) : null}
    </form>
  );
}
