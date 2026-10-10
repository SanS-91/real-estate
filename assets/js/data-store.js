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

  // Cross-tab news routing: one canonical article can appear in several modules.
  // Source metadata alone is insufficient: preserve explicit tags and legacy categories.
  function newsModules(article) {
    if (!article || !article.url || !article.title || String(article.source_id || '').startsWith('demo-') ||
        /^(demo|illustrative)[\s:–-]/i.test(String(article.title || ''))) return [];
    const allowed = ['market', 'legal', 'infrastructure', 'macro'];
    const tags = Array.isArray(article.tags) ? article.tags : [];
    const explicit = Array.isArray(article.module_ids) ? article.module_ids : [];
    const modules = [...explicit, article.category, ...tags].filter(m => allowed.includes(m));
    return [...new Set(modules)];
  }
  function isNewsFor(article, module) {
    return newsModules(article).includes(module);
  }

  window.DataStore = {
    newsModules,
    isNewsFor,
    getNewsHealth: () => loadDirectJSON('./data/state/news-ingestion-health.json', 'news ingestion health'),
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
    getListingScopeEvidence: () => loadJSON('market/listing-scope-evidence.json'),
    getAlternativePriceEvidence: () => loadJSON('market/alternative-price-evidence.json'),
    getSecondaryListingEvidence: () => loadJSON('market/secondary-listing-evidence.json'),
    getReverVerifiedUnitListings: () => loadJSON('market/verified-unit-listings.json'),
    getMuabanVerifiedUnitListings: () => loadJSON('market/verified-muaban-unit-listings.json'),
    getOneHousingSubprojectEvidence: () => loadJSON('market/alternative-subproject-monthly-evidence.json'),
    getOneHousingSubprojectHistory: () => loadJSON('market/alternative-subproject-monthly-history.json'),
    getOneHousingProjectHistory: () => loadJSON('market/onehousing-project-monthly-history.json'),
    getPeerMonthlyVerified: () => loadJSON('market/peer-project-monthly-verified.json'),
    getPeerMonthlyTargets: () => loadDirectJSON('./config/market-onehousing-peer-monthly-targets.json', 'peer monthly targets'),
    getPeerMonthlySourceHealth: () => loadDirectJSON('./data/state/market-onehousing-peer-monthly-health.json', 'peer monthly source health'),
    getListingSourceCoverage: () => loadDirectJSON('./data/state/listing-source-coverage.json', 'listing source coverage'),
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
    getIntelligenceModel: () => loadDirectJSON('./config/intelligence_model.json', 'intelligence model'),
    getIntelligenceRankingRules: () => loadDirectJSON('./config/intelligence-ranking.json', 'intelligence ranking rules'),
    getAIAnalysisConfig: () => loadDirectJSON('./config/ai-analysis.json', 'AI analysis policy')
  };
})();
