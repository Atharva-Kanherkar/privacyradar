<!-- /autoplan restore point: /Users/atharva/.gstack/projects/privacyradar/main-autoplan-restore-20260813-234107.md -->
# PrivacyRadar Consumer Product Plan

Status: reviewed plan awaiting founder approval of the strategic sequencing challenge.

## Product premise

PrivacyRadar helps ordinary people understand what companies collect, notice when those practices change, compare alternatives, and take the next privacy-protecting action. Every factual claim must remain traceable to a captured policy quotation.

## Initial direction

- Keep the public company directory and change feed free and indexable.
- Add accounts only to support personal watchlists, preferences, saved comparisons, and notification delivery.
- Expand from 10 companies to hundreds through a governed source catalog and crawl-quality system.
- Add email notifications after trustworthy change detection and user-controlled frequency settings exist.
- Add side-by-side company comparison using a stable privacy-practice taxonomy.
- Add a small retrieval-based assistant that answers questions from stored policy evidence and cites its sources.
- Keep all functionality free during the validation period. Add billing only after activation and retention show repeat consumer value.
- Avoid B2B vendor management, compliance workflows, audit exports, team seats, and legal recommendations.

## Rough phases

1. Make the monitoring engine trustworthy and observable.
2. Grow the public directory and improve discovery.
3. Add authentication, onboarding, and personal watchlists.
4. Add notification preferences and evidence-backed alerts.
5. Add comparisons and policy Q&A.
6. Validate retention before introducing paid tiers.

## Executive decision

Build PrivacyRadar as an evidence-first consumer privacy product, not a generic page monitor and not a compliance tool. The recurring loop is:

```text
DISCOVER a company
      ↓
UNDERSTAND its current practices from cited evidence
      ↓
WATCH companies the person actually uses
      ↓
NOTICE a material change without notification noise
      ↓
COMPARE alternatives and take a concrete action
      ↓
RETURN when the next change occurs
```

The product wins on trustworthy interpretation and useful next steps. Raw change detection is already a commodity. Termsight, Watchobots, Osano, ToS;DR, and Common Sense Privacy prove that directories, ratings, monitoring, and summaries all exist. PrivacyRadar must combine four things unusually well: current structured practices, longitudinal changes, primary-source evidence, and personalized relevance.

Do not hide public facts or evidence behind payment. Future revenue may charge for automation and convenience, never for the basic truth about what a company says it does with people’s data.

## Premises confirmed

| Premise | Verdict | Consequence |
|---|---|---|
| Primary user is an individual consumer | Confirmed by founder | No workspaces, vendor inventories, audit exports, team roles, or compliance recommendations |
| Privacy policies are hard to understand | Supported | Use a stable taxonomy, plain language, and evidence citations |
| People will not repeatedly browse a directory | High confidence | The retention loop must be watchlist → alert → action, not passive reading |
| More companies automatically means more value | False without quality controls | Coverage growth is gated by crawl health and extraction accuracy |
| A chatbot itself is differentiating | False | It is useful only as a cited interface over trusted stored evidence |
| Billing should be designed now | Partly false | Instrument future entitlements now; do not integrate payment until retention gates pass |

## What already exists

| Sub-problem | Existing implementation | Decision |
|---|---|---|
| Company identity and public catalog | `companies`, `policy_sources`, `catalog.yaml`, `/companies` | Reuse, but move catalog operations from YAML-only to governed database records |
| Policy acquisition | `fetch_url()` with httpx and Trafilatura | Keep as first fetch strategy; add render/PDF fallbacks and explicit crawl outcomes |
| Change suppression | normalized SHA-256 document and section hashes | Keep as the inexpensive first gate |
| Materiality classification | structured OpenAI response in `judge_materiality()` | Keep, version prompts and models, add evaluation and review states |
| Current-practice extraction | `PracticeDocument` with quote requirements | Keep the evidence invariant; version the taxonomy and extraction |
| Scheduling | ARQ cron four times daily | Keep during early scale; add per-source scheduling, leases, retries, and run records |
| Public change feed | home page and RSS | Keep public; repair canonical URLs and add change-detail pages |
| Company profile | current practices plus event history | Make this the primary acquisition and trust surface |

Good patterns to preserve: hash before model spend; quotes required for extracted claims; simple Postgres data access; calm editorial visual language. Anti-patterns to remove: broad `catch` blocks returning empty public data, no test suite, no run-level observability, and conflating “no data” with an infrastructure failure.

## Dream-state delta

```text
CURRENT                         THIS PLAN                         12-MONTH IDEAL
10 curated URLs                200-500 healthy companies         Thousands of verified services
One global privacy page        Region-aware source registry      Privacy/terms/AI/data-control graph
Snapshots and summaries   →    Evidence-backed profiles      →   Public longitudinal privacy memory
Anonymous browsing             Personal watchlists               Personalized privacy radar
RSS only                       Email digests and alert inbox      Multi-channel, user-tuned delivery
No comparison                  2-4 company comparisons            Alternative recommendations by need
No Q&A                         Company-scoped cited Q&A           Cross-company cited research assistant
No product analytics           Trust/activation/retention gates   Sustainable consumer subscription
```

This plan reaches a defensible consumer product, but stops before becoming a privacy assistant that knows every service a person uses or acts on their behalf.

## Implementation alternatives

| Approach | Shape | Effort | Risk | Completeness | Verdict |
|---|---|---:|---:|---:|---|
| A. Feature-first patchwork | Add auth, watchlists, email, compare, chat directly to the current schema | M | High | 5/10 | Reject. It produces visible features on top of unmeasured data quality and silent failures. |
| B. Reliability-first modular monolith | Keep Next.js, Python worker, Postgres, Redis; add explicit domain tables, job state, outbox delivery, evidence APIs, then consumer features | L | Medium | 9/10 | Choose. It reuses nearly all current code and creates safe boundaries without a rewrite. |
| C. Event-driven platform rewrite | Split crawler, analyzer, notifications, search, and chat into separate deployed services | XL | High | 10/10 | Reject for now. Operational complexity arrives far before the workload needs it. |

The selected approach is B. It is the ideal architecture for the next 12 months without spending the project’s limited complexity budget on premature microservices.

## Scope posture

Mode: selective expansion. The founder’s requested capabilities remain the target, but they are sequenced behind reliability and product validation.

Accepted scope:

- Evidence-backed public company profiles and change pages.
- Governed expansion to hundreds of companies.
- Consumer authentication and privacy-minimal account data.
- Personal watchlists and notification preferences.
- Email alert inbox plus daily/weekly digests.
- Company comparison based on the same versioned taxonomy.
- Company-scoped cited Q&A with hard safety boundaries.
- Product analytics that store events, not invasive behavioral profiles.
- Entitlement-ready schema and future tier definitions without live billing.

## NOT in scope

- B2B vendor-risk workflows, team seats, SSO, SCIM, procurement, and audit exports: wrong customer.
- Legal advice or automated compliance conclusions: high liability and outside the evidence product.
- Monitoring arbitrary user-submitted URLs in the first product cycle: it creates abuse, SSRF, crawl-cost, and support risks before catalog operations are ready.
- Native mobile apps: responsive web and email cover the early retention loop.
- Browser extensions: valuable later for “privacy at point of use,” but a separate distribution and permissions problem.
- Automated opt-out/deletion requests: materially different legal and identity-verification workflow.
- Social feeds, comments, and community ratings: moderation and brigading would weaken trust.
- Generic web search inside the assistant: answers must stay bounded to captured PrivacyRadar evidence.
- Multi-policy coverage beyond privacy policies during the first reliability milestone; Terms of Service, AI policies, cookie policies, and subprocessors follow only after the source model proves stable.
- Payments before retention gates pass.

## Product principles

