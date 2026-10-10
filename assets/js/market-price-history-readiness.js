/* Phase 6.3A — source-isolated historical evidence coverage.
 * Pure derivation from canonical records loaded by Market. No network calls,
 * interpolation, averaged publisher data or fabricated observations.
 */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.MarketPriceHistoryReadiness = api;
})(typeof window !== 'undefined' ? window : null, function() {
  'use strict';
  const MIN_OBSERVATIONS = 3;
  const MIN_DAYS = 30;
  const isMoney = x => typeof x === 'number' && Number.isFinite(x) && x > 0;
  const validDay = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') &&
    Number.isFinite(Date.parse(value+'T00:00:00Z')) &&
    new Date(value+'T00:00:00Z').toISOString().slice(0,10) === value;
  const validMonth = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value || '');
  const monthOrdinal = value => Number(value.slice(0,4)) * 12 + Number(value.slice(5,7));
  function uniqueSorted(values) { return [...new Set(values)].sort(); }
  function statusForDates(days) {
    const dates = uniqueSorted(days.filter(validDay));
    const spanDays = dates.length > 1
      ? Math.round((Date.parse(dates.at(-1)+'T00:00:00Z') - Date.parse(dates[0]+'T00:00:00Z')) / 86400000)
      : 0;
    return {observations:dates.length, from:dates[0] || null,
      to:dates.at(-1) || null, span_days:spanDays,
      trend_eligible:dates.length >= MIN_OBSERVATIONS && spanDays >= MIN_DAYS};
  }
  function statusForMonths(months) {
    const periods = uniqueSorted(months.filter(validMonth));
    const spanMonths = periods.length > 1 ? monthOrdinal(periods.at(-1)) - monthOrdinal(periods[0]) : 0;
    return {observations:periods.length, from:periods[0]||null,
      to:periods.at(-1)||null, span_months:spanMonths,
      trend_eligible:periods.length>=MIN_OBSERVATIONS && spanMonths>=2};
  }
  function isVerifiedActiveOffer(row, today) {
    if (!row || !validDay(today) || row.review_status !== 'automated-two-hosted-checks' ||
        row.asset_type !== 'apartment' ||
        row.metric_type !== 'single-listing-asking-price-per-sqm' ||
        !isMoney(row.value_vnd_per_m2) ||
        new Set(row.verification_run_ids || []).size < 2) return false;
    if (row.source_id === 'muaban-vn') {
      if (!validDay(row.source_listed_date) || !validDay(row.source_expiration_date) ||
          row.source_listed_date > today || row.source_expiration_date < today) return false;
      const elapsed = (Date.parse(today+'T00:00:00Z')-Date.parse(row.source_listed_date+'T00:00:00Z'))/86400000;
      return elapsed >= 0 && elapsed <= 90;
    }
    if (row.source_id === 'rever-vn') {
      if (!validDay(row.source_updated_date) || row.source_updated_date > today) return false;
      return (Date.parse(today+'T00:00:00Z') - Date.parse(row.source_updated_date+'T00:00:00Z')) / 86400000 <= 90;
    }
    return false;
  }
  function priceSeriesForProject(projectId, args, today) {
    const portal = new Map();
    for (const x of args.listingObservations || []) {
      if (x.project_id !== projectId || !x.source_id || !validDay(x.observation_date)) continue;
      if (x.coverage_status !== 'full' || !isMoney(x.asking_price_low_vnd_per_m2) ||
          !isMoney(x.asking_price_high_vnd_per_m2) ||
          x.asking_price_low_vnd_per_m2 > x.asking_price_high_vnd_per_m2) continue;
      // A villa and an apartment may NOT form one composite price trend.
      const key = [x.source_id,x.asset_type || 'unspecified',x.market_layer||'listing-asking'].join('|');
      if (!portal.has(key)) portal.set(key,{source_id:x.source_id,asset_type:x.asset_type||'unspecified',dates:[]});
      portal.get(key).dates.push(x.observation_date);
    }
    const portalSeries = [...portal.values()].map(s=>({...s,...statusForDates(s.dates)}))
      .sort((a,b)=>b.observations-a.observations||a.source_id.localeCompare(b.source_id));

    const monthly = new Map();
    for (const row of [...(args.projectMonthly || []),...(args.subprojectMonthly || [])]) {
      if (row.project_id !== projectId || !row.source_id || !validMonth(row.period) ||
          !isMoney(row.value_vnd_per_m2)) continue;
      const scope = row.subproject_id ? 'subproject':'project';
      const subject = row.subproject_id || projectId;
      const key = [row.source_id,scope,subject,row.asset_type || '',row.metric_type || ''].join('|');
      if (!monthly.has(key)) monthly.set(key,{source_id:row.source_id,scope,subject,
        subproject_name:row.subproject_name||null,periods:[]});
      monthly.get(key).periods.push(row.period);
    }
    const monthlySeries = [...monthly.values()].map(x=>({...x,...statusForMonths(x.periods)}))
      .sort((a,b)=>b.observations-a.observations||a.subject.localeCompare(b.subject));
    const projectMetrics = (args.marketObservations||[]).filter(x=>
      x.scope_type==='project' && x.project_id===projectId);
    const officialPrice = projectMetrics.filter(x=>isMoney(x.average_asp));
    const sales = projectMetrics.filter(x=>Number.isFinite(x.sales_units));
    const absorption = projectMetrics.filter(x=>Number.isFinite(x.absorption_rate));

    const individualOffers = new Map();
    for(const row of [...(args.reverOffers||[]),...(args.muabanOffers||[])]) {
      if(row.project_id!==projectId || !isVerifiedActiveOffer(row,today)) continue;
      individualOffers.set(row.source_id+'|'+row.listing_id,row);
    }
    const portalPeriods = Math.max(0,...portalSeries.map(x=>x.observations));
    const monthlyPeriods = Math.max(0,...monthlySeries.map(x=>x.observations));
    return {
      project_id:projectId, portal_series:portalSeries, monthly_series:monthlySeries,
      parent_monthly_series:monthlySeries.filter(x=>x.scope==='project').length,
      subproject_monthly_series:monthlySeries.filter(x=>x.scope==='subproject').length,
      portal_max_snapshots:portalPeriods, monthly_max_periods:monthlyPeriods,
      current_verified_unit_ads:individualOffers.size,
      disclosed_project_asp_observations:officialPrice.length,
      disclosed_project_sales_observations:sales.length,
      disclosed_project_absorption_observations:absorption.length,
      portal_trend_eligible:portalSeries.some(x=>x.trend_eligible),
      monthly_trend_eligible:monthlySeries.some(x=>x.trend_eligible),
      history_ready:portalSeries.some(x=>x.trend_eligible) || monthlySeries.some(x=>x.trend_eligible)
    };
  }
  function build(args={},today) {
    if(!validDay(today)) throw new Error('Explicit source-check date YYYY-MM-DD required');
    const projects=(args.projects||[]).filter(x=>x.id);
    const rows=projects.map(p=>({...priceSeriesForProject(p.id,args,today),
      project_name:p.name||p.id,region_ids:p.region_ids||[]}));
    rows.sort((a,b)=>Number(a.history_ready)-Number(b.history_ready) ||
      a.portal_max_snapshots-b.portal_max_snapshots ||
      a.monthly_max_periods-b.monthly_max_periods ||
      a.project_name.localeCompare(b.project_name));
    return {
      generated_for:today,projects:rows,
      total_projects:rows.length,
      portal_priced_projects:rows.filter(x=>x.portal_max_snapshots>0).length,
      monthly_priced_projects:rows.filter(x=>x.monthly_max_periods>0).length,
      history_ready_projects:rows.filter(x=>x.history_ready).length,
      project_asp_projects:rows.filter(x=>x.disclosed_project_asp_observations>0).length,
      project_sales_projects:rows.filter(x=>x.disclosed_project_sales_observations>0).length,
      unit_offer_projects:rows.filter(x=>x.current_verified_unit_ads>0).length,
      methodology:'Source- and product-isolated history counts; three priced dates spanning at least 30 days or three publisher months spanning two months. Publisher 1Y trend is not a local series. Verified unit ads, popular monthly price, portal asking ranges, project ASP and sales observations remain separate; not inferred as equivalent.'
    };
  }
  return {build,statusForDates,statusForMonths,isVerifiedActiveOffer};
});
