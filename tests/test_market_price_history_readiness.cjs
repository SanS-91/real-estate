const assert = require('node:assert/strict');
const fs=require('node:fs');
const model=require('../assets/js/market-price-history-readiness.js');
const now='2026-10-10';
const project={id:'test-project',name:'A test apartment',region_ids:['hcmc']};
const portal=(date,source='portal-one',asset='apartment')=>({
  project_id:project.id,source_id:source,asset_type:asset,market_layer:'listing-asking',
  coverage_status:'full',observation_date:date,
  asking_price_low_vnd_per_m2:50000000,asking_price_high_vnd_per_m2:60000000
});
const month=(period,subprojectId=null)=>({
  project_id:project.id,source_id:'onehousing-vn',asset_type:'apartment',
  metric_type:'popular-asking-price-per-sqm',period,value_vnd_per_m2:73000000,
  ...(subprojectId?{subproject_id:subprojectId,subproject_name:subprojectId}:{})
});
const base={
  projects:[project],listingObservations:[
    portal('2026-09-01'),portal('2026-09-15'),portal('2026-10-01')
  ],projectMonthly:[],subprojectMonthly:[],marketObservations:[],
  reverOffers:[],muabanOffers:[]
};

let result=model.build(base,now);
assert.equal(result.total_projects,1);
assert.equal(result.history_ready_projects,1);
assert.equal(result.projects[0].portal_max_snapshots,3);
assert.equal(result.projects[0].portal_series[0].span_days,30);
assert.equal(result.projects[0].monthly_max_periods,0);

result=model.build({...base,listingObservations:[
  portal('2026-09-01'),portal('2026-09-15','portal-two'),portal('2026-10-01','portal-two')
]},now);
assert.equal(result.history_ready_projects,0,'different publishers must never form one time series');
result=model.build({...base,listingObservations:[
  portal('2026-09-01'),portal('2026-09-15','portal-one','landed'),portal('2026-10-01')
]},now);
assert.equal(result.history_ready_projects,0,'apartment vs landed cannot be blended');
result=model.build({...base,listingObservations:[
  portal('2026-09-01'),portal('2026-09-01'),portal('2026-09-15'),portal('2026-10-01')
]},now);
assert.equal(result.projects[0].portal_max_snapshots,3,'duplicate dated snapshot does not increase history count');
result=model.build({...base,listingObservations:[portal('2026-09-01'),{
  ...portal('2026-10-01'),coverage_status:'partial',asking_price_high_vnd_per_m2:null
}]},now);
assert.equal(result.projects[0].portal_max_snapshots,1,'partial/no-price snapshots cannot imply observed trend');

result=model.build({...base,listingObservations:[],
  subprojectMonthly:[month('2026-07','tower-a'),month('2026-08','tower-a'),month('2026-09','tower-a')],
  projectMonthly:[month('2026-10')]},now);
assert.equal(result.history_ready_projects,1);
assert.equal(result.projects[0].parent_monthly_series,1);
assert.equal(result.projects[0].subproject_monthly_series,1);
assert.equal(result.projects[0].monthly_max_periods,3);
result=model.build({...base,listingObservations:[],
  subprojectMonthly:[month('2026-08','tower-a'),month('2026-09','tower-b'),month('2026-10','tower-c')]},now);
assert.equal(result.history_ready_projects,0,'three different subdivisions are NOT three months');
result=model.build({...base,listingObservations:[],
  projectMonthly:[month('2026-09'),month('2026-09'),month('2026-10')]},now);
assert.equal(result.projects[0].monthly_max_periods,2);
assert.equal(result.history_ready_projects,0,'repeated publisher month cannot create synthetic history');

const ad={project_id:project.id,source_id:'muaban-vn',listing_id:'987654321',
 review_status:'automated-two-hosted-checks',asset_type:'apartment',
 metric_type:'single-listing-asking-price-per-sqm',value_vnd_per_m2:50000000,
 verification_run_ids:['run-1','run-2'],
 source_listed_date:'2026-10-01',source_expiration_date:'2026-10-15'};
assert.equal(model.isVerifiedActiveOffer(ad,now),true);
assert.equal(model.isVerifiedActiveOffer({...ad,source_expiration_date:'2026-10-09'},now),false);
assert.equal(model.isVerifiedActiveOffer({...ad,verification_run_ids:['run-1','run-1']},now),false);
result=model.build({...base,listingObservations:[],muabanOffers:[ad,ad],
  marketObservations:[{scope_type:'project',project_id:project.id,period:'2025',
    sales_units:110,average_asp:null,absorption_rate:.5}]},now);
assert.equal(result.projects[0].current_verified_unit_ads,1,'duplicate listings should be deduped');
assert.equal(result.projects[0].disclosed_project_sales_observations,1);
assert.equal(result.projects[0].disclosed_project_asp_observations,0);
assert.equal(result.history_ready_projects,0,'one live unit ad is not a trend');

// Production corpus must be parsed dynamically, with no future-proof assumption
// that the current number of dated snapshots or projects remains fixed.
const read=n=>JSON.parse(fs.readFileSync('data/mock/market/'+n+'.json','utf8')).data;
const prod=model.build({projects:read('projects'),
 listingObservations:read('listing-observations'),
 projectMonthly:read('onehousing-project-monthly-history'),
 subprojectMonthly:read('alternative-subproject-monthly-history'),
 marketObservations:read('observations'),
 reverOffers:read('verified-unit-listings'),
 muabanOffers:read('verified-muaban-unit-listings')},now);
assert.equal(prod.total_projects,read('projects').length);
assert.equal(prod.projects.length,prod.total_projects);
assert(prod.history_ready_projects<=prod.total_projects);
assert(prod.monthly_priced_projects<=prod.total_projects);
assert(prod.projects.every(x=>typeof x.history_ready==='boolean'));
const site=fs.readFileSync('market.html','utf8');
const js=fs.readFileSync('assets/js/market.js','utf8');
assert(site.indexOf('market-price-history-readiness.js')<site.indexOf('assets/js/market.js'));
assert(js.includes('data-market-history-audit'));
assert(js.includes('priceHistoryReadinessHTML(filteredProjects)'));
assert(js.includes('state.priceLayer ==='));
assert(js.includes('Số tháng của các phân khu không được cộng'));
console.log('PASS: source-isolated price history readiness for',prod.total_projects,'current projects; eligible:',prod.history_ready_projects);
