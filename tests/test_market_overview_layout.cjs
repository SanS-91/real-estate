'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=file=>fs.readFileSync(path.join(root,file),'utf8');
const code=read('assets/js/market.js');
const start=code.indexOf('  function marketOverviewProjectHighlightsHTML() {');
const end=code.indexOf('  function relatedInfrastructureForProject(',start);
assert.ok(start>=0&&end>start,'Overview renderer or support functions missing');
const fn=code.slice(start,end);
const count=(s,needle)=>s.split(needle).length-1;
const today='2026-11-03T08:00:00+07:00';
const projectIds=['izumi-city','aqua-city','waterpoint','the-global-city'];
const projects=projectIds.map((id,i)=>({id,name:['Izumi City','Aqua City','Waterpoint','The Global City'][i]}));
function fixture({hasPrices=true,hasSupply=true,priceLayer='listing'}={}) {
  const calls=[];
  let html='';
  const data={
    projects,
    listingObservations:hasPrices?[{status:'reviewed',observation_date:'2026-10-09'}]:[],
    observations:hasSupply?[{average_asp:98000000,source_id:'source-one',source_date:'2026-08-12',period:'2026-Q2'}]:[],
    researchBriefs:[{period:'2026-Q3',period_type:'quarter',
      region_ids:['hcmc'],segment_ids:['apartment'],
      data_basis:'press-attributed-secondary-confirmation-only',
      source_date:'2026-10-17',
      source_url:'https://publisher.example/savills-q3',
      title:'Savills Q3 research with source qualification'}],
    marketDailyPulse:{article_index:[{
      project_id:'izumi-city',published_at:today,
      url:'https://publisher.example/izumi',title:'Izumi news'
    }]}
  };
  const state={priceLayer};
  const params=[
    'data','state','hcmcSeries','listingRangeChartData','priceSeries',
    'summaryMetrics','Components','marketPulseHTML','marketResearchBriefsHTML',
    'marketCoverageNoteHTML','priceFreshnessNote','priceLayerControls',
    'sourceRef','setView','requestAnimationFrame','ChartTools',
    'App','regionNames','developerName','projectActivityDate','esc','Formatters'
  ];
  const fixtures=[
    data,state,
    ()=>hasSupply?[{period:'2026-Q2',source_id:'source-one',source_date:'2026-08-12'}]:[],
    ()=>hasPrices?{labels:['Izumi City'],lowValues:[50000000],highValues:[60000000]}:{labels:[],lowValues:[],highValues:[]},
    ()=>hasPrices?[{label:'Elysian',values:[{period:'2026-Q2',value:70000000}]}]:[],
    ()=>[
      {label:'Giá tham chiếu',value:'6/18'},
      {label:'Kỳ nguồn cung',value:'2026-Q2'},
      {label:'Dự án theo dõi',value:'18'},
      {label:'Tin có nguồn',value:'42'}
    ],
    {compactMetric:item=>'<div class="compact-metric">'+item.label+': '+item.value+'</div>'},
    max=>'<section class="section market-pulse" data-news-max="'+max+'">Market pulse</section>',
    ()=>'<section class="section market-research-briefs">Q3 research details</section>',
    ()=>'<div class="market-coverage-note">Monitoring details</div>',
    ()=>'<p class="market-data-freshness">09/10/2026 · lịch sử</p>',
    ()=>'<div class="segmented-control">Price layers</div>',
    ()=>'<span class="source-ref">Nguồn có ngày</span>',
    markup=>{html=markup},
    callback=>callback(),
    {renderSupplySales:()=>calls.push('supply'),
      renderRangeSeries:()=>calls.push('asking'),
      renderPriceTrend:()=>calls.push('official-price')},
    {formatDate:date=>String(date).slice(0,10)},
    ()=> 'Đồng Nai',
    ()=> 'Nam Long',
    id=>id==='izumi-city'?today:null,
    x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
    {aspVndPerSqm:()=>''}
  ];
  const render=new Function(...params,fn+'return renderOverview;')(...fixtures);
  render();
  return {html,calls};
}
let n=0;
function test(name,action){action();process.stdout.write('PASS '+name+'\n');n++}

test('business priority starts with metrics, pricing/supply, projects, then news and research',()=>{
  const {html}=fixture();
  const order=['market-overview-metrics','market-overview-primary','market-overview-projects',
               'market-pulse','market-overview-evidence'];
  const at=order.map(x=>html.indexOf(x));
  assert.ok(at.every(x=>x>=0));
  for(let i=1;i<at.length;i++)assert.ok(at[i]>at[i-1],order[i]+' is out of order');
  assert.ok(html.indexOf('market-overview-panel--pricing')<html.indexOf('market-overview-panel--supply'));
});
test('four compact project cards without unwieldy nine-column overview table',()=>{
  const {html}=fixture();
  assert.equal(count(html,'class="market-overview-project"'),4);
  assert.ok(html.includes('Izumi City')&&html.includes('Waterpoint'));
  assert.ok(!html.includes('data-table--market-projects'));
  assert.ok(html.includes('market.html?view=projects'));
});
test('Q3 brief is visible near supply chart but research detail stays expandable',()=>{
  const {html}=fixture();
  assert.ok(html.includes('Savills Q3 research'));
  assert.ok(html.includes('chưa nhập vào chuỗi thống kê chính'));
  assert.ok(html.includes('<details class="market-overview-evidence">'));
  assert.ok(html.includes('Q3 research details'));
  assert.ok(html.indexOf('Q3 research details')>html.indexOf('<details'));
});
test('charts render only when data exists, with source-date notes',()=>{
  const complete=fixture();
  assert.deepEqual(complete.calls,['supply','asking']);
  assert.ok(complete.html.includes('Giá chào đã rà soát'));
  assert.ok(complete.html.includes('không phải giá giao dịch'));
  const empty=fixture({hasPrices:false,hasSupply:false});
  assert.deepEqual(empty.calls,[]);
  assert.ok(empty.html.includes('Chưa có chuỗi giá phù hợp'));
  assert.ok(empty.html.includes('Chưa có chuỗi nguồn cung'));
});
test('official-price switch still works',()=>{
  const out=fixture({priceLayer:'official'});
  assert.deepEqual(out.calls,['supply','official-price']);
});
test('pulse has at most one item per topic, not two screens of headlines',()=>{
  const {html}=fixture();
  assert.ok(html.includes('data-news-max="1"'));
});
test('overview layout is responsive and the old banner is removed',()=>{
  const css=read('assets/css/market-news.css');
  const html=read('market.html');
  assert.ok(css.includes('.market-overview-primary{display:grid;grid-template-columns:repeat(2'));
  assert.ok(css.includes('.market-overview-project-grid{display:grid;grid-template-columns:repeat(4'));
  assert.ok(css.includes('@media(max-width:600px)'));
  assert.ok(html.startsWith('<!doctype html>'));
  assert.ok(!html.includes('<div class="demo-banner"'));
  assert.ok(html.includes('MARKET-OVERVIEW-PRIORITY-1103'));
});
test('no chart/source code is swapped into HTML or CSS',()=>{
  assert.ok(read('assets/js/market.js').startsWith('(() => {'));
  assert.ok(read('assets/css/main.css').startsWith(':root {'));
  assert.ok(read('assets/css/market-news.css').startsWith('/*'));
  assert.ok(read('market.html').includes('</html>'));
});
process.stdout.write('Market Overview priority QA: '+n+' tests passed\n');
