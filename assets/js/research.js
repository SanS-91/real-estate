(() => {
  'use strict';

  const state = { type: 'project', ids: [] };
  let data = null;

  const esc = value => Components.escapeHTML(value);
  const payload = x => Array.isArray(x?.data) ? x.data : [];
  const byId = rows => new Map(rows.map(row => [row.id, row]));
  const unique = values => [...new Set((values || []).filter(Boolean))];
  const WATCHLIST_KEY = 're-mi-research-watchlist-v1';
  const WATCH_REVIEW_KEY = 're-mi-research-watch-reviewed-v1';

  function readJSONStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function writeJSONStorage(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
  }

  function watchlistItems() {
    const rows = readJSONStorage(WATCHLIST_KEY, []);
    return Array.isArray(rows) ? rows : [];
  }

  function reviewedEvidence() {
    const rows = readJSONStorage(WATCH_REVIEW_KEY, []);
    return new Set(Array.isArray(rows) ? rows : []);
  }

  function saveWatchlist(rows) {
    writeJSONStorage(WATCHLIST_KEY, rows);
  }

  function saveReviewed(set) {
    writeJSONStorage(WATCH_REVIEW_KEY, [...set]);
  }
  const isRealSource = id => Boolean(id) && !String(id).startsWith('demo-');

  function currentLanguage() {
    return window.AppLocalization?.getLanguage?.() || document.documentElement.lang || 'vi';
  }

  function tr(vi, en) {
    return currentLanguage() === 'vi' ? vi : en;
  }

  function setView(html) {
    const node = document.querySelector('[data-research-view]');
    if (node) node.innerHTML = html;
  }

  function queryState() {
    const params = new URLSearchParams(location.search);
    const type = params.get('type');
    const ids = params.get('ids');
    const legacyId = params.get('id');
    if (['project','region','developer'].includes(type)) state.type = type;
    state.ids = unique((ids ? ids.split(',') : legacyId ? [legacyId] : []).map(x => x.trim())).slice(0,3);
  }

  function subjectRows() {
    if (!data) return [];
    if (state.type === 'region') return data.regions;
    if (state.type === 'developer') return data.developers;
    return data.projects;
  }

  function subjectLabel(row) {
    return row?.name || row?.title || row?.id || '—';
  }

  function renderSelector() {
    const type = document.querySelector('[data-research-type]');
    const selects = [...document.querySelectorAll('[data-research-entity]')];
    if (!type || !selects.length) return;
    type.value = state.type;
    const rows = [...subjectRows()].sort((a,b) => subjectLabel(a).localeCompare(subjectLabel(b)));
    if (!state.ids.length || !rows.some(row => row.id === state.ids[0])) state.ids = rows[0] ? [rows[0].id] : [];

    selects.forEach((select, index) => {
      const allowNone = index > 0;
      const options = [
        ...(allowNone ? ['<option value="">— None —</option>'] : []),
        ...rows.map(row => `<option value="${esc(row.id)}">${esc(subjectLabel(row))}</option>`)
      ];
      select.innerHTML = options.join('');
      select.value = state.ids[index] || '';
    });
  }

  function selectedSubjects() {
    const map = byId(subjectRows());
    return state.ids.map(id => map.get(id)).filter(Boolean);
  }

  function contextFor(subject) {
    let projects = [];
    let regionIds = [];
    let developerIds = [];

    if (state.type === 'project') {
      projects = [subject];
      regionIds = subject.region_ids || [];
      developerIds = subject.developer_ids || (subject.lead_developer_id ? [subject.lead_developer_id] : []);
    } else if (state.type === 'developer') {
      developerIds = [subject.id];
      projects = data.projects.filter(project =>
        (project.developer_ids || []).includes(subject.id) || project.lead_developer_id === subject.id
      );
      regionIds = unique([...(subject.region_ids || []), ...projects.flatMap(project => project.region_ids || [])]);
    } else {
      regionIds = [subject.id];
      projects = data.projects.filter(project => (project.region_ids || []).includes(subject.id));
      developerIds = unique(projects.flatMap(project =>
        project.developer_ids || (project.lead_developer_id ? [project.lead_developer_id] : [])
      ));
    }

    const projectIds = projects.map(project => project.id);
    const legalTopicIds = unique(projects.flatMap(project => project.related_legal_topic_ids || []));
    const infrastructureIds = unique([
      ...projects.flatMap(project => project.related_infrastructure_ids || []),
      ...data.infrastructure
        .filter(infra => projectIds.some(id => (infra.related_real_estate_project_ids || []).includes(id)))
        .map(infra => infra.id)
    ]);

    const infrastructure = data.infrastructure.filter(infra =>
      infrastructureIds.includes(infra.id) ||
      (state.type === 'region' && (infra.region_ids || []).includes(subject.id))
    );

    const legalDocuments = data.legal.filter(doc =>
      (doc.topic_ids || []).some(id => legalTopicIds.includes(id))
    );

    const articles = data.articles.filter(article =>
      ((article.project_ids || []).some(id => projectIds.includes(id)) ||
      (article.developer_ids || []).some(id => developerIds.includes(id)) ||
      (article.region_ids || []).some(id => regionIds.includes(id)) ||
      (article.infrastructure_project_ids || []).some(id => infrastructure.map(x => x.id).includes(id))) &&
      isRealSource(article.source_id)
    );

    const events = data.events.filter(event =>
      ((event.entity_type === 'real-estate-project' && projectIds.includes(event.entity_id)) ||
      (event.entity_type === 'infrastructure-project' && infrastructure.map(x => x.id).includes(event.entity_id)) ||
      (event.region_ids || []).some(id => regionIds.includes(id))) &&
      (event.source_ids || []).some(isRealSource)
    );

    return { subject, projects, projectIds, regionIds, developerIds, legalTopicIds, infrastructure, legalDocuments, articles, events };
  }

  function watchKey(type, id) {
    return type + ':' + id;
  }

  function evidenceRowsForContext(ctx) {
    const rows = [];
    ctx.articles.forEach(row => {
      if (!isRealSource(row.source_id)) return;
      rows.push({
        id: 'article:' + row.id,
        date: row.published_at,
        title: row.title,
        source: sourceName(row.source_id),
        type: 'article',
        href: row.category === 'market' ? 'market.html?view=news'
          : row.category === 'legal' ? 'legal.html?view=news'
          : row.category === 'infrastructure' ? 'infrastructure.html?view=news'
          : 'macro.html?view=news'
      });
    });
    ctx.events.forEach(row => {
      const sourceId = (row.source_ids || []).find(isRealSource);
      if (!sourceId) return;
      rows.push({
        id: 'event:' + row.id,
        date: row.event_date,
        title: row.title,
        source: sourceName(sourceId),
        type: 'event',
        href: row.entity_type === 'infrastructure-project'
          ? 'infrastructure.html?view=projects&project=' + encodeURIComponent(row.entity_id)
          : row.entity_type === 'real-estate-project'
            ? 'market.html?view=projects&project=' + encodeURIComponent(row.entity_id)
            : 'index.html'
      });
    });
    return rows.filter(row => row.date).sort((a,b) => String(b.date).localeCompare(String(a.date)));
  }

  function watchlistContexts() {
    const rows = watchlistItems();
    const projectMap = byId(data.projects);
    const regionMap = byId(data.regions);
    const developerMap = byId(data.developers);
    return rows.map(row => {
      const map = row.type === 'region' ? regionMap : row.type === 'developer' ? developerMap : projectMap;
      const subject = map.get(row.id);
      if (!subject) return null;
      const priorType = state.type;
      state.type = row.type;
      const ctx = contextFor(subject);
      state.type = priorType;
      return { row, ctx };
    }).filter(Boolean);
  }

  function renderWatchlist() {
    if (!data) return;
    const savedNode = document.querySelector('[data-watchlist-saved]');
    const inboxNode = document.querySelector('[data-watchlist-inbox]');
    const countNode = document.querySelector('[data-watchlist-new-count]');
    if (!savedNode || !inboxNode || !countNode) return;

    const watched = watchlistContexts();
    const reviewed = reviewedEvidence();
    const allEvidence = [];
    watched.forEach(({row,ctx}) => {
      evidenceRowsForContext(ctx).forEach(ev => allEvidence.push({ ...ev, watch: row }));
    });

    const deduped = [...new Map(allEvidence.map(row => [row.id, row])).values()]
      .sort((a,b) => String(b.date).localeCompare(String(a.date)));
    const fresh = deduped.filter(row => !reviewed.has(row.id));

    savedNode.innerHTML = watched.length
      ? '<div class="research-watchlist__chips">' + watched.map(({row,ctx}) =>
          '<button class="research-watch-chip" type="button" data-watch-open="' + esc(watchKey(row.type,row.id)) + '">' +
            '<span>' + esc(subjectLabel(ctx.subject)) + '</span><small>' + esc(row.type) + '</small>' +
            '<span class="research-watch-chip__remove" data-watch-remove="' + esc(watchKey(row.type,row.id)) + '" aria-label="Remove from watchlist">×</span>' +
          '</button>'
        ).join('') + '</div>'
      : '<div class="state-box">' + esc(tr('Chưa có nghiên cứu đã lưu.', 'No saved research yet.')) + '</div>';

    countNode.textContent = String(fresh.length);
    inboxNode.innerHTML = fresh.length
      ? '<div class="research-list research-watchlist__inbox">' + fresh.slice(0,20).map(row =>
          '<a href="' + esc(row.href) + '" data-watch-evidence="' + esc(row.id) + '">' +
            '<strong>' + esc(row.title) + '</strong>' +
            '<span>' + esc(App.formatDate(row.date)) + ' · ' + esc(row.source) + ' · ' + esc(subjectLabel(
              (row.watch.type === 'project' ? data.projectMap : row.watch.type === 'region' ? data.regionMap : data.developerMap).get(row.watch.id)
            )) + '</span>' +
          '</a>'
        ).join('') + '</div>'
      : '<div class="state-box">' + esc(tr('Không có cập nhật mới chưa xem.', 'No unseen updates.')) + '</div>';

    window.AppDynamicLocalization?.apply?.();
  }

  function saveCurrentResearch() {
    collectSelections();
    const current = watchlistItems();
    const existing = new Set(current.map(row => watchKey(row.type,row.id)));
    const newlySaved = [];
    state.ids.forEach(id => {
      const key = watchKey(state.type,id);
      if (!existing.has(key)) {
        current.push({ type: state.type, id });
        newlySaved.push({ type: state.type, id });
      }
    });
    saveWatchlist(current.slice(0,30));

    // Treat currently linked evidence as the baseline at the moment a subject is saved.
    // The inbox then highlights only evidence IDs that appear later.
    if (newlySaved.length) {
      const reviewed = reviewedEvidence();
      const map = byId(subjectRows());
      newlySaved.forEach(row => {
        const subject = map.get(row.id);
        if (!subject) return;
        evidenceRowsForContext(contextFor(subject)).forEach(ev => reviewed.add(ev.id));
      });
      saveReviewed(reviewed);
    }
    renderWatchlist();
  }

  function removeWatch(key) {
    saveWatchlist(watchlistItems().filter(row => watchKey(row.type,row.id) !== key));
    renderWatchlist();
  }

  function openWatch(key) {
    const [type,id] = String(key || '').split(':');
    if (!['project','region','developer'].includes(type) || !id) return;
    state.type = type;
    state.ids = [id];
    renderSelector();
    updateUrl();
    render();
  }

  function markAllReviewed() {
    const reviewed = reviewedEvidence();
    watchlistContexts().forEach(({ctx}) => evidenceRowsForContext(ctx).forEach(row => reviewed.add(row.id)));
    saveReviewed(reviewed);
    renderWatchlist();
  }

  function sourceName(id) {
    return data.sourceMap.get(id)?.name || id || 'Source';
  }

  function latestMacroRows() {
    const latest = new Map();
    data.macroRows.forEach(row => {
      const prior = latest.get(row.indicator_id);
      const key = row.data_date || row.period || '';
      const priorKey = prior ? (prior.data_date || prior.period || '') : '';
      if (!prior || key > priorKey) latest.set(row.indicator_id, row);
    });
    return latest;
  }

  function latestMacroCards() {
    const latest = latestMacroRows();
    return ['usd-vnd-central-rate','sjc-gold-sell','credit-growth-ytd','cpi-yoy']
      .map(id => latest.get(id)).filter(Boolean).map(row => {
        const label = data.indicatorMap.get(row.indicator_id)?.name || row.indicator_id;
        return Components.compactMetric({
          label,
          value: Formatters.unitValue(row.unit, row.value, { compact:true }),
          note: row.period || row.data_date || ''
        });
      }).join('');
  }

  function projectCards(ctx) {
    if (!ctx.projects.length) return Components.stateBox('No curated projects linked to this subject.');
    return `<div class="research-card-grid">${ctx.projects.map(project => {
      const devNames = (project.developer_ids || []).map(id => data.developerMap.get(id)?.name).filter(Boolean).join(', ')
        || (project.lead_developer_id ? data.developerMap.get(project.lead_developer_id)?.name : '') || '—';
      return `<a class="research-entity-card" href="market.html?view=projects&project=${encodeURIComponent(project.id)}">
        <span class="eyebrow">Project</span>
        <strong>${esc(project.name)}</strong>
        <span>${esc(project.location_text || '')}</span>
        <small>${esc(devNames)} · ${esc(String(project.status || '').replaceAll('-',' '))}</small>
      </a>`;
    }).join('')}</div>`;
  }

  function infrastructureCards(ctx) {
    if (!ctx.infrastructure.length) return Components.stateBox('No canonical infrastructure links for this subject.');
    return `<div class="research-card-grid">${ctx.infrastructure.map(infra => `
      <a class="research-entity-card" href="infrastructure.html?view=projects&project=${encodeURIComponent(infra.id)}">
        <span class="eyebrow">Infrastructure</span>
        <strong>${esc(infra.name)}</strong>
        <span>${esc(infra.location_text || '')}</span>
        <small>${esc(String(infra.status || '').replaceAll('-',' '))} · ${esc(infra.current_expected_completion || '—')}</small>
      </a>`).join('')}</div>`;
  }

  function legalCards(ctx) {
    const topics = ctx.legalTopicIds.map(id => data.topicMap.get(id)).filter(Boolean);
    const docs = [...ctx.legalDocuments].sort((a,b) =>
      String(b.issued_date || b.effective_date || '').localeCompare(String(a.issued_date || a.effective_date || ''))
    ).slice(0,8);
    return `
      <div class="research-topic-row">${topics.map(topic => `<span class="research-topic-chip">${esc(topic.name)}</span>`).join('') || '<span class="muted-text">No project-level legal topics linked.</span>'}</div>
      <p class="research-disclaimer">Shared legal topics indicate research relevance only; they do not determine legal applicability to a project.</p>
      ${docs.length ? `<div class="research-list">${docs.map(doc => `
        <a href="legal.html?view=documents&document=${encodeURIComponent(doc.id)}">
          <strong>${esc(doc.document_number)} · ${esc(doc.title)}</strong>
          <span>${esc(App.formatDate(doc.effective_date || doc.issued_date))} · ${esc(sourceName(doc.primary_source_id))}</span>
        </a>`).join('')}</div>` : Components.stateBox('No official documents match the linked research topics.')}`;
  }

  function recentActivity(ctx) {
    const rows = [
      ...ctx.events.map(row => ({
        date: row.event_date,
        title: row.title,
        meta: `${row.category || 'event'} · ${sourceName((row.source_ids || [])[0])}`,
        href: row.entity_type === 'infrastructure-project'
          ? `infrastructure.html?view=projects&project=${encodeURIComponent(row.entity_id)}`
          : row.entity_type === 'real-estate-project'
            ? `market.html?view=projects&project=${encodeURIComponent(row.entity_id)}`
            : 'index.html'
      })),
      ...ctx.articles.map(row => ({
        date: row.published_at,
        title: row.title,
        meta: `${row.category || 'article'} · ${sourceName(row.source_id)}`,
        href: row.category === 'market' ? 'market.html?view=news'
          : row.category === 'legal' ? 'legal.html?view=news'
          : row.category === 'infrastructure' ? 'infrastructure.html?view=news'
          : 'macro.html?view=news'
      }))
    ].filter(row => row.date).sort((a,b) => String(b.date).localeCompare(String(a.date))).slice(0,10);

    if (!rows.length) return Components.stateBox('No recent source-backed activity linked to this subject.');
    return `<div class="research-list">${rows.map(row => `
      <a href="${esc(row.href)}">
        <strong>${esc(row.title)}</strong>
        <span>${esc(App.formatDate(row.date))} · ${esc(row.meta)}</span>
      </a>`).join('')}</div>`;
  }

  function contextStats(ctx) {
    return {
      projects: ctx.projects.length,
      regions: ctx.regionIds.length,
      infrastructure: ctx.infrastructure.length,
      legalTopics: ctx.legalTopicIds.length,
      legalDocs: ctx.legalDocuments.length,
      recent: ctx.articles.length + ctx.events.length
    };
  }

  function marketCoverage(ctx) {
    const observations = data.marketObservations.filter(row => row.project_id && ctx.projectIds.includes(row.project_id) && isRealSource(row.source_id));
    const projectCount = ctx.projects.length;
    const countWith = field => new Set(observations.filter(row => row[field] !== null && row[field] !== undefined).map(row => row.project_id)).size;
    return { projects: projectCount, observations: observations.length, price: countWith('average_asp'), sales: countWith('sales_units'), absorption: countWith('absorption_rate') };
  }

  function projectObservation(projectId) {
    return data.marketObservations
      .filter(row => row.project_id === projectId && isRealSource(row.source_id))
      .sort((a,b) => String(b.source_date || b.period || '').localeCompare(String(a.source_date || a.period || '')))[0] || null;
  }

  function marketBenchmarkRows(ctx) {
    const segmentIds = unique(ctx.projects.flatMap(project => project.segment_ids || []));
    return data.marketObservations
      .filter(row => !row.project_id && isRealSource(row.source_id)
        && (row.region_ids || []).some(id => ctx.regionIds.includes(id))
        && (row.segment_ids || []).some(id => segmentIds.includes(id)))
      .sort((a,b) => String(b.source_date || b.period || '').localeCompare(String(a.source_date || a.period || '')));
  }

  function fmtMarketValue(value, kind) {
    if (value === null || value === undefined) return '—';
    if (kind === 'asp') return Formatters.unitValue('vnd-per-m2', value, { compact:true });
    if (kind === 'absorption') return Formatters.number(Number(value) * 100, { min:0, max:1 }) + '%';
    return Formatters.number(value, { min:0, max:0 });
  }

  function projectMarketRow(project) {
    const obs = projectObservation(project.id);
    const developer = (project.developer_ids || []).map(id => data.developerMap.get(id)?.name).filter(Boolean).join(', ')
      || (project.lead_developer_id ? data.developerMap.get(project.lead_developer_id)?.name : '') || '—';
    const segments = (project.segment_ids || []).map(id => String(id).replaceAll('-', ' ')).join(', ') || '—';
    return {
      project, developer, segments, obs,
      units: project.planned_units ?? null,
      asp: obs?.average_asp ?? null,
      sales: obs?.sales_units ?? null,
      absorption: obs?.absorption_rate ?? null,
      period: obs?.period || obs?.source_date || '—'
    };
  }

  function marketCoverageLine(ctx) {
    const cov = marketCoverage(ctx);
    return tr(
      'Coverage: Giá ' + cov.price + '/' + cov.projects + ' · Bán hàng ' + cov.sales + '/' + cov.projects + ' · Hấp thụ ' + cov.absorption + '/' + cov.projects,
      'Coverage: Price ' + cov.price + '/' + cov.projects + ' · Sales ' + cov.sales + '/' + cov.projects + ' · Absorption ' + cov.absorption + '/' + cov.projects
    );
  }

  function marketSingleHTML(ctx) {
    const rows = ctx.projects.map(projectMarketRow);
    const benchmarks = marketBenchmarkRows(ctx).slice(0,4);
    const table = '<div class="table-wrap"><table class="data-table data-table--market-first"><thead><tr>' +
      '<th>' + esc(tr('Dự án','Project')) + '</th><th>' + esc(tr('Chủ đầu tư','Developer')) + '</th><th>' + esc(tr('Phân khúc','Segment')) + '</th><th>' + esc(tr('Trạng thái','Status')) + '</th><th>' + esc(tr('Quy mô căn','Units')) + '</th><th>' + esc(tr('ASP mới nhất','Latest ASP')) + '</th><th>' + esc(tr('Bán hàng','Sales')) + '</th><th>' + esc(tr('Hấp thụ','Absorption')) + '</th></tr></thead><tbody>' +
      rows.map(row => '<tr><td><a class="table-link" href="market.html?view=projects&project=' + encodeURIComponent(row.project.id) + '">' + esc(row.project.name) + '</a><span class="table-subtext">' + esc(row.project.location_text || '') + '</span></td><td>' + esc(row.developer) + '</td><td>' + esc(row.segments) + '</td><td>' + esc(String(row.project.status || '—').replaceAll('-',' ')) + '</td><td class="numeric">' + esc(row.units === null ? '—' : Formatters.number(row.units,{min:0,max:0})) + '</td><td class="numeric">' + esc(fmtMarketValue(row.asp,'asp')) + '</td><td class="numeric">' + esc(fmtMarketValue(row.sales,'sales')) + '</td><td class="numeric">' + esc(fmtMarketValue(row.absorption,'absorption')) + '</td></tr>').join('') +
      '</tbody></table></div>';
    const bench = benchmarks.length ? '<div class="research-market-benchmarks">' + benchmarks.map(row =>
      '<div class="research-market-benchmark"><strong>' + esc(row.period) + '</strong><span>' + esc((row.segment_ids || []).join(', ')) + '</span><small>' +
      [row.new_supply != null ? tr('Nguồn cung ','Supply ') + Formatters.number(row.new_supply,{min:0,max:0}) : '', row.sales_units != null ? tr('Bán ','Sales ') + Formatters.number(row.sales_units,{min:0,max:0}) : '', row.average_asp != null ? 'ASP ' + fmtMarketValue(row.average_asp,'asp') : '', row.absorption_rate != null ? tr('Hấp thụ ','Absorption ') + fmtMarketValue(row.absorption_rate,'absorption') : ''].filter(Boolean).join(' · ') +
      '</small><em>' + esc(sourceName(row.source_id)) + '</em></div>').join('') + '</div>' : '<div class="state-box">' + esc(tr('Chưa có benchmark thị trường tương thích cho đối tượng này.','No compatible market benchmark is available for this subject.')) + '</div>';
    return '<section class="section research-market-primary"><div class="section-header"><div><span class="eyebrow">Market first</span><h2 class="section-title">' + esc(tr('Hiệu quả & vị thế thị trường','Market Performance & Positioning')) + '</h2><p class="section-note">' + esc(marketCoverageLine(ctx)) + '</p></div><a class="text-link" href="market.html">' + esc(tr('Mở Thị trường','Open Market')) + '</a></div><div class="section-body">' + table + '<div class="research-market-benchmark-head"><strong>' + esc(tr('Benchmark thị trường','Market benchmarks')) + '</strong></div>' + bench + '</div></section>';
  }

  function marketCompareHTML(contexts) {
    const rows = [
      [tr('Số dự án','Projects'), ctx => ctx.projects.length],
      [tr('Dự án đang bán/triển khai','Selling / ongoing'), ctx => ctx.projects.filter(p => ['selling','ongoing','construction','active'].includes(p.status)).length],
      [tr('Coverage giá','Price coverage'), ctx => marketCoverage(ctx).price + '/' + marketCoverage(ctx).projects],
      [tr('Coverage bán hàng','Sales coverage'), ctx => marketCoverage(ctx).sales + '/' + marketCoverage(ctx).projects],
      [tr('Coverage hấp thụ','Absorption coverage'), ctx => marketCoverage(ctx).absorption + '/' + marketCoverage(ctx).projects],
      [tr('ASP dự án mới nhất','Latest project ASP'), ctx => { const x=ctx.projects.map(projectMarketRow).find(r=>r.asp!=null); return x ? fmtMarketValue(x.asp,'asp') + ' · ' + x.project.name : '—'; }],
      [tr('Sales dự án mới nhất','Latest project sales'), ctx => { const x=ctx.projects.map(projectMarketRow).find(r=>r.sales!=null); return x ? fmtMarketValue(x.sales,'sales') + ' · ' + x.project.name : '—'; }],
      [tr('Hấp thụ dự án mới nhất','Latest project absorption'), ctx => { const x=ctx.projects.map(projectMarketRow).find(r=>r.absorption!=null); return x ? fmtMarketValue(x.absorption,'absorption') + ' · ' + x.project.name : '—'; }],
      [tr('Benchmark gần nhất','Latest benchmark'), ctx => { const x=marketBenchmarkRows(ctx)[0]; return x ? x.period + ' · ' + sourceName(x.source_id) : '—'; }]
    ];
    return '<section class="section research-market-primary"><div class="section-header"><div><span class="eyebrow">Market first</span><h2 class="section-title">' + esc(tr('Ma trận so sánh thị trường','Market Comparison Matrix')) + '</h2><p class="section-note">' + esc(tr('Ưu tiên dữ liệu giá, bán hàng, hấp thụ và benchmark có nguồn; phần thiếu giữ trống.','Prioritizes sourced price, sales, absorption and benchmark data; missing fields stay blank.')) + '</p></div></div><div class="section-body"><div class="table-wrap table-wrap--research-compare"><table class="data-table data-table--research-compare data-table--market-first"><thead><tr><th>' + esc(tr('Chỉ tiêu','Metric')) + '</th>' + contexts.map(ctx => '<th>' + esc(subjectLabel(ctx.subject)) + '</th>').join('') + '</tr></thead><tbody>' + rows.map(([label,getter]) => '<tr><td><strong>' + esc(label) + '</strong></td>' + contexts.map(ctx => '<td>' + esc(String(getter(ctx))) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div></div></section>';
  }

  function supportingContextHTML(ctx) {
    return '<section class="section research-supporting-context"><div class="section-header"><div><span class="eyebrow">Context</span><h2 class="section-title">' + esc(tr('Bối cảnh hỗ trợ','Supporting Context')) + '</h2></div></div><div class="section-body"><div class="research-context-grid"><article><h3>' + esc(tr('Hạ tầng','Infrastructure')) + '</h3>' + infrastructureCards(ctx) + '</article><article><h3>' + esc(tr('Pháp lý','Legal')) + '</h3>' + legalCards(ctx) + '</article><article><h3>' + esc(tr('Vĩ mô','Macro')) + '</h3><p class="research-disclaimer">' + esc(tr('Bối cảnh chung, không phải quan hệ nhân quả riêng cho dự án.','Common context, not project-specific causality.')) + '</p><div class="research-macro-grid research-macro-grid--compact">' + latestMacroCards() + '</div></article></div></div></section>';
  }
  function latestEvidence(ctx) {
    const rows = [];
    ctx.articles.forEach(row => rows.push({ date: row.published_at, title: row.title, source: sourceName(row.source_id) }));
    ctx.events.forEach(row => rows.push({ date: row.event_date, title: row.title, source: sourceName((row.source_ids || [])[0]) }));
    ctx.projects.filter(row => row.source_date && isRealSource(row.primary_source_id)).forEach(row => rows.push({
      date: row.source_date,
      title: row.name + ' · ' + tr('cập nhật hồ sơ dự án', 'project registry update'),
      source: sourceName(row.primary_source_id)
    }));
    return rows.filter(row => row.date).sort((a,b) => String(b.date).localeCompare(String(a.date)))[0] || null;
  }

  function commonIds(contexts, getter) {
    return contexts.reduce((set, ctx, index) => {
      const ids = new Set(getter(ctx));
      if (index === 0) return ids;
      return new Set([...set].filter(id => ids.has(id)));
    }, new Set());
  }

  function briefModel(contexts) {
    if (contexts.length === 1) {
      const ctx = contexts[0];
      const coverage = marketCoverage(ctx);
      const latest = latestEvidence(ctx);
      const infraNames = ctx.infrastructure.map(x => x.name).slice(0,3);
      const topicNames = ctx.legalTopicIds.map(id => data.topicMap.get(id)?.name).filter(Boolean).slice(0,5);
      const scope = [tr(
        ctx.projects.length + ' dự án · ' + ctx.infrastructure.length + ' liên kết hạ tầng · ' + ctx.legalTopicIds.length + ' chủ đề pháp lý.',
        ctx.projects.length + ' projects · ' + ctx.infrastructure.length + ' infrastructure links · ' + ctx.legalTopicIds.length + ' legal topics.'
      )];
      if (state.type === 'project') {
        const area = ctx.subject.total_area_sqm ? Formatters.number(ctx.subject.total_area_sqm / 10000, { min: 0, max: 1 }) + ' ha' : '';
        scope.unshift([subjectLabel(ctx.subject), ctx.subject.location_text, area, String(ctx.subject.status || '').replaceAll('-', ' ')].filter(Boolean).join(' · '));
      }
      const evidence = [];
      evidence.push(latest ? tr(
        'Evidence gần nhất: ' + App.formatDate(latest.date) + ' · ' + latest.title + ' · ' + latest.source + '.',
        'Latest evidence: ' + App.formatDate(latest.date) + ' · ' + latest.title + ' · ' + latest.source + '.'
      ) : tr('Chưa có recent activity có nguồn được liên kết.', 'No recent source-backed activity is linked.'));
      if (infraNames.length) evidence.push(tr('Hạ tầng liên quan: ' + infraNames.join(', ') + '.', 'Related infrastructure: ' + infraNames.join(', ') + '.'));
      if (topicNames.length) evidence.push(tr('Chủ đề pháp lý liên quan: ' + topicNames.join(', ') + '.', 'Related legal topics: ' + topicNames.join(', ') + '.'));
      const gaps = [tr(
        'Coverage cấp dự án — giá: ' + coverage.price + '/' + coverage.projects + '; bán hàng: ' + coverage.sales + '/' + coverage.projects + '; hấp thụ: ' + coverage.absorption + '/' + coverage.projects + '.',
        'Project-level coverage — price: ' + coverage.price + '/' + coverage.projects + '; sales: ' + coverage.sales + '/' + coverage.projects + '; absorption: ' + coverage.absorption + '/' + coverage.projects + '.'
      )];
      if (coverage.price < coverage.projects || coverage.sales < coverage.projects || coverage.absorption < coverage.projects) gaps.push(tr('Phần thiếu được giữ trống; không tự ước tính ASP, sales hay absorption.', 'Missing fields remain blank; ASP, sales and absorption are not inferred.'));
      gaps.push(tr(ctx.legalDocuments.length + ' văn bản chính thức được nối qua shared topics; chỉ thể hiện mức liên quan nghiên cứu.', ctx.legalDocuments.length + ' official documents are linked through shared topics; this shows research relevance only.'));
      return [
        { title: tr('Tóm tắt phạm vi', 'Scope snapshot'), items: scope },
        { title: tr('Evidence & liên kết', 'Evidence & links'), items: evidence },
        { title: tr('Khoảng trống dữ liệu', 'Data gaps'), items: gaps }
      ];
    }

    const coverage = contexts.map(ctx => {
      const cov = marketCoverage(ctx);
      return tr(
        subjectLabel(ctx.subject) + ': ' + ctx.projects.length + ' dự án · coverage giá/bán hàng/hấp thụ = ' + cov.price + '/' + cov.sales + '/' + cov.absorption + ' trên ' + cov.projects + ' dự án.',
        subjectLabel(ctx.subject) + ': ' + ctx.projects.length + ' projects · price/sales/absorption coverage = ' + cov.price + '/' + cov.sales + '/' + cov.absorption + ' across ' + cov.projects + ' projects.'
      );
    });
    const sharedInfra = [...commonIds(contexts, ctx => ctx.infrastructure.map(x => x.id))].map(id => data.infrastructureMap.get(id)?.name).filter(Boolean);
    const sharedTopics = [...commonIds(contexts, ctx => ctx.legalTopicIds)].map(id => data.topicMap.get(id)?.name).filter(Boolean);
    const overlap = [
      sharedInfra.length ? tr('Hạ tầng chung: ' + sharedInfra.join(', ') + '.', 'Shared infrastructure: ' + sharedInfra.join(', ') + '.') : tr('Không có liên kết hạ tầng canonical chung.', 'No canonical infrastructure link is shared.'),
      sharedTopics.length ? tr('Chủ đề pháp lý chung: ' + sharedTopics.join(', ') + '.', 'Shared legal topics: ' + sharedTopics.join(', ') + '.') : tr('Không có shared legal topic cho toàn bộ đối tượng.', 'No legal topic is shared by all selected subjects.')
    ];
    const recent = contexts.map(ctx => {
      const latest = latestEvidence(ctx);
      return latest ? tr(subjectLabel(ctx.subject) + ': evidence gần nhất ' + App.formatDate(latest.date) + ' · ' + latest.title + '.', subjectLabel(ctx.subject) + ': latest evidence ' + App.formatDate(latest.date) + ' · ' + latest.title + '.') : tr(subjectLabel(ctx.subject) + ': chưa có recent evidence có nguồn.', subjectLabel(ctx.subject) + ': no recent source-backed evidence.');
    });
    recent.push(tr('Không dùng synthetic score hoặc xếp hạng tốt/xấu.', 'No synthetic score or better/worse ranking is used.'));
    return [
      { title: tr('Độ phủ dữ liệu', 'Data coverage'), items: coverage },
      { title: tr('Điểm giao nhau', 'Shared context'), items: overlap },
      { title: tr('Mốc evidence gần nhất', 'Latest evidence'), items: recent }
    ];
  }

  function researchBriefHTML(contexts) {
    const sections = briefModel(contexts);
    return '<section class="section research-brief" data-research-brief>' +
      '<div class="section-header"><div><span class="eyebrow">' + esc(tr('Tóm tắt quyết định', 'Decision summary')) + '</span><h2 class="section-title">Research Brief</h2></div>' +
      '<div class="research-brief__actions"><button class="button" type="button" data-research-copy-brief>' + esc(tr('Sao chép brief', 'Copy brief')) + '</button><button class="button" type="button" data-research-print>' + esc(tr('In / Lưu PDF', 'Print / Save PDF')) + '</button></div></div>' +
      '<div class="section-body"><div class="research-brief__grid">' + sections.map(section => '<article class="research-brief__card"><h3>' + esc(section.title) + '</h3><ul>' + section.items.map(item => '<li>' + esc(item) + '</li>').join('') + '</ul></article>').join('') + '</div>' +
      '<p class="research-disclaimer">' + esc(tr('Brief được tạo theo quy tắc cố định từ dữ liệu canonical hiện có; không phải khuyến nghị đầu tư hay tư vấn pháp lý.', 'The brief is deterministically generated from current canonical data; it is not investment advice or legal advice.')) + '</p></div></section>';
  }

  function briefText(contexts) {
    const heading = 'RESEARCH BRIEF — ' + contexts.map(ctx => subjectLabel(ctx.subject)).join(' vs ');
    const sections = briefModel(contexts).map(section => section.title + '\n' + section.items.map(item => '- ' + item).join('\n')).join('\n\n');
    return heading + '\n' + location.href + '\n\n' + sections;
  }
  function compareTable(contexts) {
    const rows = [
      ['Projects', c => contextStats(c).projects],
      ['Regions', c => contextStats(c).regions],
      ['Infrastructure links', c => contextStats(c).infrastructure],
      ['Legal topics', c => contextStats(c).legalTopics],
      ['Relevant legal documents', c => contextStats(c).legalDocs],
      ['Recent related activity', c => contextStats(c).recent]
    ];
    return `<div class="table-wrap table-wrap--research-compare"><table class="data-table data-table--research-compare">
      <thead><tr><th>Metric</th>${contexts.map(c => `<th>${esc(subjectLabel(c.subject))}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(([label,getter]) => `<tr><td><strong>${esc(label)}</strong></td>${contexts.map(c => `<td class="numeric">${esc(String(getter(c)))}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>`;
  }

  function compareShared(contexts) {
    const sharedInfra = contexts.reduce((set, ctx, index) => {
      const ids = new Set(ctx.infrastructure.map(x => x.id));
      if (index === 0) return ids;
      return new Set([...set].filter(id => ids.has(id)));
    }, new Set());
    const sharedTopics = contexts.reduce((set, ctx, index) => {
      const ids = new Set(ctx.legalTopicIds);
      if (index === 0) return ids;
      return new Set([...set].filter(id => ids.has(id)));
    }, new Set());

    const infra = [...sharedInfra].map(id => data.infrastructureMap.get(id)).filter(Boolean);
    const topics = [...sharedTopics].map(id => data.topicMap.get(id)).filter(Boolean);

    return `<div class="research-two-column">
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Shared infrastructure</span><h2 class="section-title">Common Connectivity</h2></div></div>
        <div class="section-body">${infra.length ? `<div class="research-list">${infra.map(x => `<a href="infrastructure.html?view=projects&project=${encodeURIComponent(x.id)}"><strong>${esc(x.name)}</strong><span>${esc(x.location_text || '')}</span></a>`).join('')}</div>` : Components.stateBox('No shared canonical infrastructure link across all selected subjects.')}</div>
      </section>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Shared legal context</span><h2 class="section-title">Common Legal Topics</h2></div></div>
        <div class="section-body">
          <p class="research-disclaimer">Shared topics indicate research overlap only; they do not establish legal applicability.</p>
          <div class="research-topic-row">${topics.map(x => `<span class="research-topic-chip">${esc(x.name)}</span>`).join('') || '<span class="muted-text">No common legal topics.</span>'}</div>
        </div>
      </section>
    </div>`;
  }

  function renderSingle(ctx) {
    const coverage = marketCoverage(ctx);
    setView(`
      <section class="research-hero">
        <div>
          <span class="eyebrow">${esc(state.type)}</span>
          <h2>${esc(subjectLabel(ctx.subject))}</h2>
          <p>${esc(ctx.subject.summary || ctx.subject.description || '')}</p>
        </div>
        <div class="research-meta research-meta--market">
          <span>${ctx.projects.length} ${esc(tr('dự án','projects'))}</span>
          <span>${coverage.price}/${coverage.projects} ${esc(tr('có dữ liệu giá','with price data'))}</span>
          <span>${coverage.sales}/${coverage.projects} ${esc(tr('có dữ liệu bán hàng','with sales data'))}</span>
          <span>${coverage.absorption}/${coverage.projects} ${esc(tr('có dữ liệu hấp thụ','with absorption data'))}</span>
        </div>
      </section>

      ${marketSingleHTML(ctx)}

      <section class="section research-key-changes">
        <div class="section-header"><div><span class="eyebrow">${esc(tr('Diễn biến','Changes'))}</span><h2 class="section-title">${esc(tr('Cập nhật đáng chú ý','Notable Updates'))}</h2></div><button class="button" type="button" data-search-open>${esc(tr('Tìm toàn bộ dữ liệu','Search all data'))}</button></div>
        <div class="section-body">${recentActivity(ctx)}</div>
      </section>

      ${supportingContextHTML(ctx)}

      ${researchBriefHTML([ctx])}
    `);
  }
  function renderCompare(contexts) {
    setView(`
      <section class="research-hero research-hero--compare">
        <div>
          <span class="eyebrow">${esc(tr('So sánh thị trường','Market comparison'))} · ${esc(state.type)}</span>
          <h2>${contexts.map(c => esc(subjectLabel(c.subject))).join(' vs ')}</h2>
          <p>${esc(tr('Ưu tiên chỉ tiêu thị trường có nguồn; hạ tầng, pháp lý và vĩ mô là bối cảnh hỗ trợ.','Market evidence comes first; Infrastructure, Legal and Macro are supporting context.'))}</p>
        </div>
        <div class="research-meta research-meta--market">
          <span>${contexts.length} ${esc(tr('đối tượng','subjects'))}</span>
          <span>${esc(tr('So sánh cùng loại','Same subject type'))}</span>
          <span>${esc(tr('URL có thể chia sẻ','Shareable URL'))}</span>
          <span>${esc(tr('Không chấm điểm giả lập','No synthetic scoring'))}</span>
        </div>
      </section>

      ${marketCompareHTML(contexts)}

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">${esc(tr('Dự án','Projects'))}</span><h2 class="section-title">${esc(tr('Danh mục để đào sâu','Projects to Explore'))}</h2></div><a class="text-link" href="market.html?view=projects">${esc(tr('Mở Thị trường','Open Market'))}</a></div>
        <div class="section-body"><div class="research-card-grid">${contexts.flatMap(ctx => ctx.projects.map(project => ({ctx,project}))).slice(0,12).map(({project}) => `
          <a class="research-entity-card" href="market.html?view=projects&project=${encodeURIComponent(project.id)}">
            <span class="eyebrow">${esc(tr('Dự án','Project'))}</span>
            <strong>${esc(project.name)}</strong>
            <span>${esc(project.location_text || '')}</span>
            <small>${esc(String(project.status || '').replaceAll('-',' '))}</small>
          </a>`).join('')}</div></div>
      </section>

      <section class="section research-supporting-context">
        <div class="section-header"><div><span class="eyebrow">Context</span><h2 class="section-title">${esc(tr('Bối cảnh hỗ trợ','Supporting Context'))}</h2></div></div>
        <div class="section-body">
          ${compareShared(contexts)}
          <div class="research-macro-strip"><strong>${esc(tr('Vĩ mô chung','Common Macro'))}</strong><span>${esc(tr('Bối cảnh chung, không dùng để chấm điểm đối tượng.','Common context, not used to score subjects.'))}</span><div class="research-macro-grid research-macro-grid--compact">${latestMacroCards()}</div></div>
        </div>
      </section>

      ${researchBriefHTML(contexts)}
    `);
  }
  function render() {
    const subjects = selectedSubjects();
    if (!subjects.length) {
      setView(Components.stateBox('Select a research subject.'));
      return;
    }
    const contexts = subjects.map(contextFor);
    if (contexts.length === 1) renderSingle(contexts[0]);
    else renderCompare(contexts);
    window.AppDynamicLocalization?.apply?.();
  }

  function updateUrl() {
    const url = new URL(location.href);
    url.searchParams.set('type', state.type);
    url.searchParams.delete('id');
    if (state.ids.length) url.searchParams.set('ids', state.ids.join(','));
    else url.searchParams.delete('ids');
    history.replaceState({}, '', url);
  }

  function collectSelections() {
    const selects = [...document.querySelectorAll('[data-research-entity]')];
    state.ids = unique(selects.map(select => select.value).filter(Boolean)).slice(0,3);
  }

  function bind() {
    const type = document.querySelector('[data-research-type]');
    document.querySelector('[data-research-load]')?.addEventListener('click', () => {
      state.type = type?.value || 'project';
      collectSelections();
      updateUrl();
      render();
    });
    type?.addEventListener('change', () => {
      state.type = type.value;
      state.ids = [];
      renderSelector();
    });
    document.querySelector('[data-research-share]')?.addEventListener('click', async event => {
      collectSelections();
      updateUrl();
      const button = event.currentTarget;
      try {
        await navigator.clipboard.writeText(location.href);
        const prior = button.textContent;
        button.textContent = tr('Đã sao chép liên kết', 'Link copied');
        setTimeout(() => { button.textContent = prior; window.AppDynamicLocalization?.apply?.(); }, 1200);
      } catch {
        button.textContent = tr('Sao chép URL trên thanh địa chỉ', 'Copy URL from address bar');
      }
    });

    document.querySelector('[data-research-watch]')?.addEventListener('click', event => {
      saveCurrentResearch();
      const button = event.currentTarget;
      const prior = button.textContent;
      button.textContent = tr('Đã lưu', 'Saved');
      setTimeout(() => { button.textContent = prior; window.AppDynamicLocalization?.apply?.(); }, 1000);
    });

    document.querySelector('[data-watchlist-review]')?.addEventListener('click', markAllReviewed);

    document.addEventListener('click', event => {
      const remove = event.target.closest('[data-watch-remove]');
      if (remove) {
        event.preventDefault();
        event.stopPropagation();
        removeWatch(remove.getAttribute('data-watch-remove'));
        return;
      }
      const open = event.target.closest('[data-watch-open]');
      if (open) {
        event.preventDefault();
        openWatch(open.getAttribute('data-watch-open'));
      }
    });

    document.addEventListener('click', async event => {
      const copyButton = event.target.closest('[data-research-copy-brief]');
      if (copyButton) {
        const contexts = selectedSubjects().map(contextFor);
        try {
          await navigator.clipboard.writeText(briefText(contexts));
          copyButton.textContent = tr('Đã sao chép brief', 'Brief copied');
        } catch {
          copyButton.textContent = tr('Không thể sao chép', 'Unable to copy');
        }
        return;
      }
      const printButton = event.target.closest('[data-research-print]');
      if (printButton) {
        document.body.classList.add('print-research-brief');
        const clear = () => document.body.classList.remove('print-research-brief');
        window.addEventListener('afterprint', clear, { once: true });
        window.print();
        setTimeout(clear, 1000);
        return;
      }
      if (event.target.closest('[data-search-open]')) App.openSearch?.();
    });

    document.addEventListener('app:language-changed', () => {
      if (data) render();
    });
  }

  async function load() {
    try {
      const [regions, developers, projects, phases, marketObs, topics, legal, infra, schedules, indicators, production, events, articles, sources] = await Promise.all([
        DataStore.getRegions(), DataStore.getDevelopers(), DataStore.getProjects(), DataStore.getProjectPhases(),
        DataStore.getMarketObservations(), DataStore.getLegalTopics(), DataStore.getLegalDocuments(),
        DataStore.getInfrastructureProjects(), DataStore.getInfrastructureSchedules(), DataStore.getMacroIndicators(),
        DataStore.getProcessedMacroObservations(), DataStore.getEvents(), DataStore.getArticles(), DataStore.getSources()
      ]);
      data = {
        regions: payload(regions), developers: payload(developers), projects: payload(projects), phases: payload(phases),
        marketObservations: payload(marketObs), topics: payload(topics), legal: payload(legal),
        infrastructure: payload(infra), schedules: payload(schedules), indicators: payload(indicators),
        macroRows: payload(production), events: payload(events), articles: payload(articles), sources: payload(sources)
      };
      data.regionMap = byId(data.regions);
      data.developerMap = byId(data.developers);
      data.projectMap = byId(data.projects);
      data.topicMap = byId(data.topics);
      data.infrastructureMap = byId(data.infrastructure);
      data.indicatorMap = byId(data.indicators);
      data.sourceMap = byId(data.sources);
      queryState();
      renderSelector();
      bind();
      render();
      renderWatchlist();
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load the integrated research workspace.','error'));
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();