1. Evidence before interpretation. Every claim links to a quote, source URL, snapshot time, and document version.
2. Change before score. A single grade hides tradeoffs and invites false precision. Show practices and changes first; any score must expose its rubric.
3. Quiet by default. No email when nothing meaningful happened.
4. Relevance over volume. A watchlist of 12 services matters more than a catalog of 10,000 broken profiles.
5. Privacy-minimal accounts. Store only what the feature needs; never monetize user watchlists or Q&A content.
6. Public knowledge compounds. Profiles, evidence, histories, RSS, and basic comparisons remain public and indexable.
7. Models are fallible components. Persist prompt/model versions, confidence, evidence, and review state.

## Product success model

North-star metric: weekly users who receive or inspect at least one evidence-backed insight about a company they watch.

Supporting metrics:

| Stage | Metric | Initial gate |
|---|---|---:|
| Coverage | Enabled sources with a fresh successful snapshot | ≥95% in trailing 7 days |
| Accuracy | Material-change precision on a labeled evaluation set | ≥95% |
| Evidence | Published claims with a valid quote anchored to the target snapshot | 100% |
| Activation | New accounts watching ≥3 companies within first session | ≥40% |
| Relevance | Alert recipients opening a cited change or company page | ≥20% |
| Retention | Activated accounts still watching or reading in week 4 | ≥25% |
| Noise | Users muting/unwatching directly after an alert | <5% |
| Assistant trust | Answers with valid citations and no unsupported material claims | ≥98% on eval set |

Do not optimize raw registered users, page views, catalog count, emails sent, or chatbot message count. Those proxies can rise while the product becomes less trustworthy.

## Error and rescue registry

| Codepath | Failure | Named outcome | Rescue action | User-visible result |
|---|---|---|---|---|
| Source fetch | timeout/DNS/TLS/403/429/5xx | `fetch_failed` with reason | bounded exponential retry, record attempt, reschedule | Last verified snapshot stays visible with “check delayed” |
| Text extraction | empty, too short, navigation-only, wrong language | `content_invalid` | try rendered browser, then PDF strategy; quarantine after threshold | Never overwrite current verified policy |
| Snapshot write | uniqueness race or DB unavailable | `snapshot_persist_failed` | transaction retry; job remains retryable | No partial event or alert |
| Materiality model | timeout, refusal, malformed structured output | `analysis_failed` | retry with same version, then fallback model/manual queue | Change marked pending, never silently cosmetic |
| Practice extraction | unsupported claim or missing quotes | `evidence_validation_failed` | reject extraction and keep previous verified view | “Analysis pending” instead of fabricated data |
| Auth magic link | expired/replayed token or provider outage | `auth_link_invalid` / `auth_delivery_failed` | atomic single-use token; resend with cooldown | Specific recovery message |
| Watch mutation | duplicate click or stale session | `watch_conflict` / `unauthorized` | unique constraint and idempotent upsert | Stable watched state or sign-in prompt |
| Notification enqueue | duplicate event | `delivery_duplicate` | unique delivery key in transactional outbox | One alert only |
| Email delivery | bounce, complaint, provider timeout | `delivery_failed` / `suppressed` | retry transient failures; suppress hard bounces/complaints | Delivery status in notification settings |
| Comparison | company lacks current verified extraction | `comparison_incomplete` | show partial matrix and freshness labels | Clear missing-data cells, no false equivalence |
| Assistant retrieval | no relevant evidence | `insufficient_evidence` | refuse to answer and link to source policy | “PrivacyRadar doesn’t have enough evidence” |
| Assistant generation | unsupported citation or prompt attack in policy text | `answer_validation_failed` | discard output; treat policy as untrusted data; retry once | Safe failure with source links |
| Web database query | DB unavailable | `public_data_unavailable` | error boundary, health log, stale cache if present | Service-unavailable state, never empty catalog |

## Failure modes registry

| Failure mode | Prevention/detection | Test | Severity |
|---|---|---|---|
| Failed fetch hashes empty content and appears as a real change | Never persist `empty` as a valid document hash; explicit attempt records | Integration test | Critical |
| Current broad web query catches hide production outages as empty pages | Typed query errors and route error boundaries | Integration test | Critical |
| Model publishes a claim whose quote is absent from snapshot | Server-side quote-anchor validator blocks publication | Unit + adversarial eval | Critical |
| Same material change sends duplicate emails | Outbox uniqueness on user/event/channel + idempotent worker | Concurrency test | High |
| User accesses or mutates another user’s watchlist | Derive user ID from server session; never accept it from request body | Authorization integration test | Critical |
| A policy contains instructions targeting the assistant | Delimit untrusted documents, tool-free model call, citation validator | Prompt-injection eval | High |
| Regional policy is presented as global | Explicit region on source, snapshot, extraction, event, and user preference | Data-model test | High |
| Taxonomy changes make historical comparisons invalid | Version taxonomy and normalization; migrations are additive | Contract test | High |
| Crawler growth overwhelms one serial worker | Per-source leases, concurrency caps, queue latency metrics | Load test | High |
| Email provider records create a shadow subscriber list | DPA review, minimum metadata, deletion/suppression sync | Operational audit | Medium |
| Company count grows faster than review capacity | Cohort gates and automatic quarantine | Release checklist | High |
| Assistant costs can be abused | Authentication, per-user daily limits, request size caps, caching | Rate-limit integration test | High |

## Temporal interrogation

```text
FOUNDATION
  Decide taxonomy versioning, evidence anchors, source states, and migration tool.
  If these are vague, every later feature invents its own truth model.

CORE LOGIC
  Decide publication gates, regional semantics, deduplication keys, retry ownership,
  and what “current verified” means.

INTEGRATION
  Decide transactional boundaries from event → outbox → delivery, account deletion,
  authentication recovery, and provider webhook verification.

POLISH AND TESTS
  Decide all empty/error/partial/stale states, mobile compare behavior, accessibility,
  evaluation datasets, rollback switches, and support diagnostics.
```

The strict plan resolves these decisions below instead of leaving them to implementation.

## CEO dual-voice review

The independent subagent completed. The separate Codex CLI voice authenticated and inspected the plan but produced no final verdict in two attempts, so this phase is tagged `subagent-only` rather than pretending there was cross-model agreement.

Top accepted findings:

1. Reframe the product from policy monitoring to a personal privacy decision layer: what changed, why it may matter, and what the person can do.
2. Every material event should support an evidence-backed action card such as changing a setting, opting out, exporting data, deleting an account, or comparing an alternative.
3. Say “disclosed practices,” never imply the crawler observed a company’s real behavior.
4. Start with one high-intent wedge and demand-ranked cohorts rather than breadth for its own sake.
5. Build the consumer taxonomy backward from decisions: AI training, selling/sharing, targeting, sensitive data, retention, deletion, opt-out, location, biometrics, children, and region.
6. Treat trust operations as product scope: public methodology, model disclosure, corrections, appeals, and evidence context.
7. Validate the loop with a 30-person concierge pilot before committing to full auth, chat, or broad coverage.

```text
CEO DUAL VOICES — CONSENSUS TABLE
Dimension                              CLI voice       Subagent          Result
Premises valid?                        N/A             Mixed             Flagged
Right problem?                         N/A             Reframe           Accepted
Scope calibration?                     N/A             Too broad early   Flagged
Alternatives explored?                 N/A             Gaps found        Accepted
Competitive risk covered?              N/A             Material gaps     Accepted
Six-month trajectory sound?            N/A             Conditional       Flagged
```

Because one voice was unavailable, no item is claimed as two-model consensus.

## CEO completion summary

