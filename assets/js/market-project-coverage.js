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
        x.coverage_status !== 'historical-segment-reference-not-current' &&
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
          scoped?.price_scope === 'landlot-only' ? 'landlot' :
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
  // Monitoring is a separate evidence layer: individual verified apartment
  // listings never become a representative project price or absorption metric.
  function monitoring(coverage, snapshot, now = Date.now()) {
    const records = coverage?.records || [];
    const sourceRows = Array.isArray(snapshot?.projects) ? snapshot.projects : null;
    if (!sourceRows) return { available:false, records:[], byId:{}, monitored:0, withCurrent:0 };
    const bySource = new Map(sourceRows.map(row => [row.project_id, row]));
    const checked = Date.parse(snapshot.generated_at || '');
    const age = now - checked;
    const freshness = Number.isFinite(checked) && age >= 0 && age <= 72 * 3600000
      ? 'recent' : 'stale';
    const joined = records.map(price => {
      const row = bySource.get(price.project_id);
      const monitors = Math.max(0, Number(row?.sources_monitored) || 0);
      const units = Math.max(0, Number(row?.current_verified_ads) || 0);
      return {
        project_id:price.project_id,
        sources_monitored:monitors,
        verified_ads:units,
        status:monitors === 0 ? 'not-monitored'
          : units > 0 ? 'verified-single-offers'
          : row?.status === 'source-qualified-awaiting-verification' ? 'awaiting-verification'
          : 'monitored-no-offers'
      };
    });
    return {
      available:true, freshness, generated_at:snapshot.generated_at || null,
      records:joined, byId:Object.fromEntries(joined.map(row => [row.project_id,row])),
      monitored:joined.filter(row => row.sources_monitored > 0).length,
      withCurrent:joined.filter(row => row.verified_ads > 0).length
    };
  }

  window.MarketProjectCoverage = { build, monitoring };
})();
