const fs=require('fs');
const path=require('path');
const ROOT=path.resolve(__dirname,'..');
const Pack=require(path.join(ROOT,'assets/js/analysis-context-pack.js'));
global.location={href:'https://example.local/research.html',origin:'https://example.local'};
const AI=require(path.join(ROOT,'assets/js/optional-ai-analysis.js'));

const ctx={
  subject:{id:'izumi-city',name:'Izumi City',summary:'Tracked project'},
  projectIds:['izumi-city'],regionIds:['dong-nai'],developerIds:['nam-long'],
  legalTopicIds:['land'],semantics:{legal:'topic-relevance',macro:'contextual-only'},
  marketObservations:[{
    id:'m1',period:'2026-Q2',average_asp:80000000,asp_unit:'vnd-per-m2',
    source_id:'cbre-vietnam-market',source_url:'https://source/market'
  }],
  listingObservations:[{
    id:'l1',observation_date:'2026-10-08',market_layer:'listing-asking',
    asking_price_low_vnd_per_m2:70000000,asking_price_high_vnd_per_m2:85000000,
    source_id:'batdongsan-com-vn',source_url:'https://source/listing'
  }],
  legalDocuments:[{
    id:'law1',document_number:'31/2024/QH15',title:'Luật Đất đai',
    topic_ids:['land'],primary_source_id:'gov-vietnam-legal-documents',
    official_url:'https://source/legal'
  }],
  infrastructure:[],infrastructureSchedules:[],articles:[],events:[],
  macroContext:[{
    id:'fx1',indicator_id:'usd-vnd-central-rate',period:'2026-10-08',
    value:26000,unit:'vnd-per-usd',source_id:'sbv',source_url:'https://source/macro'
  }]
};

const pack=Pack.buildContextPack([ctx],{type:'project',action:'ask-database',question:'What changed?'});
if(pack.subjects[0].id!=='izumi-city') throw new Error('subject missing');
if(pack.evidence[0].direct.verified_market.length!==1) throw new Error('verified market missing');
if(pack.evidence[0].direct.listing_asking.length!==1) throw new Error('listing layer missing');
if(pack.evidence[0].contextual.legal_documents.length!==1) throw new Error('legal context missing');
if(pack.constraints.legal_relevance_is_not_applicability!==true) throw new Error('legal safeguard missing');
if(pack.constraints.listing_asking_is_separate_from_verified_pricing!==true) throw new Error('price layer safeguard missing');

const prompt=Pack.buildPrompt(pack);
for(const phrase of [
  'Use only the supplied canonical evidence',
  'Legal evidence, relevance does not establish legal applicability',
  'Keep listing asking prices separate',
  'Do not infer missing values',
  'source IDs and source URLs'
]) if(!prompt.includes(phrase)) throw new Error('prompt safeguard missing: '+phrase);

const cfg=JSON.parse(fs.readFileSync(path.join(ROOT,'config/ai-analysis.json'),'utf8'));
if(AI.status(cfg).mode!=='off') throw new Error('AI must be off by default');
if(AI.canRunRemote(cfg)!==false) throw new Error('remote call must be disabled by default');
let unsafe=false;
try { AI.safeConfig({enabled:true,api_key:'secret'}); } catch (_) { unsafe=true; }
if(!unsafe) throw new Error('browser secret guard failed');
if(AI.canRunRemote({enabled:true,external_requests:true,endpoint:'https://evil.example/api',same_origin_only:true})!==false) throw new Error('cross-origin endpoint guard failed');

(async()=>{
  const result=await AI.run({config:cfg,pack,prompt});
  if(result.executed!==false) throw new Error('disabled adapter executed');
  if(!String(result.reason).includes('No network request')) throw new Error('disabled reason missing');
  console.log('Phase 7.2 optional AI analysis behavior PASS');
})().catch(err=>{ console.error(err); process.exit(1); });
