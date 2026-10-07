(() => {
  'use strict';

  const MIN_CHARS = 2;
  const MAX_RESULTS = 12;
  const GROUP_ORDER = ['project', 'developer', 'legal-document', 'infrastructure-project', 'macro-indicator', 'event', 'article'];
  const TYPE_LABELS = {
    project: 'Projects',
    developer: 'Developers',
    'legal-document': 'Legal Documents',
    'infrastructure-project': 'Infrastructure',
    'macro-indicator': 'Macro Indicators',
    event: 'Events',
    article: 'Articles & Research'
  };
  const ENTITY_BOOST = {
    project: 45,
    developer: 42,
    'legal-document': 45,
    'infrastructure-project': 45,
    'macro-indicator': 45,
    event: 16,
    article: 10
  };

  let indexPromise = null;
  let searchIndex = [];
  let debounceTimer = null;

  function payloadData(payload) { return payload?.data || []; }
  function esc(value) { return window.Components?.escapeHTML ? Components.escapeHTML(value) : String(value ?? ''); }

  function normalizeText(value) {
    return String(value ?? '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .trim()
      .replace(/\s+/g, ' ');
  }

  function tokens(value) {
    return normalizeText(value).split(' ').filter(Boolean);
  }

  function arrayText(values = []) {
    return (values || []).filter(Boolean).join(' ');
  }

  function byId(records = []) {
    return new Map(records.map(item => [item.id, item]));
  }

  function labels(ids = [], map) {
    return (ids || []).map(id => map.get(id)?.name || map.get(id)?.title || '').filter(Boolean).join(' ');
  }

  function buildHref(item) {
    const id = encodeURIComponent(item.id);
    if (item.type === 'project') return `market.html?view=projects&project=${id}`;
    if (item.type === 'developer') return `market.html?view=projects&developer=${id}`;
    if (item.type === 'legal-document') return `legal.html?view=documents&document=${id}`;
    if (item.type === 'infrastructure-project') return `infrastructure.html?view=projects&project=${id}`;
    if (item.type === 'macro-indicator') return `macro.html?indicator=${id}`;
    if (item.type === 'event') {
      const entityId = encodeURIComponent(item.entityId || '');
      if (item.entityType === 'real-estate-project') return `market.html?view=projects&project=${entityId}`;
      if (item.entityType === 'legal-document') return `legal.html?view=documents&document=${entityId}`;
      if (item.entityType === 'infrastructure-project') return `infrastructure.html?view=projects&project=${entityId}`;
      if (item.entityType === 'macro-indicator') return `macro.html?indicator=${entityId}`;
      if (item.category === 'infrastructure') return `infrastructure.html?view=timeline&q=${encodeURIComponent(item.title)}`;
      if (item.category === 'macro') return `macro.html?view=news&q=${encodeURIComponent(item.title)}`;
      return `index.html`;
    }
    if (item.type === 'article') {
      const q = encodeURIComponent(item.title);
      if (item.category === 'market') return `market.html?view=news&q=${q}`;
      if (item.category === 'legal') return `legal.html?view=news&q=${q}`;
      if (item.category === 'infrastructure') return `infrastructure.html?view=news&q=${q}`;
      if (item.category === 'macro') return `macro.html?view=news&q=${q}`;
    }
    return 'index.html';
  }

  function makeItem({ type, id, title, subtitle = '', meta = '', aliases = '', extra = '', importance = 0, date = '', category = '', entityType = '', entityId = '' }) {
    const item = { type, id, title, subtitle, meta, importance, date, category, entityType, entityId };
    item.href = buildHref(item);
    item.fields = [
      { text: id, weight: 1.35, kind: 'id' },
      { text: title, weight: 1.25, kind: 'title' },
      { text: aliases, weight: 1.15, kind: 'alias' },
      { text: subtitle, weight: 0.82, kind: 'subtitle' },
      { text: meta, weight: 0.72, kind: 'meta' },
      { text: extra, weight: 0.58, kind: 'extra' }
    ].filter(field => field.text);
    return item;
  }

  async function buildIndex() {
    if (indexPromise) return indexPromise;
    indexPromise = (async () => {
      const loaders = [
        ['regions', DataStore.getRegions],
        ['developers', DataStore.getDevelopers],
        ['agencies', DataStore.getAgencies],
        ['topics', DataStore.getLegalTopics],
        ['projects', DataStore.getProjects],
        ['legal', DataStore.getLegalDocuments],
        ['infrastructure', DataStore.getInfrastructureProjects],
        ['indicators', DataStore.getMacroIndicators],
        ['articles', DataStore.getArticles],
        ['events', DataStore.getEvents],
        ['productionMacro', DataStore.getProcessedMacroObservations]
      ];

      const settled = await Promise.allSettled(loaders.map(([, loader]) => loader()));
      const datasets = {};
      settled.forEach((result, index) => {
        const key = loaders[index][0];
        datasets[key] = result.status === 'fulfilled' ? payloadData(result.value) : [];
        if (result.status === 'rejected') console.warn(`Global search: unable to load ${key}`, result.reason);
      });

      const regionMap = byId(datasets.regions);
      const developerMap = byId(datasets.developers);
      const agencyMap = byId(datasets.agencies);
      const topicMap = byId(datasets.topics);
      const projectMap = byId(datasets.projects);
      const legalMap = byId(datasets.legal);
      const infraMap = byId(datasets.infrastructure);
      const indicatorMap = byId(datasets.indicators);
      const productionMacroRows = datasets.productionMacro || [];
      const latestMacroMap = new Map();
      productionMacroRows.forEach(row => {
        const key = row.indicator_id;
        const current = latestMacroMap.get(key);
        const rowKey = `${row.period || ''}|${row.data_date || ''}|${row.published_at || ''}`;
        const currentKey = current ? `${current.period || ''}|${current.data_date || ''}|${current.published_at || ''}` : '';
        if (!current || rowKey > currentKey) latestMacroMap.set(key, row);
      });

      function macroValue(row) {
        if (!row || row.value === null || row.value === undefined) return '';
        const value = Number(row.value);
        const formatted = Number.isFinite(value) ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : String(row.value);
        if (row.unit === 'percent') return `${formatted}%`;
        if (row.unit === 'percent-per-year') return `${formatted}% p.a.`;
        if (row.unit === 'vnd-per-usd') return `${formatted} VND/USD`;
        if (row.unit === 'vnd-per-tael') return `${formatted} VND/tael`;
        return `${formatted} ${row.unit || ''}`.trim();
      }

      const result = [];

      datasets.projects.forEach(project => {
        const relatedInfrastructure = labels(project.related_infrastructure_ids, infraMap);
        const legalTopics = labels(project.related_legal_topic_ids, topicMap);
        result.push(makeItem({
          type: 'project', id: project.id, title: project.name,
          subtitle: `${project.location_text || ''}${project.lead_developer_id ? ` · ${developerMap.get(project.lead_developer_id)?.name || ''}` : ''}`,
          meta: `${labels(project.region_ids, regionMap)} · ${arrayText(project.segment_ids)} · ${project.status || ''}`,
          extra: `${project.summary || ''} ${relatedInfrastructure} ${legalTopics}`
        }));
      });

      datasets.developers.forEach(developer => {
        result.push(makeItem({
          type: 'developer', id: developer.id, title: developer.name,
          aliases: arrayText(developer.aliases),
          subtitle: labels(developer.region_ids, regionMap),
          meta: arrayText(developer.segment_ids),
          extra: developer.summary || ''
        }));
      });

      datasets.legal.forEach(document => {
        result.push(makeItem({
          type: 'legal-document', id: document.id, title: document.title,
          aliases: document.document_number,
          subtitle: `${document.document_number || ''} · ${arrayText((document.agency_ids || []).map(id => agencyMap.get(id)?.name || id))}`,
          meta: `${arrayText((document.topic_ids || []).map(id => topicMap.get(id)?.name || id))} · ${document.document_type || ''} · ${document.status || ''}`,
          extra: `${document.summary || ''} ${arrayText(document.key_changes)}`,
          date: document.issued_date || ''
        }));
      });

      datasets.infrastructure.forEach(project => {
        const relatedProjects = labels(project.related_real_estate_project_ids, projectMap);
        result.push(makeItem({
          type: 'infrastructure-project', id: project.id, title: project.name,
          subtitle: project.location_text || labels(project.region_ids, regionMap),
          meta: `${project.infrastructure_type || ''} · ${project.status || ''} · ${labels(project.region_ids, regionMap)}`,
          extra: `${project.summary || ''} ${relatedProjects}`
        }));
      });

      datasets.indicators.forEach(indicator => {
        const latest = latestMacroMap.get(indicator.id);
        const latestLabel = latest ? `${macroValue(latest)} · ${latest.period || latest.data_date || ''}` : '';
        result.push(makeItem({
          type: 'macro-indicator', id: indicator.id, title: indicator.name,
          subtitle: latestLabel || `${indicator.indicator_category || ''} · ${indicator.frequency || ''}`,
          meta: `${indicator.indicator_category || ''} · ${indicator.indicator_subcategory || ''} · ${indicator.frequency || ''} · ${indicator.unit || ''}`,
          extra: `${indicator.description || ''} ${indicator.methodology_note || ''} ${latest?.evidence_status || ''}`
        }));
      });

      datasets.articles.forEach(article => {
        const related = [
          labels(article.region_ids, regionMap),
          labels(article.project_ids, projectMap),
          labels(article.developer_ids, developerMap),
          labels(article.legal_document_ids, legalMap),
          labels(article.infrastructure_project_ids, infraMap),
          labels(article.indicator_ids, indicatorMap)
        ].filter(Boolean).join(' ');
        result.push(makeItem({
          type: 'article', id: article.id, title: article.title,
          subtitle: `${article.category || ''} · ${article.content_type || ''}`,
          meta: related,
          extra: `${article.summary || ''} ${arrayText(article.tags)}`,
          importance: article.importance || 0,
          date: article.published_at || '',
          category: article.category || ''
        }));
      });

      datasets.events.forEach(event => {
        let entityLabel = '';
        if (event.entity_type === 'real-estate-project') entityLabel = projectMap.get(event.entity_id)?.name || '';
        else if (event.entity_type === 'legal-document') entityLabel = legalMap.get(event.entity_id)?.title || '';
        else if (event.entity_type === 'infrastructure-project') entityLabel = infraMap.get(event.entity_id)?.name || '';
        else if (event.entity_type === 'macro-indicator') entityLabel = indicatorMap.get(event.entity_id)?.name || '';
        result.push(makeItem({
          type: 'event', id: event.id, title: event.title,
          subtitle: `${event.category || ''} · ${event.event_type || ''}`,
          meta: `${entityLabel} ${labels(event.region_ids, regionMap)}`,
          extra: event.summary || '',
          importance: event.importance || 0,
          date: event.event_date || '',
          category: event.category || '',
          entityType: event.entity_type || '',
          entityId: event.entity_id || ''
        }));
      });

      searchIndex = result;
      return searchIndex;
    })().catch(error => {
      indexPromise = null;
      throw error;
    });
    return indexPromise;
  }

  function fieldScore(field, query, queryTokens) {
    const text = normalizeText(field.text);
    if (!text) return 0;
    const weight = field.weight || 1;
    let score = 0;

    if (text === query) score = 180;
    else if (text.startsWith(query)) score = 120;
    else if (text.includes(query)) score = 82;
    else {
      const textTokens = text.split(' ');
      const matched = queryTokens.filter(token => textTokens.some(textToken => textToken === token || textToken.startsWith(token)));
      if (matched.length === queryTokens.length) score = 58 + matched.length * 5;
      else if (matched.length) score = 18 + matched.length * 4;
    }

    // Very short aliases should only rank when the alias itself is an exact token match.
    if (field.kind === 'alias' && query.length <= 3 && !text.split(' ').includes(query)) return 0;
    return score * weight;
  }

  function scoreItem(item, rawQuery) {
    const query = normalizeText(rawQuery);
    if (!query) return 0;
    const queryTokens = tokens(query);
    const combinedTokens = item.fields.flatMap(field => tokens(field.text));
    if (queryTokens.length > 1 && !queryTokens.every(token => combinedTokens.some(candidate => candidate === token || candidate.startsWith(token)))) return 0;
    let best = 0;
    let cumulative = 0;
    item.fields.forEach(field => {
      const score = fieldScore(field, query, queryTokens);
      best = Math.max(best, score);
      cumulative += score * 0.22;
    });
    if (!best) return 0;
    const importance = Math.min(Number(item.importance || 0), 5) * 1.5;
    return best + cumulative + (ENTITY_BOOST[item.type] || 0) + importance;
  }

  function search(rawQuery) {
    const query = normalizeText(rawQuery);
    if (query.length < MIN_CHARS) return [];
    return searchIndex
      .map(item => ({ ...item, score: scoreItem(item, query) }))
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score || String(b.date || '').localeCompare(String(a.date || '')) || a.title.localeCompare(b.title))
      .slice(0, MAX_RESULTS);
  }

  function resultMarkup(item) {
    const date = item.date ? App.formatDate(item.date) : '';
    return `<a class="search-result-item" href="${esc(item.href)}" data-search-result>
      <div class="search-result-item__main">
        <strong>${esc(item.title)}</strong>
        ${item.subtitle ? `<span>${esc(item.subtitle)}</span>` : ''}
      </div>
      <div class="search-result-item__aside">
        <span class="search-type-badge">${esc(TYPE_LABELS[item.type]?.replace(/s$/, '') || item.type)}</span>
        ${date ? `<small>${esc(date)}</small>` : ''}
      </div>
    </a>`;
  }

  function renderResults(results, query) {
    const container = document.querySelector('[data-global-search-results]');
    const status = document.querySelector('[data-global-search-status]');
    if (!container || !status) return;

    if (normalizeText(query).length < MIN_CHARS) {
      status.textContent = 'Type at least 2 characters. Vietnamese accents are optional.';
      container.innerHTML = `<div class="search-empty-state">Try “Izumi”, “NLG”, “Đồng Nai”, “CPI”, “airport” or a legal document number.</div>`;
      return;
    }

    if (!results.length) {
      status.textContent = `No matches for “${query}”.`;
      container.innerHTML = '<div class="search-empty-state">No structured records match this query. Try a broader project, region, topic or indicator name.</div>';
      return;
    }

    status.textContent = `${results.length} best matches across the integrated research registry.`;
    const grouped = new Map();
    results.forEach(item => {
      if (!grouped.has(item.type)) grouped.set(item.type, []);
      grouped.get(item.type).push(item);
    });
    container.innerHTML = GROUP_ORDER
      .filter(type => grouped.has(type))
      .map(type => `<section class="search-result-group"><div class="search-result-group__title">${esc(TYPE_LABELS[type])}</div>${grouped.get(type).map(resultMarkup).join('')}</section>`)
      .join('');
  }

  async function handleQuery(query) {
    const container = document.querySelector('[data-global-search-results]');
    const status = document.querySelector('[data-global-search-status]');
    if (!container || !status) return;
    if (normalizeText(query).length < MIN_CHARS) {
      renderResults([], query);
      return;
    }
    status.textContent = 'Searching structured datasets…';
    container.innerHTML = '<div class="search-loading">Loading research index…</div>';
    try {
      await buildIndex();
      renderResults(search(query), query);
    } catch (error) {
      console.error(error);
      status.textContent = 'Search index could not be loaded.';
      container.innerHTML = '<div class="search-empty-state search-empty-state--error">Unable to load the integrated search datasets. Refresh the page and try again.</div>';
    }
  }

  function bind() {
    const input = document.querySelector('[data-global-search-input]');
    const results = document.querySelector('[data-global-search-results]');
    if (!input || !results) return;

    renderResults([], '');

    input.addEventListener('input', () => {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => handleQuery(input.value.trim()), 180);
    });

    input.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown') {
        const first = results.querySelector('[data-search-result]');
        if (first) {
          event.preventDefault();
          first.focus();
        }
      }
      if (event.key === 'Enter') {
        const first = results.querySelector('[data-search-result]');
        if (first && normalizeText(input.value).length >= MIN_CHARS) {
          event.preventDefault();
          first.click();
        }
      }
    });

    results.addEventListener('keydown', event => {
      const items = [...results.querySelectorAll('[data-search-result]')];
      const index = items.indexOf(document.activeElement);
      if (index < 0) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        items[Math.min(index + 1, items.length - 1)]?.focus();
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (index === 0) input.focus();
        else items[index - 1]?.focus();
      }
    });

    document.addEventListener('app:search-opened', () => {
      if (input.value.trim()) handleQuery(input.value.trim());
    });
  }

  window.SearchEngine = { normalizeText, buildIndex, search };
  document.addEventListener('DOMContentLoaded', bind);
})();
