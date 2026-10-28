const assert=require('node:assert/strict');
const fs=require('node:fs');
const read=p=>fs.readFileSync(p,'utf8');
const ui=read('assets/js/market.js');
const html=read('market.html');
const store=read('assets/js/data-store.js');
const css=read('assets/css/market-listing-evidence.css');
const benchmark=JSON.parse(read('data/processed/market/product-comparables.json'));
assert.equal(benchmark.schema_version,1);
assert.equal(benchmark.record_count,benchmark.data.length);
assert.equal(benchmark.verified_live_count,benchmark.data.filter(row=>row.is_verified_live_offer).length);
assert.equal(benchmark.official_payment_schedules,0);
assert.deepEqual(new Set(benchmark.watchlist_coverage.map(x=>x.project_id)),new Set([
  'izumi-city','aqua-city','springville','elyse-island',
  'kita-airport-city','nam-long-ii-central-lake'
]));
assert(ui.includes("state.view === 'benchmark'"));
assert(ui.includes("function renderProductBenchmark()"));
assert(ui.includes("function projectProductBenchmarkHTML(project)"));
assert(ui.includes("function benchmarkRecordTable(rows)"));
assert(ui.includes("renderProductBenchmark();"));
assert(ui.includes("row.is_verified_live_offer") && ui.includes("Đã đối soát tin và nguồn gần đây"), 'Current source-verified unit ads must be visibly distinguished from historic ads');
assert(ui.includes("Tin đã hết hạn"));
assert(ui.includes("Chưa xác minh còn hiệu lực"));
assert(ui.includes("Chưa xác minh"));
assert(ui.includes("Không nội suy"));
assert(ui.includes("Không suy ra giá/m² sàn xây dựng"));
assert(html.includes('data-view="benchmark" href="market.html?view=benchmark"'));
assert(html.includes('assets/js/market.js?v=PHASE8B-POLICY28'));
assert(store.includes('getProductComparables: () => loadDirectJSON'));
assert(css.includes('.benchmark-summary-grid'));
assert(css.includes('.product-benchmark-table'));
assert(css.includes('@media(max-width:580px)'));
for(const row of benchmark.data){
  assert.equal(row.fs_asp_eligible,false);
  assert.equal(row.discount_to_pv_vnd,null);
  assert.equal(row.handover_verified_date,null);
  assert(row.source_url.startsWith('https://nhadat.cafeland.vn/'));
  assert(row.price_unit_label_vi);
}
console.log('PASS: product benchmark UI, six watchlist records and no unverified promotion');
