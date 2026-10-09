const fs=require('fs'),assert=require('assert');
const common=fs.readFileSync('assets/js/common.js','utf8');
const loc=fs.readFileSync('assets/js/localization-static.js','utf8');
const news=fs.readFileSync('assets/css/market-news.css','utf8');
const css=fs.readFileSync('assets/css/main.css','utf8');
assert(common.includes("key: 'maintenance', label: 'Maintenance', href: 'maintenance.html'"));
assert(loc.includes("'Maintenance', 'Maintenance'"));
for(const topic of ['all','legal','infrastructure','macro'])assert(news.includes('data-topic="'+topic+'"'));
assert(news.includes('overflow-x: auto')||news.includes('overflow-x:auto'));
assert(css.includes('.section-body--table{max-width:100%;overflow-x:auto'));
console.log('PASS navigation, translation, mobile scroll containment and news taxonomy');
const maintenance=fs.readFileSync('maintenance.html','utf8');
for (const id of ['maintenance-operations-title','market-source-health-title','maintenance-check-title']) {
  assert(maintenance.includes('id="'+id+'"'));
  assert(loc.includes("'#"+id+"'"), 'Missing localization for '+id);
}
assert(loc.includes('07:45 ICT freshness · 08:05 ICT operations health'));
assert(loc.includes('Repository + Actions'));
assert(loc.includes('production collectors keep their own controlled gates'));
assert(loc.includes("research: {"));
console.log('PASS maintenance operations copy matches current page and research title');
