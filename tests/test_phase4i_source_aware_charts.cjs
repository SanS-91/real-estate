const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const context = { window: {}, Intl, Number, Map };
vm.runInNewContext(fs.readFileSync('assets/js/market-history-series.js', 'utf8'), context);
const hist = context.window.MarketHistorySeries;

const cbre = { source_id:'cbre-vietnam-market', period:'2026-Q2', period_type:'quarter',
  new_supply:850, sales_units:null, absorption_rate:null };
const cushman = { source_id:'cushman-wakefield-vietnam-market', period:'2026-Q2', period_type:'quarter',
  new_supply:null, new_supply_lower_bound:1300, sales_units:null, absorption_rate:.31 };

assert.equal(hist.preferredQuarterlySource([cbre,cushman]), 'cushman-wakefield-vietnam-market',
  'More complete current quarter must win a tied source-period decision');
assert.equal(hist.preferredQuarterlySource([cbre, {...cushman, period:'2026-Q3'}]),
  'cushman-wakefield-vietnam-market', 'New source quarters must update default selection');
assert.equal(hist.preferredQuarterlySource([{...cbre, period:'2026-Q4'},cushman]),
  'cbre-vietnam-market', 'Freshest quarter must outrank older completeness');
assert.equal(hist.preferredQuarterlySource([]), '', 'Empty inputs must stay empty');

const expanded = hist.expandQuarterHistory([
  {period:'2026-Q1', period_type:'quarter', new_supply:1200, absorption_rate:.25},
  cushman,
]);
const c = hist.coverageSummary(expanded);
assert.equal(c.supplyPeriods, 1);
assert.equal(c.lowerBoundSupplyPeriods, 1);
assert.equal(c.absorptionPeriods, 2);
assert.equal(c.salesPeriods, 0, 'Absorption must not be called completed sales');

let lastConfig = null;
class TestChart { constructor(canvas, config) { this.config=config; lastConfig=config; } destroy() {} }
const chartContext = {
  window: { Formatters: {compact: x => String(x)} },
  document: { getElementById: () => ({}) },
  Chart: TestChart, Map, Number
};
vm.runInNewContext(fs.readFileSync('assets/js/charts.js', 'utf8'),chartContext);
chartContext.window.ChartTools.renderSupplySales('supply',[
  {period:'2026-Q1',new_supply:1200,sales_units:300,absorption_rate:.25},
  {...cushman,sales_units:null}
]);
const series = lastConfig.data.datasets;
const lower = series.find(x => x.marketValueKind === 'lower-bound');
const absorption = series.find(x => x.marketValueKind === 'absorption');
assert.ok(lower);
assert.ok(absorption);
assert.equal(lower.data[0], null);
assert.equal(lower.data[1], 1300);
assert.equal(absorption.data[1], .31);
assert.equal(absorption.yAxisID, 'y1');
assert.equal(series.find(x=>x.marketValueKind==='supply').data[1], null,
  'Source lower bound must never become exact new_supply');
assert.equal(series.find(x=>x.marketValueKind==='sales').data[1], null,
  'Missing transactions must remain missing');
assert.ok(lastConfig.options.plugins.tooltip.callbacks.label({parsed:{y:1300},dataset:lower}).includes('> 1300'));
assert.ok(lastConfig.options.plugins.tooltip.callbacks.label({parsed:{y:.31},dataset:absorption}).includes('31.0%'));

const market = fs.readFileSync('assets/js/market.js','utf8');
assert.ok(market.includes('MarketHistorySeries?.preferredQuarterlySource?.(rows)'));
assert.ok(market.includes('coverage.absorptionPeriods'));
assert.ok(market.includes('coverage.lowerBoundSupplyPeriods'));
assert.ok(!market.includes("if (ids.includes('cbre-vietnam-market')) return 'cbre-vietnam-market'"));
assert.ok(market.includes("const rows = state.source ? allRows.filter(item => item.source_id === state.source) : allRows"),
 'Chart must still filter source rather than blend publisher data');

console.log('PASS 4I: latest period source choice, verified lower-bound and absorption visuals, source isolation and missingness');
