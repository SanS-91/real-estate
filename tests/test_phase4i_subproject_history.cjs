const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = { window: {}, Number, Set, Map };
vm.runInNewContext(fs.readFileSync('assets/js/market-subproject-trends.js','utf8'), context);
const api = context.window.MarketSubprojectTrends;

const base = {
  project_id:'vinhomes-grand-park', source_id:'onehousing-vn',
  subproject_name:'Lumière Boulevard',
  series_key:'onehousing-lumiere-boulevard-apartment-popular-asking',
  metric_type:'popular-asking-price-per-sqm',
  value_vnd_per_m2:73400000, period:'2026-09', review_status:'source-indexed-baseline',
  source_url:'https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Lumiere-Boulevard.34'
};
const newMonth = { ...base, period:'2026-10', value_vnd_per_m2:73740000,
  review_status:'automated-source-verified' };
assert.equal(api.verifiedGroups([base],base.project_id).length, 0,
  'One month cannot produce a trend');
const series=api.verifiedGroups([newMonth,base],base.project_id);
assert.equal(series.length,1);
assert.equal(series[0].values.length,2);
assert.equal(series[0].values[0].period,'2026-09');
assert.equal(series[0].values[1].value,73740000);
assert.equal(api.forRow(series,newMonth).series_key,base.series_key);
assert.equal(api.forRow(series,{...newMonth,subproject_name:'Masteri Centre Point'}),null);
assert.equal(api.verifiedGroups([base,newMonth,{...base,series_key:'different'}]).length,1,
  'Another incomplete series must not be merged with Lumière');
assert.equal(api.verifiedGroups([base,newMonth,{...newMonth,value_vnd_per_m2:99999999}]).length,0,
  'Conflicting same month numbers must block the chart');
assert.equal(api.verifiedGroups([base,{...newMonth,review_status:'candidate-only'}]).length,0,
  'Unpublished candidates cannot create a live chart');
assert.equal(api.verifiedGroups([base,newMonth], 'another-project').length,0);

const market=fs.readFileSync('assets/js/market.js','utf8');
const page=fs.readFileSync('market.html','utf8');
assert.ok(market.includes('MarketSubprojectTrends?.verifiedGroups?.(data.oneHousingSubprojectHistory)'));
assert.ok(market.includes('trend.values.length') && market.includes('data-subproject-trend-toggle'));
assert.ok(market.includes('ChartTools.renderPriceTrend(canvas.id'));
assert.ok(page.indexOf('market-subproject-trends.js') < page.indexOf('assets/js/market.js'));
assert.ok(market.includes('if (!details.open) return'), 'Collapsed reference must not render a chart');
console.log('PASS 4I: monthly trends appear after second released source period, with no source mixing or candidates');
