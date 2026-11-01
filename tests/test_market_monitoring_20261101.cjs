const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const window = {};
vm.runInNewContext(fs.readFileSync('assets/js/market-project-coverage.js','utf8'), {window});
const c = window.MarketProjectCoverage;
const price = {records:[
  {project_id:'a',tier:'aggregate-asking'},
  {project_id:'b',tier:'scoped-asking'},
  {project_id:'c',tier:'no-price'}
]};
const snapshot = {generated_at:'2026-11-01T00:00:00Z',projects:[
  {project_id:'a',sources_monitored:2,current_verified_ads:0,status:'monitored-no-current-verified-offer'},
  {project_id:'b',sources_monitored:1,current_verified_ads:3,status:'published-current-unit-offer'},
  {project_id:'c',sources_monitored:0,current_verified_ads:0,status:'no-verified-unit-source-target'}
]};
const m=c.monitoring(price,snapshot,Date.parse('2026-11-01T07:00:00Z'));
assert.equal(m.monitored,2);
assert.equal(m.withCurrent,1);
assert.equal(m.byId.b.verified_ads,3);
assert.equal(m.byId.c.status,'not-monitored');
assert.equal(m.byId.a.status,'monitored-no-offers');
assert.equal(m.freshness,'recent');
assert.equal(c.monitoring(price,snapshot,Date.parse('2026-11-06T00:00:00Z')).freshness,'stale');
assert.equal(c.monitoring(price,null).available,false);
const live = JSON.parse(fs.readFileSync('data/state/market-active-listing-coverage.json','utf8'));
const p=JSON.parse(fs.readFileSync('data/mock/market/projects.json','utf8')).data;
const active=c.monitoring({records:p.map(item=>({project_id:item.id}))},live,Date.parse(live.generated_at));
assert.equal(active.monitored,live.projects_monitored);
assert.equal(active.withCurrent,live.projects_with_current_verified_unit_offers);
assert.equal(active.records.length,p.length);
const market=fs.readFileSync('assets/js/market.js','utf8');
assert(market.includes('MarketProjectCoverage?.monitoring?.'));
assert(market.includes('getActiveListingCoverage().catch'));
assert(market.includes('HomeEditorial.filterArchive(latestMarketNews'));
assert(market.includes('monitorLabels[watched.status]'));
console.log('PASS Market: separately derived monitoring, no fabricated price, stale snapshots marked, Overview screened');
