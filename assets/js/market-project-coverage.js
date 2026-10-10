/* Market project price coverage is derived from live production JSON, never estimated. */
(() => {
  'use strict';
  const priced = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
  const latest = (rows, field) => [...rows].sort((a,b) =>
    String(b[field] || '').localeCompare(String(a[field] || '')))[0] || null;
  function build(d) {
    const projects = d.projects || [];
    const listings = d.listingObservations || [];
    const scopes = d.listingScopeEvidence || [];
    const monthly = d.oneHousingProjectHistory || [];
    const phases = d.phases || [];
    const observations = d.observations || [];
    const records = projects.map(project => {
      const full = latest(listings.filter(x=>x.project_id===project.id &&
        x.coverage_status==='full' && priced(x.asking_price_low_vnd_per_m2) &&
        priced(x.asking_price_high_vnd_per_m2)), 'observation_date');
      const scoped = latest(scopes.filter(x=>x.project_id===project.id &&
        priced(x.asking_price_low_vnd_per_m2) &&
        priced(x.asking_price_high_vnd_per_m2)), 'review_date');
      const popular = latest(monthly.filter(x=>x.project_id===project.id &&
        x.source_id==='onehousing-vn' && !x.subproject_id && priced(x.value_vnd_per_m2) &&
        ['source-indexed-baseline','reviewed-release','automated-source-verified'].includes(x.review_status)), 'period');
      const asp = latest(observations.filter(x=>x.project_id===project.id &&
        priced(x.average_asp)), 'period');
      const phaseRows = phases.filter(x=>x.project_id===project.id);
      const tier = full ? 'aggregate-asking' : scoped ? 'scoped-asking' : popular ? 'monthly-popular' : 'no-price';
      const row = tier === 'aggregate-asking' ? full : tier === 'scoped-asking' ? scoped : tier === 'monthly-popular' ? popular : null;
      return {
        project_id:project.id,project_name:project.name, tier, row,
        full:!!full,scoped:!!scoped,popular:!!popular,asp:!!asp,
        asp_row:asp, phase_count:phaseRows.length,
        product:full?.asset_type || (scoped?.price_scope === 'landed-only' ? 'landed' :
          scoped?.price_scope === 'apartment-only' ? 'apartment' :
          scoped?.price_scope === 'publisher-faq-indicative' ? 'indicative' : popular?.asset_type || null),
        as_of:full?.source_data_as_of || full?.observation_date ||
          scoped?.review_date || popular?.period || null
      };
    });
    return {
      records,
      byId:Object.fromEntries(records.map(x=>[x.project_id,x])),
      count:projects.length,
      aggregate:records.filter(x=>x.full).length,
      scoped:records.filter(x=>!x.full && x.scoped).length,
      popular:records.filter(x=>!x.full && !x.scoped && x.popular).length,
      asp:records.filter(x=>x.asp).length,
      noPrice:records.filter(x=>x.tier==='no-price').length,
      withPhase:records.filter(x=>x.phase_count>0).length,
      needsReview:records.filter(x=>!x.full)
    };
  }
  window.MarketProjectCoverage = { build };
})();