| Area | Result |
|---|---|
| Premise | Consumer-only, evidence-first monitoring confirmed |
| Existing leverage | Current crawler, hashes, extraction schema, Postgres, feed, and profiles retained |
| Selected approach | Reliability-first modular monolith |
| Scope | Selective expansion with requested consumer features sequenced behind trust gates |
| Critical strategic risk | Building a generic monitor or chatbot indistinguishable from existing products |
| Monetization | Deferred until retention; future payment covers convenience, not public facts |
| Deferred scope | 9 explicit categories listed above |

## Design review

Initial design completeness: 3/10. The current site has a coherent editorial style but the product plan initially named features without specifying screens, hierarchy, states, or mobile behavior. No `DESIGN.md` or reusable component system exists. The gstack visual designer was unavailable, so this review uses explicit text wireframes and interaction contracts.

Target after implementation-ready specifications: 8/10. Visual art direction should still receive a dedicated exploration before implementation.

### Information architecture

Public navigation:

```text
PrivacyRadar | Search companies | Changes | Compare | Methodology | Sign in/avatar
```

Authenticated navigation adds `My Radar` as the first destination. Do not add a generic “Dashboard” label.

Site map:

```text
/
├── /companies
│   └── /companies/[slug]
│       └── /changes/[change-id]
├── /changes
├── /compare?companies=a,b
├── /methodology
├── /corrections
├── /login
└── /radar                         authenticated
    ├── /radar/watching
    ├── /radar/alerts
    └── /radar/settings
```

The home page is an acquisition surface, not the logged-in product. Authenticated users land on `/radar`, which prioritizes their companies and unread material changes.

### Core-screen wireframes

Anonymous home:

```text
┌──────────────────────────────────────────────────────────────┐
│ PrivacyRadar        [Search a company…]    Compare  Sign in │
├──────────────────────────────────────────────────────────────┤
│ What do the services you use disclose about your data?      │
│ [ Search Google, OpenAI, Spotify…                         ]  │
│ Evidence-backed. Dated. Correctable.                         │
├──────────────────────────────────────────────────────────────┤
│ Important recent changes                                    │
│ Company · plain-language change · impact · evidence          │
├──────────────────────────────────────────────────────────────┤
│ Explore: AI tools · Social · Health · Dating · Finance      │
└──────────────────────────────────────────────────────────────┘
```

First-run onboarding:

```text
Step 1 of 2: Which services do you use?
[search]  Suggested by category
[ ] ChatGPT [ ] Claude [ ] Gemini [ ] Meta AI …

Sticky footer: 3 selected                 [Watch these companies]

Step 2 of 2: How should we contact you?
(•) Only important changes
( ) Weekly digest
Email: already verified                   [Finish]
```

My Radar:

```text
┌──────────────────────────────────────────────────────────────┐
│ My Radar                         [Add companies] [Settings]  │
│ 12 watched · last checked 2h ago                             │
├──────────────────────────────────────────────────────────────┤
│ NEEDS ATTENTION                                              │
│ OpenAI changed AI-training language                          │
│ Why it may matter · evidence · [Review your setting]         │
├──────────────────────────────────────────────────────────────┤
│ WATCHING                                                     │
│ Company   key disclosed practices   freshness   latest       │
└──────────────────────────────────────────────────────────────┘
```

Company profile hierarchy:

```text
Company + category + verified-through date
[Watch] [Compare]

At a glance
  Sensitive data | Sharing/sale | AI training | Retention | Controls

What the company discloses
  Expandable practice rows with evidence, context, region, freshness

What changed
  Chronological material changes with before/after evidence

What you can do
  Verified settings/rights links, jurisdiction labels, last checked date

Ask about this policy
  Suggested questions first; answer always cites captured evidence
```

Comparison:

```text
Compare [Company A ×] [Company B ×] [+ Add, maximum 4]
Context: region [United States]

Dimension          A                         B
AI training        Disclosed; opt-out…       Not found in evidence
Targeted ads       …                         …
Retention          …                         …
Deletion           …                         …

“Not found” never means “does not happen.” Freshness is visible per column.
```

### Interaction-state contract

Every page and mutation must specify these states:

| Surface | Loading | Empty | Partial/stale | Error | Success |
|---|---|---|---|---|---|
| Company search | stable input + result skeleton | suggested categories and request-company action | results with coverage badges | retry without losing query | keyboard-selectable result |
| My Radar | layout skeleton | warm onboarding with search and category presets | stale company rows retain last verified data | scoped error plus retry | unread changes announced |
| Watch button | optimistic label with disabled repeat | N/A | expired session prompts re-auth without losing company | revert and explain | `Watching` plus undo |
| Change page | content skeleton | not publishable | evidence pending never appears publicly | 404 or service state | shareable canonical page |
| Comparison | column skeletons | prompt to select first two companies | cells explicitly mark unavailable/stale/region mismatch | preserve selected companies | URL is shareable |
| Assistant | streamed answer skeleton | suggested evidence-based questions | missing evidence causes bounded refusal | retry and direct source links | citations focus matching evidence |
| Notifications | pending toggle state | default quiet mode | delivery degraded badge | revert preference change | inline saved confirmation |

Double submission is handled idempotently. Navigating away must not leave ambiguous preference mutations. Back navigation must restore search and comparison selections from the URL. No important action relies only on a toast.

### User journey and emotional arc

| Moment | User question | Intended feeling | Design response |
|---|---|---|---|
| Search arrival | “Can I trust this?” | Skeptical → curious | date, evidence, methodology visible immediately |
| Company profile | “What matters?” | Overwhelmed → oriented | five decision dimensions before detailed practices |
| Evidence inspection | “Did the model make this up?” | Suspicious → reassured | quote context, source, snapshot, correction affordance |
| Watch onboarding | “Is this worth my email?” | Guarded → in control | explain exactly what is stored and frequency default |
| Alert | “Is this urgent?” | Concerned → capable | severity rationale and one concrete next step |
| Comparison | “Should I switch?” | Uncertain → informed | side-by-side disclosed facts, no winner theater |
| Assistant | “Can I ask naturally?” | Curious → bounded confidence | cited answers and explicit insufficient-evidence behavior |

### Visual direction and anti-slop rules

- Retain the editorial paper/ink/serif identity; it suits a public-interest bulletin.
- Add a compact sans-serif UI face for controls and dense comparison data; retain mono only for timestamps, hashes, and evidence metadata.
- Avoid gradients, glass cards, oversized hero copy, generic feature-card grids, animated counters, mascots, and glowing AI chat treatments.
- Evidence is visually distinct from interpretation. Quotes use a stable rail, source metadata, and “view context.”
- Severity never relies on red/green alone and uses plain labels: `Important`, `Moderate`, `Minor`, `Pending review`.
- The assistant is a small contextual panel on company pages, not a floating bubble across the site.
- Do not display a universal privacy score in v1.

### Design tokens and reusable components

Create `DESIGN.md` before UI implementation with:

- Color tokens for paper, ink, muted, rule, surface, focus, important, warning, and success that pass WCAG AA.
- Type ramp with explicit mobile and desktop sizes.
- 4px spacing base, 44px minimum touch target, 2px visible focus ring.
- Components: `SearchCombobox`, `CompanyBadge`, `WatchButton`, `FreshnessLabel`, `EvidenceQuote`, `DisclosureRow`, `ChangeCard`, `ActionCard`, `StatePanel`, `CompanyPicker`, `ComparisonMatrix`, `CitationLink`, and `AssistantPanel`.
- Copy rules: “discloses,” “we found,” “we have not found evidence,” and “last verified”; never “takes” in structured factual UI because it overstates policy evidence.

### Responsive and accessibility contract

