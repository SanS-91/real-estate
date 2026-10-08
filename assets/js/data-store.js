(() => {
  'use strict';

  const memoryCache = new Map();
  let settingsPromise = null;

  async function getSettings() {
    if (!settingsPromise) {
      settingsPromise = fetch('config/settings.json', { cache: 'no-cache' })
        .then(response => {
          if (!response.ok) throw new Error(`Unable to load settings (${response.status})`);
          return response.json();
        });
    }
    return settingsPromise;
  }

  function normalizeRoot(root) {
    if (!root) return './data/mock/';
    return root.endsWith('/') ? root : `${root}/`;
  }

  async function loadJSON(relativePath) {
    const settings = await getSettings();
    const root = normalizeRoot(settings.data_root);
    const path = `${root}${relativePath}`;
    return loadDirectJSON(path, relativePath);
  }

  function loadDirectJSON(path, label = path) {
    if (memoryCache.has(path)) return memoryCache.get(path);

    const request = fetch(path, { cache: 'no-cache' })
      .then(response => {
        if (!response.ok) throw new Error(`Unable to load ${label} (${response.status})`);
        return response.json();
      })
      .catch(error => {
        memoryCache.delete(path);
        throw error;
      });

    memoryCache.set(path, request);
    return request;
  }

  function clearCache() {
    memoryCache.clear();
  }

  window.DataStore = {
    getSettings,
    loadJSON,
    clearCache,
    getHomeToday: () => loadJSON('home/today.json'),
    getHomeIndicators: () => loadJSON('home/indicators.json'),
    getHomeChanges: () => loadJSON('home/changes.json'),
    getHomeWeekly: () => loadJSON('home/weekly.json'),
    getMeta: () => loadJSON('core/meta.json'),
    getRegions: () => loadJSON('core/regions.json'),
    getDevelopers: () => loadJSON('core/developers.json'),
    getAgencies: () => loadJSON('core/agencies.json'),
    getSources: () => loadJSON('core/sources.json'),
    getProjects: () => loadJSON('market/projects.json'),
    getProjectPhases: () => loadJSON('market/project-phases.json'),
    getMarketObservations: () => loadJSON('market/observations.json'),
    getListingObservations: () => loadJSON('market/listing-observations.json'),
    getListingComparables: () => loadJSON('market/listing-comparables.json'),
    getLegalTopics: () => loadJSON('legal/topics.json'),
    getLegalDocuments: () => loadJSON('legal/documents.json'),
    getInfrastructureProjects: () => loadJSON('infrastructure/projects.json'),
    getInfrastructureSchedules: () => loadJSON('infrastructure/schedules.json'),
    getMacroIndicators: () => loadJSON('macro/indicators.json'),
    getMacroObservations: () => loadJSON('macro/observations.json'),
    getProcessedMacroObservations: () => loadDirectJSON('./data/processed/macro/observations.json', 'processed macro observations'),
    getProcessedMacroPublishMeta: () => loadDirectJSON('./data/processed/macro/repository-publish.json', 'processed macro publish metadata'),
    getEvents: () => loadJSON('events/events.json'),
    getArticles: () => loadJSON('articles/articles.json'),
    getDataHealth: () => loadDirectJSON('./data/state/data-health.json', 'unified data health'),
    getIntelligenceModel: () => loadDirectJSON('./config/intelligence_model.json', 'intelligence model')
  };
})();
