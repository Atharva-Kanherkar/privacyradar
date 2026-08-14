# Branch protection for PrivacyRadar

Required checks are configured on `main` by a repository owner. Agents must not bypass them.

## Currently required on `main`

These checks already gate merge (strict, linear history, conversation resolution, `enforce_admins`):

- `Web lint, typecheck, build`
- `Worker lint, typecheck, test`
- `PostgreSQL schema validation`
- `Dependency review`

## Add after this foundation lands

Once the jobs exist on `main`, an owner should add these required checks without lowering the existing four:

- `Browser smoke`
- `PR secret guard`

GitHub settings: Settings → Branches → Branch protection rules → `main` → Status checks that are required.

Do not enable admin bypass. Do not allow force pushes. Keep required linear history.

## Production deploys after CI on `main`

Push to `main` runs `CI`. When that push succeeds:

- **Web (Vercel):** the `Deploy` workflow deploys production. Git auto-deploys are off in `web/vercel.json`.
- **Worker (Railway):** the GitHub App deploys the `worker` service from `main` with **Wait for CI** on. A failed check suite skips the worker; production keeps the previous revision.

`Deploy` uses GitHub environment `production` for Vercel tokens. Do not interpolate those secrets into pull-request workflows.

## Untrusted pull requests

Workflows use `pull_request` and `push` to `main` only. `pull_request_target` is forbidden. Pull-request workflows must not interpolate `secrets.*`. Application credentials stay in the production deploy environment, never in PR CI.
