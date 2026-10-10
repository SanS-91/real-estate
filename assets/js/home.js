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
      DataStore.getIntelligenceRankingRules(),
      loadHomeProduction()
    ]).then(([projects, phases, marketObservations, legal, infrastructure, schedules, articles, events, sources, rankingRules, production]) => {
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
        sourceRows,
        rankingRules,
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

  function homeReferenceDate() {
    const parts=new Intl.DateTimeFormat('en-CA',{
      timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'
    }).formatToParts(new Date());
    const map=Object.fromEntries(parts.map(part=>[part.type,part.value]));
    return `${map.year}-${map.month}-${map.day}`;
  }

  function categoryLabel(category) {
    return ({ market:'Market', legal:'Legal', infrastructure:'Infrastructure', macro:'Macro' })[category] || category;
  }

  function macroHref(row) {
    const id=row?.indicator_id || row?.current?.indicator_id || row?.entity_id || '';
    if (id==='usd-vnd-central-rate') return 'macro.html?view=fx';
    if (id.startsWith('sjc-gold')) return 'macro.html?view=gold';
    if (id.includes('cpi')) return 'macro.html?view=inflation';
    if (id.includes('rate')) return 'macro.html?view=rates';
    return 'macro.html?view=liquidity';
  }

  function buildRankableCandidates(data) {
    const rows=[];
    const intelligence=window.HistoryEngine?.buildIntelligence?.({
      macroRows:data.production.rows,
      legalDocuments:data.legal,
      infrastructureProjects:data.infrastructure,
      schedules:data.schedules,
      events:data.events,
      marketObservations:data.marketObservations
    }) || [];
    rows.push(...intelligence);

    data.articles
      .filter(row=>['market','legal','infrastructure','macro'].includes(row.category) && nonDemoSource(row.source_id))
      .forEach(row=>rows.push({
        id:`article:${row.id}`,
        category:row.category,
        type:row.category==='market' && row.content_type==='developer-update' ? 'sales-update' : 'default',
        date:row.published_at,
        source_id:row.source_id,
        project_ids:row.project_ids || [],
        developer_ids:row.developer_ids || [],
        region_ids:row.region_ids || [],
        infrastructure_project_ids:row.infrastructure_project_ids || [],
        legal_document_ids:row.legal_document_ids || [],
        importance:row.importance,
        display_title:row.title,
        display_summary:row.summary,
        display_href:row.category==='market' ? 'market.html?view=news'
          : row.category==='legal' ? 'legal.html?view=news'
          : row.category==='macro' ? 'macro.html?view=news' : 'infrastructure.html?view=news'
      }));

    data.legal.forEach(row=>{
      if (!nonDemoSource(row.primary_source_id)) return;
      if (row.issued_date) rows.push({
        id:`legal-issued:${row.id}`,category:'legal',type:'issued',date:row.issued_date,
        entity_id:row.id,source_id:row.primary_source_id,legal_document_ids:[row.id],
        display_title:`${row.document_number} · ${row.title}`,
        display_summary:row.summary || 'Official legal document issued.',
        display_href:`legal.html?view=documents&document=${encodeURIComponent(row.id)}`
      });
      if (row.effective_date && row.effective_date!==row.issued_date) rows.push({
        id:`legal-effective:${row.id}`,category:'legal',type:'effective',date:row.effective_date,
        entity_id:row.id,source_id:row.primary_source_id,legal_document_ids:[row.id],
        display_title:`${row.document_number} becomes effective`,
        display_summary:row.summary || row.title,
        display_href:`legal.html?view=documents&document=${encodeURIComponent(row.id)}`
      });
    });

    data.production.latest.forEach(row=>{
      if (!nonDemoSource(row.source_id)) return;
      const delta=window.HistoryEngine?.macroDelta?.(data.production.rows,row.indicator_id);
      let type='data-release';
      if (delta?.previous && delta.delta!==null && delta.delta!==0) {
        if (row.indicator_id.includes('policy')) type='policy-change';
        else if (row.indicator_id.includes('rate')) type='rate-change';
        else if (row.indicator_id.includes('credit')) type='credit-update';
        else type='value-change';
      }
      rows.push({
        id:`macro-release:${row.indicator_id}:${row.period}`,
        category:'macro',type,date:row.published_at || row.data_date || row.period,
        entity_id:row.indicator_id,source_id:row.source_id,
        current:row,previous:delta?.previous || null,delta:delta?.delta ?? null,pct:delta?.pct ?? null,
        display_title:productionTodayTitle(row),
        display_summary:weeklyMacroSummary(row,data.production),
        display_href:macroHref(row)
      });
    });

    const byId=new Map();
    rows.forEach(row=>{ if (row?.id && !byId.has(row.id)) byId.set(row.id,row); });
    return [...byId.values()];
  }

  function rankedCandidates(data) {
    if (!window.IntelligenceRanking) return [];
    return IntelligenceRanking.rankAll(buildRankableCandidates(data),{
      sources:data.sourceRows,
      rules:data.rankingRules,
      referenceDate:homeReferenceDate()
    });
  }

  function rankedChangeCandidates(data) {
    if (!window.HistoryEngine || !window.IntelligenceRanking) return [];
    const rows=HistoryEngine.buildIntelligence({
      macroRows:data.production.rows,
      legalDocuments:data.legal,
      infrastructureProjects:data.infrastructure,
      schedules:data.schedules,
      events:data.events,
      marketObservations:data.marketObservations
    });
    return IntelligenceRanking.rankAll(rows,{
      sources:data.sourceRows,
      rules:data.rankingRules,
      referenceDate:homeReferenceDate()
    });
  }

  function formatRankedItem(item,data) {
    if (item.display_title) {
      return {
        ...item,
        category_label:categoryLabel(item.category),
        date_label:App.formatDate(item.ranking_evidence?.evidence_date || item.date),
        sort_date:item.ranking_evidence?.evidence_date || item.date,
        title:item.display_title,
        summary:item.display_summary || '',
        href:item.display_href || '#',
        importance_label:`${item.attention_label} · ${item.attention_score}`
      };
    }

    if (item.category==='macro') {
      const current=item.current, previous=item.previous;
      let summary='Source-backed macro change.';
      if (current && previous && item.delta!==null) {
        if (current.unit==='vnd-per-tael') summary=`${item.delta>0?'+':''}${Formatters.number(item.delta/1_000_000,{min:1,max:1})} mn VND/tael versus ${formatProductionPeriod(previous)}.`;
        else if (current.unit==='vnd-per-usd') summary=`${item.delta>0?'+':''}${Formatters.number(item.delta,{min:0,max:0})} VND/USD versus ${formatProductionPeriod(previous)}.`;
        else summary=`Changed versus ${formatProductionPeriod(previous)}.`;
      }
      return {
        ...item,category_label:'Macro',
        date_label:current ? formatProductionPeriod(current) : App.formatDate(item.date),
        sort_date:item.date,title:current ? productionTodayTitle(current) : item.title,
        summary,href:macroHref(current || item),
        importance_label:`${item.attention_label} · ${item.attention_score}`
      };
    }

    if (item.category==='infrastructure') {
      return {
        ...item,category_label:'Infrastructure',date_label:App.formatDate(item.date),sort_date:item.date,
        title:item.title,
        summary:item.type==='schedule-change'
          ? `Schedule revised from ${item.from} to ${item.to}; prior target remains preserved in history.`
          : item.summary || 'Source-backed infrastructure milestone recorded in the curated timeline.',
        href:`infrastructure.html?view=projects&project=${encodeURIComponent(item.entity_id)}`,
        importance_label:`${item.attention_label} · ${item.attention_score}`
      };
    }

    if (item.category==='market') {
      const current=item.current, previous=item.previous;
      return {
        ...item,category_label:'Market',
        date_label:current?.period ? formatQuarterPeriod(current.period) : App.formatDate(item.date),
        sort_date:item.date,
        title:current?.new_supply!=null ? `HCMC apartment new supply at ${Formatters.number(current.new_supply,{min:0,max:0})} units` : (item.title || 'Market update'),
        summary:current && previous
          ? `Comparable source series moved from ${Formatters.number(previous.new_supply,{min:0,max:0})} to ${Formatters.number(current.new_supply,{min:0,max:0})} units (${item.pct>0?'+':''}${Formatters.number(item.pct,{min:1,max:1})}%).`
          : item.summary || '',
        href:'market.html?view=supply-sales',
        importance_label:`${item.attention_label} · ${item.attention_score}`
      };
    }

    const doc=data.legal.find(row=>row.id===item.entity_id);
    const target=data.legal.find(row=>row.id===item.target_id);
    return {
      ...item,category_label:'Legal',date_label:App.formatDate(item.date),sort_date:item.date,
      title:doc ? `${doc.document_number} · ${doc.title}` : item.title,
      summary:target
        ? `${doc?.document_number || 'Document'} ${item.type==='amends'?'amends':'supplements'} ${target.document_number}; both records remain linked in the legal lifecycle.`
        : item.summary || '',
      href:doc ? `legal.html?view=documents&document=${encodeURIComponent(doc.id)}` : 'legal.html?view=documents',
      importance_label:`${item.attention_label} · ${item.attention_score}`
    };
  }

  function buildTodayGroups(data) {
    const ref = homeReferenceDate();
    const ranked = rankedCandidates(data);
    const vi = document.documentElement.lang !== 'en';
    const metaByCategory = {
      market: { label: vi ? 'Thị trường' : 'Market', href: 'market.html?view=news' },
      legal: { label: vi ? 'Pháp lý' : 'Legal', href: 'legal.html?view=news' },
      infrastructure: { label: vi ? 'Hạ tầng' : 'Infrastructure', href: 'infrastructure.html?view=news' },
      macro: { label: vi ? 'Vĩ mô' : 'Macro', href: 'macro.html?view=overview' }
    };
    // Rank within a recent window first, then backfill with real older
    // evidence if necessary. Never create or date a synthetic headline.
    const within = days => window.IntelligenceSurfaces?.withinDays?.(ranked, ref, days) || [];
    const recent = within(7), extended = within(90), older = within(365);
    return Object.keys(metaByCategory).map(category => {
      const picked = [], seen = new Set();
      for (const source of [recent, extended, older]) {
        for (const row of source) {
          if (row.category !== category || picked.length >= 3) continue;
          const key = row.id || row.title || '';
          if (!key || seen.has(key)) continue;
          seen.add(key);
          picked.push(row);
        }
      }
      const items = picked.map(row => {
        const item = formatRankedItem(row, data);
        const sourceIds = row.ranking_evidence?.source_ids || [];
        return {
          title: item.title,
          date_label: item.date_label || App.formatDate(item.sort_date),
          meta: sourceIds.length ? sourceName(data.sources, sourceIds[0]) : (vi ? 'Dữ liệu có nguồn' : 'Source-backed'),
          href: item.href
        };
      });
      const withinWeek = picked.filter(row =>
        recent.some(current => current.id === row.id)).length;
      const countLabel = !items.length
        ? (vi ? 'Chưa có tin có nguồn trong 12 tháng' : 'No sourced updates in 12 months')
        : vi
          ? `${items.length} cập nhật gần nhất${withinWeek < items.length ? ' · có tin kỳ trước' : ''}`
          : `${items.length} latest updates${withinWeek < items.length ? ' · includes older dates' : ''}`;
      return {
        category, label: metaByCategory[category].label,
        count: items.length, count_label: countLabel,
        href: metaByCategory[category].href, items
      };
    });
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
    const ranked=rankedChangeCandidates(data);
    const selected=window.IntelligenceSurfaces?.topPerCategory?.(
      ranked,['macro','infrastructure','market','legal']
    ) || [];
    return selected.map(item=>formatRankedItem(item,data));
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
    const ranked=rankedCandidates(data);
    const selected=window.IntelligenceSurfaces?.thisWeek?.(ranked,{
      referenceDate:homeReferenceDate(),
      limit:6,
      maxPerCategory:2
    }) || [];
    return selected.map(item=>formatRankedItem(item,data));
  }

  function buildTopDevelopments(data) {
    const ranked=rankedCandidates(data);
    const selected=window.IntelligenceSurfaces?.topDevelopments?.(ranked,{
      referenceDate:homeReferenceDate(),
      days:30,
      limit:6,
      maxPerCategory:2
    }) || [];
    return selected.map(item=>formatRankedItem(item,data));
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
      cadence_label: row.period_type === 'month' ? 'Monthly' :
        row.indicator_id === 'policy-refinancing-rate' ? 'Policy update' : 'Dated release',
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
      cadence_label: lowRow.period_type === 'month' ? 'Monthly' : 'Latest published',
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
      // Home is a high-level snapshot, not a substitute for the full Macro page.
      // Show two latest dated FX/gold observations and two released monthly series.
      const priority = ['usd-vnd-central-rate','sjc-gold-sell',
                        'credit-growth-ytd','cpi-yoy'];
      const nonEmpty = cards.filter(card => card.display_value !== '—' &&
        card.display_value !== null && card.display_value !== undefined);
      const shortlist = priority.map(id => nonEmpty.find(card => card.id === id))
        .filter(Boolean);
      for (const card of nonEmpty) {
        if (shortlist.length >= 4) break;
        if (!shortlist.some(item => item.id === card.id)) shortlist.push(card);
      }
      setHTML('[data-home-indicators]', (shortlist.length ? shortlist : cards.slice(0,4))
        .map(Components.metricCard).join(''));
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

  async function renderTopDevelopments() {
    try {
      const data = await loadCanonicalHomeData();
      setHTML('[data-home-top-developments]', buildTopDevelopments(data).map(Components.weeklyItem).join(''));
    } catch (error) {
      console.warn('[home] ranked Top Developments derivation failed.', error);
      setHTML('[data-home-top-developments]', Components.stateBox('Unable to load top developments.', 'error'));
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
    renderTopDevelopments();
    renderWeekly();
    document.addEventListener('app:language-changed', () => {
      renderToday();
      renderChanges();
      renderTopDevelopments();
      renderWeekly();
      renderDataHealth();
    });
  });
})();
