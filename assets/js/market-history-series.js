(() => {
  'use strict';

  // Quarter-missing intervals must remain visible. Null is never replaced by 0.
  function quarterIndex(period) {
    const match = /^(20\d{2})-Q([1-4])$/.exec(String(period || ''));
    return match ? Number(match[1]) * 4 + Number(match[2]) - 1 : null;
  }
  function quarterFromIndex(index) {
    return Math.floor(index / 4) + '-Q' + (index % 4 + 1);
  }
  function expandQuarterHistory(rows, maxIntervals = 28) {
    const quarterly = (rows || []).filter(r => r.period_type === 'quarter' && quarterIndex(r.period) !== null);
    const keyed = new Map(quarterly.map(r => [quarterIndex(r.period), r]));
    const indices = [...keyed.keys()].sort((a,b) => a-b);
    if (!indices.length) return { rows: [], missing: [], observed: 0, start: null, end: null };
    const first = indices[0], last = indices[indices.length - 1];
    if (last - first > maxIntervals) {
      // Reject suspicious or excessive time ranges without synthesizing a long chart.
      return { rows: quarterly.sort((a,b) => String(a.period).localeCompare(String(b.period))), missing: [],
        observed: indices.length, start: quarterFromIndex(first), end: quarterFromIndex(last), truncated: true };
    }
    const expanded = [], missing = [];
    for (let index = first; index <= last; index += 1) {
      const existing = keyed.get(index);
      if (existing) expanded.push(existing);
      else {
        const period = quarterFromIndex(index);
        missing.push(period);
        expanded.push({ period, period_type: 'quarter', new_supply: null, sales_units: null,
          absorption_rate: null, average_asp: null, data_missing: true });
      }
    }
    return { rows: expanded, missing, observed: indices.length, start: quarterFromIndex(first), end: quarterFromIndex(last), truncated: false };
  }
  function coverageSummary(series) {
    const hasSales = series.rows.filter(r => !r.data_missing && r.sales_units != null).length;
    const hasSupply = series.rows.filter(r => !r.data_missing && r.new_supply != null).length;
    return { total:series.rows.length, observed:series.observed, missing:series.missing.length,
      supplyPeriods:hasSupply, salesPeriods:hasSales, missingPeriods:series.missing };
  }
  function originalUsdPrice(row) {
    if (!Number.isFinite(row?.reported_primary_price_usd_per_sqm)) return '—';
    return 'US$ ' + new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
      .format(row.reported_primary_price_usd_per_sqm) + '/m²';
  }
  window.MarketHistorySeries = { quarterIndex, quarterFromIndex, expandQuarterHistory, coverageSummary, originalUsdPrice };
})();
