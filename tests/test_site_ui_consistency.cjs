const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const common = fs.readFileSync('assets/js/common.js','utf8');
const localization = fs.readFileSync('assets/js/localization-static.js','utf8');
const css = fs.readFileSync('assets/css/main.css','utf8');
const newsCss = fs.readFileSync('assets/css/market-news.css','utf8');
const newsJs = fs.readFileSync('assets/js/market-news-ui.js','utf8');
const root = ['index','research','market','legal','infrastructure','macro','maintenance'];

for (const name of root) {
  const html = fs.readFileSync(name+'.html','utf8');
  for(const asset of ['main.css','common.js','localization-static.js']) {
    const row=html.split('\n').find(line=>line.includes('assets/'+(asset.endsWith('.css')?'css/':'js/')+asset));
    assert.ok(row && row.includes('&ui=UI8'), name+' not cache-busted for '+asset);
  }
  assert.match(html, /<meta name="viewport" content="width=device-width, initial-scale=1">/);
}
assert.match(common, /key: 'maintenance', label: 'Maintenance', href: 'maintenance.html'/);
assert.match(common, /aria-controls="site-mobile-navigation" aria-expanded="false"/);
assert.match(common, /class="mobile-nav-panel"/);
assert.match(common, /setAttribute\('aria-expanded', String\(!!open\)\)/);
assert.match(common, /MutationObserver/);
assert.match(common, /maintenance.html#maintenance-rules-title/);
assert.ok(!common.includes('<a href="#">Methodology'));
assert.match(localization, /Maintenance · Trạng thái dữ liệu/);
assert.match(localization, /Quy tắc & nguồn dữ liệu/);
assert.match(localization, /'Research', 'Nghiên cứu'/);
assert.match(css, /@media \(max-width: 1199px\)/);
assert.match(css, /\.mobile-nav-panel\s*\{[\s\S]*?max-height: calc\(100dvh/);
assert.match(css, /\.tabs \{[\s\S]*?scroll-snap-type: x proximity;/);
assert.match(css, /-webkit-overflow-scrolling: touch/);
assert.match(newsJs, /function articleTopics\(/);
assert.match(newsJs, /market-news-card__topics/);
assert.match(newsJs, /data-topic="\$\{esc\(topic\)\}"/);
assert.match(newsCss, /market-news-card__topic\[data-topic="pricing"\]/);
assert.match(newsCss, /market-news-card__topic\[data-topic="legal"\]/);
assert.match(newsCss, /market-news-card__topic\[data-topic="research"\]/);
assert.match(newsCss, /market-news-card__topic\[data-topic="sales"\]/);

const params={};
const browser = {Components:{escapeHTML:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')},
 Resolver:{getEntities:()=>[]},
 App:{getQueryParam:k=>params[k]||null, formatDate:s=>s.slice(0,10),setQueryParam:(k,v)=>{if(!v)delete params[k];else params[k]=v;},removeQueryParam:k=>delete params[k]},
 FilterEngine:{textMatch:()=>true}};
vm.runInNewContext(newsJs, {window:browser,console});
const article={category:'market',title:'Giá căn hộ dự án',url:'https://example.org/article',
  source_id:'vnexpress-real-estate', published_at:'2026-10-09T03:00:00Z',
  summary:'Tin nhà ở',tags:['pricing','supply'],project_ids:['izumi-city'],developer_ids:[],region_ids:['hcmc']};
const args={articles:[article],regions:[],developers:[],state:{q:'',region:'',developer:''}};
let html=browser.MarketNewsUI.render(args);
assert.match(html, /data-topic="pricing"/);
assert.match(html, /market-news-card__topics/);
assert.match(html, /aria-label="Lọc tin: Giá bán"/);
assert.match(html, /market-news-card__topic/);
assert.ok((html.match(/class="market-news-card__topic"/g)||[]).length <= 2);
assert.ok(html.includes('data-news-topic="pricing"'));

const scriptContext = {
  window:{},
  document:{documentElement:{lang:'vi'},addEventListener(){}}
};
vm.runInNewContext(common, scriptContext);
const labels=scriptContext.window.App;
assert.equal(labels.newsKindLabel('analysis'),'Phân tích');
assert.equal(labels.newsKindLabel('news'),'Tin tức');
assert.equal(labels.newsKindLabel('official-update'),'Cập nhật chính thức');
assert.equal(labels.newsKindLabel('data-release'),'Công bố dữ liệu');
assert.equal(labels.newsViewCopy('macro').title,'Tin tức vĩ mô');
assert.ok(labels.newsViewCopy('legal').description.includes('văn bản gốc'));
scriptContext.document.documentElement.lang='en';
assert.equal(labels.newsKindLabel('official-update'),'Official update');
assert.equal(labels.newsViewCopy('infrastructure').title,'Infrastructure news');
for(const module of ['legal','infrastructure','macro']) {
  const js=fs.readFileSync('assets/js/'+module+'.js','utf8');
  const html=fs.readFileSync(module+'.html','utf8');
  assert.ok(js.includes("module: '"+module+"'"),module+' must route to its own news');
  assert.ok(js.includes('MarketNewsUI.render'),module+' must use shared topic/card layout');
  assert.ok(html.includes('assets/js/market-news-ui.js?v=NEWS-UNIFIED-20261010'),module+' must load the common News renderer');
  assert.ok(html.includes('assets/css/market-news.css?v=NEWS-UNIFIED-20261010'),module+' must load mobile-responsive News CSS');
}
assert.match(css,/\.article-row__meta \.news-kind-chip/);
assert.match(css,/\.news-kind-chip\[data-news-kind="official-update"\]/);
assert.match(css,/\.news-kind-chip\[data-news-kind="data-release"\]/);
console.log('PASS: shared News topic filter and responsive components across four modules');

console.log('PASS: 7-site shared navigation, VI/EN terminology, auto-swipe tabs and distinct news topic chips');
