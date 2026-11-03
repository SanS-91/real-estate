'use strict';
// No dependencies; use the same editorial module and real Home source code
// that GitHub Pages loads. Run: node tests/test_home_latest_news.cjs
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const editorial=require(path.join(root,'assets/js/home-editorial.js'));
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const now=Date.parse('2026-11-03T03:47:00Z');
const reference='2026-11-03';
const row=(title,published_at,category='market',extra={})=>({
  id:'article-test-'+Math.random().toString(16).slice(2),
  title,published_at,category,module_ids:[category],
  url:'https://publisher.example/'+encodeURIComponent(title),
  content_type:'publisher-rss',source_id:'vnexpress-real-estate',...extra
});
let tests=0;
function check(name,fn){fn();tests++;process.stdout.write('PASS '+name+'\n');}

check('newer publisher date precedes older higher editorial score',()=>{
  const newest=row('Bàn giao phân khu thấp tầng Casa Villa thuộc Blanca City',
    '2026-11-03T01:00:00Z');
  const older=row('Dự án nhà ở xã hội công bố nguồn cung khu đô thị mới',
    '2026-11-01T01:00:00Z');
  const chosen=editorial.latestForHome([older,newest], 'market',reference,{now,max:2});
  assert.equal(chosen.length,2);
  assert.equal(chosen[0].article.title,newest.title);
});

check('publisher timestamps sort within a calendar day, not by date-only key',()=>{
  const a=row('Dự án khu đô thị ABC mở bán nhà phố mới','2026-11-03T00:01:00Z');
  const b=row('Dự án khu đô thị XYZ bàn giao biệt thự','2026-11-03T02:00:00Z');
  const latest=editorial.latestForHome([a,b],'market',reference,{now,max:2});
  assert.equal(latest[0].article.title,b.title);
});

check('legal near-duplicates do not occupy two headline slots',()=>{
  const l1=row('Bộ trưởng Trịnh Việt Hùng: Không lạm dụng thu hồi đất',
    '2026-10-29T05:32:17Z','legal');
  const l2=row('Bộ trưởng Trịnh Việt Hùng: Không lạm dụng việc thu hồi đất',
    '2026-10-29T05:03:41Z','legal');
  const l3=row('Đề xuất nguyên tắc bồi thường khi thu hồi đất',
    '2026-10-29T03:14:55Z','legal');
  const actual=editorial.latestForHome([l1,l2,l3],'legal',reference,{now,max:3});
  assert.equal(actual.length,2);
  assert.equal(actual[0].article.title,l1.title);
  assert.equal(actual[1].article.title,l3.title);
});

check('not all new gold-price stories can displace other Macro topics',()=>{
  const g1=row('Giá vàng hôm nay 3.11 tăng mạnh','2026-11-03T02:03:00Z','macro');
  const g2=row('Giá vàng SJC tăng thêm một triệu đồng','2026-11-03T02:00:00Z','macro');
  const fed=row('Fed dự báo điều chỉnh lãi suất vào tháng tới',
    '2026-11-03T01:00:00Z','macro');
  const chosen=editorial.latestForHome([g2,g1,fed],'macro',reference,{now,max:3});
  assert.equal(chosen.length,2);
  assert.equal(chosen[0].article.title,g1.title);
  assert.equal(chosen[1].article.title,fed.title);
});

check('use the last 7 publication days before extending to 30 days',()=>{
  const f=row('Bàn giao phân khu thấp tầng dự án khu đô thị','2026-11-02T14:00:00Z');
  const m=row('Nhà phố khu đô thị mở bán trong tuần','2026-11-01T14:00:00Z');
  const old=row('Căn hộ nhà ở xã hội mở bán theo quy hoạch mới','2026-10-18T10:00:00Z');
  const chosen=editorial.latestForHome([old,f,m],'market',reference,{now,max:3});
  assert.equal(chosen.length,3);
  assert.deepEqual(chosen.map(x=>x.article.title),[f.title,m.title,old.title]);
  assert.equal(chosen[2].age>=7,true);
});

check('future dates, undated links, non-https and demo sources are rejected',()=>{
  const valid=row('Dự án khu đô thị mới bàn giao biệt thự','2026-11-02T01:00:00Z');
  const future=row('Dự án khu đô thị mới mở bán biệt thự','2026-11-04T01:00:00Z');
  const undated=row('Nguồn cung căn hộ mới','not-a-date');
  const unsafe=row('Thị trường bất động sản tăng nguồn cung','2026-11-03T02:00:00Z',
    'market',{url:'javascript:alert(1)'});
  const demo=row('Dự án khu đô thị mở bán biệt thự','2026-11-03T02:01:00Z',
    'market',{source_id:'demo-source'});
  const chosen=editorial.latestForHome([valid,future,undated,unsafe,demo],
    'market',reference,{now});
  assert.deepEqual(chosen.map(x=>x.article.title),[valid.title]);
});

check('editorial verification still removes unrelated lifestyle content',()=>{
  const bad=row('5 mẹo vệ sinh nhà cửa cực đơn giản bạn ước biết sớm hơn',
    '2026-11-03T02:00:00Z','market');
  const good=row('Bàn giao phân khu thấp tầng Casa Villa thuộc Blanca City',
    '2026-11-03T01:00:00Z','market');
  const chosen=editorial.latestForHome([bad,good],'market',reference,{now});
  assert.deepEqual(chosen.map(x=>x.article.title),[good.title]);
});

check('cross-module legal articles qualify as legal on Home',()=>{
  const article=row('Đề xuất thu hồi đất phải có cơ chế bồi thường mới',
    '2026-11-02T05:30:00Z','market',{module_ids:['market','legal']});
  const results=editorial.latestForHome([article],'legal',reference,{now});
  assert.equal(results.length,1);
  const home=read('assets/js/home.js');
  assert.ok(home.includes('DataStore.isNewsFor(article,category)'));
  assert.ok(!home.slice(home.indexOf('  async function renderToday() {'),
    home.indexOf('  async function renderIndicators() {')).includes('DataStore.getHomeToday()'));
});

check('Home Latest is independent from other API loads and shows source-sync time',()=>{
  const home=read('assets/js/home.js');
  const render=home.slice(home.indexOf('  async function renderToday() {'),
    home.indexOf('  async function renderIndicators() {'));
  assert.ok(render.includes('DataStore.getArticles()'));
  assert.ok(!render.includes('loadCanonicalHomeData()'));
  assert.ok(render.includes("DataStore.getSources().catch"));
  assert.ok(render.includes("setText('[data-home-news-updated]'"));
  const html=read('index.html');
  assert.ok(html.startsWith('<!doctype html>'));
  assert.ok(html.includes('data-home-news-updated'));
  assert.ok(html.indexOf('home-editorial.js?')<html.indexOf('home.js?'));
  assert.ok(html.includes('HOME-RECENCY-1103'));
});

check('Home keeps original compact four-column desktop design',()=>{
  const css=read('assets/css/main.css');
  assert.ok(css.includes('.today-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }'));
  assert.ok(!css.startsWith('<!doctype html>'));
});

process.stdout.write('Home Latest: '+tests+' tests passed\n');
