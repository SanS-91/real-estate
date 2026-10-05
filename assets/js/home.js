(() => {
  'use strict';

  const HOME_PRODUCTION_RULES = new Map([
    ['usd-vnd-central-rate', { unit: 'vnd-per-usd', evidenceStatus: 'corroborated', sources: ['banking-times-vn', 'vna-vietnamplus'] }],
    ['sjc-gold-sell', { unit: 'vnd-per-tael', evidenceStatus: 'corroborated', sources: ['baonghean-gold', 'vietnamnet-gold'] }],
    ['credit-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['bank-funding-growth-ytd', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }],
    ['cpi-yoy', { unit: 'percent', evidenceStatus: 'verified', sources: ['nso-vietnam'] }]
  ]);
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
    'cpi-yoy': 'CPI YoY'
  };

  let productionPromise = null;

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
        console.warn('[home] processed macro observations unavailable; keeping demo macro snapshot.', error);
        return null;
      }),
      DataStore.getProcessedMacroPublishMeta().catch(error => {
        console.warn('[home] processed macro publish metadata unavailable; keeping demo macro snapshot.', error);
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

  function formatProductionPeriod(row) {
    if (!row) return '';
    if (row.period_type === 'month' && /^\d{4}-\d{2}$/.test(row.period || '')) {
      const [year, month] = row.period.split('-').map(Number);
      return new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric' })
        .format(new Date(Date.UTC(year, month - 1, 1)));
    }
    return App.formatDate(row.data_date || row.period);
  }

  function productionCard(row) {
    return {
      id: row.indicator_id,
      label: HOME_LABELS[row.indicator_id] || row.indicator_id,
      display_value: Formatters.unitValue(row.unit, row.value, { compact: true }),
      change_label: 'Latest only',
      change_direction: 'neutral',
      period_label: formatProductionPeriod(row),
      source: productionEvidenceLabel(row)
    };
  }

  function mergeHomeIndicatorCards(mockCards, production) {
    const cards = mockCards.map(card => {
      const indicatorId = HOME_CARD_TARGETS[card.id];
      const row = indicatorId ? production.latest.get(indicatorId) : null;
      return row ? productionCard(row) : card;
    });

    const bankFunding = production.latest.get('bank-funding-growth-ytd');
    if (bankFunding) {
      const creditIndex = cards.findIndex(card => card.id === 'credit-growth-ytd' || card.id === 'credit-demo');
      cards.splice(creditIndex >= 0 ? creditIndex + 1 : cards.length, 0, productionCard(bankFunding));
    }
    return cards;
  }

  async function renderToday() {
    try {
      const payload = await DataStore.getHomeToday();
      setHTML('[data-home-today]', (payload.data || []).map(Components.todayCard).join(''));
    } catch (error) {
      console.error(error);
      setHTML('[data-home-today]', Components.stateBox('Unable to load Today data.', 'error'));
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
      const payload = await DataStore.getHomeChanges();
      setHTML('[data-home-changes]', (payload.data || []).map(Components.changeCard).join(''));
    } catch (error) {
      console.error(error);
      setHTML('[data-home-changes]', Components.stateBox('Unable to load change events.', 'error'));
    }
  }

  async function renderWeekly() {
    try {
      const payload = await DataStore.getHomeWeekly();
      setHTML('[data-home-weekly]', (payload.data || []).map(Components.weeklyItem).join(''));
    } catch (error) {
      console.error(error);
      setHTML('[data-home-weekly]', Components.stateBox('Unable to load weekly highlights.', 'error'));
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
        setText('[data-home-updated]', `Mixed data · ${production.totalRecordCount} controlled macro records`);
        return;
      }
      const date = payload?.last_successful_build;
      setText('[data-home-updated]', date ? `Demo data · ${App.formatDate(date)}` : 'Demo data');
    } catch (error) {
      console.warn('Meta unavailable', error);
      setText('[data-home-updated]', 'Demo data');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderQuickResearch();
    renderMeta();
    renderToday();
    renderIndicators();
    renderChanges();
    renderWeekly();
  });
})();
