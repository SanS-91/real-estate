const fs=require('fs');
const path=require('path');
const ROOT=path.resolve(__dirname,'..');
const Ranking=require(path.join(ROOT,'assets/js/intelligence-ranking.js'));
const rules=JSON.parse(fs.readFileSync(path.join(ROOT,'config/intelligence-ranking.json'),'utf8'));
const sources=JSON.parse(fs.readFileSync(path.join(ROOT,'data/mock/core/sources.json'),'utf8')).data;

const rows=[
  {
    id:'legal-recent',category:'legal',type:'amends',date:'2026-10-08',
    entity_id:'decree-new',source_id:'gov-vietnam-legal-documents'
  },
  {
    id:'infra-schedule',category:'infrastructure',type:'schedule-change',date:'2026-10-07',
    entity_id:'hcmc-ring-road-3',source_id:'gov-vietnam-infrastructure',from:'2026-Q2',to:'2026-Q4'
  },
  {
    id:'market-delta',category:'market',type:'market-delta',date:'2026-08-12',
    entity_id:'hcmc-apartment-supply',source_id:'cbre-vietnam-market',pct:-48,
    current:{source_id:'cbre-vietnam-market',region_ids:['hcmc']}
  },
  {
    id:'demo-event',category:'macro',type:'rate-change',date:'2026-10-08',
    entity_id:'policy-refinancing-rate',source_id:'demo-central-bank',importance:5
  }
];

const ranked=Ranking.rankAll(rows,{sources,rules,referenceDate:'2026-10-08'});
if(ranked.some(x=>x.id==='demo-event')) throw new Error('demo source leaked into ranking');
if(ranked.length!==3) throw new Error('unexpected ranked count');
if(ranked[0].id!=='legal-recent' && ranked[0].id!=='infra-schedule') throw new Error('high-significance official change should rank first');
if(!ranked.every(x=>x.attention_score>=0 && x.attention_score<=100)) throw new Error('score out of range');
if(!ranked.every(x=>x.ranking_semantics==='attention-priority-only')) throw new Error('ranking semantics missing');

const legal=ranked.find(x=>x.id==='legal-recent');
if(legal.ranking_components.source_quality!==25) throw new Error('official source quality wrong');
if(legal.ranking_components.event_significance!==23) throw new Error('legal amendment significance wrong');
if(legal.ranking_components.entity_relevance<5) throw new Error('legal entity relevance missing');
if(legal.ranking_components.change_magnitude!==12) throw new Error('legal magnitude wrong');

const market=ranked.find(x=>x.id==='market-delta');
if(market.ranking_components.change_magnitude!==15) throw new Error('market magnitude band wrong');
if(market.ranking_evidence.source_priority!==3) throw new Error('research source priority wrong');

const old=Ranking.rankOne({
  id:'old-context',category:'market',type:'default',date:'2025-01-01',
  source_id:'cbre-vietnam-market',region_ids:['hcmc']
},{sources,rules,referenceDate:'2026-10-08'});
if(old.ranking_components.freshness!==0) throw new Error('old evidence freshness should be zero');

const tied=Ranking.rankAll([
 {id:'b',category:'market',type:'default',date:'2026-10-01',source_id:'cbre-vietnam-market',region_ids:['hcmc']},
 {id:'a',category:'market',type:'default',date:'2026-10-01',source_id:'cbre-vietnam-market',region_ids:['hcmc']}
],{sources,rules,referenceDate:'2026-10-08'});
if(tied.map(x=>x.id).join(',')!=='a,b') throw new Error('stable tie-break failed');

console.log('Phase 7.0 intelligence ranking engine tests PASS');
