# privacyradar

public bulletin for what data companies take, and what just changed in their privacy policies.

the site is next.js. the product is a python worker that crawls, hashes, and only then calls openai.

## product roadmap

- [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) is the reviewed product, architecture, and milestone source of truth.
- [`docs/AGENT_IMPLEMENTATION_GUIDE.md`](docs/AGENT_IMPLEMENTATION_GUIDE.md) tells coding agents how to select, implement, test, and hand off roadmap issues.
- [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) defines the required unit, integration, browser, evaluation, load, and operational coverage.
- [`docs/TODOS.md`](docs/TODOS.md) records deliberately deferred work and its prerequisites.

Do not implement later milestones merely because they are documented. Every milestone has an entrance and exit gate; GitHub subissues carry the executable scope.

## how it works

1. hand-picked catalog of privacy-policy urls (start with 10, grow to 100-200).
2. fetch with httpx, clean with trafilatura, sha-256 the markdown.
3. if the hash matches the last snapshot, stop. no model, no feed item.
4. if it changed, a cheap openai model decides cosmetic vs material.
5. material diffs get structured extraction (data types, purposes, third parties, quotes) and land on the public feed.

## stack

| piece | choice |
| --- | --- |
| public site | next.js on vercel (`web/`) |
| worker | python 3.12 + cli / arq (`worker/`) |
| db | postgres 16 |
| queue | redis + arq (4 crawls/day) |
| models | openai structured outputs (`gpt-4.1-mini`, `gpt-5.6` for hard cases) |

## run locally

this repo talks to postgres. if you already have postgres on `:5432`:

```bash
createdb privacyradar
psql -d privacyradar -f db/schema.sql
cp .env.example .env
# set DATABASE_URL=postgresql://$USER@localhost:5432/privacyradar
```

or use compose (postgres on `:5433` so it does not collide with a local server):

```bash
docker compose up -d
```

then:

```bash
cp .env.example .env
# paste OPENAI_API_KEY when you want extraction (crawling works without it)

cd worker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
privacyradar seed
privacyradar crawl

cd ../web
echo 'DATABASE_URL=postgresql://'"$USER"'@localhost:5432/privacyradar' > .env.local
npm install
npm run dev
```

first crawl of the seed catalog (2026-08-13, httpx + trafilatura, no openai key): 9/10 policies extracted at 22k-211k characters. apple's privacy page is a js shell (~337 chars) and needs playwright later.

arq worker (optional, for the 00:20 / 06:20 / 12:20 / 18:20 cron):

```bash
cd worker
source .venv/bin/activate
arq privacyradar.jobs.WorkerSettings
```

## what not to do

- do not send every policy through a model every day.
- do not crawl from vercel serverless (no chromium, short timeouts).
- do not publish a claim without a verbatim quote.
- do not call this legal advice on the public page.

## layout

```
web/          next.js bulletin (feed, catalog, company pages, rss)
worker/       crawler + hasher + openai extractor
db/schema.sql postgres schema
docker-compose.yml   postgres + redis
```
