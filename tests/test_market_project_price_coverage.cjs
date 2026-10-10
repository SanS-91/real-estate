const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const window = {};
vm.runInNewContext(fs.readFileSync('assets/js/market-project-coverage.js','utf8'), {window});
const load = filename=>JSON.parse(fs.readFileSync(filename,'utf8')).data;
const data={
 projects:load('data/mock/market/projects.json'),
 phases:load('data/mock/market/project-phases.json'),
 listingObservations:load('data/mock/market/listing-observations.json'),
 listingScopeEvidence:load('data/mock/market/listing-scope-evidence.json'),
 oneHousingProjectHistory:load('data/mock/market/onehousing-project-monthly-history.json'),
 observations:load('data/mock/market/observations.json')
};
const c=window.MarketProjectCoverage.build(data);
assert.equal(c.count,13);
assert.equal(c.aggregate,8,'Only 8 fully scoped publisher project ranges');
assert.equal(c.scoped,4,'Category-only evidence must stay separate');
assert.equal(c.popular,1,'OneHousing single-project monthly popular rate is NOT project aggregate');
assert.equal(c.noPrice,0,'Every project has at least one differently qualified price reference');
assert.equal(c.asp,0,'No fabricated project transaction ASP');
assert.equal(c.byId['izumi-city'].tier,'scoped-asking');
assert.equal(c.byId['izumi-city'].product,'landed');
assert.equal(c.byId['izumi-city'].row.asking_price_low_vnd_per_m2,54_500_000);
assert.equal(c.byId['the-9-stellars'].product,'apartment');
assert.equal(c.byId['the-9-stellars'].row.asking_price_high_vnd_per_m2,116_700_000);
assert.equal(c.byId['celesta-gold'].product,'indicative');
assert.equal(c.byId['lumiere-riverside'].tier,'monthly-popular');
assert.equal(c.byId['lumiere-riverside'].row.value_vnd_per_m2,178_170_000);
assert.equal(c.byId['vinhomes-grand-park'].tier,'aggregate-asking');
assert.equal(data.phases.length,11,'Three source-verified components added to original registry');
for (const row of c.records) {
 if(row.tier==='no-price') assert.equal(row.row,null);
 if(row.tier==='scoped-asking') assert.ok(row.row.price_scope);
}
const market=fs.readFileSync('assets/js/market.js','utf8');
const html=fs.readFileSync('market.html','utf8');
assert.ok(html.includes('market-project-coverage.js?v=MARKET-4P1'));
assert.ok(market.includes('projectCoverageStatusHTML(filteredProjects, true)'));
assert.ok(market.includes('projectPriceCell(coverage?.byId[project.id],listing)'));
assert.ok(market.includes('label:priceCoverageLabel'));
const rever=JSON.parse(fs.readFileSync('config/market-rever-listing-targets.json','utf8'));
assert.ok(rever.targets.some(x=>x.project_id==='lumiere-riverside' && x.url==='https://rever.vn/s/masterise-lumiere-riverside/mua/can-ho'));
console.log('PASS: 13 projects, 11 phases, 8 full/4 scoped/1 modal price tiers, 0 fabricated ASP, expanded publisher listing monitoring');
