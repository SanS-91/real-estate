(() => {
  'use strict';

  const ALLOWED = new Set(['source-indexed-baseline', 'reviewed-release', 'automated-source-verified']);

  function verifiedGroups(rows, projectId = null) {
    const groups = new Map();
    (rows || []).forEach(row => {
      if ((projectId && row.project_id !== projectId) ||
          row.source_id !== 'onehousing-vn' ||
          row.metric_type !== 'popular-asking-price-per-sqm' ||
          !ALLOWED.has(row.review_status) ||
          !/^(20\d{2})-(0[1-9]|1[0-2])$/.test(String(row.period || '')) ||
          !Number.isFinite(row.value_vnd_per_m2) ||
          row.value_vnd_per_m2 <= 0 ||
          !row.series_key || !row.subproject_name) return;

      const key = [row.project_id, row.source_id, row.series_key].join('|');
      if (!groups.has(key)) groups.set(key, {
        project_id: row.project_id, source_id: row.source_id,
        series_key: row.series_key, subproject_name: row.subproject_name,
        periods: new Map(), conflict: false
      });
      const group = groups.get(key);
      if (group.subproject_name !== row.subproject_name) {
        group.conflict = true; return;
      }
      const existing = group.periods.get(row.period);
      if (existing && (existing.value_vnd_per_m2 !== row.value_vnd_per_m2 ||
          existing.source_url !== row.source_url)) {
        group.conflict = true;
      } else {
        group.periods.set(row.period, row);
      }
    });
    return [...groups.values()].filter(group => !group.conflict && group.periods.size >= 2)
      .map(group => {
        const observations = [...group.periods.values()]
          .sort((a,b) => a.period.localeCompare(b.period));
        return {
          project_id: group.project_id,
          source_id: group.source_id,
          series_key: group.series_key,
          subproject_name: group.subproject_name,
          observations,
          values: observations.map(row => ({
            period: row.period, value: row.value_vnd_per_m2
          }))
        };
      });
  }

  function forRow(groups, row) {
    if (!row || !row.series_key) return null;
    return (groups || []).find(group =>
      group.project_id === row.project_id &&
      group.source_id === row.source_id &&
      group.series_key === row.series_key &&
      group.subproject_name === row.subproject_name) || null;
  }

  window.MarketSubprojectTrends = { verifiedGroups, forRow };
})();
