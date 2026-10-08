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

const region=IntelligenceContext.query(data,{type:'region',id:'hcmc',includeMacroContext:true,macroIndicatorIds:['cpi-yoy','usd-vnd-central-rate']});
if(!region) throw new Error('region dossier query missing');
if(region.direct.projects.length<1) throw new Error('region projects missing');
if(region.relations.developerIds.length<1) throw new Error('region developers missing');
if(region.direct.infrastructure.length<1) throw new Error('region infrastructure missing');
if(region.contextual.legalDocuments.length<1) throw new Error('region legal context missing');
if(region.contextual.macroObservations.length<1) throw new Error('region macro context missing');
if(region.semantics.legal!=='topic-relevance') throw new Error('region legal semantics wrong');

const developer=IntelligenceContext.query(data,{type:'developer',id:'nam-long',includeMacroContext:true,macroIndicatorIds:['cpi-yoy']});
if(!developer) throw new Error('developer dossier query missing');
for(const pid of ['mizuki-park','waterpoint','akari-city','izumi-city']){
  if(!developer.relations.projectIds.includes(pid)) throw new Error('developer portfolio missing '+pid);
}
if(developer.relations.regionIds.length<2) throw new Error('developer footprint too shallow');
if(developer.direct.infrastructure.length<1) throw new Error('developer infrastructure missing');
if(developer.contextual.legalDocuments.length<1) throw new Error('developer legal context missing');
if(developer.contextual.macroObservations.length<1) throw new Error('developer macro context missing');

console.log('Phase 6.2 Region & Developer intelligence data tests PASS');
