# Dual scheduler for RSS news

Primary GitHub schedule: 07:20–21:20 Vietnam time, every two hours.
Backup GitHub schedule: 07:50–21:50 Vietnam time, every two hours.

The backup gate reads data/state/news-ingestion-health.json and skips collection when the corresponding primary slot was already collected.

## Independent Cloudflare timer
Cloudflare Worker source is at workers/news-rss-fallback/src/index.mjs.
Configuration is at workers/news-rss-fallback/wrangler.jsonc.

The Worker is NOT active until deployed in a Cloudflare account.
A fine-grained GitHub access token is required with Actions write and Contents read permissions, restricted to this repository. Store the token as a Worker secret, not in source files.

Deployment commands (repository root):
- npx wrangler login
- npx wrangler deploy --config workers/news-rss-fallback/wrangler.jsonc
- npx wrangler secret put GITHUB_TOKEN --config workers/news-rss-fallback/wrangler.jsonc

Verify Worker logs and GitHub workflow_dispatch runs after the next backup schedule. Confirm news-ingestion-health.json checked_at has advanced, and examine the article count.

GitHub scheduler is best-effort, and even an independent timer still relies on GitHub to execute the actual workflow.

## Macro recovery — 12 October 2026

The same existing Cloudflare Worker `real-estate` additionally acts as an independent trigger for the existing controlled daily FX/gold Macro pipeline.

- GitHub primary daily FX/gold collection: 10:15 ICT (03:15 UTC).
- Cloudflare fallback: 10:45 ICT (03:45 UTC).
- GitHub primary business-day afternoon: 16:15 ICT (09:15 UTC Monday–Friday).
- Cloudflare fallback: 16:45 ICT (09:45 UTC Monday–Friday).

At each fallback check, the Worker queries recent runs of `macro-candidate.yml`. It skips a slot already completed successfully or currently queued/running. If missing or failed, it dispatches `daily-markets-production` using the existing `GITHUB_TOKEN` secret. No token or source values are committed. No upstream collector or verification policy is bypassed.

### Important
The Worker source and wrangler schedule in GitHub are NOT deployment proof. After code review/CI, deploy updated code to the existing Cloudflare Worker `real-estate`; preserve the existing `GITHUB_TOKEN` secret and RSS schedules. Verify Cloudflare Cron settings contain three expressions, not just the RSS expression.

- `50 0,2,4,6,8,10,12,14 * * *` (RSS).
- `45 3 * * *` (Macro morning).
- `45 9 * * 1-5` (Macro business-day afternoon).

Cloudflare logs should show `already-running`, `already-success` or `dispatched`. For dispatched runs, check the GitHub workflow job result plus `data/processed/macro/observations.json`. A successful no-change run is valid if no new source passes corroboration.

Macro CPI, customer bank rates and SBV policy rates retain their separate release-based schedules and publication quality gates. This recovery change covers daily FX/gold only; expanding to other groups needs individual cadence and evidence checks.
