const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ctx = { window: {}, Map, Set, Number };
vm.runInNewContext(fs.readFileSync('assets/js/market-subproject-trends.js','utf8'), ctx);
const m=ctx.window.MarketSubprojectTrends;
const base = { project_id:'vinhomes-grand-park', source_id:'onehousing-vn',
  source_record_id:'onehousing-vinhomes-grand-park-apartment-2026-10',
  series_key:'onehousing-parent-vinhomes-grand-park-apartment-popular-asking',
  metric_type:'popular-asking-price-per-sqm',
  review_status:'source-indexed-baseline',
  value_vnd_per_m2:54470000, period:'2026-10',
  source_url:'https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Vinhomes-Grand-Park.1012' };
const nov = {...base,period:'2026-11',value_vnd_per_m2:55470000,review_status:'automated-source-verified'};
const subproject = {...nov,subproject_name:'Lumière Boulevard',
   source_record_id:'onehousing-lumiere-boulevard-apartment-2026-09',
   series_key:'onehousing-lumiere-boulevard-apartment-popular-asking'};
assert.equal(m.verifiedParentGroups([base]).length,0,'one indexed baseline is not a chart');
const series=m.verifiedParentGroups([base,nov,subproject]);
assert.equal(series.length,1);
assert.equal(series[0].values.length,2);
assert.equal(series[0].values[0].period,'2026-10');
assert.equal(m.forParentRow(series,nov).series_key,base.series_key);
assert.equal(m.forParentRow(series,subproject),null);
assert.equal(m.verifiedParentGroups([base,nov,{...nov,review_status:'candidate-only'}]).length,1);
assert.equal(m.verifiedParentGroups([base,nov,{...nov,value_vnd_per_m2:99999999}]).length,0);
assert.equal(m.verifiedParentGroups([base,nov], 'izumi-city').length,0);
assert.equal(m.verifiedGroups([base,nov]).length,0,'parent price must not become a subproject price');
const market=fs.readFileSync('assets/js/market.js','utf8');
const store=fs.readFileSync('assets/js/data-store.js','utf8');
assert.ok(market.includes('data.oneHousingProjectHistory'));
assert.ok(market.includes('verifiedParentGroups'));
assert.ok(market.includes('forParentRow'));
assert.ok(store.includes('getOneHousingProjectHistory'));
assert.ok(market.includes('parentPublished.get(item.id) || item'),
  'Latest publisher month must replace its own reference, not create duplicates');
console.log('PASS: project monthly prices remain parent scoped and series display only 2+ released months');
