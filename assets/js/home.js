(() => {
  'use strict';

  function setHTML(selector, html) {
    const node = document.querySelector(selector);
    if (node) node.innerHTML = html;
  }

  function setText(selector, text) {
    const node = document.querySelector(selector);
    if (node) node.textContent = text;
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
      const payload = await DataStore.getHomeIndicators();
      setHTML('[data-home-indicators]', (payload.data || []).map(Components.metricCard).join(''));
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
      const payload = await DataStore.getMeta();
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
