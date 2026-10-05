(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'rates', 'fx', 'gold', 'liquidity', 'inflation', 'news'];
  const VIEW_SERIES = {
    rates: ['deposit-rate-12m-average', 'lending-rate-average', 'interbank-on', 'policy-refinancing-rate'],
    fx: ['usd-vnd-central-rate', 'usd-vnd-bank-sell'],
    gold: ['sjc-gold-sell', 'sjc-gold-buy', 'global-gold-usd-oz'],
    liquidity: ['interbank-on', 'credit-growth-ytd', 'm2-growth-yoy'],
    inflation: ['cpi-yoy', 'cpi-mom', 'core-cpi-yoy']
  };
  const DEFAULT_SERIES = {
    rates: 'deposit-rate-12m-average', fx: 'usd-vnd-central-rate', gold: 'sjc-gold-sell',
    liquidity: 'credit-growth-ytd', inflation: 'cpi-yoy'
  };
  const CATEGORY_VIEW = {
    'interest-rate': 'rates', 'banking-liquidity': 'liquidity', credit: 'liquidity', 'money-supply': 'liquidity',
    fx: 'fx', gold: 'gold', inflation: 'inflation'
  };
  const PRODUCTION_INDICATORS = new Map([
    ['cpi-yoy', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['cpi-mom', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['core-cpi-yoy', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['usd-vnd-central-rate', { unit: 'vnd-per-usd', evidenceStatus: 'corroborated', sources: ['banking-times-vn', 'vna-vietnamplus'] }],
    ['sjc-gold-buy', { unit: 'vnd-per-tael', evidenceStatus: 'corroborated', sources: ['baonghean-gold', 'vietnamnet-gold'] }],
    ['sjc-gold-sell', { unit: 'vnd-per-tael', evidenceStatus: 'corroborated', sources: ['baonghean-gold', 'vietnamnet-gold'] }]
  ]);
  const PRODUCTION_INDICATOR_OVERRIDES = {
    'cpi-yoy': {
      default_source_id: 'nso-vietnam',
      description: 'Year-on-year change in Vietnam Consumer Price Index (CPI).',
      methodology_note: 'Canonical observations are promoted only from verified official NSO releases. Historical periods appear only after they pass the controlled production gate.'
    },
    'cpi-mom': {
      default_source_id: 'nso-vietnam',
      description: 'Month-on-month change in Vietnam Consumer Price Index (CPI).',
      methodology_note: 'Canonical observations are promoted only from verified official NSO releases. Historical periods appear only after they pass the controlled production gate.'
    },
    'core-cpi-yoy': {
      default_source_id: 'nso-vietnam',
      description: 'Year-on-year change in Vietnam core consumer-price inflation.',
      methodology_note: 'Canonical observations are promoted only from verified official NSO releases. Historical periods appear only after they pass the controlled production gate.'
    },
    'usd-vnd-central-rate': {
      description: 'State Bank of Vietnam central USD/VND reference rate.',
      methodology_note: 'Controlled production observations require at least two independent trusted sources to agree within the configured tolerance when the direct SBV endpoint is unavailable.'
    },
    'sjc-gold-buy': {
      description: 'Domestic SJC gold-bar buying price in VND per tael.',
      methodology_note: 'Controlled production observations require at least two independent public price sources to agree within the configured tolerance.'
    },
    'sjc-gold-sell': {
      description: 'Domestic SJC gold-bar selling price in VND per tael.',
      methodology_note: 'Controlled production observations require at least two independent public price sources to agree within the configured tolerance.'
    }
  };

  let state = { view: 'overview', range: '1Y', series: '', q: '', indicatorFilter: '' };
  let data = { indicators: [], observations: [], articles: [], events: [] };
  let productionState = { active: false, recordCount: 0, indicatorIds: new Set(), rows: [], publishMeta: null };

  function payloadData(payload) { return payload?.data || []; }

  function validProductionRows(payload, publishMeta) {
    if (!payload || !publishMeta) return [];
    if (payload.repository_publish !== true || payload.production_write !== true || publishMeta.repository_publish !== true) return [];
    if (!Array.isArray(payload.data)) return [];
    if (Number.isFinite(Number(publishMeta.final_record_count)) && Number(publishMeta.final_record_count) !== payload.data.length) return [];

    return payload.data.filter(row => {
      const rule = PRODUCTION_INDICATORS.get(row?.indicator_id);
      return rule
        && row.unit === rule.unit
        && rule.sources.includes(row.source_id)
        && row.evidence_status === rule.evidenceStatus
        && row.observation_status === 'final'
        && typeof row.period === 'string'
        && row.period.length > 0
        && Number.isFinite(Number(row.value));
    });
  }

  function integrateMacroObservations(mockPayload, productionPayload, publishMeta) {
    const mockRows = payloadData(mockPayload).map(row => ({ ...row, _data_layer: 'demo' }));
    const productionRows = validProductionRows(productionPayload, publishMeta).map(row => ({ ...row, _data_layer: 'production' }));
    const productionIndicatorIds = new Set(productionRows.map(row => row.indicator_id));

    // Never mix illustrative and canonical history inside the same indicator series.
    // Once an indicator has at least one approved production record, its demo series
    // is removed entirely and only controlled production observations are rendered.
    const retainedMockRows = mockRows.filter(row => !productionIndicatorIds.has(row.indicator_id));
    return {
      rows: [...retainedMockRows, ...productionRows],
      productionRows,
      productionIndicatorIds
    };
  }

  function applyProductionIndicatorMetadata(indicators, productionIndicatorIds) {
    return indicators.map(item => productionIndicatorIds.has(item.id)
      ? { ...item, ...(PRODUCTION_INDICATOR_OVERRIDES[item.id] || {}) }
      : item);
  }
  function esc(value) { return Components.escapeHTML(value); }
  function sourceRef(sourceId, context = {}) {
    return window.Provenance?.sourceButton?.(sourceId, context) || `<span class="source-tag">${esc(labelize(sourceId))}</span>`;
  }
  function indicator(id) { return Resolver.getEntity('macro-indicator', id); }
  function labelize(value) { return String(value || '—').replaceAll('-', ' ').replace(/\b\w/g, c => c.toUpperCase()); }

  function productionEvidenceLabel(row) {
    if (row?._data_layer !== 'production') return '';
    if (row.evidence_status === 'verified') return 'Canonical';
    if (row.evidence_status === 'corroborated') return 'Corroborated';
    return 'Production';
  }

  function dataLayerBadge(ind, row) {
    return row?._data_layer === 'production' ? productionEvidenceLabel(row) : labelize(ind?.frequency);
  }

  function updateStatusBanner() {
    const title = document.querySelector('[data-macro-status-title]');
    const text = document.querySelector('[data-macro-status-text]');
    if (!title || !text) return;
    if (!productionState.active) {
      title.textContent = 'Implementation demo.';
      text.textContent = 'No controlled production observations are available. All displayed macro series are illustrative demo data.';
      return;
    }
    title.textContent = 'Controlled production mode.';
    text.textContent = 'Production observations are labeled by evidence status: verified official data as Canonical and independently matched data as Corroborated. Unpromoted indicators remain illustrative demo data.';
  }

  function overviewChartNote(id) {
    const { current } = latestPair(id);
    if (current?._data_layer === 'production') {
      return current.evidence_status === 'corroborated'
        ? 'Corroborated production series · demo points are not mixed into this indicator. Historical coverage will build as new approved observations are persisted.'
        : 'Canonical production series · demo points are not mixed into this indicator. Historical coverage will build as new approved observations are persisted.';
    }
    return 'Illustrative demo series · data date and publication date are stored separately.';
  }

  function corroborationProvenance(row) {
    const ids = Array.isArray(row?.corroboration_source_ids) ? [...new Set(row.corroboration_source_ids)] : [];
    if (row?._data_layer !== 'production' || row.evidence_status !== 'corroborated' || ids.length < 2) return '';
    return `<div class="provenance-inline-row provenance-inline-row--wrap"><span class="source-tag">Corroborated</span>${ids.map(id => sourceRef(id, { period: row.period })).join('')}<span class="muted-text">Matched across independent sources</span></div>`;
  }

  function obsKey(item) { return item.data_date || item.period || ''; }
  function observationsFor(id) {
    return data.observations.filter(item => item.indicator_id === id).sort((a,b) => obsKey(a).localeCompare(obsKey(b)));
  }
  function latestPair(id) {
    const rows = observationsFor(id);
    return { current: rows.at(-1) || null, previous: rows.at(-2) || null };
  }

  function formatNumber(value, digits = 0) {
    return window.Formatters?.number?.(value, { min: digits, max: digits })
      ?? (value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : String(value));
  }

  function formatValue(ind, value, compact = false) {
    if (!ind || value === null || value === undefined) return '—';
    return window.Formatters?.unitValue?.(ind.unit, value, { compact }) ?? formatNumber(value, 2);
  }

  function formatPeriod(obs) {
    if (!obs) return '—';
    if (obs.period_type === 'month' && /^\d{4}-\d{2}$/.test(obs.period || '')) {
      const [y,m] = obs.period.split('-').map(Number);
      return new Intl.DateTimeFormat('en', { month:'short', year:'numeric' }).format(new Date(Date.UTC(y,m-1,1)));
    }
    return App.formatDate(obs.data_date || obs.period);
  }

  function deltaInfo(id) {
    const ind = indicator(id);
    const { current, previous } = latestPair(id);
    if (!current || !previous) return { label:'—', direction:'neutral' };
    const delta = Number(current.value) - Number(previous.value);
    if (ind?.unit === 'percent' || ind?.unit === 'percent-per-year') {
      return { label:`${delta > 0 ? '+' : ''}${delta.toFixed(2)} ppt`, direction: delta > 0 ? 'up' : delta < 0 ? 'down' : 'neutral' };
    }
    const pct = Number(previous.value) ? delta / Number(previous.value) * 100 : null;
    const abs = ind?.unit === 'vnd-per-tael' ? `${delta > 0 ? '+' : ''}${formatNumber(delta/1_000_000, 1)} mn` : `${delta > 0 ? '+' : ''}${formatNumber(delta, ind?.unit === 'usd-per-oz' ? 1 : 0)}`;
    return { label: pct === null ? abs : `${abs} (${pct > 0 ? '+' : ''}${pct.toFixed(2)}%)`, direction: delta > 0 ? 'up' : delta < 0 ? 'down' : 'neutral' };
  }

  function observationDate(row) {
    const raw = row?.data_date || row?.period || '';
    const normalized = /^\d{4}-\d{2}$/.test(raw) ? `${raw}-01` : raw;
    const date = new Date(`${normalized}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function rangeRows(id, range = state.range) {
    const rows = observationsFor(id);
    if (!rows.length || range === 'ALL') return rows;
    const latest = observationDate(rows.at(-1));
    if (!latest) return rows;
    const days = range === '1M' ? 31 : range === '3M' ? 93 : 366;
    const start = new Date(latest); start.setDate(start.getDate() - days);
    return rows.filter(row => {
      const date = observationDate(row);
      return date && date >= start;
    });
  }

  function metricCard(id) {
    const ind = indicator(id); if (!ind) return '';
    const { current } = latestPair(id); const delta = deltaInfo(id);
    return `<button class="macro-metric-card" type="button" data-macro-indicator-id="${esc(id)}">
      <div class="macro-metric-card__top"><span>${esc(ind.name)}</span><span class="source-tag">${esc(dataLayerBadge(ind, current))}</span></div>
      <strong>${esc(formatValue(ind, current?.value, true))}</strong>
      <div class="macro-metric-card__foot"><span class="macro-delta">${esc(delta.label)}</span><span>${esc(formatPeriod(current))}</span></div>
    </button>`;
  }

  function updatedLabel() {
    const meta = document.querySelector('[data-macro-updated]');
    return meta;
  }

  function parseState() {
    const view = App.getQueryParam('view');
    state.view = VALID_VIEWS.includes(view) ? view : 'overview';
    state.range = ['1M','3M','1Y','ALL'].includes(App.getQueryParam('range')) ? App.getQueryParam('range') : '1Y';
    state.series = App.getQueryParam('series') || '';
    state.q = App.getQueryParam('q') || '';
    state.indicatorFilter = App.getQueryParam('indicator-filter') || '';
  }

  function adjustViewFromDeepLink() {
    if (App.getQueryParam('view')) return;
    const deep = indicator(App.getQueryParam('indicator'));
    if (deep) state.view = CATEGORY_VIEW[deep.indicator_category] || 'overview';
  }

  function updateTabs() {
    document.querySelectorAll('[data-macro-tabs] [data-view]').forEach(link => link.classList.toggle('is-active', link.dataset.view === state.view));
  }

  function bindMacroTabs() {
    const tabs = document.querySelector('[data-macro-tabs]');
    if (!tabs || tabs.dataset.bound === 'true') return;
    tabs.dataset.bound = 'true';
    tabs.addEventListener('click', event => {
      const link = event.target.closest('[data-view]');
      if (!link || !tabs.contains(link)) return;
      const nextView = link.dataset.view;
      if (!VALID_VIEWS.includes(nextView)) return;

      // Keep Macro navigation inside the already-loaded runtime. This avoids a full
      // document reload (and any stale cached demo HTML) when moving between tabs.
      event.preventDefault();
      state.view = nextView;
      state.series = '';
      state.q = '';
      state.indicatorFilter = '';
      App.setQueryParam('view', nextView, { push: true });
      App.removeQueryParam('series');
      App.removeQueryParam('q');
      App.removeQueryParam('indicator-filter');
      App.removeQueryParam('indicator');
      App.closeDrawer();
      render();
    });
  }

  function setView(html) {
    const node = document.querySelector('[data-macro-view]');
    if (node) node.innerHTML = html;
  }

  function keyIndicators() {
    return ['usd-vnd-central-rate','sjc-gold-sell','deposit-rate-12m-average','lending-rate-average','credit-growth-ytd','cpi-yoy'];
  }

  function latestEventList(limit = 5) {
    const rows = [...data.events]
      .filter(event => !productionState.indicatorIds.has(event.entity_id))
      .sort((a,b)=>String(b.event_date).localeCompare(String(a.event_date)))
      .slice(0,limit);
    if (!rows.length) return Components.stateBox('No demo developments remain for unpromoted macro indicators.');
    return rows.map(event => {
      const ind = indicator(event.entity_id);
      return `<button class="macro-release-row" type="button" data-macro-indicator-id="${esc(event.entity_id)}"><span>${esc(App.formatDate(event.event_date))}</span><div><span class="source-tag">DEMO</span><span class="source-tag">${esc(labelize(event.event_type))}</span><strong>${esc(event.title)}</strong><small>${esc(ind?.name || '')}</small></div></button>`;
    }).join('');
  }

  function indicatorTable(ids) {
    const rows = ids.map(id => {
      const ind = indicator(id); const {current} = latestPair(id); const delta = deltaInfo(id);
      return `<tr><td><button class="table-link" type="button" data-macro-indicator-id="${esc(id)}">${esc(ind?.name || id)}</button><span class="table-subtext">${esc(labelize(ind?.indicator_category))}</span></td><td class="numeric">${esc(formatValue(ind,current?.value))}</td><td class="numeric">${esc(delta.label)}</td><td>${esc(formatPeriod(current))}<span class="table-subtext">Published ${esc(App.formatDate(current?.published_at))}</span></td><td>${current ? sourceRef(current.source_id,{publishedAt:current.published_at,period:current.period,sourceUrl:current.source_url}) : '—'}</td></tr>`;
    }).join('');
    return `<div class="table-wrap"><table class="data-table data-table--macro"><thead><tr><th>Indicator</th><th class="numeric">Current</th><th class="numeric">Change</th><th>Data Period</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderOverview() {
    const ids = keyIndicators();
    const fxRows = rangeRows('usd-vnd-central-rate','1M');
    setView(`
      <div class="macro-metric-grid">${ids.map(metricCard).join('')}</div>
      <div class="market-layout market-layout--overview">
        <section class="section market-panel market-panel--wide">
          <div class="section-header"><div><span class="eyebrow">Daily monitor</span><h2 class="section-title">USD/VND Central Rate</h2></div><a class="text-link" href="macro.html?view=fx&series=usd-vnd-central-rate&range=1M">Open FX</a></div>
          <div class="section-body"><div class="chart-frame"><canvas id="macro-overview-chart"></canvas></div><p class="chart-note">${esc(overviewChartNote('usd-vnd-central-rate'))}</p></div>
        </section>
        <section class="section market-panel">
          <div class="section-header"><div><span class="eyebrow">Demo context</span><h2 class="section-title">Illustrative Developments</h2></div><a class="text-link" href="macro.html?view=news">View demo news</a></div>
          <div class="section-body macro-release-list">${latestEventList(5)}</div>
        </section>
      </div>
      <section class="section"><div class="section-header"><div><span class="eyebrow">Comparable series</span><h2 class="section-title">Key Indicators</h2></div></div><div class="section-body section-body--table">${indicatorTable(ids)}</div></section>`);
    requestAnimationFrame(() => renderChart('macro-overview-chart','usd-vnd-central-rate',fxRows));
  }

  function viewTitle(view) {
    return ({rates:'Interest Rates',fx:'Foreign Exchange',gold:'Gold',liquidity:'Liquidity, Credit & Money Supply',inflation:'Inflation'})[view] || 'Macro';
  }

  function viewDescription(view) {
    return ({
      rates:'Track deposit, lending, interbank and policy-rate series without mixing publication dates with observation periods.',
      fx:'Compare structured daily USD/VND series and keep each quote definition as a separate indicator.',
      gold:'Monitor domestic and global gold as separate series because their units and market bases differ.',
      liquidity:'Follow interbank liquidity, credit growth and broad money without forcing incompatible units onto one axis.',
      inflation:'Track CPI YoY, CPI MoM and core inflation with the underlying monthly data period preserved.'
    })[view] || '';
  }

  function seriesControls(view, selected) {
    const ids = VIEW_SERIES[view] || [];
    return `<div class="macro-series-toolbar"><label class="filter-field"><span>Indicator</span><select data-series-select>${ids.map(id=>`<option value="${esc(id)}"${id===selected?' selected':''}>${esc(indicator(id)?.name || id)}</option>`).join('')}</select></label><div class="macro-range-group" aria-label="Chart range">${['1M','3M','1Y','ALL'].map(range=>`<button class="macro-range-button${state.range===range?' is-active':''}" type="button" data-range="${range}">${range}</button>`).join('')}</div></div>`;
  }

  function recentObservationTable(id, limit = 12) {
    const ind = indicator(id);
    const rows = [...observationsFor(id)].reverse().slice(0,limit).map(row => `<tr><td>${esc(formatPeriod(row))}<span class="table-subtext">${esc(row.period)}</span></td><td class="numeric">${esc(formatValue(ind,row.value))}</td><td>${esc(labelize(row.observation_status))}</td><td>${esc(App.formatDate(row.published_at))}</td><td>${sourceRef(row.source_id,{publishedAt:row.published_at,period:row.period,sourceUrl:row.source_url})}</td></tr>`).join('');
    return `<div class="table-wrap"><table class="data-table data-table--macro-history"><thead><tr><th>Data Period</th><th class="numeric">Value</th><th>Status</th><th>Published</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderSeriesView(view) {
    const ids = VIEW_SERIES[view] || [];
    let selected = ids.includes(state.series) ? state.series : DEFAULT_SERIES[view];
    if (!selected) selected = ids[0];
    const ind = indicator(selected); const rows = rangeRows(selected);
    const currentSourceRow = latestPair(selected).current;
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Historical series</span><h2>${esc(viewTitle(view))}</h2><p>${esc(viewDescription(view))}</p></div></div>
      <div class="macro-metric-grid macro-metric-grid--section">${ids.map(metricCard).join('')}</div>
      <section class="section"><div class="section-header"><div><span class="eyebrow">${esc(labelize(ind?.frequency))}</span><h2 class="section-title">${esc(ind?.name || '')}</h2></div>${seriesControls(view,selected)}</div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="macro-series-chart"></canvas></div><p class="chart-note">${currentSourceRow ? sourceRef(currentSourceRow.source_id,{publishedAt:currentSourceRow.published_at,period:currentSourceRow.period,sourceUrl:currentSourceRow.source_url}) : "—"} · ${esc(ind?.methodology_note || '')}</p></div></section>
      <section class="section"><div class="section-header"><div><span class="eyebrow">Observation history</span><h2 class="section-title">Recent Data</h2></div><button class="button macro-detail-button" type="button" data-macro-indicator-id="${esc(selected)}">Indicator details</button></div><div class="section-body section-body--table">${recentObservationTable(selected)}</div></section>`);
    bindSeriesControls(view,selected);
    requestAnimationFrame(() => renderChart('macro-series-chart',selected,rows));
  }

  function axisFormatter(ind) {
    if (!ind) return value => String(value);
    return value => window.Formatters?.chartValue?.(ind.unit, value) ?? formatNumber(value, 1);
  }

  function renderChart(canvasId,id,rows) {
    const ind = indicator(id); if (!ind) return;
    ChartTools.renderTimeSeries(canvasId, {
      label: ind.name,
      labels: rows.map(formatPeriod),
      values: rows.map(row => row.value),
      yFormatter: axisFormatter(ind),
      stepped: ind.frequency === 'event-driven'
    });
  }

  function bindSeriesControls(view, selected) {
    document.querySelector('[data-series-select]')?.addEventListener('change', event => {
      state.series = event.target.value; App.setQueryParam('series',state.series); renderSeriesView(view);
    });
    document.querySelectorAll('[data-range]').forEach(button => button.addEventListener('click', () => {
      state.range = button.dataset.range; App.setQueryParam('range',state.range); renderSeriesView(view);
    }));
  }

  function renderNews() {
    let articles = [...data.articles]
      .filter(item => !(item.indicator_ids || []).some(id => productionState.indicatorIds.has(id)))
      .sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at)));
    if (state.indicatorFilter) articles = articles.filter(item => (item.indicator_ids || []).includes(state.indicatorFilter));
    if (state.q) articles = articles.filter(item => FilterEngine.textMatch(item,state.q,['title','summary','tags']));
    const opts = data.indicators.map(ind=>`<option value="${esc(ind.id)}"${state.indicatorFilter===ind.id?' selected':''}>${esc(ind.name)}</option>`).join('');
    setView(`<div class="view-intro"><div><span class="eyebrow">Demo context</span><h2>Illustrative Macro News &amp; Research</h2><p>This article layer remains demo-only. Demo articles linked to production indicators are hidden to avoid mixing illustrative evidence with controlled observations.</p></div></div>
      <div class="filter-bar filter-bar--macro-news"><label class="filter-field filter-field--search"><span>Search</span><input type="search" data-macro-news-q value="${esc(state.q)}" placeholder="Rates, FX, gold, CPI…"></label><label class="filter-field"><span>Indicator</span><select data-macro-news-indicator><option value="">All indicators</option>${opts}</select></label><button class="button filter-reset" type="button" data-macro-news-reset>Reset</button></div>
      <div class="article-list">${articles.map(article => `<article class="article-row"><div class="article-row__date">${esc(App.formatDate(article.published_at))}</div><div><div class="article-row__meta"><span class="source-tag">DEMO</span><span class="source-tag">${esc(article.content_type)}</span>${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}<span>${esc((article.indicator_ids||[]).map(id=>indicator(id)?.name).filter(Boolean).join(' · '))}</span></div><h3>${esc(article.title)}</h3><p>${esc(article.summary)}</p><div class="article-relations">${(article.indicator_ids||[]).map(id=>`<button class="relation-button" type="button" data-macro-indicator-id="${esc(id)}">${esc(indicator(id)?.name || id)}</button>`).join('')}</div></div></article>`).join('') || Components.stateBox('No demo macro articles match the selected filters.')}</div>`);
    bindNewsFilters();
  }

  function bindNewsFilters() {
    document.querySelector('[data-macro-news-q]')?.addEventListener('change', event => { state.q=event.target.value.trim(); App.setQueryParam('q',state.q||null); renderNews(); });
    document.querySelector('[data-macro-news-indicator]')?.addEventListener('change', event => { state.indicatorFilter=event.target.value; App.setQueryParam('indicator-filter',state.indicatorFilter||null); renderNews(); });
    document.querySelector('[data-macro-news-reset]')?.addEventListener('click', () => { state.q=''; state.indicatorFilter=''; App.removeQueryParam('q'); App.removeQueryParam('indicator-filter'); renderNews(); });
  }

  function render() {
    updateTabs();
    ChartTools.destroy('macro-overview-chart'); ChartTools.destroy('macro-series-chart');
    if (state.view === 'news') renderNews();
    else if (state.view === 'overview') renderOverview();
    else renderSeriesView(state.view);
  }

  function indicatorDrawerHTML(id) {
    const ind = indicator(id); if (!ind) return '';
    const {current,previous}=latestPair(id); const delta=deltaInfo(id);
    const articles=(current?._data_layer === 'production' ? [] : data.articles.filter(item=>(item.indicator_ids||[]).includes(id))).sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at))).slice(0,4);
    const recent=[...observationsFor(id)].reverse().slice(0,6);
    const view=CATEGORY_VIEW[ind.indicator_category] || 'overview';
    return `<div class="drawer-entity-head"><span class="eyebrow">Macro Indicator</span><h2>${esc(ind.name)}</h2><p>${esc(labelize(ind.indicator_category))} · ${esc(labelize(ind.frequency))}</p></div>
      <div class="drawer-metrics">${Components.compactMetric({label:'Current',value:formatValue(ind,current?.value),note:formatPeriod(current)})}${Components.compactMetric({label:'Previous',value:formatValue(ind,previous?.value),note:formatPeriod(previous)})}${Components.compactMetric({label:'Change',value:delta.label,note:'Previous available observation'})}${Components.compactMetric({label:'Source',value:window.Provenance?.label?.(current?.source_id) || labelize(current?.source_id),note:current ? `Published ${App.formatDate(current.published_at)}` : ''})}</div>
      <div class="drawer-section"><h3>Definition</h3><p>${esc(ind.description)}</p></div>
      <div class="drawer-section"><h3>Methodology</h3><p>${esc(ind.methodology_note)}</p></div>
      <div class="drawer-section"><h3>Data Provenance</h3>${current ? `<div class="provenance-inline-row"><span class="source-tag">${esc(dataLayerBadge(ind,current))}</span>${sourceRef(current.source_id,{publishedAt:current.published_at,period:current.period,sourceUrl:current.source_url,methodology:ind.methodology_note})}<span class="muted-text">Current displayed observation · ${esc(formatPeriod(current))}</span></div>${corroborationProvenance(current)}` : '<p class="muted-text">No current observation source available.</p>'}</div>
      <div class="drawer-section"><h3>Recent Observations</h3>${recent.map(row=>`<div class="drawer-list-row"><div><strong>${esc(formatPeriod(row))}</strong><span>${esc(row.period)} · ${esc(labelize(row.observation_status))}</span></div><div><strong>${esc(formatValue(ind,row.value))}</strong><span>${sourceRef(row.source_id,{publishedAt:row.published_at,period:row.period,sourceUrl:row.source_url})}</span></div></div>`).join('')}</div>
      <div class="drawer-section"><h3>Related Evidence</h3>${articles.length ? articles.map(item=>`<div class="drawer-list-row drawer-list-row--stack"><span>DEMO · ${esc(App.formatDate(item.published_at))} · ${esc(item.content_type)}</span><strong>${esc(item.title)}</strong></div>`).join('') : `<p class="muted-text">${current?._data_layer === 'production' ? 'No promoted evidence articles yet.' : 'No related articles.'}</p>`}</div>
      <div class="drawer-section"><a class="text-link" href="macro.html?view=${encodeURIComponent(view)}&series=${encodeURIComponent(id)}&range=1Y">Open historical series</a></div>`;
  }

  function openIndicator(id,{push=true}={}) {
    const ind=indicator(id); if (!ind) return;
    if (push) App.setQueryParam('indicator',id,{push:true});
    App.openDrawer({title:ind.name,html:indicatorDrawerHTML(id)});
  }

  function bindDelegatedEvents() {
    document.addEventListener('click', event => {
      const trigger=event.target.closest('[data-macro-indicator-id]');
      if (!trigger) return; openIndicator(trigger.dataset.macroIndicatorId);
    });
    document.addEventListener('app:drawer-closed',()=>{ if (App.getQueryParam('indicator')) App.removeQueryParam('indicator'); });
    window.addEventListener('popstate',()=>{
      parseState(); adjustViewFromDeepLink(); render();
      const id=App.getQueryParam('indicator'); if (id) openIndicator(id,{push:false}); else App.closeDrawer();
    });
  }

  async function load() {
    try {
      await window.Provenance?.load?.();
      const productionObservationsPromise = DataStore.getProcessedMacroObservations()
        .catch(error => { console.warn('[macro] processed observations unavailable; using demo fallback.', error); return null; });
      const productionMetaPromise = DataStore.getProcessedMacroPublishMeta()
        .catch(error => { console.warn('[macro] processed publish metadata unavailable; using demo fallback.', error); return null; });

      const [indicators, observations, articles, events, meta, productionObservations, productionMeta] = await Promise.all([
        DataStore.getMacroIndicators(), DataStore.getMacroObservations(), DataStore.getArticles(), DataStore.getEvents(), DataStore.getMeta(),
        productionObservationsPromise, productionMetaPromise
      ]);

      const integrated = integrateMacroObservations(observations, productionObservations, productionMeta);
      productionState = {
        active: integrated.productionRows.length > 0,
        recordCount: integrated.productionRows.length,
        indicatorIds: integrated.productionIndicatorIds,
        rows: integrated.productionRows,
        publishMeta: productionMeta
      };
      data = {
        indicators: applyProductionIndicatorMetadata(payloadData(indicators), integrated.productionIndicatorIds),
        observations: integrated.rows,
        articles:payloadData(articles).filter(item=>item.category==='macro').map(item=>({ ...item, _data_layer:'demo' })),
        events:payloadData(events).filter(item=>item.category==='macro').map(item=>({ ...item, _data_layer:'demo' }))
      };
      Resolver.setData('macro-indicator',data.indicators);
      parseState(); adjustViewFromDeepLink();
      if (updatedLabel()) {
        updatedLabel().textContent = productionState.active
          ? `Controlled macro · ${productionState.recordCount} production records`
          : (meta?.last_successful_build ? `Demo data · ${App.formatDate(meta.last_successful_build)}` : 'Demo data');
      }
      updateStatusBanner();
      render();
      const deep=App.getQueryParam('indicator'); if (deep) openIndicator(deep,{push:false});
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load Macro data. Check the frontend data files and try again.', 'error'));
    }
  }

  document.addEventListener('DOMContentLoaded',()=>{ bindDelegatedEvents(); bindMacroTabs(); load(); });
})();
