(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'projects', 'project-detail', 'supply-sales', 'pricing', 'developers', 'news'];
  let state = {
    view: 'overview',
    q: '',
    region: '',
    developer: '',
    segment: '',
    status: '',
    sort: 'latest',
    source: '',
    priceLayer: 'listing'
  };
  let data = { regions: [], developers: [], projects: [], phases: [], observations: [], listingObservations: [], listingComparables: [], articles: [], allArticles: [], infrastructureProjects: [], infrastructureSchedules: [], legalTopics: [], legalDocuments: [], events: [], macroIndicators: [], macroRows: [] };

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

  function formatMarketMetric(row, field) {
    if (!row) return '—';
    const qualifiers = row.metric_qualifiers || {};
    if (field === 'new_supply' && row.new_supply == null && Number.isFinite(row.new_supply_lower_bound)) {
      return '>' + formatCompact(row.new_supply_lower_bound);
    }
    const value = row[field];
    let formatted = '—';
    if (field === 'absorption_rate') formatted = formatPercent(value);
    else if (field === 'average_asp') formatted = formatAsp(value);
    else formatted = formatCompact(value);
    if (formatted === '—') return formatted;
    return qualifiers[field] === 'approx' ? '≈' + formatted : formatted;
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
    ['q','region','developer','segment','status','sort','source'].forEach(key => {
      const value = App.getQueryParam(key);
      if (value !== null) state[key] = value;
    });
    const priceLayer = App.getQueryParam('price-layer');
    state.priceLayer = ['verified','listing'].includes(priceLayer) ? priceLayer : 'listing';
  }

  function updateTabs() {
    document.body.classList.toggle('market-news-page', state.view === 'news');
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

  function marketSourceLabel(sourceId) {
    const labels = {
      'cbre-vietnam-market': 'CBRE Vietnam Research',
      'savills-vietnam-market': 'Savills Vietnam Research',
      'jll-vietnam-market': 'JLL Vietnam Research',
      'cushman-wakefield-vietnam-market': 'Cushman & Wakefield Vietnam Research'
    };
    return labels[sourceId] || String(sourceId || '—').replaceAll('-', ' ');
  }

  function preferredMarketSource(rows) {
    const ids = [...new Set(rows.map(item => item.source_id).filter(Boolean))];
    if (ids.includes('cbre-vietnam-market')) return 'cbre-vietnam-market';
    return ids[0] || '';
  }

  function hcmcSeries(segment = 'apartment', sourceId = null) {
    const rows = data.observations
      .filter(item => item.scope_type === 'region-segment' && item.period_type === 'quarter' && (item.region_ids || []).includes('hcmc') && (item.segment_ids || []).includes(segment));
    const selected = sourceId || preferredMarketSource(rows);
    return rows
      .filter(item => !selected || item.source_id === selected)
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

  function relatedInfrastructureForProject(project) {
    const ids = new Set(project.related_infrastructure_ids || []);
    data.infrastructureProjects.forEach(item => {
      if ((item.related_real_estate_project_ids || []).includes(project.id)) ids.add(item.id);
    });
    return Resolver.getEntities('infrastructure-project', [...ids]);
  }

  function projectDetailListingHistory(project) {
    const rows = window.HistoryEngine?.listingMarketSeries?.(data.listingObservations, project.id) || [];
    if (!rows.length) return '<div class="state-box">No listing-market history is available for this project yet.</div>';
    return `
      <div class="chart-frame chart-frame--large"><canvas id="market-project-listing-history"></canvas></div>
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Snapshot</th><th class="numeric">Asking Low</th><th class="numeric">Asking High</th><th class="numeric">1Y Trend</th><th>Coverage</th><th>Source</th></tr></thead><tbody>
      ${[...rows].reverse().map(row=>`<tr><td>${esc(row.observation_date)}</td><td class="numeric">${row.asking_price_low_vnd_per_m2 == null ? '—' : esc(formatAsp(row.asking_price_low_vnd_per_m2))}</td><td class="numeric">${row.asking_price_high_vnd_per_m2 == null ? '—' : esc(formatAsp(row.asking_price_high_vnd_per_m2))}</td><td class="numeric">${esc(listingTrendLabel(row))}</td><td>${esc(row.coverage_status || 'full')}</td><td>${sourceRef(row.source_id,{sourceDate:row.observation_date,sourceUrl:row.source_url,methodology:row.methodology_note})}</td></tr>`).join('')}
      </tbody></table></div>`;
  }

  function renderProjectDetailListingChart(projectId) {
    const rows = window.HistoryEngine?.listingMarketSeries?.(data.listingObservations, projectId) || [];
    if (!rows.length) return;
    ChartTools.renderRangeSeries('market-project-listing-history', {
      labels: rows.map(row => row.observation_date),
      lowValues: rows.map(row => row.asking_price_low_vnd_per_m2),
      highValues: rows.map(row => row.asking_price_high_vnd_per_m2),
      lowLabel: 'Asking low',
      highLabel: 'Asking high',
      yFormatter: value => Formatters.aspVndPerSqm(value, { short:true })
    });
  }

  function projectIntelligence(project) {
    if (!window.IntelligenceContext || !project) return null;
    return IntelligenceContext.query({
      projects:data.projects,
      regions:data.regions,
      developers:data.developers,
      infrastructure:data.infrastructureProjects,
      infrastructureSchedules:data.infrastructureSchedules,
      marketObservations:data.observations,
      listingObservations:data.listingObservations,
      legal:data.legalDocuments,
      articles:data.allArticles,
      events:data.events,
      macroRows:data.macroRows
    }, {
      type:'project',
      id:project.id,
      includeMacroContext:true,
      macroIndicatorIds:[
        'usd-vnd-central-rate',
        'credit-growth-ytd',
        'cpi-yoy',
        'deposit-rate-12m',
        'policy-refinancing-rate'
      ]
    });
  }

  function latestMacroContextRows(rows) {
    const byIndicator=new Map();
    (rows || []).forEach(row => {
      const key=row.data_date || row.period || row.published_at || '';
      const prior=byIndicator.get(row.indicator_id);
      const priorKey=prior ? (prior.data_date || prior.period || prior.published_at || '') : '';
      if (!prior || key > priorKey) byIndicator.set(row.indicator_id,row);
    });
    return [...byIndicator.values()].sort((a,b)=>String(a.indicator_id).localeCompare(String(b.indicator_id)));
  }

  function macroIndicatorName(id) {
    return data.macroIndicators.find(x=>x.id===id)?.name || String(id || '—').replaceAll('-',' ');
  }

  function projectIntelligenceSummaryHTML(intel) {
    if (!intel) return '';
    const direct=intel.direct || {};
    const contextual=intel.contextual || {};
    const counts=[
      ['Verified project observations',(direct.marketObservations || []).length],
      ['Listing snapshots',(direct.listingObservations || []).length],
      ['Infrastructure links',(direct.infrastructure || []).length],
      ['Legal topic-relevant docs',(contextual.legalDocuments || []).length],
      ['Regional benchmarks',(contextual.regionalMarketObservations || []).length],
      ['Macro context series',latestMacroContextRows(contextual.macroObservations || []).length]
    ];
    return `<section class="section project-intelligence-summary">
      <div class="section-header"><div><span class="eyebrow">Cross-module dossier</span><h2 class="section-title">Intelligence Coverage</h2></div><a class="text-link" href="research.html?type=project&ids=${encodeURIComponent(intel.subject.id)}">Open Research workspace</a></div>
      <div class="section-body">
        <div class="project-intelligence-counts">${counts.map(([label,value])=>`<div><strong>${esc(String(value))}</strong><span>${esc(label)}</span></div>`).join('')}</div>
        <p class="research-disclaimer">Direct project evidence is separated from contextual evidence. Legal documents are linked by controlled topic relevance only; macro data is broad context and is not a project-specific fact.</p>
      </div>
    </section>`;
  }

  function projectLegalEvidenceHTML(intel, project) {
    const topics=legalTopicLinks(project);
    const docs=[...(intel?.contextual?.legalDocuments || [])]
      .sort((a,b)=>String(b.issued_date || b.effective_date || '').localeCompare(String(a.issued_date || a.effective_date || '')))
      .slice(0,6);
    const topicLinks=topics.length ? `<div class="research-topic-row">${topics.map(item=>`<a class="research-topic-chip" href="legal.html?view=documents&topic=${encodeURIComponent(item.id)}">${esc(item.name)}</a>`).join('')}</div>` : '';
    const docRows=docs.length ? `<div class="project-evidence-list">${docs.map(doc=>`<a href="legal.html?view=documents&document=${encodeURIComponent(doc.id)}"><div><strong>${esc(doc.document_number || doc.title)}</strong><span>${esc(doc.title)}</span></div><small>${esc(App.formatDate(doc.issued_date || doc.effective_date))} · ${esc(String(doc.status || '').replaceAll('-',' '))}</small></a>`).join('')}</div>` : '<p class="muted-text">No topic-relevant Legal documents in the canonical registry.</p>';
    return `${topicLinks}${docRows}<p class="muted-text">Topic relevance is a research shortcut only. It does not determine whether a document legally applies to this project.</p>`;
  }

  function projectInfrastructureEvidenceHTML(intel) {
    const infrastructure=intel?.direct?.infrastructure || [];
    const schedules=intel?.direct?.infrastructureSchedules || [];
    if (!infrastructure.length) return '<p class="muted-text">No direct infrastructure links in the curated dataset.</p>';
    return `<div class="project-evidence-list">${infrastructure.map(item=>{
      const latest=schedules.filter(x=>x.infrastructure_project_id===item.id)
        .sort((a,b)=>String(b.announced_date || '').localeCompare(String(a.announced_date || '')))[0];
      const scheduleText=latest ? `${latest.schedule_type?.replaceAll('-',' ') || 'schedule'} · ${latest.target_period || '—'}` : (item.current_expected_completion || 'No schedule record');
      return `<a href="infrastructure.html?view=projects&project=${encodeURIComponent(item.id)}"><div><strong>${esc(item.name)}</strong><span>${esc(item.location_text || '')}</span></div><small>${esc(scheduleText)} · ${esc(String(item.status || '').replaceAll('-',' '))}</small></a>`;
    }).join('')}</div>`;
  }

  function projectContextHTML(intel) {
    if (!intel) return '<p class="muted-text">No cross-module context available.</p>';
    const market=[...(intel.contextual?.regionalMarketObservations || [])]
      .sort((a,b)=>String(b.period || b.source_date || '').localeCompare(String(a.period || a.source_date || '')))
      .slice(0,5);
    const macro=latestMacroContextRows(intel.contextual?.macroObservations || []);
    return `<div class="project-context-grid">
      <div>
        <h3>Regional Market Context</h3>
        ${market.length ? `<div class="project-evidence-list">${market.map(row=>`<div class="project-evidence-static"><div><strong>${esc((row.segment_ids || []).join(', ') || 'Market benchmark')}</strong><span>${esc(row.period || row.source_date || '—')}</span></div><small>${row.new_supply != null ? 'Supply '+esc(formatMarketMetric(row,'new_supply'))+' · ' : ''}${row.absorption_rate != null ? 'Absorption '+esc(formatMarketMetric(row,'absorption_rate'))+' · ' : ''}${esc(marketSourceLabel(row.source_id))}</small></div>`).join('')}</div>` : '<p class="muted-text">No compatible regional benchmark.</p>'}
      </div>
      <div>
        <h3>Macro Context</h3>
        ${macro.length ? `<div class="project-evidence-list">${macro.map(row=>`<div class="project-evidence-static"><div><strong>${esc(macroIndicatorName(row.indicator_id))}</strong><span>${esc(row.period || row.data_date || '—')}</span></div><small>${esc(Formatters.unitValue(row.unit,row.value,{compact:true}))}</small></div>`).join('')}</div>` : '<p class="muted-text">No selected macro context available.</p>'}
      </div>
    </div><p class="research-disclaimer">Regional market and macro rows are contextual evidence only; they are not attributed to the project itself.</p>`;
  }

  function setupProjectDetailNavigation() {
    const nav = document.querySelector('[data-project-detail-nav]');
    if (!nav) return;
    const links = [...nav.querySelectorAll('a[href^="#"]')];
    const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
    const setActive = id => {
      links.forEach(link => link.classList.toggle('is-active', link.getAttribute('href') === '#' + id));
    };
    links.forEach(link => link.addEventListener('click', event => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior:'smooth', block:'start' });
      history.replaceState(null, '', window.location.pathname + window.location.search + link.getAttribute('href'));
      setActive(target.id);
    }));
    if (!sections.length || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(entries => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a,b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible?.target?.id) setActive(visible.target.id);
    }, { rootMargin:'-28% 0px -58% 0px', threshold:[0.05,0.25,0.5] });
    sections.forEach(section => observer.observe(section));
    setActive(sections[0].id);
  }

  function renderProjectDetail() {
    const projectId = App.getQueryParam('id');
    const project = Resolver.getEntity('project', projectId);
    if (!project) {
      setView(`<div class="view-intro"><div><span class="eyebrow">Project detail</span><h2>Project not found</h2><p>Select a project from the project database.</p></div></div><a class="button" href="market.html?view=projects">Back to Projects</a>`);
      return;
    }

    const intelligence = projectIntelligence(project);
    const obsRows = [...(intelligence?.direct?.marketObservations || [])]
      .sort((a,b)=>String(b.period || b.source_date || '').localeCompare(String(a.period || a.source_date || '')));
    const latestObs = obsRows[0] || null;
    const listingRows = [...(intelligence?.direct?.listingObservations || [])]
      .sort((a,b)=>String(a.observation_date || '').localeCompare(String(b.observation_date || '')));
    const listing = listingRows.at(-1) || null;
    const phases = data.phases.filter(item => item.project_id === project.id);
    const relatedArticles = [...(intelligence?.direct?.articles || [])]
      .filter(item => (item.project_ids || []).includes(project.id))
      .sort((a,b)=>String(b.published_at || '').localeCompare(String(a.published_at || '')));
    const dev = leadDeveloper(project);

    const verifiedRows = obsRows.length
      ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Period</th><th class="numeric">ASP</th><th class="numeric">Absorption</th><th>Basis</th><th>Source</th></tr></thead><tbody>${obsRows.map(row=>`<tr><td>${esc(row.period)}</td><td class="numeric">${esc(formatAsp(row.average_asp))}</td><td class="numeric">${esc(formatPercent(row.absorption_rate))}</td><td>${esc(row.price_basis?.replaceAll('-',' ') || '—')}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td></tr>`).join('')}</tbody></table></div>`
      : '<div class="state-box">No verified project-level market observations are available.</div>';

    const html = `
      <div class="project-detail-head">
        <div>
          <div class="project-detail-breadcrumb"><a href="market.html?view=projects">Projects</a><span>›</span><span>${esc(project.name)}</span></div>
          <span class="eyebrow">Project intelligence</span>
          <h2>${esc(project.name)}</h2>
          <p>${esc(project.location_text)} · ${esc(developerName(project))}</p>
          <div class="chip-row">${Components.statusBadge(project.status)}${(project.segment_ids || []).map(id=>`<span class="relation-chip">${esc(id.replaceAll('-',' '))}</span>`).join('')}</div>
        </div>
        <div class="project-detail-actions">
          ${project.official_url ? `<a class="button" href="${esc(project.official_url)}" target="_blank" rel="noopener noreferrer">Official source</a>` : ''}
          <a class="button" href="research.html?type=project&ids=${encodeURIComponent(project.id)}">Open Research</a>
        </div>
      </div>

      <div class="market-metric-grid project-detail-metrics">
        ${Components.compactMetric({label:'Planned units',value:Number.isFinite(project.planned_units) ? formatCompact(project.planned_units) : '—',note:project.known_units_note || 'No exact comparable count published'})}
        ${Components.compactMetric({label:'Area',value:formatArea(project.total_area_sqm)})}
        ${Components.compactMetric({label:'Verified ASP',value:formatAsp(latestObs?.average_asp),note:latestObs?.period || 'No project-level observation'})}
        ${Components.compactMetric({label:'Listing asking',value:formatListingRange(listing),note:listing?.observation_date || 'No listing snapshot'})}
      </div>

      <nav class="project-detail-nav" data-project-detail-nav aria-label="Project sections">
        <a href="#project-overview">Tổng quan</a>
        <a href="#project-pricing">Giá &amp; lịch sử</a>
        <a href="#project-updates">Tin tức</a>
        <a href="#project-legal">Pháp lý</a>
        <a href="#project-infrastructure">Hạ tầng</a>
        <a href="#project-context">Bối cảnh</a>
        <a href="#project-phases">Phân kỳ</a>
      </nav>

      ${projectIntelligenceSummaryHTML(intelligence)}

      <div class="project-detail-grid" id="project-overview">
        <section class="section project-detail-main">
          <div class="section-header"><div><span class="eyebrow">Project profile</span><h2 class="section-title">Overview</h2></div></div>
          <div class="section-body"><p>${esc(project.summary)}</p>
            <div class="project-detail-facts">
              <div><span>Developer</span><strong>${esc(dev?.name || '—')}</strong></div>
              <div><span>Location</span><strong>${esc(project.location_text || '—')}</strong></div>
              <div><span>Segments</span><strong>${esc((project.segment_ids || []).map(x=>x.replaceAll('-',' ')).join(', ') || '—')}</strong></div>
              <div><span>Latest linked activity</span><strong>${projectActivityDate(project.id) ? esc(App.formatDate(projectActivityDate(project.id))) : '—'}</strong></div>
            </div>
          </div>
        </section>

        <aside class="section project-detail-side">
          <div class="section-header"><h2 class="section-title">Data Sources</h2></div>
          <div class="section-body">
            <div class="provenance-inline-row">${sourceRef(project.primary_source_id,{sourceUrl:project.official_url,sourceDate:project.source_date})}<span class="muted-text">Project entity</span></div>
            ${latestObs ? `<div class="provenance-inline-row">${sourceRef(latestObs.source_id,{sourceDate:latestObs.source_date,period:latestObs.period,methodology:latestObs.methodology_note,sourceUrl:latestObs.source_url})}<span class="muted-text">Verified project market data</span></div>` : ''}
            ${listing ? `<div class="provenance-inline-row">${sourceRef(listing.source_id,{sourceDate:listing.observation_date,sourceUrl:listing.source_url,methodology:listing.methodology_note})}<span class="muted-text">Listing asking market</span></div>` : ''}
          </div>
        </aside>
      </div>

      <section class="section project-detail-anchor" id="project-pricing">
        <div class="section-header"><div><span class="eyebrow">Secondary market</span><h2 class="section-title">Listing Price History</h2></div><span class="section-meta">${listingRows.length} snapshot${listingRows.length===1?'':'s'}</span></div>
        <div class="section-body">${projectDetailListingHistory(project)}</div>
      </section>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Source-stated project metrics</span><h2 class="section-title">Verified Pricing &amp; Sales Evidence</h2></div></div>
        <div class="section-body section-body--table">${verifiedRows}</div>
      </section>

      <div class="project-detail-grid project-detail-anchor" id="project-updates">
        <section class="section project-detail-main">
          <div class="section-header"><div><span class="eyebrow">Evidence timeline</span><h2 class="section-title">Official &amp; Research Updates</h2></div></div>
          <div class="section-body">
            <div class="article-list article-list--embedded">${relatedArticles.map(article=>`<article class="article-row"><div class="article-row__date">${esc(App.formatDate(article.published_at))}</div><div><div class="article-row__meta"><span class="source-tag">${esc(article.content_type)}</span>${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}</div><h3><a class="article-title-link" href="${esc(article.url)}" target="_blank" rel="noopener noreferrer">${esc(article.title)}</a></h3><p>${esc(article.summary)}</p></div></article>`).join('') || '<div class="state-box">No project-linked market updates yet.</div>'}</div>
          </div>
        </section>

        <aside class="project-detail-stack">
          <section class="section project-detail-anchor" id="project-legal">
            <div class="section-header"><div><span class="eyebrow">Contextual evidence</span><h2 class="section-title">Legal Research</h2></div><a class="text-link" href="legal.html?view=documents">Open Legal</a></div>
            <div class="section-body">${projectLegalEvidenceHTML(intelligence, project)}</div>
          </section>

          <section class="section project-detail-anchor" id="project-infrastructure">
            <div class="section-header"><div><span class="eyebrow">Direct project links</span><h2 class="section-title">Infrastructure</h2></div><a class="text-link" href="infrastructure.html?view=projects">Open Infrastructure</a></div>
            <div class="section-body">${projectInfrastructureEvidenceHTML(intelligence)}</div>
          </section>
        </aside>
      </div>

      <section class="section project-detail-anchor" id="project-context">
        <div class="section-header"><div><span class="eyebrow">Contextual intelligence</span><h2 class="section-title">Regional Market &amp; Macro Context</h2></div></div>
        <div class="section-body">${projectContextHTML(intelligence)}</div>
      </section>

      <section class="section project-detail-anchor" id="project-phases">
        <div class="section-header"><div><span class="eyebrow">Development structure</span><h2 class="section-title">Phases</h2></div></div>
        <div class="section-body"><div class="project-phase-grid">${phases.map(item=>`<article><div><strong>${esc(item.name)}</strong><span>${esc(String(item.phase_type || '').replaceAll('-',' '))}</span></div>${Components.statusBadge(item.status)}${item.known_units_note ? `<p>${esc(item.known_units_note)}</p>` : ''}</article>`).join('') || '<p class="muted-text">No phase records yet.</p>'}</div></div>
      </section>`;
    setView(html);
    requestAnimationFrame(() => {
      renderProjectDetailListingChart(project.id);
      setupProjectDetailNavigation();
      if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target) target.scrollIntoView({ block:'start' });
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
    const allRows = data.observations
      .filter(item => item.scope_type === 'region-segment' && (item.region_ids || []).includes(region) && (item.segment_ids || []).includes(segment))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)) || marketSourceLabel(a.source_id).localeCompare(marketSourceLabel(b.source_id)));
    const sourceIds = [...new Set(allRows.map(item => item.source_id).filter(Boolean))];
    if (!state.source || !sourceIds.includes(state.source)) {
      state.source = preferredMarketSource(allRows);
      if (state.source) App.setQueryParam('source', state.source);
      else App.removeQueryParam('source');
    }
    const rows = state.source ? allRows.filter(item => item.source_id === state.source) : allRows;
    const latest = rows[rows.length - 1] || null;
    const hasApproximateMetrics = rows.some(row => Object.values(row.metric_qualifiers || {}).includes('approx') || Number.isFinite(row.new_supply_lower_bound));
    const sourceOptions = sourceIds.map(id => option(marketSourceLabel(id), id, state.source)).join('');
    const sourceControl = `
      <label class="filter-field market-source-filter">
        <span>Source</span>
        <select data-filter="source">${sourceOptions || option('No source','',state.source)}</select>
      </label>`;
    const comparisonRows = [...allRows].sort((a,b) => String(b.period).localeCompare(String(a.period)) || marketSourceLabel(a.source_id).localeCompare(marketSourceLabel(b.source_id)));
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Published observations</span><h2>Supply &amp; Sales</h2><p>Metrics are source-specific. Select one research source for the chart; the comparison table keeps multiple sources for the same period visible without blending them.</p></div></div>
      ${filterToolbar({ includeDeveloper:false, includeSegment:true, includeStatus:false })}
      <div class="market-source-toolbar">${sourceControl}<p>Chart source: <strong>${esc(marketSourceLabel(state.source))}</strong>. Values from different research houses are not averaged or merged.</p></div>
      <section class="section"><div class="section-header"><h2 class="section-title">${esc(regionObj?.name || 'Selected Region')} · ${esc(segment.replaceAll('-',' '))}</h2></div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="market-supply-sales"></canvas></div><p class="chart-note">Selected source: ${latest ? sourceRef(latest.source_id,{sourceDate:latest.source_date,period:latest.period,sourceUrl:latest.source_url,methodology:latest.methodology_note}) : '—'}${hasApproximateMetrics ? ' · ≈ / > retain the wording precision published by the source.' : ''}</p></div></section>
      <section class="section"><div class="section-header"><h2 class="section-title">Selected Source History</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Period</th><th class="numeric">New Supply</th><th class="numeric">Sales</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th><th>Source</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(row.period)}</td><td class="numeric">${esc(formatMarketMetric(row,'new_supply'))}</td><td class="numeric">${esc(formatMarketMetric(row,'sales_units'))}</td><td class="numeric">${esc(formatMarketMetric(row,'absorption_rate'))}</td><td class="numeric">${esc(formatMarketMetric(row,'average_asp'))}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td></tr>`).join('') || '<tr><td colspan="6" class="table-empty">No observations for this source.</td></tr>'}</tbody></table></div></div></section>
      <section class="section"><div class="section-header"><div><span class="eyebrow">Cross-source evidence</span><h2 class="section-title">Source Comparison</h2></div></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table data-table--market-source-comparison"><thead><tr><th>Period</th><th>Research Source</th><th class="numeric">New Supply</th><th class="numeric">Sales</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th></tr></thead><tbody>${comparisonRows.map(row=>`<tr class="${row.source_id === state.source ? 'is-selected-source' : ''}"><td>${esc(row.period)}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td><td class="numeric">${esc(formatMarketMetric(row,'new_supply'))}</td><td class="numeric">${esc(formatMarketMetric(row,'sales_units'))}</td><td class="numeric">${esc(formatMarketMetric(row,'absorption_rate'))}</td><td class="numeric">${esc(formatMarketMetric(row,'average_asp'))}</td></tr>`).join('') || '<tr><td colspan="6" class="table-empty">No comparable source observations for this region and segment.</td></tr>'}</tbody></table></div><p class="chart-note">Source methodologies may differ. Comparison is side-by-side only; no cross-source averaging is performed.</p></div></section>`;
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
      <section class="section"><div class="section-header"><h2 class="section-title">Market Benchmarks</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Market</th><th>Period</th><th class="numeric">New Supply</th><th class="numeric">Transactions</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th><th>Source</th></tr></thead><tbody>${benchmarkRows.map(row=>`<tr><td>HCMC · Apartment</td><td>${esc(row.period)}</td><td class="numeric">${esc(formatMarketMetric(row,'new_supply'))}</td><td class="numeric">${esc(formatMarketMetric(row,'sales_units'))}</td><td class="numeric">${esc(formatMarketMetric(row,'absorption_rate'))}</td><td class="numeric">${esc(formatMarketMetric(row,'average_asp'))}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note,sourceUrl:row.source_url})}</td></tr>`).join('') || '<tr><td colspan="7" class="table-empty">No market benchmark records.</td></tr>'}</tbody></table></div></div></section>`;
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
    if (!window.MarketNewsUI) {
      setView(Components.stateBox('News presentation module is unavailable.', 'error'));
      return;
    }
    setView(window.MarketNewsUI.render({
      articles: data.articles,
      regions: data.regions,
      developers: data.developers,
      state
    }));
    window.MarketNewsUI.bind({ state, refresh: renderNews });
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
    ChartTools.destroy('market-project-listing-history');
    if (state.view === 'projects') renderProjects();
    else if (state.view === 'project-detail') renderProjectDetail();
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
      ['q','region','developer','segment','status','sort','source'].forEach(key => {
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
        <div class="drawer-actions"><a class="button" href="market.html?view=project-detail&id=${encodeURIComponent(project.id)}">Xem chi tiết dự án</a><a class="button" href="research.html?type=project&ids=${encodeURIComponent(project.id)}">Open Research</a></div>
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
      if (state.view !== 'project-detail' && projectId) openProject(projectId, { push:false });
      else App.closeDrawer();
    });
  }

  async function load() {
    try {
      await window.Provenance?.load?.();
      const [regions, developers, projects, phases, observations, listingObservations, listingComparables, articles, infrastructureProjects, infrastructureSchedules, legalTopics, legalDocuments, events, macroIndicators, macroRows, meta] = await Promise.all([
        DataStore.getRegions(), DataStore.getDevelopers(), DataStore.getProjects(), DataStore.getProjectPhases(), DataStore.getMarketObservations(), DataStore.getListingObservations(), DataStore.getListingComparables(), DataStore.getArticles(), DataStore.getInfrastructureProjects(), DataStore.getInfrastructureSchedules(), DataStore.getLegalTopics(), DataStore.getLegalDocuments(), DataStore.getEvents(), DataStore.getMacroIndicators(), DataStore.getProcessedMacroObservations(), DataStore.getMeta()
      ]);
      data = {
        regions: payloadData(regions), developers: payloadData(developers), projects: payloadData(projects), phases: payloadData(phases), observations: payloadData(observations), listingObservations: payloadData(listingObservations), listingComparables: payloadData(listingComparables), articles: payloadData(articles).filter(item => item.category === 'market'), allArticles: payloadData(articles), infrastructureProjects: payloadData(infrastructureProjects), infrastructureSchedules: payloadData(infrastructureSchedules), legalTopics: payloadData(legalTopics), legalDocuments: payloadData(legalDocuments), events: payloadData(events), macroIndicators: payloadData(macroIndicators), macroRows: payloadData(macroRows)
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