- Mobile navigation uses a labeled menu; search stays directly accessible.
- Company profiles remain single-column through tablet widths; evidence context expands in place.
- Comparisons become one dimension at a time with horizontally swipeable company columns and a sticky dimension label. Never shrink four columns into illegible text.
- All controls are operable by keyboard with visible focus. Combobox follows ARIA authoring patterns.
- Dynamic watch/notification changes use polite live regions; material failures use assertive announcements.
- Evidence quote expansion communicates `aria-expanded`; citations have descriptive labels.
- Charts are optional; every visual representation has a table/text equivalent.
- Respect reduced motion. No content shifts while streamed assistant text arrives.
- Test at 320px, 768px, 1024px, and ≥1440px; zoom to 200%; verify long company names and translated strings.

### Design pass scores

| Pass | Before | After specification | Remaining gap |
|---|---:|---:|---|
| Information architecture | 4/10 | 9/10 | usability test needed |
| Interaction states | 2/10 | 9/10 | implementation verification needed |
| User journey | 3/10 | 8/10 | concierge pilot must validate action cards |
| AI-slop resistance | 6/10 | 9/10 | visual mockups unavailable |
| Design-system alignment | 3/10 | 8/10 | `DESIGN.md` and components not built |
| Responsive/accessibility | 2/10 | 8/10 | browser and assistive-tech testing required |
| Unresolved decisions | 2/10 | 8/10 | wedge category and final visual direction remain |

Design `NOT in scope`: gamified privacy scores, dark-pattern urgency, social proof counters, AI-first branding, native-app conventions, and dense analyst dashboards.

Design “what already exists”: Newsreader and Geist Mono fonts, paper/ink tokens, narrow editorial layouts, simple rules, accessible semantic headings, and direct source links. Reuse the calm editorial tone while replacing developer-facing empty-state copy.

## Design dual-voice review

The CLI design voice again inspected the full plan but failed to produce a final verdict. The independent design subagent returned 15 findings and scored the plan 6.6/10. Accepted changes:

- The canonical acquisition path is `search → company profile → watch`. Other home content is supporting discovery.
- Watch preserves the company through magic-link authentication, including cross-device, expired-link, existing-user, and abandoned-flow recovery.
- Email alerts and digests are first-class designed surfaces, not an implementation detail.
- Replace ambiguous “verified” language with `evidence captured`, `last checked`, or an explicit human-review label.
- `Important` and `Needs attention` require published criteria and inline reasons.
- Mobile comparison displays both companies stacked per dimension; it does not hide differences behind horizontal swipes.
- Page-level quiet, unavailable-source, unsupported-region, correction, and deletion states are required.
- Action cards must define action type, jurisdiction, destination, last-check time, external-site boundary, and completion semantics.
- Every interpretation and citation exposes `Report an issue`; corrections preserve public history and trigger corrected alerts when needed.
- Region is explicit, globally visible, account-persisted, overridable, and never silently treated as legal applicability.

```text
DESIGN LITMUS SCORECARD
Dimension                         CLI voice    Subagent    Result
Information hierarchy            N/A          7/10        Action path clarified
Interaction states               N/A          6/10        Auth/trust states added
User journey                     N/A          7/10        Recovery arc added
Specificity                      N/A          6/10        Contracts required
Responsive                       N/A          6/10        Mobile compare changed
Accessibility                    N/A          7/10        Expanded requirements
Trust/system coherence           N/A          7/10        Region/corrections clarified
```

## Design completion summary

| Item | Result |
|---|---|
| UI scope | Public discovery, onboarding, My Radar, profiles, comparisons, alerts, settings, contextual assistant |
| Overall score | 3/10 → 6.6/10 independently; target ≥8/10 after mockups and usability testing |
| Seven passes | All specified above |
| Mockups | Not generated because the local design binary is unavailable |
| Main remaining work | Choose wedge, create visual art direction, validate action cards with users |

## Engineering review

### Scope challenge

The full product touches more than eight files and introduces several stateful domains. Treating it as one implementation would be overbuilt and unsafe. The roadmap therefore uses independently shippable vertical milestones with explicit entrance and exit gates. The architecture stays a modular monolith: one Postgres database, one Next.js application, one Python worker deployment, and Redis/ARQ. No microservices or event broker.

Minimum path that proves value:

```text
25 AI companies + reliable evidence
        ↓
30-user concierge watchlist
        ↓
manually reviewed material alert
        ↓
evidence-backed action card
        ↓
did the user complete/use the action?
```

Full authentication, comparison, assistant, large-scale coverage, and billing are gated by that result.

### System architecture

```text
                              ┌──────────────────────────┐
                              │ Next.js public product   │
 Browser / email link ───────▶│ profiles, changes, radar│
                              │ auth, compare, Q&A       │
                              └────────────┬─────────────┘
                                           │ typed repositories
                                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL                                 │
│ catalog + sources + attempts + snapshots + evidence + events      │
│ users + watches + preferences + actions + outbox + corrections    │
└───────────────┬─────────────────────────────┬──────────────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│ Python monitoring worker │       │ Notification worker      │
│ schedule → fetch → clean │       │ claim outbox → render    │
│ → hash → analyze → gate  │       │ → send → record webhook  │
└────────────┬─────────────┘       └────────────┬─────────────┘
             │                                  │
             ▼                                  ▼
     public policy sources                  email provider
             │
             ▼
     OpenAI structured extraction

Company Q&A:
Browser → authenticated/rate-limited Next.js route → retrieve current evidence
        → model with untrusted text delimited, no tools → citation validator → answer
```

Security boundaries:

- Only the worker fetches external policy URLs. End users cannot cause arbitrary fetches.
- The web application reads only publication-approved evidence for public pages and assistant retrieval.
- User identity always comes from a server-validated session.
- The notification worker claims outbox rows with a lease; it never synthesizes change meaning.
- Policies and user questions are untrusted model input. The model receives no tools or secrets.
- Administrative catalog/review operations use a separate protected command or admin role, never public mutation routes.

### Domain model

Do not replace the schema in one migration. Add forward-only numbered migrations and backfill while current reads remain functional.

Core monitoring additions:

| Entity | Purpose | Key constraints |
|---|---|---|
| `source_attempts` | One record per fetch/extract attempt | source, started/finished, strategy, status, HTTP metadata, error code, retry count |
| `snapshots` changes | Preserve immutable successful content | add final URL, language, region, strategy, byte count; stop updating `fetched_at` on duplicate hash |
| `taxonomy_versions` | Name extraction contract | immutable semantic version and schema checksum |
| `extractions` changes | Auditable model output | prompt version, taxonomy version, provider request ID, validation state, confidence |
| `evidence_spans` | Anchor claims to exact snapshot text | snapshot, start/end offsets or quote hash, surrounding context, validation result |
| `change_events` changes | Publication state machine | `detected → analyzing → review_pending → published/rejected/failed/corrected` |
| `action_cards` | Curated next actions attached to company/event | action type, region, URL, checked_at, evidence, status |
| `corrections` | Public editorial history | target, reporter, state, resolution, public note, corrected event |

Consumer additions:

| Entity | Purpose | Key constraints |
|---|---|---|
| Auth provider tables | Users, sessions, verification tokens | provider-managed schema; hashed single-use tokens |
| `user_profiles` | Minimal product settings | user ID, explicit region, locale, timestamps; no unnecessary demographics |
| `watches` | User-company relationship | unique `(user_id, company_id)`, status, created source |
| `notification_preferences` | Frequency and severity | unique user/channel, quiet defaults |
| `notification_outbox` | Atomic delivery intent | unique `(user_id, event_id, channel, revision)` |
| `notification_deliveries` | Provider result | outbox, provider ID, sent/delivered/bounced/complained/suppressed timestamps |
| `saved_comparisons` | Optional named comparison | maximum four companies; region required |
| `assistant_usage` | Limits without retaining questions by default | user, day, count, token/cost aggregates; raw question nullable with short TTL |
| `product_events` | Privacy-minimal funnel events | event name, coarse source, entity IDs, timestamp; no session replay |
| `entitlements` | Future tier enforcement | user, feature key, allowance; default free values |

