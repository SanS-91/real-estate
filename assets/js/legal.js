(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'documents', 'effective-soon', 'topics', 'news'];
  const FILTER_KEYS = ['q', 'type', 'status', 'agency', 'topic', 'scope'];
  const RELATION_LABELS = {
    implements: 'Implements',
    guides: 'Guides',
    amends: 'Amends',
    replaces: 'Replaces',
    references: 'References'
  };
  const REVERSE_RELATION_LABELS = {
    implements: 'Implemented by',
    guides: 'Guided by',
    amends: 'Amended by',
    replaces: 'Replaced by',
    references: 'Referenced by'
  };

  let state = {
    view: 'overview',
    q: '',
    type: '',
    status: '',
    agency: '',
    topic: '',
    scope: ''
  };

  let data = {
    agencies: [],
    topics: [],
    documents: [],
    articles: [],
    regions: [],
    projects: []
  };

  function payloadData(payload) { return payload?.data || []; }
  function esc(value) { return Components.escapeHTML(value); }

  function sourceRef(sourceId, context = {}) {
    return window.Provenance?.sourceButton?.(sourceId, context) || `<span class="source-tag">${esc(labelize(sourceId))}</span>`;
  }

  function labelize(value) {
    return String(value || '—')
      .replaceAll('-', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  function currentDateParts() {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(new Date());
    const map = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return { year: Number(map.year), month: Number(map.month), day: Number(map.day) };
  }

  function utcDateFromISO(value) {
    if (!value) return null;
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) return null;
    return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  }

  function todayUTC() {
    const { year, month, day } = currentDateParts();
    return new Date(Date.UTC(year, month - 1, day));
  }

  function daysUntil(value) {
    const date = utcDateFromISO(value);
    if (!date) return null;
    return Math.round((date - todayUTC()) / 86400000);
  }

  function agencyNames(document) {
    return Resolver.getEntities('agency', document.agency_ids || []).map(item => item.name).join(', ') || '—';
  }

  function topicNames(document) {
    return Resolver.getEntities('legal-topic', document.topic_ids || []).map(item => item.name).join(', ') || '—';
  }

  function relatedMarketProjects(document) {
    const topicIds = new Set(document.topic_ids || []);
    if (!topicIds.size) return [];
    return data.projects.filter(project => (project.related_legal_topic_ids || []).some(id => topicIds.has(id)));
  }

  function regionNames(document) {
    return Resolver.getEntities('region', document.region_ids || []).map(item => item.short_name || item.name).join(', ');
  }

  function documentTypeOptions() {
    return [...new Set(data.documents.map(item => item.document_type).filter(Boolean))].sort();
  }

  function documentStatusOptions() {
    return [...new Set(data.documents.map(item => item.status).filter(Boolean))].sort();
  }

  function getView() {
    const value = App.getQueryParam('view');
    return VALID_VIEWS.includes(value) ? value : 'overview';
  }

  function parseState() {
    state.view = getView();
    FILTER_KEYS.forEach(key => {
      const value = App.getQueryParam(key);
      state[key] = value || '';
    });
  }

  function updateTabs() {
    document.querySelectorAll('[data-legal-tabs] [data-view]').forEach(link => {
      link.classList.toggle('is-active', link.dataset.view === state.view);
    });
  }

  function option(label, value, current) {
    return `<option value="${esc(value)}"${String(current) === String(value) ? ' selected' : ''}>${esc(label)}</option>`;
  }

  function filterToolbar({ compact = false } = {}) {
    const typeOptions = documentTypeOptions().map(id => option(labelize(id), id, state.type)).join('');
    const statusOptions = documentStatusOptions().map(id => option(labelize(id), id, state.status)).join('');
    const agencyOptions = data.agencies.map(item => option(item.name, item.id, state.agency)).join('');
    const topicOptions = data.topics.map(item => option(item.name, item.id, state.topic)).join('');
    const scopes = [...new Set(data.documents.map(item => item.scope_type).filter(Boolean))].sort();

    return `
      <div class="filter-bar filter-bar--legal${compact ? ' filter-bar--legal-compact' : ''}" data-legal-filters>
        <label class="filter-field filter-field--search">
          <span>Search</span>
          <input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Number, title or topic…">
        </label>
        ${compact ? '' : `<label class="filter-field"><span>Type</span><select data-filter="type">${option('All types','',state.type)}${typeOptions}</select></label>`}
        ${compact ? '' : `<label class="filter-field"><span>Status</span><select data-filter="status">${option('All statuses','',state.status)}${statusOptions}</select></label>`}
        <label class="filter-field"><span>Agency</span><select data-filter="agency">${option('All agencies','',state.agency)}${agencyOptions}</select></label>
        <label class="filter-field"><span>Topic</span><select data-filter="topic">${option('All topics','',state.topic)}${topicOptions}</select></label>
        ${compact ? '' : `<label class="filter-field"><span>Scope</span><select data-filter="scope">${option('All scopes','',state.scope)}${scopes.map(id => option(labelize(id), id, state.scope)).join('')}</select></label>`}
        <button class="button filter-reset" type="button" data-filter-reset>Reset</button>
      </div>
    `;
  }

  function matchesFilters(records) {
    const config = [
      { id: 'type', field: 'document_type', type: 'equals' },
      { id: 'status', field: 'status', type: 'equals' },
      { id: 'agency', field: 'agency_ids', type: 'contains-any' },
      { id: 'topic', field: 'topic_ids', type: 'contains-any' },
      { id: 'scope', field: 'scope_type', type: 'equals' }
    ];
    let result = FilterEngine.apply(records, state, config);
    if (state.q) {
      result = result.filter(document => FilterEngine.textMatch(document, state.q, [
        'document_number', 'title', 'summary', 'key_changes',
        item => agencyNames(item),
        item => topicNames(item),
        item => regionNames(item)
      ]));
    }
    return result;
  }

  function statusForDisplay(document) {
    if (document.status === 'issued' && document.effective_date) {
      const days = daysUntil(document.effective_date);
      if (days !== null && days <= 0) return 'effective';
    }
    return document.status;
  }

  function effectiveBucket(document) {
    if (!document.effective_date || ['draft','expired','replaced','withdrawn'].includes(document.status)) return null;
    const days = daysUntil(document.effective_date);
    if (days === null || days < 0) return null;
    if (days <= 30) return '30';
    if (days <= 90) return '90';
    return 'later';
  }

  function daysLabel(document) {
    const days = daysUntil(document.effective_date);
    if (days === null) return '—';
    if (days === 0) return 'Effective today';
    if (days > 0) return `In ${days} days`;
    return `${Math.abs(days)} days ago`;
  }

  function latestDocuments(limit = 5) {
    return [...data.documents]
      .filter(item => item.issued_date || item.draft_published_date)
      .sort((a,b) => String(b.issued_date || b.draft_published_date).localeCompare(String(a.issued_date || a.draft_published_date)))
      .slice(0, limit);
  }

  function upcomingDocuments() {
    return data.documents
      .filter(item => effectiveBucket(item))
      .sort((a,b) => String(a.effective_date).localeCompare(String(b.effective_date)));
  }

  function recentlyEffective(limitDays = 30) {
    return data.documents
      .filter(item => item.effective_date && statusForDisplay(item) === 'effective')
      .filter(item => {
        const days = daysUntil(item.effective_date);
        return days !== null && days <= 0 && days >= -limitDays;
      })
      .sort((a,b) => String(b.effective_date).localeCompare(String(a.effective_date)));
  }

  function overviewMetrics() {
    const current = data.documents.filter(item => statusForDisplay(item) === 'effective').length;
    const drafts = data.documents.filter(item => item.status === 'draft').length;
    const next90 = data.documents.filter(item => ['30','90'].includes(effectiveBucket(item))).length;
    return [
      { label: 'Tracked Documents', value: String(data.documents.length), note: 'Official Government document registry' },
      { label: 'Currently Effective', value: String(current), note: 'Derived from status + effective date' },
      { label: 'Drafts', value: String(drafts), note: 'Draft is a status, not a document type' },
      { label: 'Effective ≤ 90 Days', value: String(next90), note: 'Upcoming effective dates' }
    ];
  }

  function documentTable(records, { limit = null, compact = false } = {}) {
    const rows = (limit ? records.slice(0, limit) : records).map(document => `
      <tr>
        <td data-label-vi="Số hiệu" data-label-en="Number"><span class="document-number">${esc(document.document_number || '—')}</span></td>
        <td data-label-vi="Văn bản" data-label-en="Document"><button class="table-link" type="button" data-document-id="${esc(document.id)}">${esc(document.title)}</button><span class="table-subtext">${esc(topicNames(document))}</span></td>
        <td data-label-vi="Loại văn bản" data-label-en="Type">${esc(labelize(document.document_type))}</td>
        <td data-label-vi="Cơ quan" data-label-en="Agency">${esc(agencyNames(document))}</td>
        <td data-label-vi="Trạng thái" data-label-en="Status">${Components.statusBadge(statusForDisplay(document))}</td>
        <td data-label-vi="Ban hành / Dự thảo" data-label-en="Issued / Draft">${esc(App.formatDate(document.issued_date || document.draft_published_date))}</td>
        <td data-label-vi="Hiệu lực" data-label-en="Effective">${esc(App.formatDate(document.effective_date))}<span class="table-subtext">${document.effective_date ? esc(daysLabel(document)) : ''}</span></td>
      </tr>
    `).join('');
    return `
      <div class="table-wrap${compact ? ' table-wrap--legal-overview' : ''}">
        <table class="data-table data-table--legal mobile-record-table${compact ? ' data-table--legal-overview' : ''}">
          <thead><tr><th>Number</th><th>Document</th><th>Type</th><th>Agency</th><th>Status</th><th>Issued / Draft</th><th>Effective</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="7" class="table-empty">No documents match the selected filters.</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  function renderOverview() {
    const metrics = overviewMetrics().map(Components.compactMetric).join('');
    const latest = latestDocuments(5);
    const upcoming = upcomingDocuments().slice(0, 5);
    const recent = recentlyEffective(30);
    const topicCards = data.topics
      .map(topic => ({ topic, count: data.documents.filter(document => (document.topic_ids || []).includes(topic.id)).length }))
      .filter(item => item.count)
      .sort((a,b) => b.count - a.count)
      .slice(0, 4)
      .map(({topic,count}) => `<a class="legal-topic-card" href="legal.html?view=documents&topic=${encodeURIComponent(topic.id)}"><span class="eyebrow">Topic</span><strong>${esc(topic.name)}</strong><span>${esc(String(count))} documents</span></a>`)
      .join('');

    setView(`
      <div class="market-metric-grid">${metrics}</div>
      <div class="market-layout market-layout--overview market-layout--legal-overview">
        <section class="section market-panel market-panel--wide market-panel--legal-documents">
          <div class="section-header"><div><span class="eyebrow">Official document layer</span><h2 class="section-title">Latest Documents</h2></div><a class="text-link" href="legal.html?view=documents">Open database</a></div>
          <div class="section-body section-body--table">${documentTable(latest, { compact: true })}</div>
        </section>
        <section class="section market-panel market-panel--legal-timeline">
          <div class="section-header"><div><span class="eyebrow">Upcoming</span><h2 class="section-title">Effective Timeline</h2></div><a class="text-link" href="legal.html?view=effective-soon">View all</a></div>
          <div class="section-body legal-timeline-list">${upcoming.map(document => `
            <button class="legal-timeline-item" type="button" data-document-id="${esc(document.id)}">
              <span class="legal-timeline-item__date">${esc(App.formatDate(document.effective_date))}</span>
              <strong>${esc(document.title)}</strong>
              <span>${esc(daysLabel(document))} · ${esc(labelize(document.document_type))}</span>
            </button>`).join('') || '<p class="muted-text">No upcoming effective dates.</p>'}
          </div>
        </section>
      </div>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Research shortcuts</span><h2 class="section-title">Legal Topics</h2></div><a class="text-link" href="legal.html?view=topics">All topics</a></div>
        <div class="section-body"><div class="legal-topic-grid legal-topic-grid--compact">${topicCards}</div></div>
      </section>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Recently active</span><h2 class="section-title">Recently Effective</h2></div></div>
        <div class="section-body">${recent.length ? `<div class="legal-recent-grid">${recent.map(document => `<button type="button" class="legal-recent-card" data-document-id="${esc(document.id)}"><span>${esc(App.formatDate(document.effective_date))}</span><strong>${esc(document.title)}</strong><small>${esc(agencyNames(document))}</small></button>`).join('')}</div>` : '<p class="muted-text">No documents became effective in the last 30 days.</p>'}</div>
      </section>
    `);
  }

  function renderDocuments() {
    const records = matchesFilters(data.documents)
      .sort((a,b) => String(b.issued_date || b.draft_published_date || '').localeCompare(String(a.issued_date || a.draft_published_date || '')));
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Official document database</span><h2>${records.length} documents</h2><p>Filter structured legal records by type, status, issuing agency, topic and scope. Media analysis remains a separate evidence layer.</p></div></div>
      ${filterToolbar()}
      <section class="section"><div class="section-body section-body--table">${documentTable(records)}</div></section>
    `);
    bindFilters();
  }

  function effectiveGroup(title, subtitle, records) {
    return `
      <section class="section effective-group">
        <div class="section-header"><div><span class="eyebrow">${esc(subtitle)}</span><h2 class="section-title">${esc(title)}</h2></div><span class="effective-count">${records.length}</span></div>
        <div class="section-body">${records.length ? records.map(document => `
          <button class="effective-row" type="button" data-document-id="${esc(document.id)}">
            <div class="effective-row__date"><strong>${esc(App.formatDate(document.effective_date))}</strong><span>${esc(daysLabel(document))}</span></div>
            <div><span class="document-number">${esc(document.document_number)}</span><h3>${esc(document.title)}</h3><p>${esc(agencyNames(document))} · ${esc(topicNames(document))}</p></div>
            <div>${Components.statusBadge(statusForDisplay(document))}</div>
          </button>`).join('') : '<p class="muted-text">No documents in this window.</p>'}</div>
      </section>
    `;
  }

  function renderEffectiveSoon() {
    let records = matchesFilters(data.documents).filter(document => effectiveBucket(document));
    records.sort((a,b) => String(a.effective_date).localeCompare(String(b.effective_date)));
    const next30 = records.filter(item => effectiveBucket(item) === '30');
    const next90 = records.filter(item => effectiveBucket(item) === '90');
    const later = records.filter(item => effectiveBucket(item) === 'later');
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Effective-date monitor</span><h2>Effective Soon</h2><p>Upcoming dates are derived from canonical effective dates; “effective soon” is never stored as source-of-truth.</p></div></div>
      ${filterToolbar({ compact: true })}
      ${effectiveGroup('Next 30 Days','Near term',next30)}
      ${effectiveGroup('31–90 Days','Upcoming',next90)}
      ${effectiveGroup('Later','Longer horizon',later)}
    `);
    bindFilters();
  }

  function renderTopics() {
    const cards = data.topics.map(topic => {
      const docs = data.documents.filter(document => (document.topic_ids || []).includes(topic.id));
      const upcoming = docs.filter(document => effectiveBucket(document)).length;
      const draft = docs.filter(document => document.status === 'draft').length;
      return `
        <article class="legal-topic-detail-card">
          <span class="eyebrow">Legal topic</span>
          <h3>${esc(topic.name)}</h3>
          <p>${esc(topic.description)}</p>
          <div class="legal-topic-stats"><span><strong>${docs.length}</strong> documents</span><span><strong>${upcoming}</strong> upcoming</span><span><strong>${draft}</strong> drafts</span></div>
          <a class="text-link" href="legal.html?view=documents&topic=${encodeURIComponent(topic.id)}">Open documents</a>
        </article>`;
    }).join('');
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Controlled taxonomy</span><h2>${data.topics.length} legal topics</h2><p>Topics are controlled categories used for document filters and research links, rather than free-text tags invented by the crawler.</p></div></div>
      <div class="legal-topic-grid">${cards}</div>
    `);
  }

  function articleMatchesFilters(article) {
    if (!DataStore.isNewsFor(article, 'legal')) return false;
    const relatedDocs = Resolver.getEntities('legal-document', article.legal_document_ids || []);
    if (state.agency && !relatedDocs.some(document => (document.agency_ids || []).includes(state.agency))) return false;
    if (state.topic && !relatedDocs.some(document => (document.topic_ids || []).includes(state.topic))) return false;
    if (state.q && !FilterEngine.textMatch(article, state.q, ['title','summary','tags', () => relatedDocs.map(document => `${document.document_number} ${document.title}`).join(' ')])) return false;
    return true;
  }

  function newsFilterToolbar() {
    const agencyOptions = data.agencies.map(item => option(item.name, item.id, state.agency)).join('');
    const topicOptions = data.topics.map(item => option(item.name, item.id, state.topic)).join('');
    return `
      <div class="filter-bar filter-bar--news" data-legal-filters>
        <label class="filter-field filter-field--search"><span>Search</span><input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Analysis, document or topic…"></label>
        <label class="filter-field"><span>Agency</span><select data-filter="agency">${option('All agencies','',state.agency)}${agencyOptions}</select></label>
        <label class="filter-field"><span>Topic</span><select data-filter="topic">${option('All topics','',state.topic)}${topicOptions}</select></label>
        <button class="button filter-reset" type="button" data-filter-reset>Reset</button>
      </div>`;
  }

  function renderNews() {
    setView(MarketNewsUI.render({
      module: 'legal',
      articles: data.articles,
      regions: data.regions,
      state
    }));
    MarketNewsUI.bind({state, refresh: renderNews});
  }

  function relationRows(document) {
    const direct = (document.related_documents || []).map(relation => ({
      label: RELATION_LABELS[relation.relation_type] || labelize(relation.relation_type),
      document: Resolver.getEntity('legal-document', relation.document_id)
    }));
    const reverse = data.documents.flatMap(other => (other.related_documents || [])
      .filter(relation => relation.document_id === document.id)
      .map(relation => ({
        label: REVERSE_RELATION_LABELS[relation.relation_type] || `Related from ${labelize(relation.relation_type)}`,
        document: other
      })));
    return [...direct, ...reverse].filter(item => item.document);
  }

  function lifecycleHTML(document) {
    const timeline = window.HistoryEngine?.legalTimeline?.(document, data.documents) || [];
    if (!timeline.length) return '<p class="muted-text">No lifecycle dates available.</p>';
    const today = new Date();
    const lastPastIndex = timeline.reduce((idx, item, i) => {
      const dt = item.date ? new Date(`${item.date}T00:00:00`) : null;
      return dt && dt <= today ? i : idx;
    }, -1);
    return `<div class="legal-lifecycle">${timeline.map((item, index) => {
      const future = item.date ? new Date(`${item.date}T00:00:00`) > today : false;
      const state = future ? 'upcoming' : (index === lastPastIndex ? 'current' : 'done');
      const detail = item.detail ? `<span>${esc(App.formatDate(item.date))} · ${esc(item.detail)}</span>` : `<span>${esc(App.formatDate(item.date))}</span>`;
      return `<div class="legal-lifecycle__item is-${esc(state)}"><span class="legal-lifecycle__dot"></span><div><strong>${esc(item.title)}</strong>${detail}</div></div>`;
    }).join('')}</div>`;
  }

  function documentDrawerHTML(document) {
    const relations = relationRows(document);
    const relatedArticles = data.articles.filter(article => (article.legal_document_ids || []).includes(document.id)).sort((a,b) => String(b.published_at).localeCompare(String(a.published_at)));
    const days = daysUntil(document.effective_date);
    const effectiveMetric = document.effective_date ? (days !== null && days > 0 ? `In ${days} days` : App.formatDate(document.effective_date)) : '—';
    return `
      <div class="drawer-entity-head">
        <span class="eyebrow">${esc(labelize(document.document_type))}</span>
        <h2>${esc(document.title)}</h2>
        <p>${esc(document.document_number)} · ${esc(agencyNames(document))}</p>
        ${Components.statusBadge(statusForDisplay(document))}
      </div>
      <div class="drawer-metrics">
        ${Components.compactMetric({label:'Issued',value:App.formatDate(document.issued_date || document.draft_published_date)})}
        ${Components.compactMetric({label:'Effective',value:effectiveMetric,note:document.effective_date ? App.formatDate(document.effective_date) : ''})}
        ${Components.compactMetric({label:'Scope',value:labelize(document.scope_type),note:regionNames(document)})}
        ${Components.compactMetric({label:'Topics',value:String((document.topic_ids || []).length),note:topicNames(document)})}
      </div>
      <div class="drawer-section"><h3>Overview</h3><p>${esc(document.summary)}</p></div>
      <div class="drawer-section"><h3>Lifecycle</h3>${lifecycleHTML(document)}</div>
      <div class="drawer-section"><h3>Key Changes</h3><ul class="drawer-bullet-list">${(document.key_changes || []).map(item => `<li>${esc(item)}</li>`).join('') || '<li>No structured change notes.</li>'}</ul></div>
      <div class="drawer-section"><h3>Topics</h3><div class="chip-row">${(document.topic_ids || []).map(id => `<a class="relation-chip" href="legal.html?view=documents&topic=${encodeURIComponent(id)}">${esc(Resolver.getLabel('legal-topic', id, labelize(id)))}</a>`).join('')}</div></div>
      <div class="drawer-section"><h3>Related Regulations</h3>${relations.length ? relations.map(item => `<button type="button" class="drawer-list-row drawer-relation-row" data-document-id="${esc(item.document.id)}"><div><span>${esc(item.label)}</span><strong>${esc(item.document.document_number)} · ${esc(item.document.title)}</strong></div><span>›</span></button>`).join('') : '<p class="muted-text">No related-document records.</p>'}</div>
      <div class="drawer-section"><h3>Related Market Research</h3>${relatedMarketProjects(document).length ? `${relatedMarketProjects(document).map(project => `<div class="drawer-list-row"><div><strong>${esc(project.name)}</strong><span>${esc(project.location_text || '')}</span></div><a class="text-link" href="market.html?view=projects&project=${encodeURIComponent(project.id)}">Open</a></div>`).join('')}<p class="muted-text">Links are based on shared research topics only and do not determine legal applicability to a specific project.</p>` : '<p class="muted-text">No project research links for the current topics.</p>'}</div>
      <div class="drawer-section"><h3>Related Analysis / News</h3>${relatedArticles.length ? relatedArticles.map(article => `<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(article.published_at))} · ${esc(article.content_type)} · ${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}</span><strong>${esc(article.title)}</strong></div>`).join('') : '<p class="muted-text">No related analysis.</p>'}</div>
      <div class="drawer-section official-source-box"><h3>Official Source</h3><div class="provenance-inline-row">${sourceRef(document.primary_source_id,{sourceDate:document.issued_date,sourceUrl:document.official_url})}</div>${document.official_url ? `<p><a class="text-link" href="${esc(document.official_url)}" target="_blank" rel="noopener noreferrer">Open official document ↗</a></p>` : '<p>Official URL is not available for this record. Source metadata remains visible through the registry.</p>'}</div>
    `;
  }

  function openDocument(documentId, { push = true } = {}) {
    const document = Resolver.getEntity('legal-document', documentId);
    if (!document) return;
    if (push) App.setQueryParam('document', documentId, { push: true });
    App.openDrawer({ title: document.document_number || 'Legal document', html: documentDrawerHTML(document) });
  }

  function updateFilterParam(key, value) {
    state[key] = value;
    App.setQueryParam(key, value || null);
    render();
  }

  function bindFilters() {
    document.querySelectorAll('[data-filter]').forEach(control => {
      control.addEventListener('change', () => updateFilterParam(control.dataset.filter, control.value.trim()));
    });
    document.querySelector('[data-filter-reset]')?.addEventListener('click', () => {
      FILTER_KEYS.forEach(key => {
        state[key] = '';
        App.removeQueryParam(key);
      });
      render();
    });
  }

  function setView(html) {
    const node = document.querySelector('[data-legal-view]');
    if (node) node.innerHTML = html;
  }

  function render() {
    updateTabs();
    if (state.view === 'documents') renderDocuments();
    else if (state.view === 'effective-soon') renderEffectiveSoon();
    else if (state.view === 'topics') renderTopics();
    else if (state.view === 'news') renderNews();
    else renderOverview();
  }

  function bindDelegatedEvents() {
    document.addEventListener('click', event => {
      const target = event.target.closest('[data-document-id]');
      if (!target) return;
      event.preventDefault();
      openDocument(target.dataset.documentId);
    });

    document.addEventListener('app:drawer-closed', () => {
      if (App.getQueryParam('document')) App.removeQueryParam('document');
    });

    window.addEventListener('popstate', () => {
      parseState();
      render();
      const documentId = App.getQueryParam('document');
      if (documentId) openDocument(documentId, { push: false });
      else App.closeDrawer();
    });
  }

  async function load() {
    try {
      await window.Provenance?.load?.();
      const [agencies, topics, documents, articles, regions, projects, meta] = await Promise.all([
        DataStore.getAgencies(), DataStore.getLegalTopics(), DataStore.getLegalDocuments(), DataStore.getArticles(), DataStore.getRegions(), DataStore.getProjects(), DataStore.getMeta()
      ]);
      data = {
        agencies: payloadData(agencies),
        topics: payloadData(topics),
        documents: payloadData(documents),
        articles: payloadData(articles),
        regions: payloadData(regions),
        projects: payloadData(projects)
      };
      Resolver.setData('agency', data.agencies);
      Resolver.setData('legal-topic', data.topics);
      Resolver.setData('legal-document', data.documents);
      Resolver.setData('region', data.regions);
      Resolver.setData('real-estate-project', data.projects);
      parseState();
      const updated = document.querySelector('[data-legal-updated]');
      if (updated) updated.textContent = `Official registry · ${data.documents.length} documents`;
      render();
      const documentId = App.getQueryParam('document');
      if (documentId) openDocument(documentId, { push: false });
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load Legal registry data. Check that the site is running through a web server.', 'error'));
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindDelegatedEvents();
    load();
  });
})();
