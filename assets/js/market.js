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
    sort: 'latest'
  };
  let data = { regions: [], developers: [], projects: [], phases: [], observations: [], articles: [], infrastructureProjects: [] };

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

  function projectActivityDate(projectId) {
    const article = data.articles
      .filter(item => (item.project_ids || []).includes(projectId))
      .sort((a,b) => String(b.published_at).localeCompare(String(a.published_at)))[0];
    return article?.published_at || null;
  }

  function developerName(project) {
    return Resolver.getLabel('developer', project.lead_developer_id);
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
    const selling = projects.filter(item => item.status === 'selling').length;
    const latestObs = data.observations.filter(item => item.scope_type === 'project' && item.average_asp);
    const avgAsp = latestObs.length ? latestObs.reduce((sum, item) => sum + item.average_asp, 0) / latestObs.length : null;
    const totalUnits = projects.reduce((sum, item) => sum + (item.planned_units || 0), 0);
    return [
      { label: 'Tracked Projects', value: String(projects.length), note: 'Demo database' },
      { label: 'Currently Selling', value: String(selling), note: 'Current master status' },
      { label: 'Planned Units', value: formatCompact(totalUnits), note: 'Across tracked projects' },
      { label: 'Avg. Project ASP', value: formatAsp(avgAsp), note: 'Latest available demo observations' }
    ];
  }

  function hcmcSeries() {
    return data.observations
      .filter(item => item.scope_type === 'region-segment' && (item.region_ids || []).includes('hcmc') && (item.segment_ids || []).includes('apartment'))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)));
  }

  function priceSeries(projectIds = ['izumi-city','waterpoint','akari-city']) {
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
      return `
        <tr>
          <td><button class="table-link" type="button" data-project-id="${esc(project.id)}">${esc(project.name)}</button><span class="table-subtext">${esc(project.location_text)}</span></td>
          <td>${esc(developerName(project))}</td>
          <td>${esc(regionNames(project))}</td>
          <td>${Components.statusBadge(project.status)}</td>
          <td class="numeric">${esc(formatCompact(project.planned_units))}</td>
          <td class="numeric">${esc(formatAsp(obs?.average_asp))}<span class="table-subtext">${esc(obs?.period || '')}</span></td>
          <td class="numeric">${esc(formatPercent(obs?.absorption_rate))}</td>
        </tr>`;
    }).join('');
    return `
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Project</th><th>Developer</th><th>Region</th><th>Status</th><th class="numeric">Units</th><th class="numeric">Latest ASP</th><th class="numeric">Absorption</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="7" class="table-empty">No projects match the selected filters.</td></tr>'}</tbody>
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
          <div class="section-body"><div class="chart-frame"><canvas id="market-overview-supply"></canvas></div><p class="chart-note">Illustrative quarterly units · ${sourceRef(overviewMarketSource?.source_id,{sourceDate:overviewMarketSource?.source_date,period:overviewMarketSource?.period})}</p></div>
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
        <div class="section-header"><div><span class="eyebrow">Selected projects</span><h2 class="section-title">ASP Trend</h2></div><a class="text-link" href="market.html?view=pricing">Open Pricing</a></div>
        <div class="section-body"><div class="chart-frame"><canvas id="market-overview-price"></canvas></div><p class="chart-note">Primary asking price · mn VND/m² · illustrative values only · ${sourceRef(overviewPriceSource?.source_id,{sourceDate:overviewPriceSource?.source_date,period:overviewPriceSource?.period})}</p></div>
      </section>`;
    setView(html);
    requestAnimationFrame(() => {
      ChartTools.renderSupplySales('market-overview-supply', overviewMarketRows);
      ChartTools.renderPriceTrend('market-overview-price', priceSeries());
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
    if (!state.region) {
      state.region = 'hcmc';
      App.setQueryParam('region', 'hcmc');
    }
    const region = state.region;
    const regionObj = Resolver.getEntity('region', region);
    const rows = data.observations
      .filter(item => item.scope_type === 'region-segment' && (item.region_ids || []).includes(region))
      .sort((a,b) => String(a.period).localeCompare(String(b.period)));
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Historical observations</span><h2>Supply &amp; Sales</h2><p>Quarterly demo observations by region. Missing values remain null rather than being converted to zero.</p></div></div>
      ${filterToolbar({ includeDeveloper:false, includeSegment:false, includeStatus:false })}
      <section class="section"><div class="section-header"><h2 class="section-title">${esc(regionObj?.name || 'Selected Region')} · Supply vs Sales</h2></div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="market-supply-sales"></canvas></div><p class="chart-note">Source: ${rows.length ? sourceRef(rows[rows.length-1].source_id,{sourceDate:rows[rows.length-1].source_date,period:rows[rows.length-1].period}) : '—'}</p></div></section>
      <section class="section"><div class="section-header"><h2 class="section-title">Observation History</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Period</th><th class="numeric">New Supply</th><th class="numeric">Sales</th><th class="numeric">Absorption</th><th class="numeric">Average ASP</th><th>Source</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(row.period)}</td><td class="numeric">${esc(formatCompact(row.new_supply))}</td><td class="numeric">${esc(formatCompact(row.sales_units))}</td><td class="numeric">${esc(formatPercent(row.absorption_rate))}</td><td class="numeric">${esc(formatAsp(row.average_asp))}</td><td>${sourceRef(row.source_id,{sourceDate:row.source_date,period:row.period,methodology:row.methodology_note})}</td></tr>`).join('') || '<tr><td colspan="6" class="table-empty">No observations for this region.</td></tr>'}</tbody></table></div></div></section>`;
    setView(html);
    bindFilters();
    requestAnimationFrame(() => ChartTools.renderSupplySales('market-supply-sales', rows));
  }

  function renderPricing() {
    const selectedProjects = projectFilter(data.projects).filter(item => latestProjectObservation(item.id)?.average_asp).slice(0,5);
    const series = priceSeries(selectedProjects.map(item => item.id));
    const latestRows = selectedProjects.map(project => ({ project, obs: latestProjectObservation(project.id) }));
    const html = `
      <div class="view-intro"><div><span class="eyebrow">Comparable price observations</span><h2>Pricing</h2><p>Primary asking prices are kept separate from other price bases; the demo chart only compares compatible mn VND/m² display observations.</p></div></div>
      ${filterToolbar({ includeStatus:false })}
      <section class="section"><div class="section-header"><h2 class="section-title">Selected Project ASP Trend</h2></div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="market-pricing"></canvas></div><p class="chart-note">Up to five filtered projects · primary asking price · illustrative values · ${latestRows[0]?.obs ? sourceRef(latestRows[0].obs.source_id,{sourceDate:latestRows[0].obs.source_date,period:latestRows[0].obs.period}) : "—"}</p></div></section>
      <section class="section"><div class="section-header"><h2 class="section-title">Latest Pricing Snapshot</h2></div><div class="section-body section-body--table"><div class="table-wrap"><table class="data-table"><thead><tr><th>Project</th><th>Region</th><th>Period</th><th class="numeric">ASP</th><th>Basis</th><th>Source</th></tr></thead><tbody>${latestRows.map(({project,obs})=>`<tr><td><button class="table-link" data-project-id="${esc(project.id)}" type="button">${esc(project.name)}</button></td><td>${esc(regionNames(project))}</td><td>${esc(obs?.period || '—')}</td><td class="numeric">${esc(formatAsp(obs?.average_asp))}</td><td>${esc(obs?.price_basis?.replaceAll('-',' ') || '—')}</td><td>${obs ? sourceRef(obs.source_id,{sourceDate:obs.source_date,period:obs.period,methodology:obs.methodology_note}) : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="table-empty">No comparable pricing records.</td></tr>'}</tbody></table></div></div></section>`;
    setView(html);
    bindFilters();
    requestAnimationFrame(() => ChartTools.renderPriceTrend('market-pricing', series));
  }

  function renderDevelopers() {
    const cards = data.developers.map(dev => {
      const projects = data.projects.filter(project => (project.developer_ids || []).includes(dev.id));
      const selling = projects.filter(project => project.status === 'selling').length;
      return `<article class="developer-card">
        <div><span class="eyebrow">Developer</span><h3>${esc(dev.name)}</h3><p>${esc(dev.summary)}</p></div>
        <div class="developer-card__stats"><span><strong>${projects.length}</strong> tracked projects</span><span><strong>${selling}</strong> selling</span></div>
        <a class="text-link" href="market.html?view=projects&developer=${encodeURIComponent(dev.id)}">View projects</a>
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
        return `<article class="article-row"><div class="article-row__date">${esc(App.formatDate(article.published_at))}</div><div><div class="article-row__meta"><span class="source-tag">${esc(article.content_type)}</span>${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}<span>${esc(projectNames || Resolver.getEntities('region', article.region_ids || []).map(item=>item.short_name || item.name).join(' · '))}</span></div><h3>${esc(article.title)}</h3><p>${esc(article.summary)}</p></div></article>`;
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
      </div>
      <div class="drawer-metrics">
        ${Components.compactMetric({label:'Planned units',value:formatCompact(project.planned_units)})}
        ${Components.compactMetric({label:'Area',value:formatArea(project.total_area_sqm)})}
        ${Components.compactMetric({label:'Latest ASP',value:formatAsp(obs?.average_asp),note:obs?.period || ''})}
        ${Components.compactMetric({label:'Absorption',value:formatPercent(obs?.absorption_rate),note:obs?.period || ''})}
      </div>
      <div class="drawer-section"><h3>Overview</h3><p>${esc(project.summary)}</p></div>
      <div class="drawer-section"><h3>Segments</h3><div class="chip-row">${(project.segment_ids || []).map(id=>`<span class="relation-chip">${esc(id.replaceAll('-',' '))}</span>`).join('')}</div></div>
      <div class="drawer-section"><h3>Phases</h3>${phases.length ? phases.map(item=>`<div class="drawer-list-row"><div><strong>${esc(item.name)}</strong><span>${esc(item.phase_type.replaceAll('-',' '))}</span></div>${Components.statusBadge(item.status)}</div>`).join('') : '<p class="muted-text">No phase records yet.</p>'}</div>
      <div class="drawer-section"><h3>Related Infrastructure</h3>${relatedInfrastructure.length ? relatedInfrastructure.map(item=>`<div class="drawer-list-row"><div><strong>${esc(item.name)}</strong><span>${esc(item.location_text || '')}</span></div><a class="text-link" href="infrastructure.html?view=projects&project=${encodeURIComponent(item.id)}">Open</a></div>`).join('') : '<p class="muted-text">No direct infrastructure links in the demo dataset.</p>'}</div>
      <div class="drawer-section"><h3>Data Provenance</h3>${obs ? `<div class="provenance-inline-row">${sourceRef(obs.source_id,{sourceDate:obs.source_date,period:obs.period,methodology:obs.methodology_note})}<span class="muted-text">Latest displayed market observation · ${esc(obs.period || '')}</span></div>` : '<p class="muted-text">No market observation source available.</p>'}</div>
      <div class="drawer-section"><h3>Recent Evidence</h3>${relatedArticles.length ? relatedArticles.map(item=>`<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(item.published_at))} · ${sourceRef(item.source_id,{publishedAt:item.published_at,sourceUrl:item.url})}</span><strong>${esc(item.title)}</strong></div>`).join('') : '<p class="muted-text">No related articles.</p>'}</div>
      <div class="drawer-section"><a class="text-link" href="market.html?view=news&q=${encodeURIComponent(project.name)}">View related market news</a></div>`;
  }

  function openProject(projectId, { push = true } = {}) {
    const project = Resolver.getEntity('project', projectId);
    if (!project) return;
    if (push) App.setQueryParam('project', projectId, { push: true });
    App.openDrawer({ title: project.name, html: projectDrawerHTML(project) });
  }

  function syncDrawerFromURL() {
    const projectId = App.getQueryParam('project');
    if (projectId) openProject(projectId, { push: false });
    else App.closeDrawer();
  }

  function bindDelegatedEvents() {
    document.addEventListener('click', event => {
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
      const [regions, developers, projects, phases, observations, articles, infrastructureProjects, meta] = await Promise.all([
        DataStore.getRegions(), DataStore.getDevelopers(), DataStore.getProjects(), DataStore.getProjectPhases(), DataStore.getMarketObservations(), DataStore.getArticles(), DataStore.getInfrastructureProjects(), DataStore.getMeta()
      ]);
      data = {
        regions: payloadData(regions), developers: payloadData(developers), projects: payloadData(projects), phases: payloadData(phases), observations: payloadData(observations), articles: payloadData(articles).filter(item => item.category === 'market'), infrastructureProjects: payloadData(infrastructureProjects)
      };
      Resolver.setData('region', data.regions);
      Resolver.setData('developer', data.developers);
      Resolver.setData('project', data.projects);
      Resolver.setData('infrastructure-project', data.infrastructureProjects);
      parseState();
      const updated = document.querySelector('[data-market-updated]');
      if (updated) updated.textContent = meta?.last_successful_build ? `Demo data · ${App.formatDate(meta.last_successful_build)}` : 'Demo data';
      render();
      const projectId = App.getQueryParam('project');
      if (projectId) openProject(projectId, { push:false });
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load Market demo data. Check that the site is running through a web server.', 'error'));
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindDelegatedEvents();
    load();
  });
})();