### State machines

```text
SOURCE
pending → healthy → degraded → quarantined
   ▲          │          │           │
   └──────────┴──────────┴── manual/recovered check

CHANGE EVENT
detected → analyzing → review_pending → published
                │              │            │
                └→ failed      └→ rejected  └→ corrected

NOTIFICATION
pending → claimed → sent → delivered
   │         │        ├→ delayed → delivered
   │         │        ├→ bounced → suppressed
   │         │        └→ complained → suppressed
   └─────────┴→ retryable_failed → pending

CORRECTION
submitted → acknowledged → reviewing → corrected | declined
```

Database constraints reject invalid terminal-state rewinds. State transitions are implemented as explicit functions and produce audit rows.

### Technology decisions

- Authentication: Better Auth with email magic links on the existing Postgres database. Use hashed, atomic, single-use tokens; 10-minute expiry; request cooldown; generic responses that do not reveal account existence. Google/Apple sign-in can follow only if login conversion demands it.
- Email: Resend-compatible provider abstraction with one concrete provider. Verify webhook signatures, deduplicate webhook IDs, and process bounce/complaint suppression. Provider choice remains replaceable at the adapter boundary.
- Database migrations: a real migration tool and numbered migrations replace repeated execution of `schema.sql`. Keep `schema.sql` as a generated/current reference if useful.
- Python tests: pytest, pytest-asyncio only if asynchronous code is introduced, and testcontainers or disposable Postgres for SQL behavior.
- Web tests: Vitest + Testing Library for components/domain functions; Playwright for critical browser flows.
- Observability: structured JSON logs with run/source/event IDs, Sentry-compatible error reporting, and metrics for crawl health, queue lag, analysis outcomes, publication gates, alert delivery, and assistant cost.
- Feature switches: database/config switches for publication, notifications, assistant, and each expansion cohort. Rollback turns features off; destructive down-migrations are not the recovery strategy.

### Monitoring pipeline contract

```text
Scheduler selects due healthy/degraded sources
    ├─ nil: no due work → metric only
    ├─ empty result: healthy idle state
    └─ DB error: job fails visibly and alerts
            ↓
Worker atomically acquires per-source lease
            ↓
Fetch strategy: HTTP → rendered browser → PDF/document parser
    ├─ invalid content → attempt failed; last good snapshot unchanged
    ├─ 429/5xx/timeout → bounded retry with jitter
    └─ success → normalize and hash
            ↓
Same hash → record successful attempt, schedule next due time, stop
New hash  → immutable snapshot + section diff
            ↓
Materiality analysis → schema validation → evidence-anchor validation
    ├─ cosmetic → rejected event retained for audit, no alert
    ├─ uncertain → review_pending
    └─ material → current-practice extraction + action candidate
            ↓
Publication transaction: event + evidence + outbox intents
            ↓
Notification worker delivers once per user/channel/revision
```

### Assistant contract

- Available only on a company profile after that company has publication-approved current evidence.
- v1 supports a fixed family of questions plus free text: data collected, AI training, advertising, sharing, retention, deletion, opt-out, region, and recent changes.
- Retrieval uses relational evidence records and full-text search first. Do not introduce a vector database until a measured retrieval miss requires it.
- Every material sentence must reference one or more evidence IDs. The server validates quote existence and company/snapshot scope before returning the answer.
- If evidence is incomplete or conflicting, answer that directly. No browsing, legal advice, invented settings instructions, cross-company claims, or tool calls.
- Default data policy: keep aggregate usage and safety results; do not retain raw questions beyond short abuse/debug TTL unless the user explicitly saves chat history.
- Initial allowance: 10 questions per account per day, adjustable by entitlement.

### Performance and scale budget

Target milestone scale: 500 companies, up to four sources each, daily default crawl, higher frequency only for selected sources.

- Replace serial `crawl_all()` with bounded concurrency and per-domain limits. Start with 8 total HTTP fetches and 1 per registrable domain; browser rendering has its own smaller pool.
- `source_attempts(source_id, started_at desc)`, `snapshots(source_id, fetched_at desc)`, `change_events(company_id, published_at desc)`, `watches(user_id, status)`, `watches(company_id, status)`, and outbox claim indexes are mandatory.
- Public list queries use explicit pagination rather than fixed hidden limits.
- Company profile retrieval must avoid repeated lateral scans by using correct composite indexes or a maintained current-publication pointer after measurement.
- Never load full raw HTML or markdown into public page queries. Evidence endpoints fetch narrow spans.
- Set request and model input caps. Store model usage and cost per analysis/answer.
- Retention: raw HTML may be compressed/object-stored after an operational window; normalized text and evidence remain reproducible and immutable.

### Observability and operations

Operational dashboard must answer:

- How many sources are fresh, degraded, quarantined, or overdue?
- Which domains are failing and with which named reason?
- What is queue age by job type?
- How many changes are detected, cosmetic, uncertain, published, corrected, or failed?
- Which model/prompt/taxonomy version produced each claim?
- Did every published event create the expected outbox count?
- What are send, delivery, bounce, complaint, and suppression rates?
- What did assistant retrieval cite, refuse, cost, and fail to validate?

Alerts: source freshness below 95%, critical seeded-source failure, queue age above schedule window, publication-validation failure spike, notification failure spike, complaint rate threshold, or assistant cost ceiling.

Runbooks: source failure/quarantine, bad publication/correction, duplicate alerts, compromised auth/email key, model degradation, database recovery, and cohort rollback.

### Security and privacy requirements

- Threat-model SSRF even though arbitrary URLs are deferred: catalog URLs are validated on write, resolve to public IP space, limit redirects, restrict schemes/ports, and re-check DNS on redirect.
- Sanitize rendered policy content; never execute stored HTML in the product.
- Add CSP, secure cookies, CSRF protection for mutations, origin checks, rate limits, and security headers.
- Secrets are deployment-managed and rotated; logs redact tokens, email magic links, raw cookies, full questions, and policy URL query secrets.
- Account deletion revokes sessions, removes watches/preferences/saved content, pseudonymizes necessary delivery suppression records, and completes within a published period.
- Export provides the user’s watches, settings, saved comparisons, and retained assistant history.
- Publish PrivacyRadar’s own privacy notice before accounts. It must state provider subprocessors and retention plainly.
- Conduct dependency, secret, and container scanning in CI. Backups are encrypted and restoration is tested.

### Deployment and rollback

1. Apply additive schema migration.
2. Deploy code capable of old and new reads.
3. Backfill in bounded resumable batches.
4. Verify counts and invariants.
5. Enable worker behavior for an internal cohort.
6. Enable public/read UI.
7. Enable notifications only after publication and outbox reconciliation passes.

Each product capability has an off switch. A bad event is unpublished and corrected; underlying immutable snapshots remain. Rollback never deletes evidence or rewinds sent email. Schema removals occur only in later cleanup releases after old code is gone.

### Test diagram

