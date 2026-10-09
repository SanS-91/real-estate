(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'projects', 'regions', 'timeline', 'news'];
  const FILTER_KEYS = ['q', 'region', 'type', 'status', 'completion', 'projectFilter', 'event'];

  let state = {
    view: 'overview', q: '', region: '', type: '', status: '', completion: '', projectFilter: '', event: ''
  };

  let data = {
    regions: [], infrastructureProjects: [], schedules: [], events: [], articles: [], realEstateProjects: []
  };

  function payloadData(payload) { return payload?.data || []; }
  function esc(value) { return Components.escapeHTML(value); }

  function sourceRef(sourceId, context = {}) {
    return window.Provenance?.sourceButton?.(sourceId, context) || `<span class="source-tag">${esc(labelize(sourceId))}</span>`;
  }

  function labelize(value) {
    return String(value || '—').replaceAll('-', ' ').replace(/\b\w/g, char => char.toUpperCase());
  }

  function isVietnamese() {
    return String(document.documentElement.lang || 'en').toLowerCase().startsWith('vi');
  }

  function infrastructureStatusLabel(status) {
    const key = String(status || 'unknown');
    if (!isVietnamese()) return labelize(key);
    const labels = {
      'under-construction': 'Đang thi công',
      'operational': 'Đang vận hành',
      'land-clearance': 'Giải phóng mặt bằng',
      'partially-operational': 'Vận hành một phần',
      'approved': 'Đã phê duyệt',
      'planning': 'Lập kế hoạch',
      'proposed': 'Đề xuất',
      'completed': 'Hoàn thành'
    };
    return labels[key] || labelize(key);
  }

  function infrastructureStatusBadge(status) {
    const key = String(status || 'unknown');
    return `<span class="status-badge status-badge--${esc(key)}">${esc(infrastructureStatusLabel(key))}</span>`;
  }

  function formatCompact(value) {
    return window.Formatters?.compact?.(value) ?? (value === null || value === undefined ? '—' : String(value));
  }

  function formatInvestment(project) {
    if (project.current_total_investment === null || project.current_total_investment === undefined) return '—';
    return window.Formatters?.investment?.(project.current_total_investment, project.investment_currency || 'VND', project.investment_unit || 'bn')
      ?? `${project.current_total_investment} ${project.investment_currency || 'VND'} ${project.investment_unit || ''}`.trim();
  }

  function targetSortValue(value) {
    if (!value) return Number.POSITIVE_INFINITY;
    const year = Number(String(value).slice(0, 4));
    const quarter = String(value).match(/Q([1-4])/i);
    return year * 10 + (quarter ? Number(quarter[1]) : 0);
  }

  function formatTarget(value) {
    if (!value) return '—';
    const match = String(value).match(/^(\d{4})-Q([1-4])$/i);
    if (match) return `Q${match[2]} ${match[1]}`;
    return String(value);
  }

  function regionNames(project) {
    const viNames = {
      'hcmc': 'TPHCM',
      'dong-nai': 'Đồng Nai',
      'long-an': 'Long An',
      'binh-duong': 'Bình Dương'
    };
    return Resolver.getEntities('region', project.region_ids || [])
      .map(item => isVietnamese() ? (viNames[item.id] || item.name || item.short_name) : (item.short_name || item.name))
      .join(', ') || '—';
  }

  function relatedRealEstate(project) {
    return Resolver.getEntities('real-estate-project', project.related_real_estate_project_ids || []);
  }

  function schedulesFor(projectId) {
    return data.schedules
      .filter(item => item.infrastructure_project_id === projectId)
      .sort((a, b) => String(b.announced_date || '').localeCompare(String(a.announced_date || '')));
  }

  function currentSchedule(projectId, scheduleType = 'expected-completion') {
    const records = schedulesFor(projectId).filter(item => item.schedule_type === scheduleType);
    return records.find(item => item.status === 'current') || records[0] || null;
  }

  function eventsFor(projectId) {
    return data.events
      .filter(item => item.entity_id === projectId && item.entity_type === 'infrastructure-project')
      .sort((a,b) => String(b.event_date || '').localeCompare(String(a.event_date || '')));
  }

  function latestProgressEvent(projectId) {
    return eventsFor(projectId).find(item => item.event_type === 'progress' && item.event_data?.progress_percent !== undefined) || null;
  }

  function latestActivityDate(projectId) {
    const eventDate = eventsFor(projectId)[0]?.event_date || '';
    const articleDate = data.articles
      .filter(item => (item.infrastructure_project_ids || []).includes(projectId))
      .sort((a,b) => String(b.published_at || '').localeCompare(String(a.published_at || '')))[0]?.published_at || '';
    return eventDate > articleDate ? eventDate : articleDate;
  }

  function projectTypes() {
    return [...new Set(data.infrastructureProjects.map(item => item.infrastructure_type).filter(Boolean))].sort();
  }

  function projectStatuses() {
    return [...new Set(data.infrastructureProjects.map(item => item.status).filter(Boolean))].sort();
  }

  function getView() {
    const value = App.getQueryParam('view');
    return VALID_VIEWS.includes(value) ? value : 'overview';
  }

  function parseState() {
    state.view = getView();
    FILTER_KEYS.forEach(key => {
      const param = key === 'projectFilter' ? 'project-filter' : key;
      const value = App.getQueryParam(param);
      state[key] = value || '';
    });
  }

  function updateTabs() {
    document.querySelectorAll('[data-infrastructure-tabs] [data-view]').forEach(link => {
      link.classList.toggle('is-active', link.dataset.view === state.view);
    });
  }

  function option(label, value, current) {
    return `<option value="${esc(value)}"${String(current) === String(value) ? ' selected' : ''}>${esc(label)}</option>`;
  }

  function completionMatch(project) {
    if (!state.completion) return true;
    const year = Number(String(project.current_expected_completion || '').slice(0,4));
    if (!year) return false;
    if (state.completion === '2028-plus') return year >= 2028;
    return year === Number(state.completion);
  }

  function projectFilter(records) {
    const config = [
      { id: 'region', field: 'region_ids', type: 'contains-any' },
      { id: 'type', field: 'infrastructure_type', type: 'equals' },
      { id: 'status', field: 'status', type: 'equals' }
    ];
    let result = FilterEngine.apply(records, state, config).filter(completionMatch);
    if (state.q) {
      result = result.filter(project => FilterEngine.textMatch(project, state.q, [
        'name', 'location_text', 'summary', 'scale_text',
        item => regionNames(item),
        item => relatedRealEstate(item).map(project => project.name).join(' ')
      ]));
    }
    return result;
  }

  function filterToolbar({ includeCompletion = true, includeStatus = true } = {}) {
    const regions = data.regions.filter(region => data.infrastructureProjects.some(project => (project.region_ids || []).includes(region.id)));
    return `
      <div class="filter-bar filter-bar--infra" data-infrastructure-filters>
        <label class="filter-field filter-field--search"><span>Search</span><input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Project, region or related market…"></label>
        <label class="filter-field"><span>Region</span><select data-filter="region">${option('All regions','',state.region)}${regions.map(item => option(item.short_name || item.name,item.id,state.region)).join('')}</select></label>
        <label class="filter-field"><span>Type</span><select data-filter="type">${option('All types','',state.type)}${projectTypes().map(id => option(labelize(id),id,state.type)).join('')}</select></label>
        ${includeStatus ? `<label class="filter-field"><span>Status</span><select data-filter="status">${option('All statuses','',state.status)}${projectStatuses().map(id => option(labelize(id),id,state.status)).join('')}</select></label>` : ''}
        ${includeCompletion ? `<label class="filter-field"><span>Completion</span><select data-filter="completion">${option('All horizons','',state.completion)}${option('2026','2026',state.completion)}${option('2027','2027',state.completion)}${option('2028+','2028-plus',state.completion)}</select></label>` : ''}
        <button class="button filter-reset" type="button" data-filter-reset>Reset</button>
      </div>`;
  }

  function overviewMetrics() {
    const underConstruction = data.infrastructureProjects.filter(item => item.status === 'under-construction').length;
    const operational = data.infrastructureProjects.filter(item => item.status === 'operational').length;
    const nextTargets = data.infrastructureProjects.filter(item => {
      const sort = targetSortValue(item.current_expected_completion);
      return sort >= targetSortValue('2026-Q4') && sort <= targetSortValue('2027-Q4');
    }).length;
    const regionCount = new Set(data.infrastructureProjects.flatMap(item => item.region_ids || [])).size;
    return [
      { label: 'Tracked Projects', value: String(data.infrastructureProjects.length), note: 'Curated official infrastructure registry' },
      { label: 'Under Construction', value: String(underConstruction), note: 'Current master status' },
      { label: 'Operational', value: String(operational), note: 'Historical records remain searchable' },
      { label: 'Regions Covered', value: String(regionCount), note: `${nextTargets} targets through 2027` }
    ];
  }

  function progressHTML(project) {
    const progress = project.current_progress_percent;
    if (progress === null || progress === undefined) return '<span class="muted-text">No numeric progress</span>';
    return `<div class="progress-cell"><div class="progress-track"><span style="width:${Math.max(0, Math.min(100, progress))}%"></span></div><strong>${esc(progress)}%</strong></div>`;
  }

  function projectTable(records, limit = null) {
    const compact = Number.isInteger(limit) && limit > 0;
    const items = limit ? records.slice(0, limit) : records;
    const rows = items.map(project => `
      <tr>
        <td><button class="table-link" type="button" data-infra-project-id="${esc(project.id)}">${esc(project.name)}</button><span class="table-subtext">${esc(project.location_text)}</span></td>
        <td>${esc(labelize(project.infrastructure_type))}</td>
        <td>${esc(regionNames(project))}</td>
        <td>${infrastructureStatusBadge(project.status)}</td>
        <td>${progressHTML(project)}</td>
        <td>${esc(formatTarget(project.current_expected_completion))}<span class="table-subtext">${esc(project.completion_date_precision || '')}</span></td>
        <td class="numeric">${esc(String(relatedRealEstate(project).length))}</td>
      </tr>`).join('');
    return `<div class="table-wrap${compact ? ' table-wrap--infra-overview' : ''}"><table class="data-table data-table--infra${compact ? ' data-table--infra-overview' : ''}"><thead><tr><th>Infrastructure Project</th><th>Type</th><th>Region</th><th>Status</th><th>Progress</th><th>Current Target</th><th class="numeric">Related RE</th></tr></thead><tbody>${rows || '<tr><td colspan="7" class="table-empty">No infrastructure projects match the selected filters.</td></tr>'}</tbody></table></div>`;
  }

  function milestoneList(records, limit = 5) {
    return records.slice(0, limit).map(event => {
      const project = Resolver.getEntity('infrastructure-project', event.entity_id);
      return `<button class="infra-milestone" type="button" data-infra-project-id="${esc(event.entity_id)}"><span class="infra-milestone__date">${esc(App.formatDate(event.event_date))}</span><div><span class="source-tag">${esc(labelize(event.event_type))}</span><strong>${esc(event.title)}</strong><small>${esc(project?.name || 'Infrastructure')}</small></div></button>`;
    }).join('');
  }

  function renderOverview() {
    const metrics = overviewMetrics().map(Components.compactMetric).join('');
    const latestEvents = [...data.events].sort((a,b) => String(b.event_date).localeCompare(String(a.event_date)));
    const upcoming = [...data.infrastructureProjects]
      .filter(item => item.status !== 'operational' && item.current_expected_completion)
      .sort((a,b) => targetSortValue(a.current_expected_completion) - targetSortValue(b.current_expected_completion))
      .slice(0,5);
    const latestNews = [...data.articles].sort((a,b) => String(b.published_at).localeCompare(String(a.published_at))).slice(0,4);

    setView(`
      <div class="market-metric-grid">${metrics}</div>
      <div class="market-layout market-layout--overview market-layout--infra-overview">
        <section class="section market-panel market-panel--wide">
          <div class="section-header"><div><span class="eyebrow">Current situation</span><h2 class="section-title">Key Infrastructure Projects</h2></div><a class="text-link" href="infrastructure.html?view=projects">Open database</a></div>
          <div class="section-body section-body--table">${projectTable([...data.infrastructureProjects].sort((a,b) => String(latestActivityDate(b.id)).localeCompare(String(latestActivityDate(a.id)))), 5)}</div>
        </section>
        <section class="section market-panel">
          <div class="section-header"><div><span class="eyebrow">Recent milestones</span><h2 class="section-title">What Changed</h2></div><a class="text-link" href="infrastructure.html?view=timeline">View timeline</a></div>
          <div class="section-body infra-milestone-list">${milestoneList(latestEvents,5)}</div>
        </section>
      </div>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Schedule monitor</span><h2 class="section-title">Upcoming Targets</h2></div></div>
        <div class="section-body"><div class="infra-target-grid">${upcoming.map(project => `<button class="infra-target-card" type="button" data-infra-project-id="${esc(project.id)}"><span>${esc(formatTarget(project.current_expected_completion))}</span><strong>${esc(project.name)}</strong><small>${esc(regionNames(project))} · ${esc(infrastructureStatusLabel(project.status))}</small></button>`).join('')}</div></div>
      </section>
      <section class="section">
        <div class="section-header"><div><span class="eyebrow">Evidence layer</span><h2 class="section-title">Latest Infrastructure News</h2></div><a class="text-link" href="infrastructure.html?view=news">View all</a></div>
        <div class="section-body market-news-compact">${latestNews.map(article => `<article><span>${esc(App.formatDate(article.published_at))}</span><strong>${esc(article.title)}</strong></article>`).join('')}</div>
      </section>`);
  }

  function renderProjects() {
    const records = projectFilter(data.infrastructureProjects)
      .sort((a,b) => String(latestActivityDate(b.id)).localeCompare(String(latestActivityDate(a.id))));
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Infrastructure database</span><h2>${records.length} projects</h2><p>Filter structured infrastructure records, then open a project for schedule history, progress milestones and related real-estate context.</p></div></div>
      ${filterToolbar()}
      <section class="section"><div class="section-body section-body--table">${projectTable(records)}</div></section>`);
    bindFilters();
  }

  function renderRegions() {
    const cards = data.regions
      .map(region => {
        const projects = data.infrastructureProjects.filter(project => (project.region_ids || []).includes(region.id));
        if (!projects.length) return '';
        const construction = projects.filter(project => project.status === 'under-construction').length;
        const linkedProjects = new Set(projects.flatMap(project => project.related_real_estate_project_ids || [])).size;
        return `<article class="infra-region-card"><span class="eyebrow">Region</span><h3>${esc(region.name)}</h3><p>Infrastructure assets linked to the regional research database.</p><div class="infra-region-card__stats"><span><strong>${projects.length}</strong> projects</span><span><strong>${construction}</strong> construction</span><span><strong>${linkedProjects}</strong> related RE</span></div><a class="text-link" href="infrastructure.html?view=projects&region=${encodeURIComponent(region.id)}">Explore region</a></article>`;
      }).join('');
    setView(`<div class="view-intro"><div><span class="eyebrow">Regional infrastructure</span><h2>Regions</h2><p>Region cards are derived from project relationships; no duplicate region-level project lists are stored.</p></div></div><div class="infra-region-grid">${cards}</div>`);
  }

  function timelineFilters() {
    const projectOptions = data.infrastructureProjects.map(item => option(item.name,item.id,state.projectFilter)).join('');
    const eventTypes = [...new Set(data.events.map(item => item.event_type).filter(Boolean))].sort();
    return `<div class="filter-bar filter-bar--timeline"><label class="filter-field filter-field--search"><span>Search</span><input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Milestone or project…"></label><label class="filter-field"><span>Project</span><select data-filter="projectFilter">${option('All projects','',state.projectFilter)}${projectOptions}</select></label><label class="filter-field"><span>Event</span><select data-filter="event">${option('All events','',state.event)}${eventTypes.map(id => option(labelize(id),id,state.event)).join('')}</select></label><button class="button filter-reset" type="button" data-filter-reset>Reset</button></div>`;
  }

  function filteredTimelineEvents() {
    let records = [...data.events];
    if (state.projectFilter) records = records.filter(item => item.entity_id === state.projectFilter);
    if (state.event) records = records.filter(item => item.event_type === state.event);
    if (state.q) records = records.filter(item => FilterEngine.textMatch(item,state.q,['title','summary', item => Resolver.getLabel('infrastructure-project', item.entity_id)]));
    return records.sort((a,b) => String(b.event_date).localeCompare(String(a.event_date)));
  }

  function renderTimeline() {
    const records = filteredTimelineEvents();
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Project milestones</span><h2>Timeline</h2><p>Milestones are real-world events. Schedule targets remain separate history records and are never overwritten.</p></div></div>
      ${timelineFilters()}
      <section class="section"><div class="section-body"><div class="infra-timeline">${records.map(event => {
        const project = Resolver.getEntity('infrastructure-project',event.entity_id);
        const detail = event.event_type === 'progress' && event.event_data?.progress_percent !== undefined ? `${event.event_data.progress_percent}% progress` : event.event_type === 'schedule-change' ? `${formatTarget(event.event_data?.previous_target)} → ${formatTarget(event.event_data?.new_target)}` : labelize(event.event_type);
        return `<button class="infra-timeline-row" type="button" data-infra-project-id="${esc(event.entity_id)}"><div class="infra-timeline-row__date">${esc(App.formatDate(event.event_date))}</div><div class="infra-timeline-row__dot"></div><div><span class="source-tag">${esc(detail)}</span><h3>${esc(event.title)}</h3><p>${esc(project?.name || '')} · ${esc(event.summary)}</p></div></button>`;
      }).join('') || Components.stateBox('No milestones match the selected filters.')}</div></div></section>`);
    bindFilters();
  }

  function newsToolbar() {
    const regions = data.regions.filter(region => data.articles.some(article => (article.region_ids || []).includes(region.id)));
    const projectOptions = data.infrastructureProjects.map(item => option(item.name,item.id,state.projectFilter)).join('');
    return `<div class="filter-bar filter-bar--infra-news"><label class="filter-field filter-field--search"><span>Search</span><input type="search" data-filter="q" value="${esc(state.q)}" placeholder="Infrastructure news…"></label><label class="filter-field"><span>Region</span><select data-filter="region">${option('All regions','',state.region)}${regions.map(item => option(item.short_name || item.name,item.id,state.region)).join('')}</select></label><label class="filter-field"><span>Project</span><select data-filter="projectFilter">${option('All projects','',state.projectFilter)}${projectOptions}</select></label><button class="button filter-reset" type="button" data-filter-reset>Reset</button></div>`;
  }

  function renderNews() {
    let articles = [...data.articles];
    if (state.region) articles = articles.filter(item => (item.region_ids || []).includes(state.region));
    if (state.projectFilter) articles = articles.filter(item => (item.infrastructure_project_ids || []).includes(state.projectFilter));
    if (state.q) articles = articles.filter(item => FilterEngine.textMatch(item,state.q,['title','summary','tags']));
    articles.sort((a,b) => String(b.published_at).localeCompare(String(a.published_at)));
    setView(`
      <div class="view-intro"><div><span class="eyebrow" data-news-view-label="infrastructure.eyebrow">${esc(App.newsViewCopy('infrastructure').eyebrow)}</span><h2 data-news-view-label="infrastructure.title">${esc(App.newsViewCopy('infrastructure').title)}</h2><p data-news-view-label="infrastructure.description">${esc(App.newsViewCopy('infrastructure').description)}</p></div></div>
      ${newsToolbar()}
      <div class="article-list">${articles.map(article => {
        const projects = Resolver.getEntities('infrastructure-project',article.infrastructure_project_ids || []);
        const reProjects = Resolver.getEntities('real-estate-project',article.project_ids || []);
        return `<article class="article-row"><div class="article-row__date">${esc(App.formatDate(article.published_at))}</div><div><div class="article-row__meta"><span class="source-tag news-kind-chip" data-news-kind="${esc(article.content_type)}">${esc(App.newsKindLabel(article.content_type))}</span>${sourceRef(article.source_id,{publishedAt:article.published_at,sourceUrl:article.url})}<span>${esc(projects.map(item => item.name).join(' · '))}</span></div><h3>${esc(article.title)}</h3><p>${esc(article.summary)}</p>${reProjects.length ? `<div class="article-relations">${reProjects.map(project => `<a class="relation-chip" href="market.html?view=projects&project=${encodeURIComponent(project.id)}">Related RE: ${esc(project.name)}</a>`).join('')}</div>` : ''}</div></article>`;
      }).join('') || Components.stateBox('No infrastructure articles match the selected filters.')}</div>`);
    bindFilters();
  }

  function setView(html) {
    const node = document.querySelector('[data-infrastructure-view]');
    if (node) node.innerHTML = html;
  }

  function render() {
    updateTabs();
    if (state.view === 'projects') renderProjects();
    else if (state.view === 'regions') renderRegions();
    else if (state.view === 'timeline') renderTimeline();
    else if (state.view === 'news') renderNews();
    else renderOverview();
  }

  function updateFilterParam(key, value) {
    state[key] = value;
    const param = key === 'projectFilter' ? 'project-filter' : key;
    App.setQueryParam(param, value || null);
    render();
  }

  function bindFilters() {
    document.querySelectorAll('[data-filter]').forEach(control => {
      control.addEventListener('change', () => updateFilterParam(control.dataset.filter, control.value.trim()));
    });
    document.querySelector('[data-filter-reset]')?.addEventListener('click', () => {
      FILTER_KEYS.forEach(key => {
        state[key] = '';
        App.removeQueryParam(key === 'projectFilter' ? 'project-filter' : key);
      });
      render();
    });
  }

  function scheduleChangeSummaryHTML(project) {
    const change = window.HistoryEngine?.infrastructureScheduleChange?.(project.id, data.schedules);
    if (!change) return '';
    return `<div class="history-change-callout"><span class="eyebrow">Schedule change</span><strong>${esc(formatTarget(change.from))} → ${esc(formatTarget(change.to))}</strong><small>Updated ${esc(App.formatDate(change.date))} · prior target retained in history</small></div>`;
  }

  function scheduleHistoryHTML(project) {
    const records = window.HistoryEngine?.infrastructureTimeline?.(project.id, data.schedules, data.events) || [];
    if (!records.length) return '<p class="muted-text">No schedule or milestone records yet.</p>';
    return records.slice(0, 10).map(item => {
      if (item.type === 'schedule') {
        return `<div class="drawer-list-row"><div><strong>${esc(labelize(item.title))}: ${esc(formatTarget(item.detail))}</strong><span>Announced ${esc(App.formatDate(item.date))}</span><div class="provenance-inline-row">${sourceRef(item.source_id,{sourceDate:item.date,period:item.detail,sourceUrl:item.source_url})}</div></div>${Components.statusBadge(item.status)}</div>`;
      }
      return `<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(item.date))} · ${esc(labelize(item.detail))}</span><strong>${esc(item.title)}</strong></div>`;
    }).join('');
  }

  function drawerHTML(project) {
    const current = currentSchedule(project.id);
    const progressEvent = latestProgressEvent(project.id);
    const related = relatedRealEstate(project);
    const events = eventsFor(project.id).slice(0,5);
    const articles = data.articles.filter(item => (item.infrastructure_project_ids || []).includes(project.id)).sort((a,b) => String(b.published_at).localeCompare(String(a.published_at))).slice(0,3);
    return `
      <div class="drawer-entity-head"><span class="eyebrow">Infrastructure Project</span><h2>${esc(project.name)}</h2><p>${esc(project.location_text)} · ${esc(labelize(project.infrastructure_type))}</p>${Components.statusBadge(project.status)}</div>
      <div class="drawer-metrics">
        ${Components.compactMetric({label:'Current target',value:formatTarget(current?.target_period || project.current_expected_completion),note:current?.date_precision || project.completion_date_precision || ''})}
        ${Components.compactMetric({label:'Progress',value:project.current_progress_percent === null || project.current_progress_percent === undefined ? '—' : `${project.current_progress_percent}%`,note:progressEvent ? App.formatDate(progressEvent.event_date) : ''})}
        ${Components.compactMetric({label:'Investment',value:formatInvestment(project)})}
        ${Components.compactMetric({label:'Related RE',value:String(related.length),note:'Research links'})}
      </div>
      <div class="drawer-section"><h3>Overview</h3><p>${esc(project.summary)}</p></div>
      ${scheduleChangeSummaryHTML(project)}
      <div class="drawer-section"><h3>Schedule & Milestone History</h3>${scheduleHistoryHTML(project)}</div>
      <div class="drawer-section"><h3>Recent Milestones</h3>${events.length ? events.map(event => `<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(event.event_date))} · ${esc(labelize(event.event_type))} · ${sourceRef((event.source_ids || [])[0],{sourceDate:event.event_date})}</span><strong>${esc(event.title)}</strong></div>`).join('') : '<p class="muted-text">No milestone records.</p>'}</div>
      <div class="drawer-section"><h3>Related Real Estate Projects</h3>${related.length ? related.map(item => `<div class="drawer-list-row"><div><strong>${esc(item.name)}</strong><span>${esc(item.location_text || '')}</span></div><a class="text-link" href="market.html?view=projects&project=${encodeURIComponent(item.id)}">Open</a></div>`).join('') : '<p class="muted-text">No direct real-estate project links in the current registry.</p>'}</div>
      <div class="drawer-section"><h3>Related Evidence</h3>${articles.length ? articles.map(item => `<div class="drawer-list-row drawer-list-row--stack"><span>${esc(App.formatDate(item.published_at))} · ${esc(item.content_type)} · ${sourceRef(item.source_id,{publishedAt:item.published_at,sourceUrl:item.url})}</span><strong>${esc(item.title)}</strong></div>`).join('') : '<p class="muted-text">No related articles.</p>'}</div>`;
  }

  function openInfrastructureProject(projectId, { push = true } = {}) {
    const project = Resolver.getEntity('infrastructure-project',projectId);
    if (!project) return;
    if (push) App.setQueryParam('project',projectId,{push:true});
    App.openDrawer({ title: project.name, html: drawerHTML(project) });
  }

  function bindDelegatedEvents() {
    document.addEventListener('click', event => {
      const trigger = event.target.closest('[data-infra-project-id]');
      if (!trigger) return;
      openInfrastructureProject(trigger.dataset.infraProjectId);
    });

    document.addEventListener('app:drawer-closed', () => {
      if (App.getQueryParam('project')) App.removeQueryParam('project');
    });

    window.addEventListener('popstate', () => {
      parseState();
      render();
      const projectId = App.getQueryParam('project');
      if (projectId) openInfrastructureProject(projectId,{push:false});
      else App.closeDrawer();
    });
  }

  async function load() {
    try {
      await window.Provenance?.load?.();
      const [regions, projects, schedules, events, articles, realEstateProjects, meta] = await Promise.all([
        DataStore.getRegions(), DataStore.getInfrastructureProjects(), DataStore.getInfrastructureSchedules(), DataStore.getEvents(), DataStore.getArticles(), DataStore.getProjects(), DataStore.getMeta()
      ]);
      data = {
        regions: payloadData(regions),
        infrastructureProjects: payloadData(projects),
        schedules: payloadData(schedules),
        events: payloadData(events).filter(item => item.category === 'infrastructure'),
        articles: payloadData(articles).filter(item => item.category === 'infrastructure'),
        realEstateProjects: payloadData(realEstateProjects)
      };
      Resolver.setData('region',data.regions);
      Resolver.setData('infrastructure-project',data.infrastructureProjects);
      Resolver.setData('real-estate-project',data.realEstateProjects);
      parseState();
      const updated = document.querySelector('[data-infrastructure-updated]');
      if (updated) updated.textContent = `Official registry · ${data.infrastructureProjects.length} projects`;
      render();
      const projectId = App.getQueryParam('project');
      if (projectId) openInfrastructureProject(projectId,{push:false});
    } catch (error) {
      console.error(error);
      setView(Components.stateBox('Unable to load Infrastructure registry data. Check that the site is running through a web server.', 'error'));
    }
  }

  document.addEventListener('app:language-changed', () => {
    if (data.infrastructureProjects.length) render();
  });

  document.addEventListener('DOMContentLoaded', () => {
    bindDelegatedEvents();
    load();
  });
})();
