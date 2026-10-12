'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const rows = JSON.parse(fs.readFileSync('data/processed/macro/historical-fx-gold-observations.json','utf8'));
const cpi = JSON.parse(fs.readFileSync('data/processed/macro/historical-observations.json','utf8'));
const live = JSON.parse(fs.readFileSync('data/processed/macro/observations.json','utf8'));
assert.strictEqual(rows.mode, 'corroborated-fx-gold-history-v1');
assert.strictEqual(rows.repository_publish, true);
assert.strictEqual(rows.frontend_publish, false);
assert.strictEqual(rows.record_count, 14);
const exactFX = {'2025-03-10':24754,'2025-04-10':24964,'2025-06-10':24985,
  '2025-09-30':25187,'2025-10-10':25128,'2026-09-10':25591};
const exactGold = {
  '2025-04-10':[100600000,103600000,'close','15:36'],
  '2025-06-10':[115700000,117700000,'morning','09:00'],
  '2025-10-10':[140200000,142200000,'close','16:30'],
  '2026-09-10':[143600000,146600000,'morning','09:20']
};
let seen = new Set(), fx = 0, gold = 0;
const liveKeys = new Set([...live.data, ...cpi.data].map(x=>x.indicator_id+':'+x.period_type+':'+x.period));
for(const row of rows.data){
  const key = row.indicator_id+':'+row.period_type+':'+row.period;
  assert(!seen.has(key), 'duplicate FX/gold history');
  assert(!liveKeys.has(key), 'history overlaps canonical production');
  seen.add(key);
  assert.equal(row.id,'verified-historical-'+row.indicator_id+'-'+row.period);
  assert.equal(row.period_type,'day');
  assert.equal(row.data_date,row.period);
  assert.equal(row.evidence_status,'corroborated');
  assert.equal(row.observation_status,'final');
  assert.equal(row.historical_observation,true);
  assert.equal(row.corroboration_sources.length,2);
  for(const source of row.corroboration_sources)assert.strictEqual(Number(source.observed_value),row.value);
  if(row.indicator_id==='usd-vnd-central-rate'){
    assert.equal(row.value,exactFX[row.period]);
    assert.equal(row.unit,'vnd-per-usd');
    assert.equal(row.quote_session,'daily-reference');fx++;
  }else{
    const v=exactGold[row.period];
    assert(v, 'unexpected date');
    assert.equal(row.value,row.indicator_id==='sjc-gold-buy'?v[0]:v[1]);
    assert.equal(row.quote_session,v[2]);
    assert.equal(row.quote_time_local,v[3]);
    assert.equal(row.product,'SJC gold bar 1 tael / 10 taels / 1kg');
    gold++;
  }
}
assert.equal(fx,6);assert.equal(gold,8);

// Evaluate the actual frontend validation function with a stubbed browser.
// No network or test-only replacement of the validator is used.
const src=fs.readFileSync('assets/js/macro.js','utf8');
const injection='window.__macroHistoryChecks = { validHistoricalMarketRows, integrateMacroObservations };\n';
const target="  document.addEventListener('DOMContentLoaded'";
assert(src.includes(target), 'UI bootstrap anchor moved');
const context={window:{},document:{addEventListener:()=>{}},URL,console};
vm.runInNewContext(src.replace(target,injection+target),context);
const validator=context.window.__macroHistoryChecks.validHistoricalMarketRows;
assert.equal(validator(rows,live.data,cpi.data).length,14,'frontend excludes valid history');
function rejectTamper(edit) {
  const mutated=JSON.parse(JSON.stringify(rows));
  edit(mutated.data[0]);
  assert.equal(validator(mutated,live.data,cpi.data).length,13);
}
rejectTamper(x=>{x.corroboration_sources[1].observed_value = -999;});
rejectTamper(x=>{x.corroboration_sources[1].url=x.corroboration_sources[0].url;});
rejectTamper(x=>{x.corroboration_sources[1].source_id='vna-vietnamplus';});
rejectTamper(x=>{x.evidence_status='reported';});
rejectTamper(x=>{x.period_type='month';});
assert.equal(validator({...rows,record_count:13},live.data,cpi.data).length,0,'whole payload mismatch must fail');
const blended=context.window.__macroHistoryChecks.integrateMacroObservations(
  {data:[]},live,{repository_publish:true,final_record_count:live.data.length},cpi,rows
);
assert.equal(blended.historicalCount,72);
assert.equal(blended.currentProductionCount,live.data.length,
  'new automatically collected production records must not break historical QA');
assert.equal(blended.productionRows.length,live.data.length+blended.historicalCount);
console.log('PASS independent FX/SJC history: 6 FX dates + 8 gold quotes, 2 publishers each, 72 historical plus '+live.data.length+' live; rejection tests');
