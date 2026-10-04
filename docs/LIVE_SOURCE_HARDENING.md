# Live Source Hardening Notes

## NSO CPI

- Landing page: `https://www.nso.gov.vn/cpi-vi/`
- The collector discovers the latest CPI detail link, then parses the detail page.
- Canonical eligible after direct NSO parse + schema validation.
- Expected cadence: monthly.

## SBV Central USD/VND Rate

- Candidate endpoint: `https://dttktt.sbv.gov.vn/TyGia/faces/TyGia.jspx`
- Direct SBV capture is required before the indicator can be marked canonical-ready.
- The endpoint/parser is intentionally monitored through source health because SBV's web presentation may change independently of this project.
- Trusted media is evidence only and cannot silently replace the SBV record.

## SJC Gold

- Direct source: `https://sjc.com.vn/`
- Extracts HCMC SJC 1L/10L/1KG buy and sell quotes.
- Source unit is thousand VND/tael; normalized value is integer VND/tael.
- Quote timestamp is preserved.

## VOV Central Rate Evidence

- Landing page: `https://vov.vn/thi-truong/`
- Discovery searches for a recent central-rate/FX article.
- Optional source. If no relevant article is found, the core candidate build can still succeed.
- Media evidence remains `reported` until official verification.

## Vietcap Macro Research

- Landing page: `https://www.vietcap.com.vn/en/research-center/`
- Discovery searches for macro research articles.
- Research data is stored separately and never overwrites official actual observations.

## Why raw HTML is temporary

The collector needs raw content for parsing/debugging, but Phase 4.2B intentionally excludes fetched pages from Git and review artifacts. Candidate outputs retain URLs, hashes, timestamps and normalized facts instead of republishing source pages.
