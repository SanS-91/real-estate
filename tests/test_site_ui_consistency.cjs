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
  for(const asset of ['main.css?v=UI8','common.js?v=UI8','localization-static.js?v=UI8']) {
    assert.ok(html.includes(asset), name+' not cache-busted for '+asset);
  }
  assert.match(html, /<meta name="viewport" content="width=device-width, initial-scale=1">/);
}
assert.match(common, /key: 'maintenance', label: 'Data Status', href: 'maintenance.html'/);
assert.match(common, /aria-controls="site-mobile-navigation" aria-expanded="false"/);
assert.match(common, /class="mobile-nav-panel"/);
assert.match(common, /setAttribute\('aria-expanded', String\(!!open\)\)/);
assert.match(common, /MutationObserver/);
assert.match(common, /maintenance.html#maintenance-rules-title/);
assert.ok(!common.includes('<a href="#">Methodology'));
assert.match(localization, /Trạng thái dữ liệu/);
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
console.log('PASS: 7-site shared navigation, VI/EN terminology, auto-swipe tabs and distinct news topic chips');
