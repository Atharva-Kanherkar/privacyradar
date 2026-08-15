# PrivacyRadar design tokens

Modern consumer product look (2026 revamp): clean light surfaces, rounded cards,
one accent color, and plain-language data-category cards with icons. Still no
mascots, animated counters, or a universal privacy score. Evidence rigor is
unchanged: every published claim renders with its verbatim quote.

## Color

Two themes, both token-driven. Light is the default; dark is a matte black
system (near-black layered grays, hairline rules, no gloss). The stored choice
is applied pre-paint by an inline script; with no stored choice the system
preference wins via `prefers-color-scheme`. Toggle in the header
(`ThemeToggle`, `useSyncExternalStore`). `color-scheme` is set per theme so
form controls and scrollbars follow.

Light (`:root`):

| Token | Value | Use |
|---|---|---|
| `--paper` | `#f8fafc` | Page background |
| `--ink` / `--ink-contrast` | `#0f172a` / `#ffffff` | Body text / text on ink buttons |
| `--muted` | `#475569` | Secondary text |
| `--rule` | `#e2e8f0` | Borders |
| `--surface` | `#ffffff` | Cards |
| `--panel` | `#f1f5f9` | Inset panels, chips |
| `--accent` / `--accent-contrast` | `#4338ca` / `#ffffff` | Brand accent / text on accent |
| `--accent-soft` | `#eef2ff` | Accent-tinted backgrounds |
| `--danger` / `--danger-soft` | `#b91c1c` / `#fef2f2` | Sensitive data, selling data, AI training |
| `--good` / `--good-soft` | `#166534` / `#f0fdf4` | User controls, explicit denials |
| `--warning` / `--warning-soft` | `#92400e` / `#fffbeb` | Unclear / check delayed |
| `--important` | `#be123c` | Important material change (also labeled in text) |

Dark (`[data-theme="dark"]`, matte black): paper `#0a0a0a`, surface `#121212`,
panel `#1a1a1a`, rule `#262626`, ink `#f2f2f2` (contrast `#0a0a0a`), muted
`#a1a1aa`, accent `#a5b4fc` (contrast `#0a0a0a`), status hues lightened one
step (`#fca5a5` / `#86efac` / `#fcd34d` / `#fda4af`) with translucent softs.
Never hardcode `text-white` or `bg-white` in components; use
`--ink-contrast` / `--accent-contrast` / `--surface`. The one deliberate
exception is the white logo tile in `CompanyLogo`, kept for mark legibility on
both themes.

Do not rely on color alone. Materiality uses the words `Important`, `Moderate`,
`Minor`; claim badges use words (`Collected`, `Says no`, `Good sign`, `Unclear`).

## Type

- Sans: Inter (variable, self-hosted via next/font) — everything.
- Mono: Geist Mono — timestamps, hashes, snapshot ids.
- Headings: `text-wrap: balance`, tracking -0.025em. Prose: `text-wrap: pretty`.
- Display sizes are fluid via `clamp()` (hero: `clamp(2.25rem, 1.4rem+2.8vw, 3.4rem)`).
- Data and stats use tabular figures (`time` and `.tabular` get `font-variant-numeric: tabular-nums`).
- Dark mode compensates light-on-dark rendering: body line-height 1.62 (vs 1.55) and +0.004em tracking.
- Browser surfaces are themed: `::selection`, caret color, thin scrollbars, underline offset.
- Legacy `.font-serif` classes render as Inter so old pages inherit the new look.
- Elevation is declared once per element: border or shadow, not both (overlays like the chat drawer may use shadow). Quote rails are 1px.
- No eyebrow/kicker labels above headings; headings carry their own weight.

## Space and targets

4px base. Rounded corners: cards `rounded-2xl`, controls `rounded-lg`+.
Minimum tap target 44px. Visible `:focus-visible` ring 2px `--accent`.

## Motion

Honor `prefers-reduced-motion: reduce`. No content-shifting loaders on public
pages (server-rendered). Card hover lift is subtle and non-essential.

## Copy

Plain language a non-lawyer understands. Marketing surfaces (home hero, section
titles) may say "takes"; structured evidence blocks keep "discloses", "we
found", "we have not found evidence", "last checked". Policy quotes stay
visually distinct (left rail). No em or en dashes in copy.

## Data-category cards

`ClaimCard` renders one published claim as icon + plain label + badge, with the
verbatim quote one tap away (`details`). Icons come from lucide-react via
`DataTypeIcon`; labels and one-liners live in `src/lib/data-categories.ts`.
Sensitive categories (biometrics, health, children, precise location), data
sale, and AI training render in danger tones; user controls and explicit
denials render in good tones.

## Components

`SearchForm`, `FreshnessLabel`, `EvidenceQuote`, `DisclosureRow`, `ChangeCard`,
`StatePanel`, `SiteHeader`, `AuthNav`, `WatchButton`, `CompanyCard`,
`DataTypeChip`, `DataTypeIcon`, `ClaimCard`, `ChatAssistant` (streaming,
evidence-grounded, on when `OPENAI_API_KEY` is set).
