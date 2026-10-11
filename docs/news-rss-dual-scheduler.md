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
