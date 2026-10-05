# Phase 4.2J.1 — Upload / Run Note

1. Extract `PHASE4_2J_1_SBV_CUSTOMER_RATES_PATCH.zip`.
2. Upload all contents to the repository root and overwrite matching files.
3. Commit the changes.
4. Go to **Actions → Macro Candidate Collector → Run workflow**.
5. For `source`, select **`sbv-customer-rates`**.
6. Run it once.

Do **not** run Macro Production Persistence after this step.
Do **not** manually change the production JSON.

### What to send back
Send a screenshot of the Action summary. If the run succeeds, also download and send the candidate artifact if convenient. If it fails, send the expanded failing step/log; the likely hardening point would be SBV discovery/attachment access rather than production data.
