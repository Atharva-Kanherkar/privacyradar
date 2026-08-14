# PrivacyRadar design tokens (issue #9)

Editorial paper/ink bulletin. No gradients, glass, mascots, animated counters, or a universal privacy score.

## Color

| Token | Value | Use |
|---|---|---|
| `--paper` | `#f4efe6` | Page background |
| `--ink` | `#1c1917` | Body text |
| `--muted` | `#44403c` | Secondary text (AA on paper) |
| `--rule` | `#d6cfc3` | Borders |
| `--surface` | `#fffdf8` | Cards |
| `--focus` | `#1d4ed8` | 2px focus ring |
| `--important` | `#9f1239` | Important material change (also labeled in text) |
| `--warning` | `#92400e` | Check delayed / uncertainty |
| `--success` | `#166534` | Healthy / last checked ok |

Do not rely on color alone. Materiality uses the words `Important`, `Moderate`, `Minor`.

## Type

- Serif: Newsreader — headings and body.
- Sans: Source Sans 3 — controls, nav, comparison-density UI.
- Mono: Geist Mono — timestamps, hashes, snapshot ids.

Mobile h1 2rem; desktop h1 2.5rem. Body 1.125rem / 1.6.

## Space and targets

4px base. Padding scale 8 / 12 / 16 / 24 / 48. Minimum tap target 44px. Visible `:focus-visible` ring 2px `--focus`.

## Motion

Honor `prefers-reduced-motion: reduce`. No content-shifting loaders on public pages (server-rendered).

## Copy

Structured facts: “discloses”, “we found”, “we have not found evidence”, “last checked”. Never “takes” in those blocks. Policy quotes are visually distinct (left rail).

## Components (this issue)

`SearchForm`, `FreshnessLabel`, `EvidenceQuote`, `DisclosureRow`, `ChangeCard`, `StatePanel`, `SiteHeader`.

Deferred: `WatchButton`, `CompanyPicker`, `ComparisonMatrix`, `AssistantPanel` (#11+).

Added in #10: `AuthNav` (Sign in / Account from session cookie).
Added in #11: `WatchButton`.
Added in #12: `/radar/settings` and signed `/unsubscribe` for transactional alerts.
Added in #13: `/companies/request` — nominations are requested, not monitored.
Added in #14: `/compare` — published claims only, no overall score.
Added in #15: company-page cited assistant, off by default.
