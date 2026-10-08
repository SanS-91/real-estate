(() => {
  'use strict';

  const HOME_PRODUCTION_RULES = new Map([
    ['usd-vnd-central-rate', { unit: 'vnd-per-usd', evidenceStatus: 'corroborated', sources: ['banking-times-vn', 'vna-vietnamplus'] }],
    ['sjc-gold-sell', { unit: 'vnd-per-tael', evidenceStatus: 'corroborated', sources: ['baonghean-gold', 'vietnamnet-gold'] }],
    ['credit-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['bank-funding-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['cpi-yoy', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['deposit-rate-vnd-6-12m-low', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['deposit-rate-vnd-6-12m-high', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['lending-rate-vnd-average-low', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['lending-rate-vnd-average-high', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['policy-refinancing-rate', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vna-vietnamplus', 'banking-times-vn'] }]
  ]);
  const HOME_RATE_RANGES = [
    {
      lowId: 'deposit-rate-vnd-6-12m-low',
      highId: 'deposit-rate-vnd-6-12m-high',
      targetCardId: 'deposit-demo',
      label: 'VND Deposit Rate 6–12M'
    },
    {
      lowId: 'lending-rate-vnd-average-low',
      highId: 'lending-rate-vnd-average-high',
      targetCardId: 'lending-demo',
      label: 'Average VND Lending Rate Range'
    }
  ];
  const HOME_CARD_TARGETS = {
    'usd-vnd-demo': 'usd-vnd-central-rate',
    'gold-demo': 'sjc-gold-sell',
    'credit-demo': 'credit-growth-ytd',
    'cpi-demo': 'cpi-yoy'
  };
  const HOME_LABELS = {
    'usd-vnd-central-rate': 'USD/VND Central Rate',
    'sjc-gold-sell': 'Domestic Gold Sell',
    'credit-growth-ytd': 'Credit Growth YTD',
    'bank-funding-growth-ytd': 'Bank Funding Growth YTD',
    'cpi-yoy': 'CPI YoY',
    'policy-refinancing-rate': 'Policy Refinancing Rate'
  };

  let productionPromise = null;
  let canonicalHomePromise = null;

  function setHTML(selector, html) {
    const node = document.querySelector(selector);
    if (node) node.innerHTML = html;
  }

  function setText(selector, text) {
    const node = document.querySelector(selector);
    if (node) node.textContent = text;
  }

  function productionEvidenceLabel(row) {
    if (row?.evidence_status === 'verified') return 'CANONICAL';
    if (row?.evidence_status === 'corroborated') return 'CORROBORATED';
    return 'PRODUCTION';
  }

  function validHomeProductionRows(payload, publishMeta) {
    if (!payload || !publishMeta) return [];
    if (payload.repository_publish !== true || payload.production_write !== true || publishMeta.repository_publish !== true) return [];
    if (!Array.isArray(payload.data)) return [];
    if (Number.isFinite(Number(publishMeta.final_record_count)) && Number(publishMeta.final_record_count) !== payload.data.length) return [];

    return payload.data.filter(row => {
      const rule = HOME_PRODUCTION_RULES.get(row?.indicator_id);
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

  function observationKey(row) {
    return row?.data_date || row?.period || '';
  }

  function latestByIndicator(rows) {
    const latest = new Map();
    rows.forEach(row => {
      const prior = latest.get(row.indicator_id);
      if (!prior || observationKey(row).localeCompare(observationKey(prior)) > 0) latest.set(row.indicator_id, row);
    });
    return latest;
  }

  async function loadHomeProduction() {
    if (productionPromise) return productionPromise;
    productionPromise = Promise.all([
      DataStore.getProcessedMacroObservations().catch(error => {
        console.warn('[home] processed macro observations unavailable; using blank macro fallback.', error);
        return null;
      }),
      DataStore.getProcessedMacroPublishMeta().catch(error => {
        console.warn('[home] processed macro publish metadata unavailable; using blank macro fallback.', error);
        return null;
      })
    ]).then(([payload, publishMeta]) => {
      const rows = validHomeProductionRows(payload, publishMeta);
      return {
        rows,
        latest: latestByIndicator(rows),
        totalRecordCount: Array.isArray(payload?.data) ? payload.data.length : 0,
        active: rows.length > 0
      };
    });
    return productionPromise;
  }

  function payloadData(payload) {
    return Array.isArray(payload?.data) ? payload.data : [];
  }

  function dateKey(value) {
    return String(value || '').slice(0, 10);
  }

  function sortDateDesc(rows, selector) {
    return [...rows].sort((a, b) => dateKey(selector(b)).localeCompare(dateKey(selector(a))));
  }

  function sourceName(sourceMap, sourceId) {
    return sourceMap.get(sourceId)?.name || sourceId || 'Source';
  }

  function nonDemoSource(sourceId) {
    return sourceId && !String(sourceId).startsWith('demo-');
  }

  async function loadCanonicalHomeData() {
    if (canonicalHomePromise) return canonicalHomePromise;
    canonicalHomePromise = Promise.all([
      DataStore.getProjects(),
      DataStore.getProjectPhases(),
      DataStore.getMarketObservations(),
      DataStore.getLegalDocuments(),
      DataStore.getInfrastructureProjects(),
      DataStore.getInfrastructureSchedules(),
      DataStore.getArticles(),
      DataStore.getEvents(),
      DataStore.getSources(),
      loadHomeProduction()
    ]).then(([projects, phases, marketObservations, legal, infrastructure, schedules, articles, events, sources, production]) => {
      const sourceRows = payloadData(sources);
      return {
        projects: payloadData(projects),
        phases: payloadData(phases),
        marketObservations: payloadData(marketObservations),
        legal: payloadData(legal),
        infrastructure: payloadData(infrastructure),
        schedules: payloadData(schedules),
        articles: payloadData(articles),
        events: payloadData(events),
        sources: new Map(sourceRows.map(row => [row.id, row])),
        production
      };
    });
    return canonicalHomePromise;
  }

  function productionTodayTitle(row) {
    if (row.indicator_id === 'usd-vnd-central-rate') {
      return `USD/VND central rate at ${Formatters.number(row.value, { min: 0, max: 0 })}`;
    }
    if (row.indicator_id === 'sjc-gold-sell') {
      return `Domestic gold selling price at ${Formatters.unitValue(row.unit, row.value, { compact: true })}`;
    }
    return `${HOME_LABELS[row.indicator_id] || row.indicator_id} · ${Formatters.unitValue(row.unit, row.value, { compact: true })}`;
  }

  function buildTodayGroups(data) {
    const marketArticles = sortDateDesc(
      data.articles.filter(row => row.category === 'market' && nonDemoSource(row.source_id)),
      row => row.published_at
    );
    const infraArticles = sortDateDesc(
      data.articles.filter(row => row.category === 'infrastructure' && nonDemoSource(row.source_id)),
      row => row.published_at
    );
    const legalRows = sortDateDesc(data.legal, row => row.issued_date || row.effective_date);
    const macroRows = ['usd-vnd-central-rate', 'sjc-gold-sell']
      .map(id => data.production.latest.get(id))
      .filter(Boolean);

    return [
      {
        category: 'market',
        label: 'Market',
        count: data.projects.length,
        count_label: `${data.projects.length} curated projects`,
        href: 'market.html?view=projects',
        items: marketArticles.slice(0, 2).map(row => ({
          title: row.title,
          meta: `${App.formatDate(row.published_at)} · ${sourceName(data.sources, row.source_id)}`,
          href: row.subcategory === 'supply' ? 'market.html?view=supply-sales' : 'market.html?view=news'
        }))
      },
      {
        category: 'legal',
        label: 'Legal',
        count: data.legal.length,
        count_label: `${data.legal.length} official documents`,
        href: 'legal.html?view=documents',
        items: legalRows.slice(0, 2).map(row => ({
          title: `${row.document_number} · ${row.title}`,
          meta: `Effective ${App.formatDate(row.effective_date)} · Government`,
          href: 'legal.html?view=documents'
        }))
      },
      {
        category: 'infrastructure',
        label: 'Infrastructure',
        count: data.infrastructure.length,
        count_label: `${data.infrastructure.length} infrastructure projects`,
        href: 'infrastructure.html?view=projects',
        items: infraArticles.slice(0, 2).map(row => ({
          title: row.title,
          meta: `${App.formatDate(row.published_at)} · ${sourceName(data.sources, row.source_id)}`,
          href: 'infrastructure.html?view=timeline'
        }))
      },
      {
        category: 'macro',
        label: 'Macro',
        count: data.production.totalRecordCount,
        count_label: `${data.production.totalRecordCount} production records`,
        href: 'macro.html?view=overview',
        items: macroRows.map(row => ({
          title: productionTodayTitle(row),
          meta: `${formatProductionPeriod(row)} · ${productionEvidenceLabel(row)}`,
          href: row.indicator_id === 'usd-vnd-central-rate' ? 'macro.html?view=fx' : 'macro.html?view=gold'
        }))
      }
    ];
  }

  function rowsForIndicator(production, indicatorId) {
    return production.rows
      .filter(row => row.indicator_id === indicatorId)
      .sort((a, b) => observationKey(b).localeCompare(observationKey(a)));
  }

  function macroChange(data, indicatorId, href) {
    const rows = rowsForIndicator(data.production, indicatorId);
    if (!rows.length) return null;
    const latest = rows[0];
    const prior = rows[1];
    const current = Formatters.unitValue(latest.unit, latest.value, { compact: true });
    const previous = prior ? Formatters.unitValue(prior.unit, prior.value, { compact: true }) : null;
    return {
      id: `live-change-${indicatorId}-${latest.period}`,
      category: 'macro',
      category_label: 'Macro',
      date_label: formatProductionPeriod(latest),
      sort_date: observationKey(latest),
      title: productionTodayTitle(latest),
      summary: previous
        ? `Latest controlled production observation; previous available observation was ${previous} on ${formatProductionPeriod(prior)}.`
        : 'Latest controlled production observation; no earlier comparable production observation is stored.',
      href
    };
  }

  function formatQuarterPeriod(value) {
    const match = String(value || '').match(/^(\d{4})-Q([1-4])$/);
    return match ? `Q${match[2]}/${match[1]}` : String(value || '');
  }

  function buildChanges(data) {
    if (!window.HistoryEngine) return [];
    const intelligence = HistoryEngine.buildIntelligence({
      macroRows: data.production.rows,
      legalDocuments: data.legal,
      infrastructureProjects: data.infrastructure,
      schedules: data.schedules,
      events: data.events,
      marketObservations: data.marketObservations
    });

    const latestByCategory = [];
    ['macro', 'infrastructure', 'market', 'legal'].forEach(category => {
      const item = intelligence.find(row => row.category === category);
      if (item) latestByCategory.push(item);
    });

    return latestByCategory.map(item => {
      if (item.category === 'macro') {
        const current = item.current;
        const previous = item.previous;
        const deltaLabel = current.unit === 'vnd-per-tael'
          ? `${item.delta > 0 ? '+' : ''}${Formatters.number(item.delta / 1_000_000, { min: 1, max: 1 })} mn VND/tael`
          : `${item.delta > 0 ? '+' : ''}${Formatters.number(item.delta, { min: 0, max: 0 })} VND/USD`;
        return {
          id: item.id,
          category: 'macro',
          category_label: 'Macro',
          date_label: formatProductionPeriod(current),
          sort_date: item.date,
          title: productionTodayTitle(current),
          summary: `${deltaLabel} versus ${formatProductionPeriod(previous)}.`,
          href: current.indicator_id === 'usd-vnd-central-rate' ? 'macro.html?view=fx' : 'macro.html?view=gold'
        };
      }

      if (item.category === 'infrastructure') {
        if (item.type === 'schedule-change') {
          return {
            id: item.id,
            category: 'infrastructure',
            category_label: 'Infrastructure',
            date_label: App.formatDate(item.date),
            sort_date: item.date,
            title: item.title,
            summary: `Schedule revised from ${item.from} to ${item.to}; prior target remains preserved in history.`,
            href: `infrastructure.html?view=projects&project=${encodeURIComponent(item.entity_id)}`
          };
        }
        return {
          id: item.id,
          category: 'infrastructure',
          category_label: 'Infrastructure',
          date_label: App.formatDate(item.date),
          sort_date: item.date,
          title: item.title,
          summary: item.summary || 'Source-backed infrastructure milestone recorded in the curated timeline.',
          href: `infrastructure.html?view=projects&project=${encodeURIComponent(item.entity_id)}`
        };
      }

      if (item.category === 'market') {
        const current = item.current;
        const previous = item.previous;
        return {
          id: item.id,
          category: 'market',
          category_label: 'Market',
          date_label: formatQuarterPeriod(current.period),
          sort_date: item.date,
          title: `HCMC apartment new supply at ${Formatters.number(current.new_supply, { min: 0, max: 0 })} units`,
          summary: `Comparable CBRE series moved from ${Formatters.number(previous.new_supply, { min: 0, max: 0 })} to ${Formatters.number(current.new_supply, { min: 0, max: 0 })} units (${item.pct > 0 ? '+' : ''}${Formatters.number(item.pct, { min: 1, max: 1 })}%).`,
          href: 'market.html?view=supply-sales'
        };
      }

      const doc = data.legal.find(row => row.id === item.entity_id);
      const target = data.legal.find(row => row.id === item.target_id);
      return {
        id: item.id,
        category: 'legal',
        category_label: 'Legal',
        date_label: App.formatDate(item.date),
        sort_date: item.date,
        title: doc ? `${doc.document_number} · ${doc.title}` : item.title,
        summary: target
          ? `${doc?.document_number || 'Document'} ${item.type === 'amends' ? 'amends' : 'supplements'} ${target.document_number}; both records remain linked in the legal lifecycle.`
          : item.summary,
        href: doc ? `legal.html?view=documents&document=${encodeURIComponent(doc.id)}` : 'legal.html?view=documents'
      };
    }).sort((a, b) => dateKey(b.sort_date).localeCompare(dateKey(a.sort_date)));
  }

  function importanceLabel(value) {
    if (Number(value) >= 5) return 'High relevance';
    if (Number(value) >= 4) return 'Important';
    return 'Watch';
  }

  function weeklyMacroSummary(row, production) {
    const delta = window.HistoryEngine?.macroDelta?.(production.rows || [], row.indicator_id);
    if (delta?.previous && delta.delta !== null) {
      if (row.unit === 'vnd-per-usd') {
        return `Changed from ${Formatters.number(delta.previous.value, { min: 0, max: 0 })} to ${Formatters.number(delta.current.value, { min: 0, max: 0 })} VND/USD (${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta, { min: 0, max: 0 })}).`;
      }
      if (row.unit === 'vnd-per-tael') {
        return `Changed from ${Formatters.number(delta.previous.value / 1_000_000, { min: 1, max: 1 })} to ${Formatters.number(delta.current.value / 1_000_000, { min: 1, max: 1 })} mn VND/tael (${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta / 1_000_000, { min: 1, max: 1 })} mn).`;
      }
      if (row.unit === 'percent' || row.unit === 'percent-per-year') {
        return `Changed from ${Formatters.number(delta.previous.value, { min: 2, max: 2 })}% to ${Formatters.number(delta.current.value, { min: 2, max: 2 })}% (${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta, { min: 2, max: 2 })} ppt).`;
      }
    }
    return row.evidence_status === 'verified'
      ? 'Verified production observation from the approved official source.'
      : 'Corroborated production observation from the approved source set.';
  }

  function buildWeekly(data) {
    const candidates = [];

    // Keep only the latest observation of each Macro indicator in the recap.
    // HistoryEngine still provides the prior stored observation for the delta summary.
    const latestMacro = new Map();
    data.production.rows.forEach(row => {
      const key = observationKey(row);
      const prior = latestMacro.get(row.indicator_id);
      if (!prior || key.localeCompare(observationKey(prior)) > 0) latestMacro.set(row.indicator_id, row);
    });

    latestMacro.forEach(row => {
      const published = dateKey(row.published_at || row.data_date || row.period);
      if (!published) return;
      candidates.push({
        id: `weekly-live-${row.indicator_id}-${row.period}`,
        category: 'macro',
        category_label: 'Macro',
        date_label: App.formatDate(published).replace(/ \d{4}$/, ''),
        importance_label: ['cpi-yoy', 'credit-growth-ytd', 'bank-funding-growth-ytd'].includes(row.indicator_id) ? 'Important' : 'Watch',
        title: productionTodayTitle(row),
        summary: weeklyMacroSummary(row, data.production),
        href: row.indicator_id === 'usd-vnd-central-rate' ? 'macro.html?view=fx'
          : row.indicator_id.startsWith('sjc-gold') ? 'macro.html?view=gold'
          : row.indicator_id.includes('cpi') ? 'macro.html?view=inflation'
          : row.indicator_id.includes('rate') ? 'macro.html?view=rates'
          : 'macro.html?view=liquidity',
        sort_date: published
      });
    });

    data.events
      .filter(row => row.category === 'infrastructure' && (row.source_ids || []).some(nonDemoSource))
      .forEach(row => candidates.push({
        id: `weekly-live-${row.id}`,
        category: 'infrastructure',
        category_label: 'Infrastructure',
        date_label: App.formatDate(row.event_date).replace(/ \d{4}$/, ''),
        importance_label: importanceLabel(row.importance),
        title: row.title,
        summary: row.summary,
        href: 'infrastructure.html?view=timeline',
        sort_date: row.event_date
      }));

    const dated = candidates.filter(row => dateKey(row.sort_date));
    if (!dated.length) return [];
    const latest = dateKey(dated.reduce((max, row) => dateKey(row.sort_date) > max ? dateKey(row.sort_date) : max, ''));
    const latestDate = new Date(`${latest}T00:00:00Z`);
    const floor = new Date(latestDate);
    floor.setUTCDate(floor.getUTCDate() - 6);
    const floorKey = floor.toISOString().slice(0, 10);

    return dated
      .filter(row => {
        const key = dateKey(row.sort_date);
        return key >= floorKey && key <= latest;
      })
      .sort((a, b) => {
        const byDate = dateKey(b.sort_date).localeCompare(dateKey(a.sort_date));
        if (byDate) return byDate;
        const rank = { 'High relevance': 3, 'Important': 2, 'Watch': 1 };
        return (rank[b.importance_label] || 0) - (rank[a.importance_label] || 0);
      })
      .slice(0, 6);
  }

  function formatProductionPeriod(row) {
    if (!row) return '';
    if (row.period_type === 'month' && /^\d{4}-\d{2}$/.test(row.period || '')) {
      const [year, month] = row.period.split('-').map(Number);
      return new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric' })
        .format(new Date(Date.UTC(year, month - 1, 1)));
    }
    return App.formatDate(row.data_date || row.period);
  }

  function productionCard(row, production) {
    const delta = window.HistoryEngine?.macroDelta?.(production?.rows || [], row.indicator_id);
    let changeLabel = 'Latest only';
    let changeDirection = 'neutral';
    if (delta?.previous && delta.delta !== null) {
      if (row.unit === 'vnd-per-tael') {
        changeLabel = `${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta / 1_000_000, { min: 1, max: 1 })} mn vs prior`;
      } else if (row.unit === 'vnd-per-usd') {
        changeLabel = `${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta, { min: 0, max: 0 })} vs prior`;
      } else if (row.unit === 'percent' || row.unit === 'percent-per-year') {
        changeLabel = `${delta.delta > 0 ? '+' : ''}${Formatters.number(delta.delta, { min: 2, max: 2 })} ppt vs prior`;
      }
      changeDirection = delta.direction;
    }
    return {
      id: row.indicator_id,
      label: HOME_LABELS[row.indicator_id] || row.indicator_id,
      display_value: Formatters.unitValue(row.unit, row.value, { compact: true }),
      change_label: changeLabel,
      change_direction: changeDirection,
      period_label: formatProductionPeriod(row),
      source: productionEvidenceLabel(row)
    };
  }

  function productionRangeCard(lowRow, highRow, cfg) {
    const low = Formatters.number(lowRow.value, { min: 1, max: 1 });
    const high = Formatters.number(highRow.value, { min: 1, max: 1 });
    return {
      id: cfg.targetCardId.replace('-demo', '-range'),
      label: cfg.label,
      display_value: `${low}–${high}% p.a.`,
      change_label: 'Latest range',
      change_direction: 'neutral',
      period_label: formatProductionPeriod(lowRow),
      source: 'CORROBORATED'
    };
  }

  function mergeHomeIndicatorCards(mockCards, production) {
    const rangesByTarget = new Map();
    HOME_RATE_RANGES.forEach(cfg => {
      const low = production.latest.get(cfg.lowId);
      const high = production.latest.get(cfg.highId);
      if (low && high && low.period === high.period) {
        rangesByTarget.set(cfg.targetCardId, productionRangeCard(low, high, cfg));
      }
    });

    const cards = mockCards.map(card => {
      const rangeCard = rangesByTarget.get(card.id);
      if (rangeCard) return rangeCard;
      const indicatorId = HOME_CARD_TARGETS[card.id];
      const row = indicatorId ? production.latest.get(indicatorId) : null;
      return row ? productionCard(row, production) : card;
    });

    const policyRefi = production.latest.get('policy-refinancing-rate');
    if (policyRefi) {
      const lendingIndex = cards.findIndex(card => card.id === 'lending-range' || card.id === 'lending-demo');
      cards.splice(lendingIndex >= 0 ? lendingIndex + 1 : cards.length, 0, productionCard(policyRefi, production));
    }

    const bankFunding = production.latest.get('bank-funding-growth-ytd');
    if (bankFunding) {
      const creditIndex = cards.findIndex(card => card.id === 'credit-growth-ytd' || card.id === 'credit-demo');
      cards.splice(creditIndex >= 0 ? creditIndex + 1 : cards.length, 0, productionCard(bankFunding, production));
    }
    return cards;
  }

  async function renderToday() {
    try {
      const data = await loadCanonicalHomeData();
      setHTML('[data-home-today]', buildTodayGroups(data).map(Components.todayCard).join(''));
    } catch (error) {
      console.warn('[home] live Latest derivation failed; using snapshot fallback.', error);
      try {
        const payload = await DataStore.getHomeToday();
        setHTML('[data-home-today]', (payload.data || []).map(Components.todayCard).join(''));
      } catch (fallbackError) {
        console.error(fallbackError);
        setHTML('[data-home-today]', Components.stateBox('Unable to load Today data.', 'error'));
      }
    }
  }

  async function renderIndicators() {
    try {
      const [payload, production] = await Promise.all([DataStore.getHomeIndicators(), loadHomeProduction()]);
      const cards = mergeHomeIndicatorCards(payload.data || [], production);
      const grid = document.querySelector('[data-home-indicators]');
      grid?.classList.toggle('metric-grid--controlled', production.active);
      setHTML('[data-home-indicators]', cards.map(Components.metricCard).join(''));
    } catch (error) {
      console.error(error);
      setHTML('[data-home-indicators]', Components.stateBox('Unable to load indicator data.', 'error'));
    }
  }

  async function renderChanges() {
    try {
      const data = await loadCanonicalHomeData();
      setHTML('[data-home-changes]', buildChanges(data).map(Components.changeCard).join(''));
    } catch (error) {
      console.warn('[home] live What Changed derivation failed; using snapshot fallback.', error);
      try {
        const payload = await DataStore.getHomeChanges();
        setHTML('[data-home-changes]', (payload.data || []).map(Components.changeCard).join(''));
      } catch (fallbackError) {
        console.error(fallbackError);
        setHTML('[data-home-changes]', Components.stateBox('Unable to load change events.', 'error'));
      }
    }
  }

  async function renderWeekly() {
    try {
      const data = await loadCanonicalHomeData();
      setHTML('[data-home-weekly]', buildWeekly(data).map(Components.weeklyItem).join(''));
    } catch (error) {
      console.warn('[home] live weekly derivation failed; using snapshot fallback.', error);
      try {
        const payload = await DataStore.getHomeWeekly();
        setHTML('[data-home-weekly]', (payload.data || []).map(Components.weeklyItem).join(''));
      } catch (fallbackError) {
        console.error(fallbackError);
        setHTML('[data-home-weekly]', Components.stateBox('Unable to load weekly highlights.', 'error'));
      }
    }
  }

  function healthStatusLabel(status) {
    const vi = (window.AppLocalization?.getLanguage?.() || document.documentElement.lang || 'vi') === 'vi';
    const labels = vi
      ? { healthy:'Tốt', running:'Đang chạy', review:'Cần xem', degraded:'Suy giảm', stale:'Quá hạn' }
      : { healthy:'Healthy', running:'Running', review:'Review', degraded:'Degraded', stale:'Stale' };
    return labels[status] || status || '—';
  }

  function healthModuleLabel(module) {
    const vi = (window.AppLocalization?.getLanguage?.() || document.documentElement.lang || 'vi') === 'vi';
    const labels = vi
      ? { market:'Thị trường', legal:'Pháp lý', infrastructure:'Hạ tầng', macro:'Vĩ mô' }
      : { market:'Market', legal:'Legal', infrastructure:'Infrastructure', macro:'Macro' };
    return labels[module] || module;
  }

  async function renderDataHealth() {
    try {
      const payload = await DataStore.getDataHealth();
      const rows = payload?.modules || [];
      setHTML('[data-home-data-health]', rows.map(row => `
        <a class="data-health-card is-${Components.escapeHTML(row.status || 'review')}" href="maintenance.html">
          <div class="data-health-card__top">
            <strong>${Components.escapeHTML(healthModuleLabel(row.module))}</strong>
            <span class="data-health-status">${Components.escapeHTML(healthStatusLabel(row.status))}</span>
          </div>
          <div class="data-health-card__meta">
            <span>${Components.escapeHTML(String(row.dataset_count || 0))} datasets</span>
            <span>${Components.escapeHTML(String(row.candidate_backlog || 0))} backlog</span>
          </div>
        </a>
      `).join('') || Components.stateBox('Data health is not available yet.'));
    } catch (error) {
      console.warn('[home] unified data health unavailable', error);
      setHTML('[data-home-data-health]', Components.stateBox('Data health is not available yet.'));
    }
  }

  function renderQuickResearch() {
    const items = [
      { label: 'Region', title: 'Dong Nai', description: 'Projects, infrastructure and recent developments.', href: 'market.html?region=dong-nai' },
      { label: 'Developer', title: 'Nam Long', description: 'Developer profile, projects and recent activity.', href: 'market.html?view=developers&developer=nam-long' },
      { label: 'Legal topic', title: 'Land', description: 'Official documents, effective dates and analysis.', href: 'legal.html?view=documents&topic=land' },
      { label: 'Macro', title: 'Interest Rates', description: 'Deposit, lending and interbank rate views.', href: 'macro.html?view=rates' }
    ];
    setHTML('[data-home-quick-research]', items.map(Components.quickLink).join(''));
  }

  async function renderMeta() {
    try {
      const [payload, production] = await Promise.all([DataStore.getMeta(), loadHomeProduction()]);
      if (production.active) {
        setText('[data-home-updated]', `Integrated data · 4 curated modules · ${production.totalRecordCount} macro records`);
        return;
      }
      const date = payload?.last_successful_build;
      setText('[data-home-updated]', date ? `Curated registries · ${App.formatDate(date)}` : 'Curated registries');
    } catch (error) {
      console.warn('Meta unavailable', error);
      setText('[data-home-updated]', 'Curated registries');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderQuickResearch();
    renderDataHealth();
    renderMeta();
    renderToday();
    renderIndicators();
    renderChanges();
    renderWeekly();
    document.addEventListener('app:language-changed', () => {
      renderToday();
      renderChanges();
      renderWeekly();
      renderDataHealth();
    });
  });
})();
