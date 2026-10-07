(() => {
  'use strict';

  const toDateKey = value => String(value || '').slice(0, 10);
  const numeric = value => value !== null && value !== undefined && Number.isFinite(Number(value));
  const unique = values => [...new Set((values || []).filter(Boolean))];

  function sortAsc(rows, selector) {
    return [...(rows || [])].sort((a, b) => String(selector(a) || '').localeCompare(String(selector(b) || '')));
  }

  function sortDesc(rows, selector) {
    return [...(rows || [])].sort((a, b) => String(selector(b) || '').localeCompare(String(selector(a) || '')));
  }

  function macroSeries(rows, indicatorId) {
    return sortAsc(
      (rows || []).filter(row => row.indicator_id === indicatorId && numeric(row.value)),
      row => row.data_date || row.period
    );
  }

  function macroDelta(rows, indicatorId) {
    const series = macroSeries(rows, indicatorId);
    const current = series.at(-1) || null;
    const previous = series.at(-2) || null;
    if (!current) return { current: null, previous: null, delta: null, pct: null, direction: 'neutral' };
    if (!previous) return { current, previous: null, delta: null, pct: null, direction: 'neutral' };
    const delta = Number(current.value) - Number(previous.value);
    const pct = Number(previous.value) ? delta / Number(previous.value) * 100 : null;
    return {
      current,
      previous,
      delta,
      pct,
      direction: delta > 0 ? 'up' : delta < 0 ? 'down' : 'neutral'
    };
  }

  function legalTimeline(document, documents) {
    if (!document) return [];
    const byId = new Map((documents || []).map(row => [row.id, row]));
    const events = [];
    if (document.issued_date) {
      events.push({
        id: `${document.id}:issued`,
        type: 'issued',
        date: document.issued_date,
        title: 'Issued',
        detail: document.document_number || document.title,
        source_id: document.primary_source_id,
        source_url: document.official_url
      });
    }
    if (document.effective_date) {
      events.push({
        id: `${document.id}:effective`,
        type: 'effective',
        date: document.effective_date,
        title: 'Effective',
        detail: document.document_number || document.title,
        source_id: document.primary_source_id,
        source_url: document.official_url
      });
    }

    (document.related_documents || []).forEach(rel => {
      const other = byId.get(rel.document_id);
      if (!other) return;
      const relationDate = other.issued_date || other.effective_date;
      if (!relationDate) return;
      if (['amended-by', 'replaced-by'].includes(rel.relation_type)) {
        events.push({
          id: `${document.id}:${rel.relation_type}:${other.id}`,
          type: rel.relation_type,
          date: relationDate,
          title: rel.relation_type === 'amended-by' ? 'Amended by' : 'Replaced by',
          detail: `${other.document_number} · ${other.title}`,
          related_document_id: other.id,
          source_id: other.primary_source_id,
          source_url: other.official_url
        });
      }
    });

    (documents || []).forEach(other => {
      if (other.id === document.id) return;
      (other.related_documents || []).forEach(rel => {
        if (rel.document_id !== document.id) return;
        if (!['amends', 'supplements'].includes(rel.relation_type)) return;
        const relationDate = other.issued_date || other.effective_date;
        if (!relationDate) return;
        events.push({
          id: `${document.id}:incoming:${rel.relation_type}:${other.id}`,
          type: rel.relation_type,
          date: relationDate,
          title: rel.relation_type === 'amends' ? 'Amended by' : 'Supplemented by',
          detail: `${other.document_number} · ${other.title}`,
          related_document_id: other.id,
          source_id: other.primary_source_id,
          source_url: other.official_url
        });
      });
    });

    const seen = new Set();
    return sortAsc(events, row => row.date).filter(row => {
      if (seen.has(row.id)) return false;
      seen.add(row.id);
      return true;
    });
  }

  function infrastructureTimeline(projectId, schedules, events) {
    const rows = [];
    (schedules || [])
      .filter(row => row.infrastructure_project_id === projectId)
      .forEach(row => rows.push({
        id: `schedule:${row.id}`,
        type: 'schedule',
        date: row.announced_date,
        title: row.schedule_type,
        detail: row.target_period,
        status: row.status,
        source_id: row.source_id,
        source_url: row.source_url,
        raw: row
      }));
    (events || [])
      .filter(row => row.category === 'infrastructure' && row.entity_type === 'infrastructure-project' && row.entity_id === projectId)
      .forEach(row => rows.push({
        id: `event:${row.id}`,
        type: 'milestone',
        date: row.event_date,
        title: row.title,
        detail: row.event_type,
        source_id: (row.source_ids || [])[0],
        raw: row
      }));
    return sortDesc(rows.filter(row => row.date), row => row.date);
  }

  function infrastructureScheduleChange(projectId, schedules, scheduleType = 'expected-completion') {
    const rows = sortAsc(
      (schedules || []).filter(row => row.infrastructure_project_id === projectId && row.schedule_type === scheduleType),
      row => row.announced_date
    );
    if (rows.length < 2) return null;
    const current = [...rows].reverse().find(row => row.status === 'current') || rows.at(-1);
    const previous = [...rows].reverse().find(row => row.id !== current.id && row.status === 'superseded') || rows.at(-2);
    if (!current || !previous || current.target_period === previous.target_period) return null;
    return {
      project_id: projectId,
      schedule_type: scheduleType,
      date: current.announced_date,
      from: previous.target_period,
      to: current.target_period,
      current,
      previous
    };
  }

  function marketProjectHistory(project, observations, phases) {
    if (!project) return [];
    const rows = [];
    if (project.launch_date) rows.push({ id:`${project.id}:launch`, type:'launch', date:project.launch_date, title:'Launch', detail:project.name });
    if (project.construction_start_date) rows.push({ id:`${project.id}:construction`, type:'construction-start', date:project.construction_start_date, title:'Construction start', detail:project.name });

    (phases || []).filter(row => row.project_id === project.id).forEach(row => {
      if (row.launch_date) rows.push({
        id: `phase:${row.id}:launch`,
        type: 'phase-launch',
        date: row.launch_date,
        title: `${row.name} · launch`,
        detail: row.status || ''
      });
    });

    (observations || []).filter(row => row.project_id === project.id).forEach(row => {
      rows.push({
        id: `observation:${row.id}`,
        type: 'observation',
        date: row.source_date || row.period,
        title: `Market observation · ${row.period}`,
        detail: row.methodology_note || '',
        source_id: row.source_id,
        source_url: row.source_url,
        raw: row
      });
    });

    return sortDesc(rows.filter(row => row.date), row => row.date);
  }

  function compatibleMarketSeries(observations, { regionId, segmentId, metric, sourceId = null }) {
    const rows = (observations || []).filter(row => {
      if (!numeric(row[metric])) return false;
      if (row.scope_type !== 'region-segment') return false;
      if (regionId && !(row.region_ids || []).includes(regionId)) return false;
      if (segmentId && !(row.segment_ids || []).includes(segmentId)) return false;
      if (sourceId && row.source_id !== sourceId) return false;
      return true;
    });
    return sortAsc(rows, row => row.period);
  }

  function marketDelta(observations, options) {
    const rows = compatibleMarketSeries(observations, options);
    if (!rows.length) return { current:null, previous:null, delta:null, pct:null };
    const current = rows.at(-1);
    const sameSource = rows.filter(row => row.source_id === current.source_id);
    const previous = sameSource.at(-2) || null;
    if (!previous) return { current, previous:null, delta:null, pct:null };
    const delta = Number(current[options.metric]) - Number(previous[options.metric]);
    const pct = Number(previous[options.metric]) ? delta / Number(previous[options.metric]) * 100 : null;
    return { current, previous, delta, pct };
  }

  function legalAmendmentChanges(documents) {
    const byId = new Map((documents || []).map(row => [row.id, row]));
    const changes = [];
    (documents || []).forEach(row => {
      (row.related_documents || []).forEach(rel => {
        if (!['amends', 'supplements'].includes(rel.relation_type)) return;
        const target = byId.get(rel.document_id);
        if (!target) return;
        changes.push({
          id: `legal:${row.id}:${rel.relation_type}:${target.id}`,
          category: 'legal',
          date: row.issued_date || row.effective_date,
          entity_id: row.id,
          target_id: target.id,
          type: rel.relation_type,
          title: `${row.document_number} ${rel.relation_type === 'amends' ? 'amends' : 'supplements'} ${target.document_number}`,
          summary: row.summary || row.title,
          href: `legal.html?view=documents&document=${encodeURIComponent(row.id)}`
        });
      });
    });
    return sortDesc(changes.filter(row => row.date), row => row.date);
  }

  function buildIntelligence({ macroRows = [], legalDocuments = [], infrastructureProjects = [], schedules = [], events = [], marketObservations = [] } = {}) {
    const changes = [];

    ['usd-vnd-central-rate', 'sjc-gold-sell', 'sjc-gold-buy'].forEach(id => {
      const d = macroDelta(macroRows, id);
      if (!d.current || !d.previous || d.delta === null) return;
      changes.push({
        id: `macro:${id}:${d.current.period}`,
        category: 'macro',
        date: toDateKey(d.current.published_at || d.current.data_date || d.current.period),
        entity_id: id,
        type: 'value-change',
        current: d.current,
        previous: d.previous,
        delta: d.delta,
        pct: d.pct
      });
    });

    infrastructureProjects.forEach(project => {
      const change = infrastructureScheduleChange(project.id, schedules);
      if (change) {
        changes.push({
          id: `infrastructure:${project.id}:${change.date}`,
          category: 'infrastructure',
          date: change.date,
          entity_id: project.id,
          type: 'schedule-change',
          title: project.name,
          from: change.from,
          to: change.to,
          source_id: change.current.source_id,
          source_url: change.current.source_url
        });
      }
    });

    (events || [])
      .filter(row => row.category === 'infrastructure'
        && row.entity_type === 'infrastructure-project'
        && (row.source_ids || []).some(id => id && !String(id).startsWith('demo-')))
      .forEach(row => {
        changes.push({
          id: `infrastructure-event:${row.id}`,
          category: 'infrastructure',
          date: row.event_date,
          entity_id: row.entity_id,
          type: row.event_type || 'milestone',
          title: row.title,
          summary: row.summary,
          importance: row.importance,
          source_id: (row.source_ids || [])[0]
        });
      });

    legalAmendmentChanges(legalDocuments).forEach(row => changes.push(row));

    const supply = marketDelta(marketObservations, {
      regionId: 'hcmc',
      segmentId: 'apartment',
      metric: 'new_supply',
      sourceId: 'cbre-vietnam-market'
    });
    if (supply.current && supply.previous && supply.delta !== null) {
      changes.push({
        id: `market:hcmc-apartment-supply:${supply.current.period}`,
        category: 'market',
        date: supply.current.source_date || supply.current.period,
        entity_id: 'hcmc-apartment-supply',
        type: 'market-delta',
        metric: 'new_supply',
        current: supply.current,
        previous: supply.previous,
        delta: supply.delta,
        pct: supply.pct
      });
    }

    return sortDesc(changes.filter(row => row.date), row => row.date);
  }

  function withinTrailingDays(changes, days = 7) {
    const dated = (changes || []).filter(row => toDateKey(row.date));
    if (!dated.length) return [];
    const latest = toDateKey(dated[0].date);
    const max = new Date(`${latest}T00:00:00Z`);
    const min = new Date(max);
    min.setUTCDate(min.getUTCDate() - Math.max(0, days - 1));
    const minKey = min.toISOString().slice(0, 10);
    return dated.filter(row => {
      const key = toDateKey(row.date);
      return key >= minKey && key <= latest;
    });
  }

  window.HistoryEngine = {
    macroSeries,
    macroDelta,
    legalTimeline,
    infrastructureTimeline,
    infrastructureScheduleChange,
    marketProjectHistory,
    compatibleMarketSeries,
    marketDelta,
    legalAmendmentChanges,
    buildIntelligence,
    withinTrailingDays,
    toDateKey,
    unique
  };
})();