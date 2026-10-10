const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
global.window = global;
const code = fs.readFileSync(path.join(ROOT, 'assets/js/history-engine.js'), 'utf8');
vm.runInThisContext(code, { filename: 'history-engine.js' });

function load(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const macro = load('data/processed/macro/observations.json').data;
const legal = load('data/mock/legal/documents.json').data;
const infra = load('data/mock/infrastructure/projects.json').data;
const schedules = load('data/mock/infrastructure/schedules.json').data;
const events = load('data/mock/events/events.json').data;
const market = load('data/mock/market/observations.json').data;
const projects = load('data/mock/market/projects.json').data;
const phases = load('data/mock/market/project-phases.json').data;

// Live Macro production is append-only. Match the *actual* latest publisher
// periods; testing a fixed "latest = 2026-10-07" would fail when collection
// succeeds for Oct 9 or any subsequent date.
for (const id of ['usd-vnd-central-rate','sjc-gold-sell']) {
  const dated = macro.filter(x=>x.indicator_id===id && Number.isFinite(x.value))
    .sort((a,b)=>String(a.period).localeCompare(String(b.period)));
  assert(dated.length>=2, 'At least two source-backed Macro periods required');
  const actual = HistoryEngine.macroDelta(macro,id);
  assert(actual.current.period===dated.at(-1).period, id+' current must use latest source date');
  assert(actual.previous.period===dated.at(-2).period, id+' prior must use preceding actual date');
  assert(actual.delta===dated.at(-1).value-dated.at(-2).value, id+' delta must use source values');
}
const archivedFx = macro.filter(x=>x.indicator_id==='usd-vnd-central-rate' &&
  ['2026-10-05','2026-10-07'].includes(x.period));
assert(archivedFx.length===2, 'Retain original confirmed FX baseline periods');
const fxByDate = Object.fromEntries(archivedFx.map(x=>[x.period,x.value]));
assert(fxByDate['2026-10-07']-fxByDate['2026-10-05']===-5,
  'Original Oct 5-to-Oct 7 FX baseline remains auditable');

const rr3 = HistoryEngine.infrastructureScheduleChange('hcmc-ring-road-3', schedules);
assert(rr3 && rr3.from === '2026-Q2' && rr3.to === '2026-Q4', 'Ring Road 3 schedule history must preserve Q2 -> Q4 revision');

const landLaw = legal.find(x => x.id === 'law-31-2024-qh15-land');
const lawTimeline = HistoryEngine.legalTimeline(landLaw, legal);
assert(lawTimeline.some(x => x.type === 'amended-by' || x.type === 'amends'), 'Land Law timeline must expose amendment history');

const supply = HistoryEngine.marketDelta(market, {
  regionId: 'hcmc',
  segmentId: 'apartment',
  metric: 'new_supply',
  sourceId: 'cbre-vietnam-market'
});
assert(supply.current.period === '2026-Q2', 'Market current comparable quarter must be Q2/2026');
assert(supply.previous.period === '2026-Q1', 'Market prior comparable quarter must be Q1/2026');
assert(supply.current.new_supply === 850 && supply.previous.new_supply === 1642, 'Market supply history must use source-backed CBRE values');
assert(Math.abs(supply.pct - (-48.234)) < 0.01, 'Market supply delta must be about -48.2%');

const celesta = projects.find(x => x.id === 'celesta-gold');
const projectHistory = HistoryEngine.marketProjectHistory(celesta, market, phases);
assert(projectHistory.some(x => x.type === 'construction-start'), 'Celesta Gold history must include construction start');

const intelligence = HistoryEngine.buildIntelligence({
  macroRows: macro,
  legalDocuments: legal,
  infrastructureProjects: infra,
  schedules,
  events,
  marketObservations: market
});
const categories = new Set(intelligence.map(x => x.category));
for (const required of ['macro','legal','infrastructure','market']) {
  assert(categories.has(required), `Intelligence must include ${required}`);
}
assert(intelligence.every(x => x.date), 'Every intelligence item must be dated');

console.log('Phase 4.8/4.9 HistoryEngine tests PASS');
