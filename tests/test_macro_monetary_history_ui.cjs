'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const all = JSON.parse(fs.readFileSync('data/processed/macro/historical-monetary-observations.json', 'utf8'));
const live = JSON.parse(fs.readFileSync('data/processed/macro/observations.json','utf8'));
const cpi = JSON.parse(fs.readFileSync('data/processed/macro/historical-observations.json','utf8'));
const fx = JSON.parse(fs.readFileSync('data/processed/macro/historical-fx-gold-observations.json','utf8'));
const src = fs.readFileSync('assets/js/macro.js','utf8');
const target = "  document.addEventListener('DOMContentLoaded'";
assert(src.includes(target),'expected UI event bootstrap');
const exposed = [
 'validOfficialMonetaryRows',
 'validProductionRows',
 'integrateMacroObservations',
 'deltaInfo',
 'observationsFor'
].join(',');
const injectable = 'window.__macroMonetaryChecks = {'+exposed+'};\n';
const context = { window:{}, document:{addEventListener:()=>{}},URL,console };
vm.runInNewContext(src.replace(target,injectable+target),context);
const api=context.window.__macroMonetaryChecks;
const monetary=api.validOfficialMonetaryRows(all,live.data,[...cpi.data,...fx.data]);
assert.equal(monetary.length,33,'all 33 direct official rows must be accepted');
function rejects(mutator) {
  const changed=JSON.parse(JSON.stringify(all));
  mutator(changed.data[0]);
  assert.equal(api.validOfficialMonetaryRows(changed,live.data,[...cpi.data,...fx.data]).length,32);
}
rejects(x=>{x.source_id='unverified-website';});
rejects(x=>{x.period_type='day';});
rejects(x=>{x.evidence_status='reported';});
rejects(x=>{x.source_url='https://fake-sbv.example.com/rates.pdf';});
rejects(x=>{x.value='not-a-number';});
rejects(x=>{x.historical_observation=false;});
const mismatch={...all,record_count:all.record_count-1};
assert.equal(api.validOfficialMonetaryRows(mismatch,live.data,[]).length,0);
const integrated=api.integrateMacroObservations({data:[]},live,
  {repository_publish:true,final_record_count:live.data.length},cpi,fx,all);
assert.equal(integrated.currentProductionCount,live.data.length,
  'live canonical record growth must not fail historical regression');
assert.equal(integrated.historicalCount,105);
assert.equal(integrated.productionRows.length,live.data.length+integrated.historicalCount);
assert.equal(integrated.productionRows.filter(x=>x.indicator_id==='m2-growth-ytd').length,7);
const mayRanges=integrated.rows.filter(x=>x._range && x.period==='2025-05');
assert.equal(mayRanges.length,2, 'May 2025 source-verified rate ranges must be paired');
assert(mayRanges.every(x=>x.evidence_status==='verified'));
const ranges=integrated.rows.filter(x=>x._range && x.period==='2025-06');
assert.equal(ranges.length,2,'June 2025 must have two valid ranges');
assert(ranges.every(x=>x.evidence_status==='verified'),'original SBV primary verification must be retained');
assert.equal(integrated.rows.filter(x=>x.indicator_id==='m2-growth-yoy').length,0);
console.log('PASS Monetary integration: 21 NSO quarterly YTD + 12 direct SBV rate bounds; 105 historical + live official observations; no demo M2 YoY mixing');
