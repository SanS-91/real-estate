const fs=require('fs');
const vm=require('vm');

const ranking=require('../assets/js/intelligence-ranking.js');
const rules=JSON.parse(fs.readFileSync('config/intelligence-ranking.json','utf8'));
const sources=JSON.parse(fs.readFileSync('data/mock/core/sources.json','utf8')).data;

const sample={
  id:'audit-sample',
  category:'infrastructure',
  type:'schedule-change',
  date:'2026-10-08',
  source_id:'gov-vietnam-infrastructure',
  entity_type:'infrastructure-project',
  entity_id:'hcmc-ring-road-3',
  pct:12
};
const ranked=ranking.rankOne(sample,{sources,rules,referenceDate:'2026-10-08'});
const parts=Object.values(ranked.ranking_components).reduce((a,b)=>a+Number(b),0);
if(ranked.attention_score!==parts) throw new Error('score must equal component sum when under max');
if(ranked.attention_score>rules.max_score) throw new Error('score exceeds max');
if(ranked.ranking_semantics!=='attention-priority-only') throw new Error('wrong semantics');
if(!ranked.ranking_evidence.evidence_date) throw new Error('missing evidence date');
if(ranked.ranking_components.freshness!==20) throw new Error('same-day freshness must get max freshness');

const missing=ranking.rankOne({
  id:'missing-evidence',
  category:'market',
  type:'default'
},{sources,rules,referenceDate:'2026-10-08'});
if(missing.ranking_components.source_quality!==0) throw new Error('missing source must score zero');
if(missing.ranking_components.freshness!==0) throw new Error('missing date must score zero');
if(missing.ranking_components.entity_relevance!==0) throw new Error('missing relation must score zero');
if(missing.ranking_components.change_magnitude!==0) throw new Error('missing magnitude must score zero');

const tied=ranking.rankAll([
  {...sample,id:'b',date:'2026-10-08'},
  {...sample,id:'a',date:'2026-10-08'}
],{sources,rules,referenceDate:'2026-10-08'});
if(tied[0].id!=='a' || tied[1].id!=='b') throw new Error('stable ID must break exact ties');

console.log('Phase 7.0A ranking runtime audit PASS');
