# GitHub Merge Plan — Phase 4.2B

Phase 4.2B is designed as an additive collector layer beside v7.2.1.

## Frontend files that must remain untouched

- `index.html`
- `market.html`
- `legal.html`
- `infrastructure.html`
- `macro.html`
- `assets/**`
- existing `data/mock/**`
- existing `data/processed/**`

## New collector areas

- `.github/workflows/macro-candidate.yml`
- `scripts/**`
- `tests/**`
- `schemas/**`
- collector-specific files under `config/**`
- `data/candidate/**`
- `data/examples/**`
- `data/rejected/**`
- `data/state/**`
- `requirements.txt`

The standalone review package README should not overwrite the website repository README unless explicitly desired.
