/* Market pricing readability contract: dynamic source denominators + mobile-safe chart. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const projects=JSON.parse(fs.readFileSync('data/mock/market/projects.json','utf8')).data;
const coverage=JSON.parse(fs.readFileSync('data/state/listing-source-coverage.json','utf8'));
assert.ok(coverage.projects_tracked <= projects.length, 'Portal coverage is a source subset');
assert.equal(coverage.projects_tracked,12, 'Portal baseline subset stays 12, not fabricated to 13');
assert.equal(projects.length,13, 'New project registry stays separate');
const market=fs.readFileSync('assets/js/market.js','utf8');
assert.ok(market.includes('C\u00f3 kho\u1ea3ng gi\u00e1 t\u1ed5ng h\u1ee3p tr\u00ean Batdongsan'));
assert.ok(market.includes('${esc(data.projects.length)} d\u1ef1 \u00e1n to\u00e0n danh m\u1ee5c'));
assert.ok(market.includes('DataStore.getReverVerifiedUnitListings()'),
  'Do not break automated incoming individual listing facts');
assert.ok(market.includes('Ngày snapshot là ngày lưu số liệu nguồn'));
assert.ok(market.includes('Benchmark toàn thị trường'));
assert.ok(market.includes('fullLabels: listingChart.fullLabels'));
assert.ok(market.includes('horizontal: true'));
assert.ok(market.includes('listingRows.length * 46 + 90'),
  'Height must scale with number of source projects');
assert.ok(market.includes('lowValues: listingChart.lowValues'));
assert.ok(market.includes('highValues: listingChart.highValues'));

let last;
const context={
 Map, window:{Formatters:{compact:v=>String(v/1e6)+' tr/m²'}},
 document:{getElementById:id=>({id})},
 Chart:class{constructor(_,config){this.config=config;last=config}destroy(){}}
};
vm.runInNewContext(fs.readFileSync('assets/js/charts.js','utf8'),context);
const chart=context.window.ChartTools;
const rows={labels:['Waterpoint','Vinhomes Grand Park'],
 fullLabels:['Waterpoint · Thấp tầng','Vinhomes Grand Park · Căn hộ'],
 lowValues:[38200000,43800000],highValues:[60200000,77000000],
 horizontal:true,yFormatter:v=>(v/1e6)+' tr/m²'};
chart.renderRangeSeries('test-price',rows);
assert.equal(last.type,'bar');
assert.equal(last.options.indexAxis,'y');
assert.equal(last.options.scales.y.ticks.autoSkip,false);
assert.equal(last.data.datasets[0].data[0][0],38200000);
assert.equal(last.data.datasets[0].data[1][1],77000000);
assert.equal(last.options.plugins.tooltip.callbacks.title([{dataIndex:1}]),'Vinhomes Grand Park · Căn hộ');
assert.ok(last.options.plugins.tooltip.callbacks.label({raw:[38200000,60200000]}).includes('60.2 tr/m²'));
chart.renderRangeSeries('overview-price',{...rows,horizontal:false});
assert.equal(last.options.indexAxis,'x','Existing overview still retains vertical category bars');
console.log('PASS: 13-project registry vs 12-portal baseline, readable horizontal source range and unblended unit facts');
