# PrivacyRadar design system

Monochrome, shadcn/ui-based (2026). Black, greys, white. No hue anywhere in
the interface. Semantic states are expressed by fill weight and words, never
color. Still no mascots, animated counters, or a universal privacy score.
Evidence rigor is unchanged: every published claim renders with its verbatim
quote. Real company logos come from each site's own favicon (`CompanyLogo`,
Google s2 service, initials fallback); the white logo tile is the one
deliberate non-token surface, kept for mark legibility on both themes.

## Color

Tokens are shadcn/ui semantic names (`--background`, `--foreground`,
`--primary`, `--secondary`, `--muted`, `--muted-foreground`, `--border`,
`--ring`, ...) defined in `web/src/app/globals.css`, all neutral:

- Light: white background, `#171717` foreground, `#f5f5f5` muted surfaces,
  `#e5e5e5` borders, `#525252` muted text.
- Dark (matte black): `#0a0a0a` background, `#111111` cards, `#1a1a1a`
  panels, `#262626` borders, `#ededed` foreground, `#a3a3a3` muted text.
  Primary inverts (light button on black), like Vercel.

Legacy token names (`--paper`, `--ink`, `--rule`, `--surface`, `--panel`,
`--danger`, `--good`, `--warning`, ...) are aliases onto the neutral scale so
older pages inherit the system; their values are greyscale by definition. Do
not introduce a colored value anywhere.

The stored theme choice is stamped as `data-theme` before first paint by an
inline script (falling back to the system preference); the header toggle
(`ThemeToggle`, `useSyncExternalStore`) flips it. `color-scheme` follows the
theme. shadcn's `dark:` variant is bound to `[data-theme="dark"]`.

## Components

shadcn/ui primitives (`src/components/ui/`): Button, Badge, Input, Textarea,
Card, wired through `cn()` from `src/lib/utils.ts`. Prominent controls use
Button (`default` = solid primary, `outline` = hairline); pass `min-h-11`
so tap targets stay at 44px. No pill buttons: geometry is `rounded-md` for
controls and chips, `rounded-lg`/`rounded-xl` for inputs and cards.

Product components: `SearchForm`, `FreshnessLabel`, `EvidenceQuote`,
`DisclosureRow`, `ChangeCard`, `StatePanel`, `SiteHeader`, `AuthNav`,
`WatchButton`, `CompanyCard`, `CompanyLogo`, `DataTypeChip`, `DataTypeIcon`,
`ClaimCard`, `ThemeToggle`, `ChatAssistant` (slide-over drawer; streaming,
evidence-grounded, on when `OPENAI_API_KEY` is set).

## Type

- Sans: Geist (variable, self-hosted via next/font) — everything.
- Mono: Geist Mono — timestamps, hashes, snapshot ids.
- Headings: `text-wrap: balance`, tracking -0.025em. Prose: `text-wrap: pretty`.
- Statement headline: fluid `clamp()` display size; the sentence continues in
  `--muted-foreground` (`.lede-muted`), same size and weight. Section titles
  may use the same two-tone lede pattern. No eyebrow/kicker labels.
- Data and stats use tabular figures (`time`, `.tabular`).
- Dark mode compensates light-on-dark rendering: body line-height 1.62
  (vs 1.55) and +0.004em tracking.
- Browser surfaces are themed: `::selection` (inverted mono), caret, thin
  scrollbars, underline offset, focus ring in `--foreground`.

## Space and geometry

4px base. Elevation declared once per element: hairline border for in-flow
cards (no resting shadows); shadows only on overlays (chat drawer, floating
trigger). Quote rails are 1px. Minimum tap target 44px. Visible
`:focus-visible` ring 2px.

## Motion

Honor `prefers-reduced-motion: reduce`. No content-shifting loaders on public
pages (server-rendered). Card hover lift is subtle and non-essential.

## Copy

Plain language a non-lawyer understands. Marketing surfaces may say "takes";
structured evidence blocks keep "discloses", "we found", "we have not found
evidence", "last checked". Policy quotes stay visually distinct (left rail).
Materiality and claim badges use words (`Important`, `Collected`, `Says no`,
`Good sign`, `Unclear`), never color alone. No em or en dashes in copy.
