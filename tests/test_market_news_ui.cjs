const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const params = {};
const escapeHTML = text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const window = {
  Components: { escapeHTML },
  Resolver: { getEntities: (_type, ids) => (ids || []).map(id => ({name:id})) },
  App: {
    getQueryParam: key => params[key] || null,
    formatDate: value => value.slice(0,10),
    setQueryParam: (key, value) => { if (value == null) delete params[key]; else params[key]=value; },
    removeQueryParam: key => { delete params[key]; }
  },
  FilterEngine: { textMatch: (a, q, fields) => fields.map(k => a[k] || '').join(' ').toLowerCase().includes(q.toLowerCase()) }
};
vm.runInNewContext(fs.readFileSync('assets/js/market-news-ui.js','utf8'), {window, console});

const articles = Array.from({length:32}, (_, i) => ({
  id:'article-' + i,
  category:'market',
  title: 'Tin tức bất động sản số ' + i,
  summary: 'Nội dung tóm tắt dài về tin tức thị trường bất động sản tại Việt Nam và khu vực.',
  url:'https://vnexpress.net/news-' + i + '.html',
  source_id: i % 2 ? 'vnexpress-real-estate' : 'dantri-real-estate',
  published_at: new Date(Date.UTC(2026,9,9-i/2)).toISOString(),
  tags: i % 2 ? ['pricing'] : ['legal'],
  project_ids: i === 0 ? ['izumi-city'] : [],
  region_ids: ['hcmc'], developer_ids:[]
}));
const state = {q:'',region:'',developer:''};
const args = {articles,regions:[{id:'hcmc', name:'Hồ Chí Minh'}],developers:[{id:'nam-long',name:'Nam Long'}],state};
function cards(html) { return (html.match(/<article class="market-news-card /g) || []).length; }

let html = window.MarketNewsUI.render(args);
assert.equal(cards(html),16,'Only 16 records initially');
assert.match(html,/market-news-card--lead/,'Featured editorial hierarchy');
assert.match(html,/market-news-card--side/,'Two compact lead-side stories');
assert.match(html,/data-news-more/,'Progressively reveals additional records');
assert.match(html,/data-news-topic="pricing"/);
assert.match(html,/data-news-source/);
assert.match(html,/data-news-field="region"/);

params['news-source']='vnexpress-real-estate';
html=window.MarketNewsUI.render(args);
assert.equal(cards(html),16,'Source filter retains matching results');
assert.doesNotMatch(html,/market-news-card--lead/,'Filtered results use consistent compact grid');
assert.match(html,/<strong>16<\/strong> bài phù hợp/);
params['news-topic']='legal';
html=window.MarketNewsUI.render(args);
assert.equal(cards(html),0);
assert.match(html,/Không có tin phù hợp/);
delete params['news-source']; delete params['news-topic'];

state.q='unmatched query';
html=window.MarketNewsUI.render(args);
assert.equal(cards(html),0);
state.q='';

articles[0].title='<img src=x onerror=alert(1)> malicious';
html=window.MarketNewsUI.render(args);
assert.doesNotMatch(html,/<img src=x/);
assert.match(html,/&lt;img/);


/* All four modules use identical responsive News layout, with module-specific topics. */
const moduleStories = [
  {id:'legal-rss',category:'legal',module_ids:['legal'],title:'Nghị định đất đai và quy hoạch nhà ở',
   summary:'Quy định mới về đất đai',url:'https://vnexpress.net/legal.html',source_id:'vnexpress-legal',
   published_at:'2026-10-10T07:00:00Z',tags:['legal'],region_ids:[],project_ids:[]},
  {id:'infra-rss',category:'infrastructure',module_ids:['infrastructure'],title:'Thi công đường Vành đai 3',
   summary:'Tiến độ đường Vành đai tại TPHCM',url:'https://tuoitre.vn/infrastructure.html',source_id:'tuoitre-current-affairs',
   published_at:'2026-10-10T07:00:00Z',tags:['infrastructure'],region_ids:[],project_ids:[]},
  {id:'macro-rss',category:'macro',module_ids:['macro'],title:'Giá vàng và lãi suất ngân hàng',
   summary:'Cập nhật giá vàng SJC',url:'https://dantri.com.vn/gold.html',source_id:'dantri-gold',
   published_at:'2026-10-10T07:00:00Z',tags:['macro'],region_ids:[],project_ids:[]}
];
window.DataStore = {
  isNewsFor: (article, module) => (article.module_ids || [article.category]).includes(module)
};
for (const [module, heading, topic] of [
  ['legal','Tin tức pháp lý','Đất đai'],
  ['infrastructure','Tin tức hạ tầng','Đường &amp; Vành đai'],
  ['macro','Tin tức vĩ mô','Giá vàng']
]) {
  const page = window.MarketNewsUI.render({module, articles:moduleStories, regions:[],developers:[],state:{q:'',region:'',developer:''}});
  assert.equal(cards(page),1, module + ' shows only its article');
  assert.match(page, /market-news-filters/, module + ' uses Market News filters');
  assert.match(page, /market-news-topics/, module + ' uses same topic chips');
  assert.match(page, /market-news-grid/, module + ' uses responsive article grid');
  assert.ok(page.includes(heading),module + ' correct headline');
  assert.ok(page.includes(topic),module + ' correct topic');
}

const css=fs.readFileSync('assets/css/market-news.css','utf8');
assert.match(css,/@media \(max-width: 640px\)/);
assert.match(css,/@media \(max-width: 1120px\)/);
assert.match(css,/\.market-news-grid/);
assert.match(css,/\.market-news-feature/);

const entry=fs.readFileSync('market.html','utf8');
assert.ok(entry.indexOf('market-news-ui.js') < entry.indexOf('assets/js/market.js'),'Module loaded before market controller');
assert.match(entry,/market-news.css/);
console.log('Market News responsive UI contract tests PASS');
