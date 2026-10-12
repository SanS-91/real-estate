'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const data=JSON.parse(fs.readFileSync('data/processed/macro/historical-policy-monthly-observations.json','utf8'));
const live=JSON.parse(fs.readFileSync('data/processed/macro/observations.json','utf8'));
const cpi=JSON.parse(fs.readFileSync('data/processed/macro/historical-observations.json','utf8'));
const fx=JSON.parse(fs.readFileSync('data/processed/macro/historical-fx-gold-observations.json','utf8'));
const mon=JSON.parse(fs.readFileSync('data/processed/macro/historical-monetary-observations.json','utf8'));
assert.equal(data.record_count,18);
assert.equal(data.mode,'official-sbv-policy-monthly-history-v1');
const table={
'2022-12':[6,4.5,7],
'2023-01':[6,4.5,7],
'2023-02':[6,4.5,7],
'2023-03':[6,3.5,6],
'2023-04':[5.5,3.5,6],
'2023-05':[5,3.5,5.5]
};
const ids=['policy-refinancing-rate','policy-rediscount-rate','policy-overnight-lending-rate'];
let seen=new Set();
for(const row of data.data){
  const key=[row.indicator_id,row.period_type,row.period].join('|');
  assert(!seen.has(key),'duplicate historical rate/month');seen.add(key);
  assert.equal(row.value,table[row.period][ids.indexOf(row.indicator_id)]);
  assert.equal(row.data_date,null);
  assert.equal(row.published_at,null);
  assert.equal(row.source_id,'sbv-vietnam-archive');
  assert.equal(row.historical_observation,true);
  assert.equal(row.snapshot_basis,'sbv-annual-report-appendix-1-monthly-level');
}
// Use the production frontend's actual validator, not a test-only approximation.
const src=fs.readFileSync('assets/js/macro.js','utf8');
const target="  document.addEventListener('DOMContentLoaded'";
assert(src.includes(target));
const c={window:{},document:{addEventListener:()=>{}},URL,console};
vm.runInNewContext(src.replace(target,'window.__policyQA={validOfficialPolicyMonthRows,integrateMacroObservations};\n'+target),c);
const api=c.window.__policyQA;
let originals=api.validOfficialPolicyMonthRows(data,live.data,[...cpi.data,...fx.data,...mon.data]);
assert.equal(originals.length,18);
const disallow = mutate => {
  let clone=JSON.parse(JSON.stringify(data));
  mutate(clone.data[0]);
  assert.equal(api.validOfficialPolicyMonthRows(clone,live.data,[]).length,17);
};
disallow(x=>{x.period_type='date'});
disallow(x=>{x.data_date='2023-01-01'});
disallow(x=>{x.source_url='https://example.com/unverified/'});
disallow(x=>{x.value='not-number'});
disallow(x=>{x.snapshot_basis='made-up'});
const integrated=api.integrateMacroObservations({data:[]},live,
    {repository_publish:true,final_record_count:live.data.length},cpi,fx,mon,data);
assert.equal(integrated.historicalCount,119);
assert.equal(integrated.currentProductionCount,live.data.length);
assert.equal(integrated.productionRows.length,live.data.length+119);
const policy=integrated.productionRows.filter(x=>ids.includes(x.indicator_id));
assert(policy.filter(x=>x._historical).length===18);
assert(policy.filter(x=>x.period_type==='date').length===3);
console.log('PASS 18 official SBV monthly policy-rate history snapshots plus separate live decision events; all sources and month-vs-date checked');
