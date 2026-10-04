# Failure Policy

- Collectors are independent. One source failure must not erase or zero other source data.
- Production publish is disabled in Phase 4.2A.
- Direct official records are canonical for official actual series.
- Trusted-media fallback is evidence only (`reported`/`corroborated`) and cannot silently masquerade as official canonical data.
- Research forecasts remain separate evidence.
- Empty datasets, drastic record-count drops, schema errors, invalid units, and impossible ranges block publication.
- Previous good production output remains untouched on failure.
