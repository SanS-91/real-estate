(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'projects', 'supply-sales', 'pricing', 'developers', 'news'];
  let state = {
    view: 'overview',
    q: '',
    region: '',
    developer: '',
    segment: '',
    status: '',
    sort: 'latest',
    priceLayer: 'listing'
  };
  let data = { regions: [], developers: [], projects: [], phases: [], observations: [], listingObservations: [], listingComparables: [], articles: [], infrastructureProjects: [], legalTopics: [] };

  function payloadData(payload) { return payload?.data || []; }
  function byId(records) { return new Map(records.map(item => [item.id, item])); }
  function esc(value) { return Components.escapeHTML(value); }

  function sourceRef(sourceId, context = {}) {
    return window.Provenance?.sourceButton?.(sourceId, context) || `<span class="source-tag">${esc(String(sourceId || '—').replace(/^demo-/, '').replaceAll('-', ' '))}</span>`;
  }

  function formatCompact(value) {
    return window.Formatters?.compact?.(value) ?? (value === null || value === undefined ? '—' : String(value));
  }

  function formatArea(value) {
    return window.Formatters?.areaSqm?.(value) ?? (value === null || value === undefined ? '—' : `${value} m²`);
  }

  function formatAsp(value) {
    return window.Formatters?.aspVndPerSqm?.(value) ?? (value === null || value === undefined ? '—' : `${value} VND/m²`);
  }

  function formatPercent(value) {
    return window.Formatters?.percentDecimal?.(value) ?? (value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`);
  }

  function latestProjectObservation(projectId) {
    return data.observations
      .filter(item => item.project_id === projectId)
      .sort((a, b) => String(b.period).localeCompare(String(a.period)))[0] || null;
  }

  function latestListingObservation(projectId) {
    return data.listingObservations
      .filter(item => item.project_id === projectId)
      .sort((a,b) => String(b.observation_date || '').localeCompare(String(a.observation_date || '')))[0] || null;
  }

  function listingComparables(projectId) {
    return data.listingComparables
      .filter(item => item.anchor_project_id === projectId && item.project_id !== projectId)
      .sort((a,b) => Number(b.asking_price_vnd_per_m2 || 0) - Number(a.asking_price_vnd_per_m2 || 0));
  }

  function formatListingRange(row) {
    if (!row || row.asking_price_low_vnd_per_m2 == null || row.asking_price_high_vnd_per_m2 == null) return '—';
    return `${Formatters.number(row.asking_price_low_vnd_per_m2 / 1_000_000,{min:0,max:1})}–${Formatters.number(row.asking_price_high_vnd_per_m2 / 1_000_000,{min:0,max:1})} mn VND/m²`;
  }

  function listingPriceRows(records = data.projects) {
    return records.map(project => ({ project, row: latestListingObservation(project.id) }))
      .filter(item => item.row && item.row.asking_price_low_vnd_per_m2 != null && item.row.asking_price_high_vnd_per_m2 != null);
  }

  function listingTrendLabel(row) {
    return row?.asking_price_change_1y_pct == null ? '—' : Formatters.number(row.asking_price_change_1y_pct * 100,{min:1,max:1}) + '%';
  }

  function listingRangeChartData(records = data.projects) {
    const rows = listingPriceRows(records);
    return {
      labels: rows.map(item => item.project.name),
      lowValues: rows.map(item => item.row.asking_price_low_vnd_per_m2),
      highValues: rows.map(item => item.row.asking_price_high_vnd_per_m2)
    };
  }

  function priceLayerControls() {
    return `<div class="segmented-control market-price-layer" data-price-layer-control>
      <button type="button" data-price-layer="verified" class="${state.priceLayer === 'verified' ? 'is-active' : ''}">Verified price</button>
      <button type="button" data-price-layer="listing" class="${state.priceLayer === 'listing' ? 'is-active' : ''}">Listing market</button>
    </div>`;
  }

  function listingMarketDrawerHTML(project) {
    const row = latestListingObservation(project.id);
    if (!row) return '<p class="muted-text">No listing-market snapshot is available for this project yet.</p>';
    const comps = listingComparables(project.id).slice(0,8);
    const products = (row.product_price_ranges || []).map(item =>
      `<div class="drawer-list-row"><div><strong>${esc(item.product)}</strong><span>${esc(Formatters.number(item.low_vnd/1_000_000_000,{min:0,max:2}))}–${esc(Formatters.number(item.high_vnd/1_000_000_000,{min:0,max:2}))} bn</span></div></div>`
    ).join('');
    const compHTML = comps.length ? comps.map(item =>
      `<div class="drawer-list-row"><div><strong>${esc(item.comparable_name)}</strong><span>${esc(Formatters.number(item.asking_price_vnd_per_m2/1_000_000,{min:0,max:1}))} mn VND/m²</span></div></div>`
    ).join('') : '<p class="muted-text">No map comparable snapshot.</p>';
    return `
      <div class="drawer-metrics">
        ${Components.compactMetric({label:'Asking range',value:formatListingRange(row),note:'Listing portal · not transaction price'})}
        ${Components.compactMetric({label:'1Y portal trend',value:row.asking_price_change_1y_pct == null ? '—' : Formatters.number(row.asking_price_change_1y_pct*100,{min:1,max:1})+'%',note:row.observation_date})}
        ${Components.compactMetric({label:'Popular area',value:row.popular_area_low_sqm == null || row.popular_area_high_sqm == null ? '—' : row.popular_area_low_sqm+'–'+row.popular_area_high_sqm+' m²',note:row.coverage_status === 'partial' ? 'Partial portal snapshot' : 'Portal snapshot'})}
      </div>
      <p class="muted-text">${row.coverage_status === 'partial' ? 'Partial listing-market snapshot; unavailable aggregate fields remain blank. ' : ''}Secondary listing-market snapshot. Asking prices are not official sales, transaction prices or absorption.</p>
      ${products ? `<div class="drawer-subsection"><h4>Product asking ranges</h4>${products}</div>` : ''}
      <div class="drawer-subsection"><h4>Nearby map labels</h4>${compHTML}</div>
      <div class="provenance-inline-row">${sourceRef(row.source_id,{sourceDate:row.observation_date,sourceUrl:row.source_url,methodology:row.methodology_note})}<span class="muted-text">Listing-market source</span></div>
    `;
  }

  function projectActivityDate(projectId) {
    const article = data.articles
      .filter(item => (item.project_ids || []).includes(projectId))
      .sort((a,b) => String(b.published_at).localeCompare(String(a.published_at)))[0];
    return article?.published_at || null;
  }

  function developerName(project) {
    return Resolver.getLabel('developer', project.lead_developer_id);
  }

  function leadDeveloper(project) {
    return Resolver.getEntity('developer', project.lead_developer_id);
  }

  function legalTopicLinks(project) {
    return Resolver.getEntities('legal-topic', project.related_legal_topic_ids || []);
  }

  function regionNames(project) {
    return Resolver.getEntities('region', project.region_ids).map(item => item.name).join(', ') || '—';
  }

  function getView() {
    const value = App.getQueryParam('view');
    return VALID_VIEWS.includes(value) ? value : 'overview';
  }

  function parseState() {
    state.view = getView();
    ['q','region','developer','segment','status','sort'].forEach(key => {
      const value = App.getQueryParam(key);
      if (value !== null) state[key] = value;
    });
    const priceLayer = App.getQueryParam('price-layer');
    state.priceLayer = ['verified','listing'].includes(priceLayer) ? priceLayer : 'listing';
  }

  function updateTabs() {
    document.querySelectorAll('[data-market-tabs] [data-view]').forEach(link => {
      link.classList.toggle('is-active', link.dataset.view === state.view);
    });
  }

  function option(label, value, current) {
    return `<option value="${esc(value)}"${String(current) === String(value) ? ' selected' : ''}>${esc(label)}</option>`;
  }

  function filterToolbar({ includeDeveloper = true, includeSegment = true, includeStatus = true } = {}) {
    const regionOptions = data.regions.map(item => option(item.short_name || item.name, item.id, state.region)).join('');
    const developerOptions = data.developers.map(item => option(item.name, item.id, state.developer)).join('');
    const segments = [...new Set(data.projects.flatMap(item => item.segment_ids || []))].sort();
    const statuses = [...new Set(data.projects.map(item => item.status))].sort();
    return `
      <div class="filter-bar" data-market-filters>
        <label class="filter-field filter-field--search">
          <span>Search</span>
          <input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Project or location…">
        </label>
        <label class="filter-field">
          <span>Region</span>
          <select data-filter="region">${option('All regions','',state.region)}${regionOptions}</select>
        </label>
        ${includeDeveloper ? `<label class="filter-field"><span>Developer</span><select data-filter="developer">${option('All developers','',state.developer)}${developerOptions}</select></label>` : ''}
        ${includeSegment ? `<label class="filter-field"><span>Segment</span><select data-filter="segment">${option('All segments','',state.segment)}${segments.map(id => option(id.replaceAll('-',' '),id,state.segment)).join('')}</select></label>` : ''}
        ${includeStatus ? `<label class="filter-field"><span>Status</span><select data-filter="status">${option('All statuses','',state.status)}${statuses.map(id => option(id.replaceAll('-',' '),id,state.status)).join('')}</select></label>` : ''}
        <button class="button filter-reset" type="button" data-filter-reset>Reset</button>
      </div>
    `;
  }

  function projectFilter(records) {
    const config = [
      { id: 'region', field: 'region_ids', type: 'contains-any' },
      { id: 'developer', field: 'developer_ids', type: 'contains-any' },
      { id: 'segment', field: 'segment_ids', type: 'contains-any' },
      { id: 'status', field: 'status', type: 'equals' }
    ];
    let result = FilterEngine.apply(records, state, config);
    if (state.q) result = result.filter(project => FilterEngine.textMatch(project, state.q, [
      'name', 'location_text', 'summary',
      item => developerName(item),
      item => regionNames(item)
    ]));
    return result;
  }

  function summaryMetrics() {
    const projects = data.projects;
    const active = projects.filter(item => ['selling','ongoing','construction'].includes(item.status)).length;
    const knownUnitProjects = projects.filter(item => Number.isFinite(item.planned_units));
    const totalKnownUnits = knownUnitProjects.reduce((sum, item) => sum + item.planned_units, 0);
    const verifiedPriceObs = data.observations.filter(item => item.scope_type === 'project' && Number.isFinite(item.average_asp));
    return [
      { label: 'Tracked Projects', value: String(projects.length), note: 'Curated first-party entities' },
      { label: 'Active / Selling', value: String(active), note: 'Current disclosed status' },
      { label: 'Known Product Units', value: formatCompact(totalKnownUnits), note: `${knownUnitProjects.length}/${projects.length} projects disclose comparable counts` },
      { label: 'Verified Price Snapshots', value: String(verifiedPriceObs.length), note: 'No estimated project pricing' }
    ];
  }

  function hcmcSeries(segment = 'apartment') {
    return data.observations
      .filter(item => item.scope_type === 'region-segment' && item.period_type === 'quarter' && (item.region_ids || []).includes('hcmc') && (item.segment_ids || []).includes(segment))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)));
  }

  function marketBenchmarks(segment = 'apartment') {
    return data.observations
      .filter(item => item.scope_type === 'region-segment-benchmark' && (item.region_ids || []).includes('hcmc') && (item.segment_ids || []).includes(segment))
      .sort((a,b) => String(b.period).localeCompare(String(a.period)));
  }

  function priceSeries(projectIds = ['elysian']) {
    return projectIds.map(projectId => {
      const project = Resolver.getEntity('project', projectId);
      return {
        label: project?.name || projectId,
        values: data.observations
          .filter(item => item.project_id === projectId && item.average_asp)
          .sort((a,b) => String(a.period).localeCompare(String(b.period)))
          .map(item => ({ period: item.period, value: item.average_asp }))
      };
    }).filter(item => item.values.length);
  }

  function projectTable(records, limit = null) {
    const rows = (limit ? records.slice(0, limit) : records).map(project => {
      const obs = latestProjectObservation(project.id);
      const listing = latestListingObservation(project.id);
      return `
        <tr>
          <td><button class="table-link" type="button" data-project-id="${esc(project.id)}">${esc(project.name)}</button><span class="table-subtext">${esc(project.location_text)}</span></td>
          <td>${esc(developerName(project))}</td>
          <td>${esc(regionNames(project))}</td>
          <td>${Components.statusBadge(project.status)}</td>
          <td class="numeric">${Number.isFinite(project.planned_units) ? esc(formatCompact(project.planned_units)) : '<span class="table-muted">Disclosed qualitatively</span>'}</td>
          <td class="numeric">${esc(formatAsp(obs?.average_asp))}<span class="table-subtext">${esc(obs?.period || '')}</span></td>
          <td class="numeric market-listing-cell">${esc(formatListingRange(listing))}<span class="table-subtext">${listing?.coverage_status === 'partial' ? 'Partial snapshot' : (listing?.observation_date || '')}</span></td>
          <td class="numeric market-trend-cell">${esc(listingTrendLabel(listing))}</td>
          <td class="numeric">${esc(formatPercent(obs?.absorption_rate))}</td>
        </tr>`;
    }).join('');
    return `
      <div class="table-wrap">
        <table class="data-table data-table--market-projects">
          <thead><tr><th>Project</th><th>Developer</th><th>Region</th><th>Status</th><th class="numeric">Units</th><th class="numeric">Verified ASP</th><th class="numeric">Asking range</th><th class="numeric">1Y trend</th><th class="numeric">Absorption</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="9" class="table-empty">No projects match the selected filters.</td></tr>'}</tbody>
        </table>
      </div>`;
  }

  function renderOverview() {
    const recent = [...data.articles].sort((a,b) => String(b.published_at).localeCompare(String(a.published_at))).slice(0,4);
    const overviewMarketRows = hcmcSeries();
    const overviewMarketSource = overviewMarketRows[overviewMarketRows.length - 1] || null;
    const overviewPriceSource = data.observations.find(item => item.average_asp && item.source_id) || null;
    const html = `
      <div class="market-metric-grid">${summaryMetrics().map(Components.compactMetric).join('')}</div>
      <div class="market-layout market-layout--overview">
        <section class="section market-panel market-panel--wide">
          <div class="section-header"><div><span class="eyebrow">HCMC apartment</span><h2 class="section-title">Supply &amp; Sales</h2></div><a class="text-link" href="market.html?view=supply-sales">Open view</a></div>
          <div class="section-body"><div class="chart-frame"><canvas id="market-overview-supply"></canvas></div><p class="chart-note">Published quarterly new-supply observations; missing sales figures remain blank · ${sourceRef(overviewMarketSource?.source_id,{sourceDate:overviewMarketSource?.source_date,period:overviewMarketSource?.period,sourceUrl:overviewMarketSource?.source_url})}</p></div>
        </section>
        <section class="section market-panel">
          <div class="section-header"><div><span class="eyebrow">Latest activity</span><h2 class="section-title">Market Developments</h2></div><a class="text-link" href="market.html?view=news">View all</a></div>
          <div class="section-body market-news-compact">${recent.map(article => `<article><span>${esc(App.formatDate(article.published_at))}</span><strong>${esc(article.title)}</strong></article>`).join('')}</div>
        </section>
      </div>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Tracked projects</span><h2 class="section-title">Key Projects</h2></div><a class="text-link" href="market.html?view=projects">Open database</a></div>
        <div class="section-body section-body--table">${projectTable(data.projects, 6)}</div>
      </section>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Project pricing</span><h2 class="section-title">Pricing Snapshot</h2></div><div class="section-header__actions">${priceLayerControls()}<a class="text-link" href="market.html?view=pricing">Open Pricing</a></div></div>
        <div class="section-body"><div class="chart-frame"><canvas id="market-overview-price"></canvas></div><p class="chart-note">${state.priceLayer === 'listing' ? 'Listing-market asking ranges from mapped portal snapshots; not transaction prices.' : 'Only source-stated verified project pricing is shown; no synthetic history · ' + sourceRef(overviewPriceSource?.source_id,{sourceDate:overviewPriceSource?.source_date,period:overviewPriceSource?.period,sourceUrl:overviewPriceSource?.source_url})}</p></div>
      </section>`;
    setView(html);
    requestAnimationFrame(() => {
      ChartTools.renderSupplySales('market-overview-supply', overviewMarketRows);
      if (state.priceLayer === 'listing') {
        const listingChart = listingRangeChartData(data.projects);
        ChartTools.renderRangeSeries('market-overview-price', {
          labels: listingChart.labels,
          lowValues: listingChart.lowValues,
          highValues: listingChart.highValues,
          lowLabel: 'Asking low',
          highLabel: 'Asking high',
          yFormatter: value => Formatters.aspVndPerSqm(value, { short:true })
        });
      } else {
        ChartTools.renderPriceTrend('market-overview-price', priceSeries());
      }
    });
  }

  function renderProjects() {
    const records = projectFilter(data.projects);
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Project database</span><h2>${records.length} projects</h2><p>Filter structured project records, then open a project for metrics, phases and related market updates.</p></div></div>
      ${filterToolbar()}
      <section class="section"><div class="section-body section-body--table">${projectTable(records)}</div></section>`;
    setView(html);
    bindFilters();
  }

  function renderSupplySales() {
    if (!state.region) { state.region = 'hcmc'; App.setQueryParam('region', 'hcmc'); }
    if (!state.segment) { state.segment = 'apartment'; App.setQueryParam('segment', 'apartment'); }
    const region = state.region;
    const segment = state.segment;
    const regionObj = Resolver.getEntity('region', region);
    const rows = data.observations
      .filter(item => item.scope_type === 'region-segment' && (item.region_ids || []).includes(region) && (item.segment_ids || []).includes(segment))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)));
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Published observations</span><h2>Supply &amp; Sales</h2><p>Only source-published metrics are stored. Missing sales, absorption or price values remain blank rather than being inferred.</p></div></div>
      ${filterToolbar({ includeDeveloper:false, includeSegment:true, includeStatus:false })}
      <section class="section"><div class="section-header"><h2 class="section-title">${esc(regionObj?.name || 'Selected Region')} · ${esc(segment.replaceAll('-',' '))}</h2></div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="market-supply-sales"></canvas></div><p class="chart-note">Latest source: ${rows.length ? sourceRef(rows[rows.length-1].source_id,{sourceDate:rows[rows.length-1].source_date,period:rows[rows.length-1].period,sourceUrl:rows[rows.length-1].source_url}) : '—'}</p></div></section>
      <section class="section"><div class="section-header"><h2 class="section-title">Observation History</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Period</th><th class="numeric">New Supply</th><th class="numeric">Sales</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th><th>Source</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(row.period)}</td><td class="numeric">${esc(formatCompact(row.new_supply))}</td><td class="numeric">${esc(formatCompact(row.sales_units))}</td><td class="numeric">${esc(formatPercent(row.absorption_rate))}</td><td class="numeric">${esc(formatAsp(row.average_asp))}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td></tr>`).join('') || '<tr><td colspan="6" class="table-empty">No observations for this region.</td></tr>'}</tbody></table></div></div></section>`;
    setView(html);
    bindFilters();
    requestAnimationFrame(() => ChartTools.renderSupplySales('market-supply-sales', rows));
  }

  function renderPricing() {
    const filteredProjects = projectFilter(data.projects);
    const projectRows = filteredProjects
      .map(project => ({ project, obs: latestProjectObservation(project.id) }))
      .filter(item => Number.isFinite(item.obs?.average_asp));
    const listingRows = listingPriceRows(filteredProjects);
    const benchmarkRows = marketBenchmarks('apartment');
    const series = priceSeries(projectRows.map(item => item.project.id));
    const listingChart = listingRangeChartData(filteredProjects);

    const listingSnapshotRows = listingRows.map(({project,row}) =>
      '<tr><td><button class="table-link" data-project-id="' + esc(project.id) + '" type="button">' + esc(project.name) + '</button></td>' +
      '<td>' + esc(regionNames(project)) + '</td>' +
      '<td>' + esc(row.observation_date || '—') + '</td>' +
      '<td class="numeric">' + esc(formatListingRange(row)) + '</td>' +
      '<td class="numeric">' + esc(listingTrendLabel(row)) + '</td>' +
      '<td>' + esc(row.coverage_status || 'full') + '</td>' +
      '<td>' + sourceRef(row.source_id,{sourceDate:row.observation_date,sourceUrl:row.source_url,methodology:row.methodology_note}) + '</td></tr>'
    ).join('');
    const listingSnapshotTable = '<thead><tr><th>Project</th><th>Region</th><th>Snapshot</th><th class="numeric">Asking Range</th><th class="numeric">1Y Trend</th><th>Coverage</th><th>Source</th></tr></thead><tbody>' +
      (listingSnapshotRows || '<tr><td colspan="7" class="table-empty">No priced listing snapshots.</td></tr>') + '</tbody>';

    const verifiedSnapshotRows = projectRows.map(({project,obs}) =>
      '<tr><td><button class="table-link" data-project-id="' + esc(project.id) + '" type="button">' + esc(project.name) + '</button></td>' +
      '<td>' + esc(regionNames(project)) + '</td>' +
      '<td>' + esc(obs.period) + '</td>' +
      '<td class="numeric">' + esc(formatAsp(obs.average_asp)) + '</td>' +
      '<td>' + esc(obs.price_basis?.replaceAll('-',' ') || '—') + '</td>' +
      '<td>' + sourceRef(obs.source_id,{sourceDate:obs.source_date,period:obs.period,methodology:obs.methodology_note,sourceUrl:obs.source_url}) + '</td></tr>'
    ).join('');
    const verifiedSnapshotTable = '<thead><tr><th>Project</th><th>Region</th><th>Period</th><th class="numeric">ASP</th><th>Basis</th><th>Source</th></tr></thead><tbody>' +
      (verifiedSnapshotRows || '<tr><td colspan="6" class="table-empty">No comparable pricing records.</td></tr>') + '</tbody>';

    const chartBody = state.priceLayer === 'listing'
      ? (listingRows.length ? '<div class="chart-frame chart-frame--large"><canvas id="market-pricing"></canvas></div><p class="chart-note">Portal asking-price ranges; not executed transaction prices or official developer sales.</p>' : '<div class="state-box">No priced listing snapshots for the selected filters.</div>')
      : (series.length ? '<div class="chart-frame chart-frame--large"><canvas id="market-pricing"></canvas></div><p class="chart-note">Sparse source-stated snapshots; no missing project price is estimated.</p>' : '<div class="state-box">No verified project price observations for the selected filters.</div>');
    const snapshotTable = state.priceLayer === 'listing' ? listingSnapshotTable : verifiedSnapshotTable;

    const html = `
      <div class="view-intro"><div><span class="eyebrow">Evidence-backed price observations</span><h2>Pricing</h2><p>Verified project prices and listing-market asking ranges are shown as separate layers. Missing fields remain blank.</p></div></div>
      ${filterToolbar({ includeStatus:false })}
      <section class="section">
        <div class="section-header"><div><h2 class="section-title">${state.priceLayer === 'listing' ? 'Listing Market Asking Ranges' : 'Verified Project Pricing'}</h2></div>${priceLayerControls()}</div>
        <div class="section-body">${chartBody}</div>
      </section>
      <section class="section">
        <div class="section-header"><h2 class="section-title">${state.priceLayer === 'listing' ? 'Latest Listing Snapshot' : 'Latest Verified Snapshot'}</h2></div>
        <div class="section-body section-body--table"><div class="table-wrap"><table class="data-table">${snapshotTable}</table></div></div>
      </section>
      <section class="section"><div class="section-header"><h2 class="section-title">Market Benchmarks</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Market</th><th>Period</th><th class="numeric">New Supply</th><th class="numeric">Transactions</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th><th>Source</th></tr></thead><tbody>${benchmarkRows.map(row=>`<tr><td>HCMC · Apartment</td><td>${esc(row.period)}</td><td class="numeric">${esc(formatCompact(row.new_supply))}</td><td class="numeric">${esc(formatCompact(row.sales_units))}</td><td class="numeric">${esc(formatPercent(row.absorption_rate))}</td><td class="numeric">${esc(formatAsp(row.average_asp))}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td></tr>`).join('') || '<tr><td colspan="7" class="table-empty">No market benchmark records.</td></tr>'}</tbody></table></div></div></section>`;
    setView(html);
    bindFilters();
    if (state.priceLayer === 'listing') {
      if (listingRows.length) requestAnimationFrame(() => ChartTools.renderRangeSeries('market-pricing', {
        labels: listingChart.labels,
        lowValues: listingChart.lowValues,
        highValues: listingChart.highValues,
        lowLabel: 'Asking low',
        highLabel: 'Asking high',
        yFormatter: value => Formatters.aspVndPerSqm(value, { short:true })
      }));
    } else if (series.length) {
      requestAnimationFrame(() => ChartTools.renderPriceTrend('market-pricing', series));
    }
  }
  function renderDevelopers() {
    const cards = data.developers.map(dev => {
      const projects = data.projects.filter(project => (project.developer_ids || []).includes(dev.id));
      const selling = projects.filter(project => project.status === 'selling').length;
      return `<article class="developer-card">
        <div><span class="eyebrow">Developer</span><h3>${esc(dev.name)}</h3><p>${esc(dev.summary)}</p><div>${sourceRef(dev.primary_source_id,{sourceUrl:dev.official_url})}</div></div>
        <div class="developer-card__stats"><span><strong>${projects.length}</strong> tracked projects</span><span><strong>${selling}</strong> selling</span></div>
        <div class="developer-card__links"><a class="text-link" href="market.html?view=projects&developer=${encodeURIComponent(dev.id)}">View projects</a><a class="text-link" href="research.html?type=developer&ids=${encodeURIComponent(dev.id)}">Open Research</a></div>
      </article>`;
    }).join('');
    setView(`<div class="view-intro"><div><span class="eyebrow">Developer registry</span><h2>${data.developers.length} developers</h2><p>Developer records resolve to project relationships instead of storing duplicate project lists.</p></div></div><div class="developer-grid">${cards}</div>`);
  }

  function renderNews() {
    let articles = [...data.articles];
    if (state.region) articles = articles.filter(item => (item.region_ids || []).includes(state.region));
    if (state.developer) articles = articles.filter(item => (item.developer_ids || []).includes(state.developer));
    if (state.q) articles = articles.filter(item => FilterEngine.textMatch(item, state.q, ['title','summary','tags']));
    articles.sort((a,b) => String(b.published_at).localeCompare(String(a.published_at)));
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Evidence layer</span><h2>Market News &amp; Research</h2><p>Articles are evidence linked to projects, developers and regions; they are not treated as the same thing as market events.</p></div></div>
      ${filterToolbar({ includeSegment:false, includeStatus:false })}
      <div class="article-list">${articles.map(article => {
        const projectNames = Resolver.getEntities('project', article.project_ids || []).map(item => item.name).join(' · ');
        return `<article class="article-row"><div class="article-row__date">${esc(App.formatDate(article.published_at))}</div><div><div class="article-row__meta"><span class="source-tag">${esc(article.content_type)}</span>${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}<span>${esc(projectNames || Resolver.getEntities('region', article.region_ids || []).map(item=>item.short_name || item.name).join(' · '))}</span></div><h3><a class="article-title-link" href="${esc(article.url)}" target="_blank" rel="noopener noreferrer">${esc(article.title)}</a></h3><p>${esc(article.summary)}</p></div></article>`;
      }).join('') || Components.stateBox('No articles match the selected filters.')}</div>`;
    setView(html);
    bindFilters();
  }

  function setView(html) {
    const node = document.querySelector('[data-market-view]');
    if (node) node.innerHTML = html;
  }

  function render() {
    updateTabs();
    ChartTools.destroy('market-overview-supply');
    ChartTools.destroy('market-overview-price');
    ChartTools.destroy('market-supply-sales');
    ChartTools.destroy('market-pricing');
    if (state.view === 'projects') renderProjects();
    else if (state.view === 'supply-sales') renderSupplySales();
    else if (state.view === 'pricing') renderPricing();
    else if (state.view === 'developers') renderDevelopers();
    else if (state.view === 'news') renderNews();
    else renderOverview();
  }

  function updateFilterParam(key, value) {
    state[key] = value;
    App.setQueryParam(key, value || null);
    render();
  }

  function bindFilters() {
    document.querySelectorAll('[data-filter]').forEach(control => {
      const handler = () => updateFilterParam(control.dataset.filter, control.value.trim());
      control.addEventListener(control.tagName === 'INPUT' ? 'change' : 'change', handler);
    });
    document.querySelector('[data-filter-reset]')?.addEventListener('click', () => {
      ['q','region','developer','segment','status','sort'].forEach(key => {
        state[key] = '';
        App.removeQueryParam(key);
      });
      render();
    });
  }

  function listingHistoryHTML(project) {
    const rows = window.HistoryEngine?.listingMarketSeries?.(data.listingObservations, project.id) || [];
    if (!rows.length) return '<p class="muted-text">No listing snapshot history is available yet.</p>';
    const latest = rows.at(-1);
    const delta = window.HistoryEngine?.listingMarketDelta?.(data.listingObservations, project.id) || { previous:null, changes:{} };
    const chartId = 'listing-history-' + String(project.id).replace(/[^a-z0-9_-]/gi,'-');
    const changeCount = Object.keys(delta.changes || {}).length;
    const rowsHtml = [...rows].reverse().slice(0,8).map(row =>
      '<div class="drawer-list-row drawer-list-row--stack"><span>' + esc(App.formatDate(row.observation_date)) + ' · ' + esc(row.coverage_status || 'full') + '</span><strong>' + esc(formatListingRange(row)) + '</strong><span>' + esc(listingTrendLabel(row)) + ' · ' + sourceRef(row.source_id,{sourceDate:row.observation_date,sourceUrl:row.source_url,methodology:row.methodology_note}) + '</span></div>'
    ).join('');
    return '<div class="listing-history-summary"><strong>' + rows.length + ' snapshot' + (rows.length === 1 ? '' : 's') + '</strong><span>' +
      (delta.previous ? (changeCount ? changeCount + ' tracked field change(s) vs previous snapshot' : 'No tracked field change vs previous snapshot') : 'Baseline snapshot collected') +
      '</span></div><div class="chart-frame chart-frame--drawer"><canvas id="' + esc(chartId) + '"></canvas></div><div class="drawer-subsection"><h4>Snapshot history</h4>' + rowsHtml + '</div>';
  }

  function renderListingHistoryChart(projectId) {
    const rows = window.HistoryEngine?.listingMarketSeries?.(data.listingObservations, projectId) || [];
    if (!rows.length) return;
    const chartId = 'listing-history-' + String(projectId).replace(/[^a-z0-9_-]/gi,'-');
    ChartTools.renderRangeSeries(chartId, {
      labels: rows.map(row => row.observation_date),
      lowValues: rows.map(row => row.asking_price_low_vnd_per_m2),
      highValues: rows.map(row => row.asking_price_high_vnd_per_m2),
      lowLabel: 'Asking low',
      highLabel: 'Asking high',
      yFormatter: value => Formatters.aspVndPerSqm(value, { short:true })
    });
  }

  function projectHistoryHTML(project) {
    const rows = window.HistoryEngine?.marketProjectHistory?.(project, data.observations, data.phases) || [];
    if (!rows.length) return '<p class="muted-text">No dated project history is available yet.</p>';
    return rows.slice(0, 8).map(item => {
      const source = item.source_id ? ` · ${sourceRef(item.source_id,{sourceDate:item.date,sourceUrl:item.source_url})}` : '';
      return `<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(item.date))} · ${esc(String(item.type || '').replaceAll('-',' '))}${source}</span><strong>${esc(item.title)}</strong>${item.detail ? `<span>${esc(item.detail)}</span>` : ''}</div>`;
    }).join('');
  }

  function projectDrawerHTML(project) {
    const obs = latestProjectObservation(project.id);
    const phases = data.phases.filter(item => item.project_id === project.id);
    const relatedArticles = data.articles.filter(item => (item.project_ids || []).includes(project.id)).sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at))).slice(0,3);
    const linkedInfrastructureIds = new Set(project.related_infrastructure_ids || []);
    data.infrastructureProjects.forEach(item => {
      if ((item.related_real_estate_project_ids || []).includes(project.id)) linkedInfrastructureIds.add(item.id);
    });
    const relatedInfrastructure = Resolver.getEntities('infrastructure-project', [...linkedInfrastructureIds]);
    return `
      <div class="drawer-entity-head">
        <span class="eyebrow">Project</span>
        <h2>${esc(project.name)}</h2>
        <p>${esc(project.location_text)} · ${esc(developerName(project))}</p>
        ${Components.statusBadge(project.status)}
        <div class="drawer-actions"><a class="button" href="research.html?type=project&ids=${encodeURIComponent(project.id)}">Open Research</a></div>
      </div>
      <div class="drawer-metrics">
        ${Components.compactMetric({label:'Planned units',value:Number.isFinite(project.planned_units) ? formatCompact(project.planned_units) : '—',note:project.known_units_note || 'No exact comparable count published'})}
        ${Components.compactMetric({label:'Area',value:formatArea(project.total_area_sqm)})}
        ${Components.compactMetric({label:'Latest ASP',value:formatAsp(obs?.average_asp),note:obs?.period || ''})}
        ${Components.compactMetric({label:'Absorption',value:formatPercent(obs?.absorption_rate),note:obs?.period || ''})}
      </div>
      <div class="drawer-section"><h3>Overview</h3><p>${esc(project.summary)}</p></div>
      <div class="drawer-section"><h3>Listing Market</h3>${listingMarketDrawerHTML(project)}</div>
      <div class="drawer-section"><h3>Listing Price History</h3>${listingHistoryHTML(project)}</div>
      <div class="drawer-section"><h3>Project History</h3>${projectHistoryHTML(project)}</div>
      ${leadDeveloper(project) ? `<div class="drawer-section"><h3>Developer</h3><div class="drawer-list-row"><div><strong>${esc(leadDeveloper(project).name)}</strong><span>${esc(leadDeveloper(project).summary || '')}</span></div><a class="text-link" href="market.html?view=projects&developer=${encodeURIComponent(leadDeveloper(project).id)}">Open portfolio</a></div></div>` : ''}
      <div class="drawer-section"><h3>Segments</h3><div class="chip-row">${(project.segment_ids || []).map(id=>`<span class="relation-chip">${esc(id.replaceAll('-',' '))}</span>`).join('')}</div></div>
      <div class="drawer-section"><h3>Legal Research Topics</h3>${legalTopicLinks(project).length ? `<div class="chip-row">${legalTopicLinks(project).map(item=>`<a class="relation-chip" href="legal.html?view=documents&topic=${encodeURIComponent(item.id)}">${esc(item.name)}</a>`).join('')}</div><p class="muted-text">Research shortcuts by topic only; they do not determine whether a specific regulation applies to this project.</p>` : '<p class="muted-text">No curated legal-topic links.</p>'}</div>
      <div class="drawer-section"><h3>Phases</h3>${phases.length ? phases.map(item=>`<div class="drawer-list-row"><div><strong>${esc(item.name)}</strong><span>${esc(item.phase_type.replaceAll('-',' '))}${item.known_units_note ? ` · ${esc(item.known_units_note)}` : ''}</span></div>${Components.statusBadge(item.status)}</div>`).join('') : '<p class="muted-text">No phase records yet.</p>'}</div>
      <div class="drawer-section"><h3>Related Infrastructure</h3>${relatedInfrastructure.length ? relatedInfrastructure.map(item=>`<div class="drawer-list-row"><div><strong>${esc(item.name)}</strong><span>${esc(item.location_text || '')}</span></div><a class="text-link" href="infrastructure.html?view=projects&project=${encodeURIComponent(item.id)}">Open</a></div>`).join('') : '<p class="muted-text">No direct infrastructure links in the curated dataset.</p>'}</div>
      <div class="drawer-section"><h3>Data Provenance</h3><div class="provenance-inline-row">${sourceRef(project.primary_source_id,{sourceUrl:project.official_url,sourceDate:project.source_date})}<span class="muted-text">Project entity source</span></div>${obs ? `<div class="provenance-inline-row">${sourceRef(obs.source_id,{sourceDate:obs.source_date,period:obs.period,methodology:obs.methodology_note,sourceUrl:obs.source_url})}<span class="muted-text">Latest displayed market observation · ${esc(obs.period || '')}</span></div>` : '<p class="muted-text">No quantitative market observation is published for this project in the curated dataset.</p>'}</div>
      <div class="drawer-section"><h3>Recent Evidence</h3>${relatedArticles.length ? relatedArticles.map(item=>`<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(item.published_at))} · ${sourceRef(item.source_id,{publishedAt:item.published_at,sourceUrl:item.url})}</span><strong>${esc(item.title)}</strong></div>`).join('') : '<p class="muted-text">No related articles.</p>'}</div>
      <div class="drawer-section"><a class="text-link" href="market.html?view=news&q=${encodeURIComponent(project.name)}">View related market news</a></div>`;
  }

  function openProject(projectId, { push = true } = {}) {
    const project = Resolver.getEntity('project', projectId);
    if (!project) return;
    if (push) App.setQueryParam('project', projectId, { push: true });
    App.openDrawer({ title: project.name, html: projectDrawerHTML(project) });
    requestAnimationFrame(() => renderListingHistoryChart(project.id));
  }

  function syncDrawerFromURL() {
    const projectId = App.getQueryParam('project');
    if (projectId) openProject(projectId, { push: false });
    else App.closeDrawer();
  }

  function bindDelegatedEvents() {
    document.addEventListener('click', event => {
      const priceLayerButton = event.target.closest('[data-price-layer]');
      if (priceLayerButton) {
        state.priceLayer = priceLayerButton.dataset.priceLayer;
        App.setQueryParam('price-layer', state.priceLayer);
        render();
        return;
      }
      const button = event.target.closest('[data-project-id]');
      if (!button) return;
      openProject(button.dataset.projectId);
    });

    document.addEventListener('app:drawer-closed', () => {
      if (App.getQueryParam('project')) App.removeQueryParam('project');
    });

    window.addEventListener('popstate', () => {
      parseState();
      render();
      const projectId = App.getQueryParam('project');
      if (projectId) openProject(projectId, { push:false });
      else App.closeDrawer();
    });
  }

  async function load() {
    try {
      await window.Provenance?.load?.();
      const [regions, developers, projects, phases, observations, listingObservations, listingComparables, articles, infrastructureProjects, legalTopics, meta] = await Promise.all([
        DataStore.getRegions(), DataStore.getDevelopers(), DataStore.getProjects(), DataStore.getProjectPhases(), DataStore.getMarketObservations(), DataStore.getListingObservations(), DataStore.getListingComparables(), DataStore.getArticles(), DataStore.getInfrastructureProjects(), DataStore.getLegalTopics(), DataStore.getMeta()
      ]);
      data = {
        regions: payloadData(regions), developers: payloadData(developers), projects: payloadData(projects), phases: payloadData(phases), observations: payloadData(observations), listingObservations: payloadData(listingObservations), listingComparables: payloadData(listingComparables), articles: payloadData(articles).filter(item => item.category === 'market'), infrastructureProjects: payloadData(infrastructureProjects), legalTopics: payloadData(legalTopics)
      };
      Resolver.setData('region', data.regions);
      Resolver.setData('developer', data.developers);
      Resolver.setData('project', data.projects);
      Resolver.setData('infrastructure-project', data.infrastructureProjects);
      Resolver.setData('legal-topic', data.legalTopics);
      parseState();
      const updated = document.querySelector('[data-market-updated]');
      if (updated) updated.textContent = `Curated registry · ${data.projects.length} projects`;
      render();
      const projectId = App.getQueryParam('project');
      if (projectId) openProject(projectId, { push:false });
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load Market registry data. Check that the site is running through a web server.', 'error'));
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindDelegatedEvents();
    load();
  });
})();
