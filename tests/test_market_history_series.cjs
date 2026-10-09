const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = { window: {}, Intl, Number };
vm.runInNewContext(fs.readFileSync('assets/js/market-history-series.js', 'utf8'), context);
const api = context.window.MarketHistorySeries;
const rows = [
  { period: '2024-Q4', period_type:'quarter', new_supply:2719, sales_units:2630 },
  { period: '2025-Q1', period_type:'quarter', new_supply:2877, sales_units:1101 },
  { period: '2025-Q4', period_type:'quarter', new_supply:3358, sales_units:3196 },
  { period: '2026-Q1', period_type:'quarter', new_supply:1200, sales_units:null },
  { period: '2026-Q2', period_type:'quarter', new_supply:null, sales_units:null },
];
const s = api.expandQuarterHistory(rows);
assert.equal(s.observed, 5);
assert.deepEqual(Array.from(s.missing), ['2025-Q2', '2025-Q3']);
assert.deepEqual(Array.from(s.rows.filter(x=>x.data_missing).map(x=>x.new_supply)), [null,null]);
assert.equal(s.rows.length, 7);
assert.equal(s.rows[0].period, '2024-Q4');
assert.equal(s.rows.at(-1).period, '2026-Q2');
const c = api.coverageSummary(s);
assert.equal(c.observed, 5);
assert.equal(c.missing, 2);
assert.equal(c.salesPeriods, 3);
assert.equal(c.supplyPeriods, 4);
assert.equal(api.originalUsdPrice({reported_primary_price_usd_per_sqm: 6113}), 'US$ 6,113/m²');
assert.equal(api.originalUsdPrice({average_asp:102000000}), '—');
assert.equal(api.quarterIndex('2025-H1'), null);
assert.equal(api.quarterIndex('2025'), null);
assert.equal(api.expandQuarterHistory([{period:'2025-H1',period_type:'half-year',new_supply:1400}]).rows.length, 0);
assert.equal(api.expandQuarterHistory([]).rows.length, 0);
const view=fs.readFileSync('assets/js/market.js','utf8');
assert.ok(view.includes('MarketHistorySeries.expandQuarterHistory'), 'Must preserve visible quarter gaps');
assert.ok(view.includes('Source-period coverage'), 'Must explain source history completeness');
assert.ok(view.includes('Reported price (USD/m²)'), 'Must show publisher price without unverified FX conversion');
const page=fs.readFileSync('market.html','utf8');
assert.ok(page.indexOf('market-history-series.js') < page.indexOf('assets/js/market.js'));
console.log('Historical Market series tests PASS: gaps, completeness, original USD and source isolation');
