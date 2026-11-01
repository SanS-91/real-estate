const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const params={};
const escapeHTML=text=>String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const window={
  Components:{escapeHTML},
  Resolver:{getEntities:()=>[]},
  App:{getQueryParam:key=>params[key]||null,formatDate:date=>String(date).slice(0,10),setQueryParam:(k,v)=>{params[k]=v},removeQueryParam:k=>{delete params[k]}},
  FilterEngine:{textMatch:()=>true}
};
window.HomeEditorial=require('../assets/js/home-editorial.js');
window.DataStore={isNewsFor:(row,module)=>(row.module_ids||[row.category]).includes(module)};
vm.runInNewContext(fs.readFileSync('assets/js/market-news-ui.js','utf8'),{window,console});
const make=(id,title,category,summary,at='2026-10-30T10:00:00Z')=>({
  id,title,summary,category,module_ids:[category],url:'https://example.com/'+id,
  content_type:'publisher-rss',published_at:at,source_id:'vnexpress-economy',tags:[],
  region_ids:[],project_ids:[],developer_ids:[]
});
const good=make('interest','Ngân hàng điều chỉnh lãi suất cho vay','macro','Tổng hợp giá vàng và tỷ giá ngày hôm qua');
const bad=make('future','CPI tháng 10 tăng so cùng kỳ','macro','', '2099-10-30T10:00:00Z');
const undated=make('undated','Ngân hàng điều chỉnh tỷ giá','macro','', '');
let html=window.MarketNewsUI.render({module:'macro',articles:[good,bad,undated],state:{q:'',region:'',developer:''}});
assert(html.includes('https://example.com/interest'));
assert(!html.includes('https://example.com/future'));
assert(!html.includes('https://example.com/undated'));
params['news-topic']='gold';
html=window.MarketNewsUI.render({module:'macro',articles:[good],state:{q:'',region:'',developer:''}});
assert(!html.includes('https://example.com/interest'),'Gold in teaser must not relabel a rates headline');
params['news-topic']='rates';
html=window.MarketNewsUI.render({module:'macro',articles:[good],state:{q:'',region:'',developer:''}});
assert(html.includes('https://example.com/interest'));
delete params['news-topic'];
console.log('PASS News four-tab: valid publication dates and headline-based subtopic filtering');
