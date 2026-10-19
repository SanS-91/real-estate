const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');

const script = fs.readFileSync('assets/js/home.js', 'utf8');
const todayStart = script.indexOf('  function hasHomePhrase(');
const todayEnd = script.indexOf('  async function loadCanonicalHomeData()', todayStart);
assert(todayStart > 0 && todayEnd > todayStart);
const declarations = script.slice(todayStart, todayEnd);
const context = vm.createContext({ dateKey: text => String(text || '').slice(0, 10) });
vm.runInContext(declarations + '\nthis.TEST = {hasHomePhrase, newsRelevantForHome, newestHomeCandidates};', context);
const {hasHomePhrase, newsRelevantForHome, newestHomeCandidates} = context.TEST;

assert.equal(hasHomePhrase('5 bà nội trợ cùng trúng số độc đắc', 'sổ đỏ'), false);
assert.equal(hasHomePhrase('Cấp sổ đỏ cho người mua nhà', 'sổ đỏ'), true);
assert.equal(newsRelevantForHome({content_type:'publisher-rss',category:'legal',title:'5 bà nội trợ cùng trúng số độc đắc'}), false);
assert.equal(newsRelevantForHome({content_type:'publisher-rss',category:'legal',title:'Hồ sơ doanh nghiệp bắt tay tỷ phú làm thép'}), false);
assert.equal(newsRelevantForHome({content_type:'publisher-rss',category:'legal',title:'Lâm Đồng ban hành quy định mới về cấp phép xây dựng'}), true);
assert.equal(newsRelevantForHome({content_type:'publisher-rss',category:'market',title:'Phương án đường sắt vành đai phía Đông Hà Nội',source_id:'vnexpress-current-affairs',project_ids:[]}), false);
assert.equal(newsRelevantForHome({content_type:'publisher-rss',category:'market',title:'Bất động sản hưởng lợi từ cao tốc mới',source_id:'dantri-real-estate'}), true);
const ordered = newestHomeCandidates([
  {id:'old',date:'2026-10-13',attention_score:95},
  {id:'new',date:'2026-10-19',attention_score:20},
  {id:'newest-high',date:'2026-10-19',attention_score:50}
]).map(row => row.id);
assert.equal(ordered.join(','), 'newest-high,new,old');
assert(script.includes('newestHomeCandidates(source)'));
assert(script.includes('newsRelevantForHome(row)'));
assert(script.includes('DataStore.getNewsHealth()'));
console.log('PASS homepage freshness, relevance and RSS status regression checks');
