'use strict';
/**
 * Browser-like smoke test of the REAL Market overview renderer with actual
 * repository market JSON. Guards against deleted helpers, bad schemas and
 * runtime crashes hidden by the generic "Unable to load" catch.
 *
 * Run: node tests/test_market_overview_runtime.cjs
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const json=p=>JSON.parse(read(p));
const view={innerHTML:'',querySelectorAll:()=>[]};
const calls=[];
const document={
  addEventListener(){},
  querySelector(selector){return selector==='[data-market-view]'?view:null},
  documentElement:{lang:'vi'}
};
const app={
  formatDate:raw=>{
    const d=new Date(raw);
    return Number.isNaN(d.getTime())?'—':d.toISOString().slice(0,10);
  },
  getQueryParam:()=>null
};
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;')
  .replaceAll('>','&gt;').replaceAll('"','&quot;');
const projects=json('data/mock/market/projects.json').data;
const regions=json('data/mock/core/regions.json').data;
const developers=json('data/mock/core/developers.json').data;
const entity=(type,id)=>({region:regions,developer:developers,project:projects}[type]||[])
  .find(x=>x.id===id);
const Resolver={
  getEntity:entity,
  getEntities:(type,ids)=>(ids||[]).map(id=>entity(type,id)).filter(Boolean),
  getLabel:(type,id)=>entity(type,id)?.name||id
};
const ctx={
  document,App:app,Resolver,console,Date,Intl,URL,Map,Set,
  requestAnimationFrame:callback=>callback(),
  ChartTools:{
    destroy:()=>{},
    renderSupplySales:(id,rows)=>calls.push({type:'supply',id,rows:rows.length}),
    renderRangeSeries:(id,series)=>calls.push({type:'range',id,rows:series.labels.length}),
    renderPriceTrend:(id,series)=>calls.push({type:'price',id,rows:series.length})
  },
  Components:{
    escapeHTML:esc,
    compactMetric:row=>'<div class="compact-metric">'+esc(row.label)+': '+esc(row.value)+'</div>',
    statusBadge:status=>'<span>'+esc(status)+'</span>',
    stateBox:msg=>'<p>'+esc(msg)+'</p>'
  },
  Formatters:{
    compact:n=>String(n??'—'),
    areaSqm:n=>String(n??'—'),
    aspVndPerSqm:n=>n==null?'—':String(n),
    number:n=>String(n??'—'),
    percentDecimal:n=>n==null?'—':String(Math.round(n*100))+'%',
    unitValue:n=>String(n??'—')
  },
  DataStore:{
    isNewsFor:(row,category)=>[row.category,...(row.module_ids||[]),...(row.tags||[])].includes(category)
  },
  Provenance:{sourceButton:(source)=>'<span class="source-ref">'+esc(source||'—')+'</span>'}
};
ctx.window=ctx;
vm.createContext(ctx);
vm.runInContext(read('assets/js/home-editorial.js'),ctx,{filename:'home-editorial.js'});
vm.runInContext(read('assets/js/market-history-series.js'),ctx,{filename:'market-history-series.js'});
assert.equal(typeof ctx.MarketHistorySeries.preferredQuarterlySource,'function');
const marketCode=read('assets/js/market.js');
const marker="  document.addEventListener('DOMContentLoaded', () => {";
assert.ok(marketCode.includes(marker),'No Market initialization marker');
const injected=marketCode.replace(marker,
  "  window.__smoke=(payload,layer)=>{data={...data,...payload};state.priceLayer=layer;renderOverview();};\n"+marker);
vm.runInContext(injected,ctx,{filename:'market.js'});
const payload={
  projects,regions,developers,
  phases:json('data/mock/market/project-phases.json').data,
  observations:json('data/mock/market/observations.json').data,
  listingObservations:json('data/mock/market/listing-observations.json').data,
  researchBriefs:json('data/mock/market/research-briefs.json').data,
  marketDailyPulse:json('data/processed/market/market-daily-pulse.json'),
  articles:json('data/mock/articles/articles.json').data
};
assert.equal(payload.projects.length,18,'Registry should be populated');
assert.ok(payload.observations.length,'Quarterly research should exist');
let count=0;
function test(label,fn){fn();count++;process.stdout.write('PASS '+label+'\n');}
test('real renderer builds Overview from complete current registry without ReferenceError',()=>{
  calls.length=0;view.innerHTML='';
  ctx.__smoke(payload,'listing');
  assert.ok(view.innerHTML.length>1000);
  assert.equal((view.innerHTML.match(/class="compact-metric"/g)||[]).length,4);
  assert.ok(view.innerHTML.includes('market-overview-primary'));
  assert.ok(view.innerHTML.includes('market-overview-evidence'));
  assert.ok(calls.some(x=>x.type==='supply'&&x.rows>0));
  assert.ok(calls.some(x=>x.type==='range'&&x.rows>0));
});
test('quarterly publisher selection chooses one data source only',()=>{
  const sources=new Set(payload.observations.filter(x=>x.scope_type==='region-segment'
    &&x.period_type==='quarter'&&x.region_ids?.includes('hcmc')
    &&x.segment_ids?.includes('apartment')).map(x=>x.source_id));
  assert.ok(sources.size>1);
  assert.equal(typeof ctx.MarketHistorySeries.preferredQuarterlySource,'function');
  assert.ok(view.innerHTML.includes('2026-Q2'));
});
test('project names and latest sourced links render without exceptions',()=>{
  for(const name of ['Izumi City','Aqua City','Waterpoint','The Global City']){
    assert.ok(view.innerHTML.includes(name),name);
  }
  assert.equal((view.innerHTML.match(/class="market-overview-project"/g)||[]).length,4);
});
test('verified-price mode still renders and does not crash',()=>{
  calls.length=0;view.innerHTML='';
  ctx.__smoke(payload,'verified');
  assert.ok(view.innerHTML.includes('market-overview-panel--pricing'));
  assert.ok(calls.some(x=>x.type==='supply'));
});
test('missing noncritical fresh research index does not crash Overview',()=>{
  calls.length=0;view.innerHTML='';
  ctx.__smoke({...payload,marketDailyPulse:null,researchBriefs:[]},'listing');
  assert.ok(view.innerHTML.includes('market-overview-metrics'));
  assert.ok(view.innerHTML.includes('market-overview-project-grid'));
});
test('HTML and script references remain accessible and cache-busted',()=>{
  const html=read('market.html');
  assert.ok(html.startsWith('<!doctype html>'));
  assert.ok(html.includes('</html>'));
  assert.ok(html.includes('assets/js/market.js?v='));
  assert.ok(html.includes('assets/js/market-history-series.js?v='));
});
process.stdout.write('Market real-data browser smoke: '+count+' tests passed\n');