| Flow/codepath | Unit | Integration | Browser/E2E | Evaluation/load |
|---|---|---|---|---|
| Normalize/hash/section diff | yes, fixtures and Unicode | snapshot dedupe | N/A | corpus regression |
| HTTP/render/PDF strategies | parser fixtures | mocked network + real representative fixtures | N/A | 25-company canary |
| Source lease/retry/quarantine | transition tests | concurrent Postgres workers | N/A | queue/load test |
| Snapshot/publication transaction | validation tests | rollback and constraint tests | public stale/error state | fault injection |
| Materiality | schema/evidence validator | stored output/version linkage | review surface later | labeled precision/recall eval |
| Practice extraction | taxonomy/negation/context | persistence and current pointer | profile evidence expansion | adversarial/long-policy eval |
| Magic-link auth | token/cooldown helpers | hashed single-use and session tests | same/cross-device, expired, replayed | rate-limit test |
| Watch onboarding | idempotent upsert | authorization and persistence | anonymous → auth → radar, double-click, back | conversion instrument check |
| Region | applicability rules | persisted override | unsupported/mismatch UI | locale matrix |
| Notification outbox | rendering and dedupe key | atomic event/outbox, worker lease, webhook dedupe | settings/unsubscribe flows | burst and retry load |
| Email template | text/HTML snapshots | provider adapter | major clients/manual accessibility | spam/deliverability check |
| Comparison | cell semantics | partial/stale data query | desktop and 320px two-company flow | accessibility tree |
| Action cards | eligibility and status | editorial lifecycle | external action, return, unavailable | concierge outcome validation |
| Corrections | transition tests | amendment and re-notification | submit/status/public history | operational drill |
| Assistant | citation/refusal/rate rules | scoped retrieval and usage accounting | streaming, stop, retry, reduced motion | grounding, injection, cost eval |
| Account deletion/export | ownership rules | cascading/pseudonymization job | request, confirm, completion | restore/privacy audit |
| Public DB outage | typed error mapping | forced connection failure | non-empty service error | recovery drill |

Coverage rule: all domain branches and authorization decisions must be covered; line coverage floor 90% initially, with 100% for evidence validation, state transitions, entitlement checks, and notification deduplication.

### Test-plan artifact

The standalone implementation test plan is saved beside this deliverable as `PRIVACYRADAR_TEST_PLAN.md`.

### Engineering `NOT in scope`

- Microservices, Kafka, vector databases, Elasticsearch, GraphQL, Kubernetes, real-time sockets, native clients, and multi-region active-active infrastructure.
- Password authentication, MFA, social login, organizations, roles beyond a minimal admin/editor boundary, or custom crypto.
- Automatic interpretation of app behavior beyond company disclosures in the first milestones.

### Parallel implementation lanes

| Lane | Work | Dependency |
|---|---|---|
| A | Monitoring reliability, migrations, evidence validation, evals | none |
| B | Product research, wedge catalog, concierge alerts/action cards | none; uses current output initially |
| C | Design system and public profile/change UI | evidence/publication contract from A |
| D | Auth, watches, region, My Radar | migration conventions from A; design contract from C |
| E | Outbox, email, preferences | events from A; users/watches from D |
| F | Comparison | taxonomy and evidence from A; components from C |
| G | Assistant | publication-approved evidence and auth from A/D |
| H | Entitlements and billing | retention gate; last |

Start A and B in parallel. Then C. D and continued catalog work can overlap. E and F can run after their data contracts stabilize. G follows measured question demand. H does not start until the monetization gate.

## Engineering dual-voice review

The CLI engineering voice inspected the repository and plan but did not return a final report. The independent engineering subagent verified critical flaws in the current code and scored the implementation plan 6.2/10. This phase is `subagent-only`; engineering issues remain open.

Accepted blockers and resolutions:

1. **Durable detection before analysis.** A new successful observation atomically creates a `detected` work item and advances no publication state. Model analysis consumes and retries that work independently of future crawls. Crash-after-every-stage tests are mandatory.
2. **Full-document analysis.** Remove the current 120k/40k prefix truncation. Use heading-aware chunks covering every changed section with context overlap, deterministic reconciliation, stored chunk IDs, and late-document fixtures.
3. **Valid snapshot observations.** Non-2xx, error pages, wrong content types, empty/short/non-policy text, and language failures remain only in `source_attempts`; they never become snapshots or current baselines.
4. **A → B → A recurrence.** Separate immutable content snapshots from append-only successful observations. `policy_sources.current_snapshot_id` advances atomically and events compare previous versus newly observed content even when content was seen before.
5. **Cross-runtime ownership.** SQL-first numbered migrations are the single schema authority. Python owns monitoring/publication transitions; TypeScript owns user/watch/preference mutations; the notification worker owns delivery transitions. Shared enums are generated or contract-tested.
6. **Least-privilege database roles.** Separate roles for public web reads, authenticated web mutations, ingestion, notification, migrations, and editor/admin work. Forbidden-write integration tests are required.
7. **Batched fan-out.** Publication creates one durable fan-out job, not every user outbox row in its transaction. The fan-out worker pages through watchers, writes unique outbox rows, resumes by cursor, and reconciles counts.
8. **Per-source jobs.** The scheduler enqueues versioned work per source; workers claim independent leases. A single `crawl_all` invocation is no longer the failure domain.
9. **Public caching.** Public profiles/change pages use revalidation and publication-driven invalidation; personalized routes stay dynamic. Use a pooler/serverless-safe database connection with an explicit connection budget.
10. **Immutable correction revisions.** A correction supersedes rather than mutates a publication revision, keeps both records public, and follows an explicit corrected-alert policy.
11. **Token boundaries.** Return URLs are same-origin allowlisted; magic/unsubscribe links are hashed, purpose-bound, expiring, replay-safe, and redacted from logs/referrers.
12. **Operational editor surface.** Build protected admin/editor routes with strong authentication, audit identity, leased review queues, quarantine controls, action-card maintenance, corrections, and bulk triage before catalog scale.

```text
ENG DUAL VOICES — CONSENSUS TABLE
Dimension                       CLI voice    Subagent    Result
Architecture sound              N/A          7/10        Issues open
Test coverage sufficient        N/A          7/10        Harness missing
Performance risks addressed     N/A          5/10        10× budget added
Security threats covered        N/A          7/10        DB/token gaps accepted
Error paths handled             N/A          6/10        Durable work required
Deployment risk manageable      N/A          5/10        Topology specified below
```

### Concrete deployment topology

Recommended early production topology:

```text
GitHub Actions
   ├─ lint/type/unit/integration/evals
   ├─ build Next.js
   └─ build signed worker image with Chromium
          │
          ├──▶ Vercel: Next.js public + authenticated web
          │       └─ serverless-safe pooled Postgres connection
          │
          └──▶ Railway: scheduler + worker processes
                  ├─ managed Postgres 16 (primary system of record)
                  ├─ managed Redis (ARQ only)
                  └─ encrypted object storage adapter when blob threshold is crossed
```

- Keep web and backend services in the closest compatible region; measure cross-provider DB latency before launch. If Vercel-to-Railway database behavior misses the connection/latency SLO, move the web deployment to Railway rather than adding a caching maze.
- Environments: local, staging, production with separate databases, Redis, email domains, model keys, and callback URLs. No staging system sends to real users.
- One migration job takes a Postgres advisory lock and completes before application promotion.
- Health probes: web liveness/readiness, worker heartbeat, scheduler heartbeat, database, Redis, queue age, and browser-fetch canary.
- Every job payload has a schema version. Rolling deploys support N and N−1; incompatible queues are drained or isolated.
- Staging canary runs the 25-company corpus before production cohort enablement.

### True 10× capacity envelope

The milestone target is 500 companies × four sources. Capacity tests cover at least:

| Dimension | 1× operating target | 10× test envelope | Pass criterion |
|---|---:|---:|---|
| Sources due/day | 2,000 | 20,000 | 95% finish within schedule window |
| Registered users | 10,000 | 100,000 | auth/watch p95 <500ms excluding email |
| Watchers on one event | 10,000 | 100,000 | fan-out resumable; no duplicates; bounded DB locks |
| Notification burst | 10,000 | 100,000 | provider throughput respected; queue drains inside SLO |
| Public reads/day | 100,000 | 1,000,000 | cache hit target ≥90%; DB connections remain under budget |
| Assistant concurrency | 20 | 200 | rate/cost ceiling holds; graceful queue or refusal |
| Stored policy text | measured after wedge | projected 24-month 10× | storage cost and restore time within budget |

Final numeric latency, connection, queue-drain, and cost SLOs are established from Milestone 1 benchmarks before open signup.

