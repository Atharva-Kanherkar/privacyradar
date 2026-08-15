"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

type Theme = "light" | "dark";

let listeners: (() => void)[] = [];

function subscribe(listener: () => void): () => void {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((entry) => entry !== listener);
  };
}

function resolveTheme(): Theme {
  const set = document.documentElement.getAttribute("data-theme");
  if (set === "dark" || set === "light") return set;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(next: Theme) {
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem("theme", next);
  } catch {
    // private mode: the choice just won't persist
  }
  for (const listener of listeners) listener();
}

export function ThemeToggle() {
  // Server snapshot says "light"; useSyncExternalStore swaps in the real
  // resolved theme right after hydration without a mismatch.
  const theme = useSyncExternalStore(subscribe, resolveTheme, () => "light" as Theme);

  return (
    <button
      type="button"
      onClick={() => applyTheme(theme === "dark" ? "light" : "dark")}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-[var(--muted)] transition-colors hover:bg-[var(--panel)] hover:text-[var(--ink)]"
    >
      {theme === "dark" ? (
        <Sun size={18} aria-hidden="true" />
      ) : (
        <Moon size={18} aria-hidden="true" />
      )}
    </button>
  );
}
