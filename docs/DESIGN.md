# PrivacyRadar design tokens

Modern consumer product look (2026 revamp): clean light surfaces, rounded cards,
one accent color, and plain-language data-category cards with icons. Still no
mascots, animated counters, or a universal privacy score. Evidence rigor is
unchanged: every published claim renders with its verbatim quote.

## Color

| Token | Value | Use |
|---|---|---|
| `--paper` | `#f8fafc` | Page background |
| `--ink` | `#0f172a` | Body text |
| `--muted` | `#64748b` | Secondary text |
| `--rule` | `#e2e8f0` | Borders |
| `--surface` | `#ffffff` | Cards |
| `--panel` | `#f1f5f9` | Inset panels, chips |
| `--accent` | `#4f46e5` | Brand accent, focus ring, links |
| `--accent-soft` | `#eef2ff` | Accent-tinted backgrounds |
| `--danger` / `--danger-soft` | `#dc2626` / `#fef2f2` | Sensitive data, selling data, AI training |
| `--good` / `--good-soft` | `#15803d` / `#f0fdf4` | User controls, explicit denials |
| `--warning` / `--warning-soft` | `#b45309` / `#fffbeb` | Unclear / check delayed |
| `--important` | `#be123c` | Important material change (also labeled in text) |

Do not rely on color alone. Materiality uses the words `Important`, `Moderate`,
`Minor`; claim badges use words (`Collected`, `Says no`, `Good sign`, `Unclear`).

## Type

- Sans: Inter — everything (headings tighter via letter-spacing).
- Mono: Geist Mono — timestamps, hashes, snapshot ids.
- Legacy `.font-serif` classes render as Inter so old pages inherit the new look.

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