## Engineering completion summary

| Item | Result |
|---|---|
| Scope | Split into gated vertical milestones; no big-bang product build |
| Architecture | Modular monolith with explicit worker/web/security boundaries |
| Code quality | Typed errors, repositories, state transitions, migrations, no swallowed failures |
| Tests | Full flow-to-test map; critical invariants at 100% branch coverage |
| Performance | Bounded concurrency and indexes sized for 500 companies × 4 sources |
| Critical gaps in current repo | No tests, silent query failure, invalid empty snapshot behavior, no model-evidence validation, serial crawl |
| Parallelization | 8 lanes with A+B first; gated dependencies listed |

## Strict roadmap

Dates are intentionally expressed as gates, not promises. A milestone may start only when the prior exit criteria pass.

### Milestone 0: prove the wedge before building the platform

Goal: learn whether evidence-backed privacy actions matter to consumers.

Scope:

- Choose **consumer AI tools** as the recommended first wedge: high concern, frequent policy/product changes, meaningful AI-training controls, and existing seed coverage.
- Select 25 companies using concern, change frequency, actionable controls, alternative availability, and crawl feasibility.
- Recruit 30 consumers who use at least three of them.
- Run four weeks of concierge monitoring. Review every alert manually and attach one precise action card.
- Interview each participant at start and end; log alert relevance, understanding, action attempted, action completed, and trust concerns.
- Publish a lightweight methodology and correction contact before recruiting.

Exit gate:

- ≥20 participants activate a watchlist of three companies.
- ≥10 participants complete or deliberately decline a privacy action because of a PrivacyRadar insight.
- At least three repeatable alert/action archetypes emerge.
- At least 70% of participants say the alert was clear and evidence increased trust.

Kill/reframe gate: if fewer than five people act after four weeks, stop the feature roadmap. Revisit the wedge, acquisition moment, or whether policy monitoring creates consumer value.

### Milestone 1: trustworthy monitoring foundation

Scope:

- Numbered migrations and test infrastructure.
- Source attempts, immutable snapshots, leases, retry/quarantine state, and bounded concurrency.
- HTTP plus rendered-browser fallback; PDF only when a selected wedge source requires it.
- Versioned consumer-decision taxonomy and a 200-pair labeled evaluation corpus.
- Evidence anchoring, context/negation checks, publication state, correction workflow, and internal review queue.
- Typed web failures, error boundaries, canonical URLs/RSS base URL configuration, structured logs, health metrics, alerts, and runbooks.

Exit gate:

- 25 wedge companies stay ≥95% fresh for 14 consecutive days.
- Material precision ≥95%; evidence anchoring 100%; no critical silent failures.
- Every current critical path in the test artifact passes in CI.
- One bad-publication correction drill and one database restore drill succeed.

### Milestone 2: public decision pages

Scope:

- `DESIGN.md`, shared components, search-first home, searchable catalog, company profiles, individual change pages, methodology, and correction history.
- Use `disclosed practices`; show source, region, evidence context, taxonomy version, and checked date.
- Action cards for only the archetypes proven in Milestone 0.
- Indexable decision pages: “Does X train on my data?”, “How do I opt out of X?”, and “X privacy changes,” generated only from approved structured evidence.
- Privacy-minimal product analytics.

Exit gate:

- 10 moderated usability sessions: ≥8 find a company, explain one disclosed practice correctly, and locate its evidence without help.
- Accessibility checks pass at 320px and desktop; no critical axe/keyboard/VoiceOver failures.
- Search-to-profile action rate and correction rate establish a baseline without paid acquisition.

### Milestone 3: auth, personal radar, and email

Scope:

- Better Auth email magic links, explicit region onboarding, privacy notice, account export/deletion.
- Anonymous Watch intent survives same-device and cross-device authentication.
- My Radar, watches, alert inbox, quiet-state reassurance, daily/weekly/important-only preferences.
- Transactional outbox, accessible alert/digest templates, webhook verification, delivery and suppression handling.
- Cohort rollout from the original 30 users to 100, then open signup.

Exit gate:

- ≥40% of new accounts watch three companies in the first session.
- ≥90% of magic-link completions restore the intended company selection.
- Zero duplicate alerts in failure/retry drills.
- Delivery ≥98% excluding known suppression; complaints remain below provider threshold.
- 30-day activated-user retention ≥25%, and alert-to-action ≥10%.

### Milestone 4: expand in cohorts

Scope:

- Add 25 companies per cohort based on search/nominations/watch demand.
- Add a public nomination queue, clearly labeled `requested, not monitored` until approved.
- Automate catalog validation while retaining editorial approval.
- Introduce new categories only after the AI cohort retains users. Recommended order: social/dating, health, finance, children.
- Add a second region only after the first region’s applicability and source model are stable.

Per-cohort gate:

- ≥95% freshness and extraction review complete.
- At least 20% of activated users search for or watch a company in the cohort, or the cohort has a documented acquisition purpose.
- No new category ships without action cards relevant to that category.

The target is not “a shit lot of companies” as an engineering vanity metric. The target is 500 useful, healthy companies reached in validated cohorts.

### Milestone 5: comparison

Scope:

- Public URL-addressable comparison for two companies on mobile and up to four on desktop.
- Compare disclosed facts, evidence freshness, region, controls, and action availability. No universal winner or opaque grade.
- Saved comparisons are optional for signed-in users.

Entrance gate: users repeatedly inspect two competing companies or request switching guidance in interviews/search data.

Exit gate: ≥20% of comparison sessions open evidence or an action/alternative; usability participants interpret `not found in evidence` correctly.

### Milestone 6: small cited assistant

Scope:

- Contextual company-profile assistant, structured retrieval, fixed suggested questions plus free text, citations, refusal, and daily allowance.
- No generic browsing, legal advice, autonomous action, or global floating widget.
- Chat history off by default; short operational retention documented.

Entrance gate: at least 100 real search/support questions show repeated needs not solved by profile navigation.

Exit gate:

- ≥98% supported material sentences on the eval set.
- ≥95% correct refusals when evidence is absent/conflicting.
- Zero unanchored citations and zero successful prompt-injection cases in the adversarial suite.
- Per-answer cost and latency remain inside defined budgets.

### Milestone 7: tiers and billing, only after product proof

Instrument entitlements early, but do not integrate Stripe or display paid tiers until all gates pass:

- ≥1,000 activated accounts.
- ≥30% 90-day watchlist retention.
- ≥10% monthly alert-to-action rate.
- At least 100 users hit a real free allowance or request a convenience feature.
- Fake-door willingness-to-pay test produces ≥5% checkout intent among retained users.

Provisional future tiers, subject to research:

| Tier | Price hypothesis | Included |
|---|---:|---|
| Public | Free, no account | All public profiles, evidence, changes, methodology, RSS, two-company comparison |
| Free account | Free | 10 watched companies, weekly digest, important alerts, 10 assistant questions/day |
| Plus | Test $4-6/month or $40-50/year | 100 watches, instant/daily delivery, four-company saved comparisons, higher assistant allowance, action history |
| Family | Test $8-10/month | Up to five private profiles/watchlists and shared digest controls |

Do not charge for better facts, hide evidence, sell watchlist data, introduce ads, or create fear-based dark patterns. Annual plans may be introduced only with plain renewal/cancellation and a self-serve portal.

### Milestone 8: defensibility, after the core loop works

- Add discrepancy reports that clearly separate company disclosures from app-store privacy labels, permissions, tracker observations, breach reports, and regulator actions.
- Publish an open methodology, selected datasets, and research access.
- Explore browser-extension distribution only if “check before signup/use” demand is proven.
- Explore guided rights-request templates before automated requests.

## Prioritized backlog

