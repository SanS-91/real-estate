const assert=require("node:assert/strict");
const fs=require("node:fs");
const maintenance=fs.readFileSync("maintenance.html","utf8");
const js=fs.readFileSync("assets/js/maintenance.js","utf8");
const css=fs.readFileSync("assets/css/main.css","utf8");
const script=fs.readFileSync("scripts/market_active_listing_coverage.py","utf8");
const workflow=fs.readFileSync(".github/workflows/market-active-listing-coverage.yml","utf8");
const targets=JSON.parse(fs.readFileSync("config/market-muaban-listing-targets.json","utf8")).targets;

assert(maintenance.includes('data-market-active-coverage'));
assert(maintenance.includes('market-active-coverage-title'));
assert(maintenance.includes('coverage=4I7'));
assert(js.includes("data/state/market-active-listing-coverage.json"));
assert(js.includes("project_registry_count"));
assert(js.includes("projects_with_current_verified_unit_offers"));
assert(js.includes("recent_eligible_ads"));
assert(js.includes("current_verified_ads"));
assert(js.includes("market.html?view=projects&project="));
assert(js.includes("renderActiveListingCoverage();"));
assert(js.includes("app:language-changed"));
assert(js.includes("no-verified-unit-source-target"));
assert(js.includes("source-qualified-awaiting-verification"));
assert(css.includes(".data-table--listing-coverage.mobile-record-table tbody td:first-child"));
assert(script.includes('scope": "individual-verified-apartment-asking-only"'));
assert(script.includes("is_current_offer"));
assert(script.includes("MAX_HEALTH_AGE_HOURS = 48"));
assert(script.includes('"source_id"'));
assert(!script.includes("mean_price"));
assert(!script.includes("weighted_asp"));
assert(workflow.includes("python scripts/market_active_listing_coverage.py"));
assert(workflow.includes("if: github.event_name != 'pull_request'"));
for (const id of ["mizuki-park","eaton-park"]){
  const t=targets.find(x=>x.project_id===id);
  assert(t && t.url.startsWith("https://muaban.net/bat-dong-san/ban-can-ho"));
}
console.log("PASS: live per-project source coverage remains bilingual, mobile-readable and unit-price isolated");
