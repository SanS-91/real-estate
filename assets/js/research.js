(() => {
  'use strict';

  const state = { type: 'project', ids: [] };
  let data = null;

  const esc = value => Components.escapeHTML(value);
  const payload = x => Array.isArray(x?.data) ? x.data : [];
  const byId = rows => new Map(rows.map(row => [row.id, row]));
  const unique = values => [...new Set((values || []).filter(Boolean))];

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
      (article.project_ids || []).some(id => projectIds.includes(id)) ||
      (article.developer_ids || []).some(id => developerIds.includes(id)) ||
      (article.region_ids || []).some(id => regionIds.includes(id)) ||
      (article.infrastructure_project_ids || []).some(id => infrastructure.map(x => x.id).includes(id))
    );

    const events = data.events.filter(event =>
      (event.entity_type === 'real-estate-project' && projectIds.includes(event.entity_id)) ||
      (event.entity_type === 'infrastructure-project' && infrastructure.map(x => x.id).includes(event.entity_id)) ||
      (event.region_ids || []).some(id => regionIds.includes(id))
    );

    return { subject, projects, projectIds, regionIds, developerIds, legalTopicIds, infrastructure, legalDocuments, articles, events };
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
    const regionNames = ctx.regionIds.map(id => data.regionMap.get(id)?.name).filter(Boolean);
    const developerNames = ctx.developerIds.map(id => data.developerMap.get(id)?.name).filter(Boolean);
    const sourceIds = unique([
      ...ctx.projects.map(x => x.primary_source_id),
      ...ctx.legalDocuments.map(x => x.primary_source_id),
      ...ctx.articles.map(x => x.source_id),
      ...ctx.events.flatMap(x => x.source_ids || [])
    ]);

    setView(`
      <section class="research-hero">
        <div>
          <span class="eyebrow">${esc(state.type)}</span>
          <h2>${esc(subjectLabel(ctx.subject))}</h2>
          <p>${esc(ctx.subject.summary || ctx.subject.description || '')}</p>
        </div>
        <div class="research-meta">
          <span>${ctx.projects.length} linked projects</span>
          <span>${ctx.infrastructure.length} infrastructure links</span>
          <span>${ctx.legalDocuments.length} relevant legal documents</span>
          <span>${sourceIds.length} source records</span>
        </div>
      </section>

      <div class="research-overview-grid">
        ${Components.compactMetric({label:'Projects',value:String(ctx.projects.length),note:developerNames.join(', ') || '—'})}
        ${Components.compactMetric({label:'Regions',value:String(ctx.regionIds.length),note:regionNames.join(', ') || '—'})}
        ${Components.compactMetric({label:'Infrastructure',value:String(ctx.infrastructure.length),note:'Canonical relationships'})}
        ${Components.compactMetric({label:'Legal topics',value:String(ctx.legalTopicIds.length),note:'Research relevance only'})}
      </div>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Market</span><h2 class="section-title">Related Projects</h2></div><a class="text-link" href="market.html?view=projects">Open Market</a></div>
        <div class="section-body">${projectCards(ctx)}</div>
      </section>

      <div class="research-two-column">
        <section class="section">
          <div class="section-header"><div><span class="eyebrow">Infrastructure</span><h2 class="section-title">Connectivity & Milestones</h2></div><a class="text-link" href="infrastructure.html">Open Infrastructure</a></div>
          <div class="section-body">${infrastructureCards(ctx)}</div>
        </section>
        <section class="section">
          <div class="section-header"><div><span class="eyebrow">Macro</span><h2 class="section-title">Current Macro Context</h2></div><a class="text-link" href="macro.html">Open Macro</a></div>
          <div class="section-body">
            <p class="research-disclaimer">Macro indicators provide common market context and are not project-specific causality.</p>
            <div class="research-macro-grid">${latestMacroCards()}</div>
          </div>
        </section>
      </div>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Legal</span><h2 class="section-title">Legal Research Context</h2></div><a class="text-link" href="legal.html">Open Legal</a></div>
        <div class="section-body">${legalCards(ctx)}</div>
      </section>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Cross-module</span><h2 class="section-title">Recent Related Activity</h2></div><button class="button" type="button" data-search-open>Search all data</button></div>
        <div class="section-body">${recentActivity(ctx)}</div>
      </section>
    `);
  }

  function renderCompare(contexts) {
    setView(`
      <section class="research-hero research-hero--compare">
        <div>
          <span class="eyebrow">Compare · ${esc(state.type)}</span>
          <h2>${contexts.map(c => esc(subjectLabel(c.subject))).join(' vs ')}</h2>
          <p>Side-by-side comparison derived from the same canonical registries. Blank or missing business facts remain unfilled.</p>
        </div>
        <div class="research-meta">
          <span>${contexts.length} subjects</span>
          <span>Same subject type</span>
          <span>Shareable URL</span>
          <span>No synthetic scoring</span>
        </div>
      </section>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Comparison</span><h2 class="section-title">Cross-module Coverage</h2></div></div>
        <div class="section-body">${compareTable(contexts)}</div>
      </section>

      ${compareShared(contexts)}

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Subjects</span><h2 class="section-title">Open Individual Research</h2></div></div>
        <div class="section-body"><div class="research-card-grid">${contexts.map(ctx => `
          <a class="research-entity-card" href="research.html?type=${encodeURIComponent(state.type)}&ids=${encodeURIComponent(ctx.subject.id)}">
            <span class="eyebrow">${esc(state.type)}</span>
            <strong>${esc(subjectLabel(ctx.subject))}</strong>
            <span>${contextStats(ctx).projects} projects · ${contextStats(ctx).infrastructure} infrastructure links</span>
            <small>${contextStats(ctx).legalTopics} legal topics · ${contextStats(ctx).recent} recent items</small>
          </a>`).join('')}</div></div>
      </section>

      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Macro</span><h2 class="section-title">Common Macro Context</h2></div><a class="text-link" href="macro.html">Open Macro</a></div>
        <div class="section-body">
          <p class="research-disclaimer">Macro context is common to the comparison and is not used as a project score.</p>
          <div class="research-macro-grid">${latestMacroCards()}</div>
        </div>
      </section>
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
        button.textContent = 'Link copied';
        setTimeout(() => { button.textContent = prior; window.AppDynamicLocalization?.apply?.(); }, 1200);
      } catch {
        button.textContent = 'Copy URL from address bar';
      }
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
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load the integrated research workspace.','error'));
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();