| Priority | Work item | Depends on | Explicit completion criterion |
|---:|---|---|---|
| P0 | Fix silent web errors and invalid empty snapshots | none | forced failures produce explicit states and never valid snapshots |
| P0 | Test infrastructure and migrations | none | CI runs unit/integration/browser skeletons and upgrades prototype DB |
| P0 | Evidence validation/publication gate | taxonomy | unsupported claims cannot publish |
| P0 | 30-person concierge experiment | 25-company wedge | action outcome data collected for four weeks |
| P1 | Source attempt/lease/retry/quarantine | migrations | concurrency and failure drills pass |
| P1 | Versioned action-oriented taxonomy + evals | corpus | precision/evidence gates pass |
| P1 | Public methodology/corrections | evidence model | every claim is reportable and amendments remain public |
| P1 | Search/profile/change/action UI | design system | usability and accessibility exit gates pass |
| P1 | Magic-link auth + region + watches | public UI/data contract | Watch intent restoration ≥90% |
| P1 | Transactional email alerts | auth/watches/events | no duplicates; delivery gates pass |
| P2 | Demand-ranked catalog cohorts | monitoring health | each cohort passes demand and quality gate |
| P2 | Comparison | stable taxonomy | evidence/action engagement gate passes |
| P3 | Cited assistant | measured questions | grounding/refusal/security evals pass |
| P4 | Billing | retention/WTP gates | self-serve subscription lifecycle passes |

## Decision audit trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---:|---|---|---|---|---|---|
| 1 | CEO | Consumer-only product | Founder premise | Focus | Explicit user direction | B2B/hybrid |
| 2 | CEO | Personal privacy decision layer | Auto | Completeness | Action creates more value than summaries alone | Passive monitoring |
| 3 | CEO | AI-tool wedge and 30-person pilot | Taste, recommended | Pragmatic | Test demand before broad build | Generic catalog-first |
| 4 | CEO | Public facts always free | Auto | Trust | Monetization must align with public-interest premise | Evidence paywall |
| 5 | CEO | Gate billing on retention and WTP | Auto | Bias to evidence | Avoid speculative payment work | Billing now |
| 6 | Eng | Reliability-first modular monolith | Auto | Explicit/pragmatic | Reuses current stack without premature services | Patchwork/rewrite |
| 7 | Eng | Additive migrations and immutable evidence | Auto | Completeness | Historical trust requires reproducibility | Mutable current-state records |
| 8 | Eng | Transactional outbox for alerts | Auto | Completeness | Prevent missing/duplicate delivery | Direct send in crawl transaction |
| 9 | Design | Search → profile → watch as primary path | Auto | Explicit | One obvious acquisition action | Competing CTAs |
| 10 | Design | No universal privacy score | Taste, recommended | Trust | Avoid false precision and rating competition | Opaque grade |
| 11 | Design | Stacked mobile comparison | Auto | Accessibility | Keeps both companies visible | Horizontal hidden columns |
| 12 | Eng | Assistant last, relational retrieval first | Auto | DRY/pragmatic | Existing evidence is structured; vector infra is unproven | Chat-first/vector DB |
| 13 | Eng | Better Auth magic links | Taste, recommended | Boring technology | Minimal consumer auth surface | Passwords/custom auth |
| 14 | Eng | One explicit starting region | Taste, recommended | Explicit | Avoid silent legal applicability assumptions | Automatic global inference |

## Cross-phase themes

- **Actionability:** CEO and design independently found that passive insight is not enough. Action cards and measurable outcomes are the core loop.
- **Trust language:** CEO, design, and engineering all require “disclosed practices,” evidence context, corrections, and no overclaiming.
- **Scope sequencing:** Strategy and engineering both reject building auth, chat, billing, and broad coverage before consumer validation.
- **Quiet reliability:** Design requires reassuring silence; engineering requires visible failures and deduplicated delivery.
- **Region:** Design and engineering both identified region as a product-level setting, not database metadata.

## Remaining taste decisions

1. First wedge: recommended `consumer AI tools`; dating, health, or children’s apps are viable alternatives with different acquisition and sensitivity profiles.
2. Auth provider: recommended Better Auth; a hosted provider reduces auth operations but adds recurring cost and another privacy subprocessor.
3. Paid tier allowances and prices: hypotheses only; must be researched after retention.
4. Final visual direction: blocked on mockup generation and user review.

## Research record

Reviewed on 2026-08-13:

- [Pew Research: How Americans view data privacy](https://www.pewresearch.org/internet/2023/10/18/how-americans-view-data-privacy/) establishes high concern, low understanding, and low perceived control.
- [Pew Research: How Americans protect their online data](https://www.pewresearch.org/internet/2023/10/18/how-americans-protect-their-online-data/) reports that most people consider policies ineffective and something to get past, supporting an action-first product rather than a reading product.
- [FTC: Bringing Dark Patterns to Light](https://www.ftc.gov/reports/bringing-dark-patterns-light) supports careful treatment of privacy controls and avoidance of manipulative urgency.
- [ToS;DR](https://tosdr.org/en) demonstrates consumer-facing grades and point-based policy interpretation; PrivacyRadar should not copy an opaque universal score.
- [Common Sense Privacy Ratings](https://privacy.commonsense.org/resource/privacy-ratings) demonstrates a large rubric-driven consumer catalog with human review.
- [Termsight](https://termsight.ai/) already markets daily policy crawling, change summaries, impact assessment, a public directory, watchlists, alerts, RSS, API, and evidence-oriented history.
- [Watchobots policy monitoring](https://watchobots.com/use-cases/policy-monitoring) offers daily monitoring, AI summaries, importance, two free pages, and paid delivery integrations, showing that generic monitoring is commoditized.
- [Osano policy change detection](https://www.osano.com/products/policy-change-detection) validates enterprise demand but is explicitly outside PrivacyRadar’s consumer scope.
- [Better Auth magic links](https://better-auth.com/docs/plugins/magic-link) documents Next.js-compatible passwordless auth, single-use behavior, hashed token storage, and atomic storage requirements.
- [Resend webhook event types](https://resend.com/docs/webhooks/event-types) defines delivery, delay, failure, bounce, complaint, and suppression states that the notification model must consume.

## Final recommendation

Approve the long-term consumer vision, but do **not** approve immediate implementation of all requested features. Approve the gated sequence: AI-tool wedge and concierge action validation → trustworthy evidence platform → public decision pages → auth/watchlists/email → cohort expansion → comparison → assistant → billing.

This is the plan’s central user challenge. The founder asked to expand to many companies and add auth, tiers, notifications, comparisons, and chat. The review recommends preserving those as the destination but refusing to build them in parallel before the first 30 consumers prove that alerts lead to useful privacy actions. If that challenge is rejected, the fallback is still the reliability-first modular monolith, but product risk and wasted build probability rise sharply.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---:|---|---|
| CEO Review | `/autoplan` | Scope and strategy | 1 | ISSUES OPEN | Consumer wedge/action validation is a founder approval gate |
| Outside Voice | Codex CLI + subagent | Independent challenge | 3 phases | SUBAGENT-ONLY | CLI inspected but returned no verdict; subagent findings integrated |
| Eng Review | `/autoplan` | Architecture and tests | 1 | ISSUES OPEN | 6 implementation blockers; resolutions added, implementation not yet run |
| Design Review | `/autoplan` | UI/UX gaps | 1 | ISSUES OPEN | 3/10 → independently 6.6/10; visual mockups and testing remain |
| DX Review | skipped | Product is consumer-facing, not a developer tool | 0 | N/A | No public API/SDK/CLI product in scope |

**UNRESOLVED:** founder approval of the sequencing challenge, first wedge, final visual direction, and future pricing hypotheses.

**VERDICT:** strategy is ready for founder decision. Engineering is not implementation-cleared until Milestone 0 is accepted and the six Phase 3 blockers become the first implementation slice.
