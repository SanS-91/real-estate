const fs=require('fs');
const path=require('path');
const ROOT=path.resolve(__dirname,'..');
const IntelligenceContext=require(path.join(ROOT,'assets/js/intelligence-context.js'));

const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8')).data || [];
const data={
  projects:read('data/mock/market/projects.json'),
  regions:read('data/mock/core/regions.json'),
  developers:read('data/mock/core/developers.json'),
  infrastructure:read('data/mock/infrastructure/projects.json'),
  infrastructureSchedules:read('data/mock/infrastructure/schedules.json'),
  legal:read('data/mock/legal/documents.json'),
  articles:read('data/mock/articles/articles.json'),
  events:read('data/mock/events/events.json'),
  marketObservations:read('data/mock/market/observations.json'),
  listingObservations:read('data/mock/market/listing-observations.json'),
  macroRows:read('data/processed/macro/observations.json')
};

if(IntelligenceContext.periodEnd('2026-Q2')!=='2026-06-30') throw new Error('quarter-end contract');
if(IntelligenceContext.periodEnd('2026-02')!=='2026-02-28') throw new Error('month-end contract');
if(IntelligenceContext.periodEnd('2026')!=='2026-12-31') throw new Error('year-end contract');

const project=IntelligenceContext.contextFor(data,'project','mizuki-park');
if(!project) throw new Error('missing project context');
if(project.projectIds.join(',')!=='mizuki-park') throw new Error('project scope leaked');
if(!project.regionIds.includes('hcmc')) throw new Error('project region missing');
if(!project.developerIds.includes('nam-long')) throw new Error('project developer missing');
if(!project.legalTopicIds.includes('housing')) throw new Error('legal topic missing');
if(!project.infrastructureIds.includes('hcmc-ring-road-3')) throw new Error('infrastructure relation missing');
if(project.relation_semantics.legal!=='topic-relevance') throw new Error('legal semantics missing');
if(project.relation_semantics.macro!=='contextual-only') throw new Error('macro semantics missing');

const evidence=IntelligenceContext.query(data,{
  type:'project',id:'mizuki-park',
  from:'2026-09-01',to:'2026-10-08',
  includeMacroContext:false
});
if(!evidence) throw new Error('project query failed');
if(evidence.contextual.macroObservations.length!==0) throw new Error('macro must be opt-in');
if(evidence.direct.listingObservations.some(x=>x.project_id!=='mizuki-park')) throw new Error('listing relation leaked');
if(evidence.direct.infrastructure.some(x=>!project.infrastructureIds.includes(x.id))) throw new Error('infrastructure relation leaked');
if(evidence.contextual.legalDocuments.some(x=>!(x.topic_ids||[]).some(id=>project.legalTopicIds.includes(id)))) throw new Error('legal topic filter leaked');
if(evidence.direct.articles.some(x=>{
  const linked=(x.project_ids||[]).includes('mizuki-park') ||
    (x.developer_ids||[]).includes('nam-long') ||
    (x.region_ids||[]).includes('hcmc') ||
    (x.infrastructure_project_ids||[]).some(id=>project.infrastructureIds.includes(id));
  return !linked;
})) throw new Error('article relation leaked');

const region=IntelligenceContext.contextFor(data,'region','hcmc');
if(!region || region.projectIds.length<1) throw new Error('region project resolution failed');
if(!region.infrastructureIds.includes('hcmc-metro-line-1')) throw new Error('region infrastructure context failed');

const developer=IntelligenceContext.contextFor(data,'developer','nam-long');
if(!developer || !developer.projectIds.includes('mizuki-park') || !developer.projectIds.includes('waterpoint')) throw new Error('developer project resolution failed');
if(!developer.regionIds.includes('hcmc')) throw new Error('developer regions failed');

const bounded=IntelligenceContext.query(data,{type:'region',id:'hcmc',from:'2026-10-01',to:'2026-10-08'});
for(const row of bounded.direct.articles){
  const d=IntelligenceContext.evidenceDate(row,'article');
  if(d<'2026-10-01' || d>'2026-10-08') throw new Error('time window failed');
}

console.log('Phase 6.0 IntelligenceContext tests PASS');
