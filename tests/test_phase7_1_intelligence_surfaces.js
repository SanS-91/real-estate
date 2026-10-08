const path=require('path');
const ROOT=path.resolve(__dirname,'..');
global.IntelligenceRanking=require(path.join(ROOT,'assets/js/intelligence-ranking.js'));
const Surfaces=require(path.join(ROOT,'assets/js/intelligence-surfaces.js'));

const rows=[
  {id:'m1',category:'market',date:'2026-10-08',attention_score:90},
  {id:'m2',category:'market',date:'2026-10-07',attention_score:80},
  {id:'m3',category:'market',date:'2026-10-06',attention_score:70},
  {id:'l1',category:'legal',date:'2026-10-08',attention_score:88},
  {id:'i1',category:'infrastructure',date:'2026-10-04',attention_score:85},
  {id:'x1',category:'macro',date:'2026-09-20',attention_score:75}
];

const today=Surfaces.today(rows,'2026-10-08');
if(today.map(x=>x.id).join(',')!=='m1,l1') throw new Error('today selection wrong');

const week=Surfaces.thisWeek(rows,{referenceDate:'2026-10-08',limit:6,maxPerCategory:2});
if(week.some(x=>x.id==='m3')) throw new Error('category diversity cap failed');
if(!week.some(x=>x.id==='i1')) throw new Error('weekly infrastructure missing');

const top=Surfaces.topDevelopments(rows,{referenceDate:'2026-10-08',days:30,limit:5,maxPerCategory:2});
if(top.length!==5) throw new Error('top developments length wrong');
if(top.filter(x=>x.category==='market').length!==2) throw new Error('top developments category cap wrong');

const per=Surfaces.topPerCategory(rows,['market','legal','infrastructure','macro']);
if(per.map(x=>x.id).join(',')!=='m1,l1,i1,x1') throw new Error('top per category wrong');

console.log('Phase 7.1 intelligence surface selectors PASS');
