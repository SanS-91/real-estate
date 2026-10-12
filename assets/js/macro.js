(() => {
  'use strict';

  const VALID_VIEWS = ['overview', 'rates', 'fx', 'gold', 'liquidity', 'inflation', 'news'];
  const VIEW_SERIES = {
    rates: ['deposit-rate-12m-average', 'lending-rate-average', 'interbank-on', 'policy-refinancing-rate'],
    fx: ['usd-vnd-central-rate', 'usd-vnd-bank-sell'],
    gold: ['sjc-gold-sell', 'sjc-gold-buy', 'global-gold-usd-oz'],
    liquidity: ['interbank-on', 'credit-growth-ytd', 'bank-funding-growth-ytd', 'm2-growth-ytd'],
    inflation: ['cpi-yoy', 'cpi-mom', 'core-cpi-yoy']
  };
  const PRODUCTION_POLICY_RATE_SERIES = ['policy-refinancing-rate', 'policy-rediscount-rate', 'policy-overnight-lending-rate'];
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
    ['sjc-gold-sell', { unit: 'vnd-per-tael', evidenceStatus: 'corroborated', sources: ['baonghean-gold', 'vietnamnet-gold'] }],
    ['credit-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['bank-funding-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['m2-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['deposit-rate-vnd-6-12m-low', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['deposit-rate-vnd-6-12m-high', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['lending-rate-vnd-average-low', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['lending-rate-vnd-average-high', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vnba', 'vna-vietnamplus'] }],
    ['policy-refinancing-rate', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vna-vietnamplus', 'banking-times-vn'] }],
    ['policy-rediscount-rate', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vna-vietnamplus', 'banking-times-vn'] }],
    ['policy-overnight-lending-rate', { unit: 'percent-per-year', evidenceStatus: 'corroborated', sources: ['vna-vietnamplus', 'banking-times-vn'] }]
  ]);
  const PRODUCTION_RATE_RANGES = [
    {
      id: 'deposit-rate-vnd-6-12m-range',
      lowId: 'deposit-rate-vnd-6-12m-low',
      highId: 'deposit-rate-vnd-6-12m-high',
      fallbackId: 'deposit-rate-12m-average'
    },
    {
      id: 'lending-rate-vnd-average-range',
      lowId: 'lending-rate-vnd-average-low',
      highId: 'lending-rate-vnd-average-high',
      fallbackId: 'lending-rate-average'
    }
  ];
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
    },
    'credit-growth-ytd': {
      default_source_id: 'nso-vietnam',
      description: 'Year-to-date growth in economy-wide credit as reported in the official NSO socio-economic release.',
      methodology_note: 'Canonical observations are promoted only from verified official NSO releases. Missing historical periods are never backfilled with illustrative demo values.'
    },
    'm2-growth-ytd': {
      default_source_id: 'nso-vietnam',
      description: 'Vietnam total means of payment (M2) compared with the end of the preceding year.',
      methodology_note: 'Official NSO quarterly banking report. Quarterly period represents reporting window, but the as-of date is the source cutoff (often earlier than month end). YTD growth, not YoY. Do not annualize or interpolate.'
    },
    'bank-funding-growth-ytd': {
      default_source_id: 'nso-vietnam',
      description: 'Year-to-date growth in capital mobilization by Vietnamese credit institutions.',
      methodology_note: 'Canonical observations are promoted only from verified official NSO releases. Missing historical periods are never backfilled with illustrative demo values.'
    },
    'deposit-rate-vnd-6-12m-range': {
      default_source_id: 'vnba',
      description: 'Monthly VND deposit-rate range for 6–12 month tenors, reported from the SBV customer-rate bulletin.',
      methodology_note: 'Corroborated production is displayed as the official low–high range. The frontend pairs separately promoted range components and never fabricates a scalar average.'
    },
    'lending-rate-vnd-average-range': {
      default_source_id: 'vnba',
      description: 'Monthly range of average VND lending rates reported from the SBV customer-rate bulletin.',
      methodology_note: 'Corroborated production is displayed as the official low–high range. The frontend pairs separately promoted range components and never collapses the range into a single average.'
    },
    'policy-refinancing-rate': {
      default_source_id: 'vna-vietnamplus',
      description: 'State Bank of Vietnam refinancing policy rate.',
      methodology_note: 'Event-driven policy rate. Controlled production requires two independent trusted sources to agree on the decision, effective date and value. No synthetic history is created.'
    },
    'policy-rediscount-rate': {
      default_source_id: 'vna-vietnamplus',
      description: 'State Bank of Vietnam rediscount policy rate.',
      methodology_note: 'Event-driven policy rate. Controlled production requires two independent trusted sources to agree on the decision, effective date and value. No synthetic history is created.'
    },
    'policy-overnight-lending-rate': {
      default_source_id: 'vna-vietnamplus',
      description: 'State Bank of Vietnam overnight lending / clearing-deficit facility rate.',
      methodology_note: 'Event-driven administered policy rate. It is distinct from the market interbank overnight rate. Controlled production requires two independent trusted sources to agree on the decision, effective date and value.'
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

  // Official historical releases are deliberately held in a separate, reviewed
  // repository file: daily FX/gold collectors must never rewrite historical CPI.
  function validHistoricalRows(payload, currentRows) {
    if (!payload || payload.mode !== 'verified-official-nso-history-v1'
        || payload.repository_publish !== true || payload.frontend_publish !== false
        || !Array.isArray(payload.data) || payload.record_count !== payload.data.length) return [];

    const keys = new Set(currentRows.map(row => `${row.indicator_id}:${row.period_type}:${row.period}`));
    const accepted = [];
    payload.data.forEach(row => {
      const rule = PRODUCTION_INDICATORS.get(row?.indicator_id);
      const key = `${row?.indicator_id}:${row?.period_type}:${row?.period}`;
      if (!['cpi-yoy', 'cpi-mom', 'core-cpi-yoy'].includes(row?.indicator_id)
          || !rule || row.unit !== rule.unit || row.source_id !== 'nso-vietnam'
          || row.evidence_status !== 'verified' || row.observation_status !== 'final'
          || row.historical_observation !== true
          || typeof row.source_url !== 'string'
          || !/^https:\/\/www\.nso\.gov\.vn\//.test(row.source_url)
          || row.period_type !== 'month' || !/^\d{4}-\d{2}$/.test(row.period || '')
          || !Number.isFinite(Number(row.value))
          || !row.published_at || !row.source_reviewed_at || keys.has(key)) return;
      keys.add(key);
      accepted.push({ ...row, _data_layer: 'production', _historical: true });
    });
    return accepted;
  }

  // FX and SJC history is sparse, review-backed and independent of the live
  // daily persistence policy. Exact quote sessions prevent intraday mixing.
  const VERIFIED_HISTORY_HOSTS = {
    'infographics.vn': 'vna', 'vietnamplus.vn': 'vna',
    'thoibaonganhang.vn': 'banking-times',
    'en.vneconomy.vn': 'vneconomy',
    'vietnamnet.vn': 'vietnamnet',
    'baonghean.vn': 'baonghean',
    'vov.vn': 'vov', 'vietnambiz.vn': 'vietnambiz',
    'thitruongtaichinhtiente.vn': 'thitruongtaichinhtiente',
    'nhipcaukinhte.com.vn': 'nhipcaukinhte'
  };
  const VERIFIED_HISTORY_SOURCE_IDS = {
    'vna-vietnamplus': 'vna', 'vietnamnet-gold': 'vietnamnet',
    'vietnamnet': 'vietnamnet', 'banking-times-vn': 'banking-times',
    'baonghean-gold': 'baonghean', 'vov': 'vov',
    'vneconomy': 'vneconomy', 'vietnambiz': 'vietnambiz',
    'thitruongtaichinhtiente': 'thitruongtaichinhtiente',
    'nhipcaukinhte': 'nhipcaukinhte'
  };
  function independentHistoryPublisher(url) {
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== 'https:') return null;
      const host = parsed.hostname.toLowerCase().replace(/^www\./, '');
      return VERIFIED_HISTORY_HOSTS[host] || null;
    } catch (_) { return null; }
  }
  function validHistoricalMarketRows(payload, currentRows, previouslyAcceptedHistory) {
    if (!payload || payload.mode !== 'corroborated-fx-gold-history-v1'
        || payload.repository_publish !== true || payload.frontend_publish !== false
        || !Array.isArray(payload.data) || payload.record_count !== payload.data.length) return [];

    const keys = new Set([...currentRows, ...previouslyAcceptedHistory]
      .map(row => `${row.indicator_id}:${row.period_type}:${row.period}`));
    const accepted = [];
    payload.data.forEach(row => {
      const iid = row?.indicator_id;
      const rule = PRODUCTION_INDICATORS.get(iid);
      const key = `${iid}:${row?.period_type}:${row?.period}`;
      if (!['usd-vnd-central-rate', 'sjc-gold-buy', 'sjc-gold-sell'].includes(iid)
          || !rule || row.unit !== rule.unit
          || !rule.sources.includes(row.source_id)
          || row.evidence_status !== 'corroborated' || row.observation_status !== 'final'
          || row.historical_observation !== true
          || row.period_type !== 'day' || !/^\d{4}-\d{2}-\d{2}$/.test(row.period || '')
          || row.data_date !== row.period
          || !Number.isFinite(Number(row.value)) || Number(row.value) <= 0
          || !row.source_reviewed_at || !row.published_at
          || keys.has(key)) return;

      const sources = row.corroboration_sources;
      if (!Array.isArray(sources) || sources.length < 2
          || sources.some(s => !s?.source_id || !independentHistoryPublisher(s.url)
            || VERIFIED_HISTORY_SOURCE_IDS[s.source_id] !== independentHistoryPublisher(s.url)
            || Number(s.observed_value) !== Number(row.value))
          || new Set(sources.map(s => independentHistoryPublisher(s.url))).size < 2
          || sources[0].source_id !== row.source_id || sources[0].url !== row.source_url) return;
      if (iid === 'usd-vnd-central-rate') {
        if (row.quote_session !== 'daily-reference' || row.unit !== 'vnd-per-usd') return;
      } else if (row.product !== 'SJC gold bar 1 tael / 10 taels / 1kg'
          || !['morning', 'close'].includes(row.quote_session)
          || !/^([01]\d|2[0-3]):[0-5]\d$/.test(row.quote_time_local || '')) return;

      keys.add(key);
      accepted.push({ ...row, _data_layer: 'production', _historical: true });
    });
    return accepted;
  }

  const MONETARY_HISTORY_IDS = new Set([
    'm2-growth-ytd', 'credit-growth-ytd', 'bank-funding-growth-ytd',
    'deposit-rate-vnd-6-12m-low', 'deposit-rate-vnd-6-12m-high',
    'lending-rate-vnd-average-low', 'lending-rate-vnd-average-high'
  ]);
  const MONETARY_RATE_COMPONENTS = {
    'deposit-rate-vnd-6-12m-low': ['domestic-VND-commercial-bank-deposit-6-to-12-months', 'low'],
    'deposit-rate-vnd-6-12m-high': ['domestic-VND-commercial-bank-deposit-6-to-12-months', 'high'],
    'lending-rate-vnd-average-low': ['domestic-VND-commercial-bank-average-outstanding-lending-new-and-existing', 'low'],
    'lending-rate-vnd-average-high': ['domestic-VND-commercial-bank-average-outstanding-lending-new-and-existing', 'high']
  };
  function officialMonetaryHost(url, source) {
    try {
      const link = new URL(url);
      const host = link.hostname.toLowerCase().replace(/^www\./, '');
      if (link.protocol !== 'https:') return false;
      return source === 'nso-vietnam' ? host === 'nso.gov.vn'
        : source === 'sbv-vietnam' && host === 'sbv.gov.vn'
          && /\.pdf(\/|\?|$)/i.test(link.pathname + link.search) ? true
        : source === 'sbv-vietnam' && host === 'sbv.gov.vn' && link.pathname.includes('.pdf');
    } catch (_) { return false; }
  }
  function validOfficialMonetaryRows(payload, currentRows, historyRows) {
    if (!payload || payload.mode !== 'official-monetary-history-v1'
        || payload.repository_publish !== true || payload.frontend_publish !== false
        || !Array.isArray(payload.data) || payload.record_count !== payload.data.length) return [];
    const keys = new Set([...currentRows, ...historyRows]
      .map(row => `${row.indicator_id}:${row.period_type}:${row.period}`));
    const accepted = [];
    payload.data.forEach(row => {
      const rate = MONETARY_RATE_COMPONENTS[row?.indicator_id];
      const policy = PRODUCTION_INDICATORS.get(row?.indicator_id);
      const validPeriod = typeof row?.period === 'string' && /^20\d{2}-(0[1-9]|1[0-2])$/.test(row.period);
      const key = `${row?.indicator_id}:${row?.period_type}:${row?.period}`;
      if (!MONETARY_HISTORY_IDS.has(row?.indicator_id) || !policy || !validPeriod
          || row.period_type !== 'month' || row.unit !== policy.unit
          || row.evidence_status !== 'verified' || row.observation_status !== 'final'
          || row.historical_observation !== true || !row.source_reviewed_at
          || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(row.source_release_period || '')
          || !Number.isFinite(Number(row.value))
          || !officialMonetaryHost(row.source_url, row.source_id) || keys.has(key)) return;
      if (rate) {
        if (row.source_id !== 'sbv-vietnam' || row.rate_basis !== rate[0]
            || row.rate_bound !== rate[1]
            || row.value < 0 || row.value > 25) return;
      } else {
        // NSO reports growth relative to the preceding December, not YoY.
        // The stated observation date, not the nominal report period, is
        // retained for audit and must fall within that quarter-end month.
        if (row.source_id !== 'nso-vietnam'
            || row.comparison_base !== 'previous-year-end'
            || row.reporting_cadence !== 'quarterly'
            || !/(03|06|09|12)$/.test(row.period)
            || !/^20\d{2}-\d{2}-\d{2}$/.test(row.as_of_date || '')
            || row.data_date !== row.as_of_date
            || row.as_of_date.slice(0,7) !== row.period
            || row.value < -50 || row.value > 100) return;
      }
      keys.add(key);
      accepted.push({ ...row, _data_layer: 'production', _historical: true });
    });
    return accepted;
  }

  function buildProductionRateRanges(productionRows) {
    const syntheticRows = [];
    const virtualIds = new Set();
    PRODUCTION_RATE_RANGES.forEach(cfg => {
      const lows = productionRows.filter(row => row.indicator_id === cfg.lowId);
      const highs = productionRows.filter(row => row.indicator_id === cfg.highId);
      const highsByPeriod = new Map(highs.map(row => [row.period, row]));
      lows.forEach(low => {
        const high = highsByPeriod.get(low.period);
        if (!high || low.period_type !== high.period_type) return;
        const sourceIds = [...new Set([
          ...(low.corroboration_source_ids || [low.source_id]),
          ...(high.corroboration_source_ids || [high.source_id])
        ])];
        syntheticRows.push({
          id: `range:${cfg.id}:${low.period}`,
          indicator_id: cfg.id,
          period: low.period,
          period_type: low.period_type,
          data_date: low.data_date || high.data_date || low.period,
          value: (Number(low.value) + Number(high.value)) / 2,
          range_low: Number(low.value),
          range_high: Number(high.value),
          unit: 'percent-per-year',
          source_id: low.source_id,
          source_url: low.source_url,
          published_at: [low.published_at, high.published_at].filter(Boolean).sort().at(-1),
          evidence_status: low.evidence_status === 'verified' && high.evidence_status === 'verified'
            && low.source_id === 'sbv-vietnam' && high.source_id === 'sbv-vietnam'
              ? 'verified' : 'corroborated',
          observation_status: 'final',
          corroboration_source_ids: sourceIds,
          corroboration_observation_ids: [...new Set([
            ...(low.corroboration_observation_ids || [low.id]),
            ...(high.corroboration_observation_ids || [high.id])
          ])],
          methodology_note: 'Paired low/high production components for the same monthly bulletin period.',
          _data_layer: 'production',
          _range: true
        });
        virtualIds.add(cfg.id);
      });
    });
    return { syntheticRows, virtualIds };
  }

  function integrateMacroObservations(mockPayload, productionPayload, publishMeta, historyPayload, marketHistoryPayload, monetaryHistoryPayload) {
    const mockRows = payloadData(mockPayload).map(row => ({ ...row, _data_layer: 'demo' }));
    const currentProductionRows = validProductionRows(productionPayload, publishMeta).map(row => ({ ...row, _data_layer: 'production' }));
    const historyRows = validHistoricalRows(historyPayload, currentProductionRows);
    const marketHistoryRows = validHistoricalMarketRows(marketHistoryPayload, currentProductionRows, historyRows);
    const monetaryHistoryRows = validOfficialMonetaryRows(monetaryHistoryPayload, currentProductionRows, [...historyRows, ...marketHistoryRows]);
    const allHistoryRows = [...historyRows, ...marketHistoryRows, ...monetaryHistoryRows];
    const productionRows = [...currentProductionRows, ...allHistoryRows];
    const rawProductionIndicatorIds = new Set(productionRows.map(row => row.indicator_id));
    const ranges = buildProductionRateRanges(productionRows);
    const productionIndicatorIds = new Set([...rawProductionIndicatorIds, ...ranges.virtualIds]);

    // Never mix illustrative and controlled history for an indicator that has production.
    // When a complete rate range is available, suppress the old illustrative scalar card/series.
    const replacedFallbackIds = new Set(
      PRODUCTION_RATE_RANGES.filter(cfg => ranges.virtualIds.has(cfg.id)).map(cfg => cfg.fallbackId)
    );
    const retainedMockRows = mockRows.filter(row =>
      !productionIndicatorIds.has(row.indicator_id) && !replacedFallbackIds.has(row.indicator_id)
    );
    return {
      rows: [...retainedMockRows, ...productionRows, ...ranges.syntheticRows],
      productionRows,
      currentProductionCount: currentProductionRows.length,
      historicalCount: allHistoryRows.length,
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
  function localizedText(value) {
    const text = String(value ?? '');
    return window.AppDynamicLocalization?.translate?.(text) || text;
  }

  function productionEvidenceLabel(row) {
    if (row?._data_layer !== 'production') return '';
    if (row.evidence_status === 'verified') return 'Canonical';
    if (row.evidence_status === 'corroborated') return 'Corroborated';
    return 'Production';
  }

  function observationStatusLabel(row) {
    const evidence = productionEvidenceLabel(row);
    return evidence || labelize(row?.observation_status);
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
    const bankingSynced = productionState.indicatorIds.has('credit-growth-ytd')
      && productionState.indicatorIds.has('bank-funding-growth-ytd');
    const customerRatesSynced = productionState.indicatorIds.has('deposit-rate-vnd-6-12m-range')
      && productionState.indicatorIds.has('lending-rate-vnd-average-range');
    const policyRatesSynced = PRODUCTION_POLICY_RATE_SERIES.every(id => productionState.indicatorIds.has(id));
    text.textContent = customerRatesSynced && policyRatesSynced
      ? 'Controlled production includes verified NSO banking indicators, independently corroborated customer-rate ranges, and independently corroborated SBV policy rates. Rate ranges remain low–high ranges; no scalar average is fabricated.'
      : customerRatesSynced
        ? 'Controlled production includes verified NSO banking indicators plus customer-rate ranges published by the State Bank of Vietnam and independently corroborated through secondary sources. Rate ranges remain low–high ranges; no scalar average is fabricated.'
      : bankingSynced
        ? 'Controlled production now includes verified NSO banking indicators: Credit Growth YTD and Bank Funding Growth YTD. Canonical and Corroborated labels remain evidence-based; unpromoted indicators remain illustrative demo data.'
        : 'Production observations are labeled by evidence status: verified official data as Canonical and independently matched data as Corroborated. Unpromoted indicators remain illustrative demo data.';
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

  function seriesCoverageNote(id) {
    const rows = observationsFor(id);
    const current = rows.at(-1) || null;
    if (current?._data_layer === 'production' && rows.length === 1) {
      return indicator(id)?.frequency === 'event-driven'
        ? 'Current effective event only · no synthetic history is created.'
        : 'Latest observation only · no synthetic history is created.';
    }
    if (current?._data_layer === 'production') {
      return 'Controlled production history · demo points are not mixed into this series.';
    }
    return 'Illustrative demo history.';
  }

  function corroborationProvenance(row) {
    const ids = Array.isArray(row?.corroboration_source_ids) ? [...new Set(row.corroboration_source_ids)] : [];
    if (row?._data_layer !== 'production' || row.evidence_status !== 'corroborated' || ids.length < 2) return '';
    return `<div class="provenance-inline-row provenance-inline-row--wrap"><span class="source-tag">Corroborated</span>${ids.map(id => sourceRef(id, { period: row.period })).join('')}<span class="muted-text">Matched across independent sources</span></div>`;
  }

  function obsKey(item) { return item.data_date || item.period || ''; }
  function observationsFor(id) {
    if (window.HistoryEngine?.macroSeries) return HistoryEngine.macroSeries(data.observations, id);
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

  function formatObservationValue(ind, row, compact = false) {
    if (!row) return '—';
    if (row._range && Number.isFinite(Number(row.range_low)) && Number.isFinite(Number(row.range_high))) {
      const low = formatNumber(row.range_low, 1);
      const high = formatNumber(row.range_high, 1);
      return `${low}–${high}%${compact ? '' : ' p.a.'}`;
    }
    return formatValue(ind, row.value, compact);
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
    if (!current) return { label:'—', direction:'neutral' };
    if (current._range) {
      if (!previous) return { label:'Latest range', direction:'neutral' };
      const changed = Number(current.range_low) !== Number(previous.range_low)
        || Number(current.range_high) !== Number(previous.range_high);
      return { label: changed ? 'Range updated' : 'No range change', direction:'neutral' };
    }
    if (!previous) {
      return current?._data_layer === 'production'
        ? { label:'Latest only', direction:'neutral' }
        : { label:'—', direction:'neutral' };
    }
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

  function indicatorCadence(row) {
    if (!row) return { label:'Chưa có số liệu đã xác minh', stale:false };
    if (row.indicator_id === 'policy-refinancing-rate') {
      return {label:'Theo quyết định · kỳ công bố gần nhất',stale:false};
    }
    if (row.period_type === 'month') {
      return {label:'Theo tháng · không cập nhật hằng ngày',stale:false};
    }
    if (row.period_type === 'day') {
      const stamp = Date.parse((row.data_date || row.period) + 'T00:00:00Z');
      const diff = Number.isFinite(stamp) ? Math.floor((Date.now()-stamp)/86400000) : null;
      return {label:diff != null && diff >= 0
        ? `Chuỗi ngày · cách hiện tại ${diff} ngày`
        : 'Chuỗi ngày · theo ngày nguồn',stale:diff != null && diff > 3};
    }
    return {label:'Kỳ công bố gần nhất',stale:false};
  }

  function latestProductionReleaseList(limit=5) {
    const seen = new Set();
    return [...data.observations]
      .filter(row => row._data_layer === 'production' && row.published_at && row.indicator_id)
      .sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at))
        || String(b.data_date||b.period).localeCompare(String(a.data_date||a.period)))
      .filter(row => {
        if (seen.has(row.indicator_id)) return false;
        seen.add(row.indicator_id);
        return true;
      }).slice(0,limit).map(row => `<button class="macro-release-row" type="button" data-macro-indicator-id="${esc(row.indicator_id)}">
        <span>${esc(App.formatDate(row.published_at))}</span><div>
          <span class="source-tag">${esc(productionEvidenceLabel(row))}</span>
          <strong>${esc(indicator(row.indicator_id)?.name || row.indicator_id)}</strong>
          <small>Kỳ dữ liệu: ${esc(formatPeriod(row))}</small>
        </div></button>`).join('') || Components.stateBox('Chưa có kỳ công bố production mới được xác minh.');
  }

  function metricCard(id) {
    const ind = indicator(id); if (!ind) return '';
    const { current } = latestPair(id); const delta = deltaInfo(id);
    const cadence = indicatorCadence(current);
    return `<button class="macro-metric-card" type="button" data-macro-indicator-id="${esc(id)}">
      <div class="macro-metric-card__top"><span>${esc(ind.name)}</span><span class="source-tag">${esc(dataLayerBadge(ind, current))}</span></div>
      <strong>${esc(formatObservationValue(ind, current, true))}</strong>
      <div class="macro-metric-card__foot"><span class="macro-delta">${esc(delta.label)}</span><span>${esc(formatPeriod(current))}</span></div>
      <small class="macro-cadence${cadence.stale ? ' is-stale' : ''}">${esc(cadence.label)}</small>
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

  function ratesSeries() {
    const hasProductionRanges = productionState.indicatorIds.has('deposit-rate-vnd-6-12m-range')
      && productionState.indicatorIds.has('lending-rate-vnd-average-range');
    const base = hasProductionRanges
      ? ['deposit-rate-vnd-6-12m-range', 'lending-rate-vnd-average-range', 'interbank-on']
      : ['deposit-rate-12m-average', 'lending-rate-average', 'interbank-on'];
    const policyProduction = PRODUCTION_POLICY_RATE_SERIES.filter(id => productionState.indicatorIds.has(id));
    return policyProduction.length ? [...base, ...policyProduction] : [...base, 'policy-refinancing-rate'];
  }

  function seriesForView(view) {
    return view === 'rates' ? ratesSeries() : (VIEW_SERIES[view] || []);
  }

  function defaultSeriesForView(view) {
    return view === 'rates'
      ? ratesSeries()[0]
      : DEFAULT_SERIES[view];
  }

  function keyIndicators() {
    const rateIds = ratesSeries().slice(0, 2);
    const policyRate = productionState.indicatorIds.has('policy-refinancing-rate') ? ['policy-refinancing-rate'] : [];
    return ['usd-vnd-central-rate','sjc-gold-sell',...rateIds,...policyRate,'credit-growth-ytd','bank-funding-growth-ytd','cpi-yoy'];
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
      return `<tr><td data-label-vi="Chỉ số" data-label-en="Indicator"><button class="table-link" type="button" data-macro-indicator-id="${esc(id)}">${esc(ind?.name || id)}</button><span class="table-subtext">${esc(labelize(ind?.indicator_category))}</span></td><td class="numeric" data-label-vi="Giá trị gần nhất" data-label-en="Current">${esc(formatObservationValue(ind,current))}</td><td class="numeric" data-label-vi="Thay đổi" data-label-en="Change">${esc(delta.label)}</td><td data-label-vi="Kỳ dữ liệu" data-label-en="Data period">${esc(formatPeriod(current))}<span class="table-subtext">Published ${esc(App.formatDate(current?.published_at))}</span></td><td data-label-vi="Nguồn" data-label-en="Source">${current ? sourceRef(current.source_id,{publishedAt:current.published_at,period:current.period,sourceUrl:current.source_url}) : '—'}</td></tr>`;
    }).join('');
    return `<div class="table-wrap"><table class="data-table data-table--macro mobile-record-table"><thead><tr><th>Indicator</th><th class="numeric">Current</th><th class="numeric">Change</th><th>Data Period</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderOverview() {
    const ids = keyIndicators();
    const fxRows = rangeRows('usd-vnd-central-rate','1M');
    setView(`
      <p class="macro-overview-cadence-note">Các kỳ công bố được giữ nguyên: tỷ giá/vàng theo ngày nguồn, CPI/tín dụng theo tháng, lãi suất chính sách theo quyết định. Không có số liệu mới thì giữ kỳ cũ, không tự nội suy.</p>
      <div class="macro-metric-grid macro-metric-grid--overview">${ids.map(metricCard).join('')}</div>
      <div class="market-layout market-layout--overview">
        <section class="section market-panel market-panel--wide">
          <div class="section-header"><div><span class="eyebrow">Daily monitor</span><h2 class="section-title">USD/VND Central Rate</h2></div><a class="text-link" href="macro.html?view=fx&series=usd-vnd-central-rate&range=1M">Open FX</a></div>
          <div class="section-body"><div class="chart-frame"><canvas id="macro-overview-chart"></canvas></div><p class="chart-note">${esc(overviewChartNote('usd-vnd-central-rate'))}</p></div>
        </section>
        <section class="section market-panel">
          <div class="section-header"><div><span class="eyebrow">Verified releases</span><h2 class="section-title">Kỳ dữ liệu mới công bố</h2></div><a class="text-link" href="macro.html?view=overview">Xem chỉ số</a></div>
          <div class="section-body macro-release-list">${latestProductionReleaseList(5)}</div>
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
    const ids = seriesForView(view);
    return `<div class="macro-series-toolbar"><label class="filter-field"><span>Indicator</span><select data-series-select>${ids.map(id=>`<option value="${esc(id)}"${id===selected?' selected':''}>${esc(indicator(id)?.name || id)}</option>`).join('')}</select></label><div class="macro-range-group" aria-label="Chart range">${['1M','3M','1Y','ALL'].map(range=>`<button class="macro-range-button${state.range===range?' is-active':''}" type="button" data-range="${range}">${range}</button>`).join('')}</div></div>`;
  }

  function recentObservationTable(id, limit = 12) {
    const ind = indicator(id);
    const rows = [...observationsFor(id)].reverse().slice(0,limit).map(row => `<tr><td data-label-vi="Kỳ dữ liệu" data-label-en="Data period">${esc(formatPeriod(row))}<span class="table-subtext">${esc(row.period)}</span></td><td class="numeric" data-label-vi="Giá trị" data-label-en="Value">${esc(formatObservationValue(ind,row))}</td><td data-label-vi="Trạng thái" data-label-en="Status">${esc(observationStatusLabel(row))}</td><td data-label-vi="Ngày công bố" data-label-en="Published">${esc(App.formatDate(row.published_at))}</td><td data-label-vi="Nguồn" data-label-en="Source">${sourceRef(row.source_id,{publishedAt:row.published_at,period:row.period,sourceUrl:row.source_url})}</td></tr>`).join('');
    return `<div class="table-wrap"><table class="data-table data-table--macro-history mobile-record-table"><thead><tr><th>Data Period</th><th class="numeric">Value</th><th>Status</th><th>Published</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderSeriesView(view) {
    const ids = seriesForView(view);
    let selected = ids.includes(state.series) ? state.series : defaultSeriesForView(view);
    if (!selected) selected = ids[0];
    const ind = indicator(selected); const rows = rangeRows(selected);
    const currentSourceRow = latestPair(selected).current;
    setView(`
      <div class="view-intro"><div><span class="eyebrow">Historical series</span><h2>${esc(viewTitle(view))}</h2><p>${esc(viewDescription(view))}</p></div></div>
      <div class="macro-metric-grid macro-metric-grid--section">${ids.map(metricCard).join('')}</div>
      <section class="section"><div class="section-header"><div><span class="eyebrow">${esc(labelize(ind?.frequency))}</span><h2 class="section-title">${esc(ind?.name || '')}</h2></div>${seriesControls(view,selected)}</div><div class="section-body"><div class="chart-frame chart-frame--large"><canvas id="macro-series-chart"></canvas></div><p class="chart-note">${currentSourceRow ? sourceRef(currentSourceRow.source_id,{publishedAt:currentSourceRow.published_at,period:currentSourceRow.period,sourceUrl:currentSourceRow.source_url}) : "—"} · <span>${esc(seriesCoverageNote(selected))}</span> · <span>${esc(ind?.methodology_note || '')}</span></p></div></section>
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
    if (rows.some(row => row._range)) {
      ChartTools.renderRangeSeries(canvasId, {
        labels: rows.map(formatPeriod),
        lowValues: rows.map(row => row.range_low),
        highValues: rows.map(row => row.range_high),
        lowLabel: localizedText('Lower bound'),
        highLabel: localizedText('Upper bound'),
        yFormatter: axisFormatter(ind)
      });
      return;
    }
    ChartTools.renderTimeSeries(canvasId, {
      label: localizedText(ind.name),
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
    setView(MarketNewsUI.render({
      module: 'macro',
      articles: data.articles,
      state
    }));
    MarketNewsUI.bind({state, refresh: renderNews});
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
      <div class="drawer-metrics">${Components.compactMetric({label:'Current',value:formatObservationValue(ind,current),note:formatPeriod(current)})}${Components.compactMetric({label:'Previous',value:formatObservationValue(ind,previous),note:formatPeriod(previous)})}${Components.compactMetric({label:'Change',value:delta.label,note:'Previous available observation'})}${Components.compactMetric({label:'Source',value:window.Provenance?.label?.(current?.source_id) || labelize(current?.source_id),note:current ? `Published ${App.formatDate(current.published_at)}` : ''})}</div>
      <div class="drawer-section"><h3>Definition</h3><p>${esc(ind.description)}</p></div>
      <div class="drawer-section"><h3>Methodology</h3><p>${esc(ind.methodology_note)}</p></div>
      <div class="drawer-section"><h3>Data Provenance</h3>${current ? `<div class="provenance-inline-row"><span class="source-tag">${esc(dataLayerBadge(ind,current))}</span>${sourceRef(current.source_id,{publishedAt:current.published_at,period:current.period,sourceUrl:current.source_url,methodology:ind.methodology_note})}<span class="muted-text">Current displayed observation · ${esc(formatPeriod(current))}</span></div>${corroborationProvenance(current)}` : '<p class="muted-text">No current observation source available.</p>'}</div>
      <div class="drawer-section"><h3>Recent Observations</h3>${recent.map(row=>`<div class="drawer-list-row"><div><strong>${esc(formatPeriod(row))}</strong><span>${esc(row.period)} · ${esc(observationStatusLabel(row))}</span></div><div><strong>${esc(formatObservationValue(ind,row))}</strong><span>${sourceRef(row.source_id,{publishedAt:row.published_at,period:row.period,sourceUrl:row.source_url})}</span></div></div>`).join('')}</div>
      <div class="drawer-section"><h3>Related Evidence</h3>${articles.length ? articles.map(item=>`<div class="drawer-list-row drawer-list-row--stack"><span>DEMO · ${esc(App.formatDate(item.published_at))} · ${esc(item.content_type)}</span><strong>${esc(item.title)}</strong></div>`).join('') : `<p class="muted-text">${current?._data_layer === 'production' ? 'No promoted evidence articles yet.' : 'No related articles.'}</p>`}</div>
      <div class="drawer-section"><a class="text-link" href="macro.html?view=${encodeURIComponent(view)}&series=${encodeURIComponent(id)}&range=1Y">Open historical series</a></div>`;
  }

  function openIndicator(id,{push=true}={}) {
    const ind=indicator(id); if (!ind) return;
    if (push) App.setQueryParam('indicator',id,{push:true});
    App.openDrawer({title:ind.name,html:indicatorDrawerHTML(id)});
  }

  function bindDelegatedEvents() {
    document.addEventListener('app:language-changed', () => {
      if (data.indicators.length) render();
    });
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
      const historyPromise = DataStore.getVerifiedMacroHistory()
        .catch(error => { console.warn('[macro] verified historical observations unavailable.', error); return null; });
      const marketHistoryPromise = DataStore.getVerifiedMacroMarketHistory()
        .catch(error => { console.warn('[macro] reviewed FX/SJC historical quotes unavailable.', error); return null; });
      const monetaryHistoryPromise = DataStore.getVerifiedMonetaryHistory()
        .catch(error => { console.warn('[macro] NSO/SBV monetary history unavailable.', error); return null; });

      const [indicators, observations, articles, events, meta, productionObservations, productionMeta, historicalObservations, marketHistoryObservations, monetaryHistoryObservations] = await Promise.all([
        DataStore.getMacroIndicators(), DataStore.getMacroObservations(), DataStore.getArticles(), DataStore.getEvents(), DataStore.getMeta(),
        productionObservationsPromise, productionMetaPromise, historyPromise, marketHistoryPromise, monetaryHistoryPromise
      ]);

      const integrated = integrateMacroObservations(observations, productionObservations, productionMeta, historicalObservations, marketHistoryObservations, monetaryHistoryObservations);
      productionState = {
        active: integrated.productionRows.length > 0,
        recordCount: integrated.productionRows.length,
        historicalCount: integrated.historicalCount,
        currentProductionCount: integrated.currentProductionCount,
        indicatorIds: integrated.productionIndicatorIds,
        rows: integrated.productionRows,
        publishMeta: productionMeta
      };
      data = {
        indicators: applyProductionIndicatorMetadata(payloadData(indicators), integrated.productionIndicatorIds),
        observations: integrated.rows,
        articles:payloadData(articles),
        events:payloadData(events).filter(item=>item.category==='macro').map(item=>({ ...item, _data_layer:'demo' }))
      };
      Resolver.setData('macro-indicator',data.indicators);
      parseState(); adjustViewFromDeepLink();
      if (updatedLabel()) {
        updatedLabel().textContent = productionState.active
          ? `Controlled macro · ${productionState.currentProductionCount} current + ${productionState.historicalCount} verified historical records`
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
