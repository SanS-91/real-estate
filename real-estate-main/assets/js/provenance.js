(() => {
  'use strict';

  let sourceIndex = new Map();
  let sourceRecords = [];
  let loadPromise = null;
  let modalMounted = false;

  function escapeHTML(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function labelize(value) {
    return String(value || '—')
      .replace(/^demo-/, '')
      .replaceAll('-', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  function payloadData(payload) {
    return Array.isArray(payload?.data) ? payload.data : [];
  }

  async function load() {
    if (loadPromise) return loadPromise;
    if (!window.DataStore?.getSources) return [];

    loadPromise = DataStore.getSources()
      .then(payload => {
        sourceRecords = payloadData(payload);
        sourceIndex = new Map(sourceRecords.map(source => [source.id, source]));
        return sourceRecords;
      })
      .catch(error => {
        console.warn('Source registry unavailable; continuing with source IDs only.', error);
        sourceRecords = [];
        sourceIndex = new Map();
        return [];
      });

    return loadPromise;
  }

  function get(sourceId) {
    return sourceId ? sourceIndex.get(sourceId) || null : null;
  }

  function label(sourceId) {
    return get(sourceId)?.name || labelize(sourceId);
  }

  function sourceButton(sourceId, context = {}) {
    if (!sourceId) return '<span class="provenance-missing">—</span>';
    const attrs = [
      ['data-provenance-source-id', sourceId],
      ['data-provenance-source-date', context.sourceDate],
      ['data-provenance-period', context.period],
      ['data-provenance-published-at', context.publishedAt],
      ['data-provenance-source-url', context.sourceUrl && context.sourceUrl !== '#' ? context.sourceUrl : null],
      ['data-provenance-methodology', context.methodology]
    ].filter(([, value]) => value !== null && value !== undefined && value !== '')
      .map(([key, value]) => `${key}="${escapeHTML(value)}"`)
      .join(' ');

    return `<button type="button" class="source-ref" ${attrs}>${escapeHTML(label(sourceId))}</button>`;
  }

  function contextFromElement(element) {
    return {
      sourceDate: element.dataset.provenanceSourceDate || null,
      period: element.dataset.provenancePeriod || null,
      publishedAt: element.dataset.provenancePublishedAt || null,
      sourceUrl: element.dataset.provenanceSourceUrl || null,
      methodology: element.dataset.provenanceMethodology || null
    };
  }

  function formatDate(value) {
    if (!value) return null;
    return window.App?.formatDate ? App.formatDate(value) : value;
  }

  function modalMarkup() {
    return `
      <div class="provenance-overlay" data-provenance-overlay aria-hidden="true">
        <section class="provenance-modal" role="dialog" aria-modal="true" aria-labelledby="provenance-title">
          <div class="provenance-modal__header">
            <div>
              <span class="eyebrow">Source &amp; provenance</span>
              <h2 id="provenance-title" data-provenance-title>Data Sources</h2>
            </div>
            <button class="icon-button" type="button" aria-label="Close source details" data-provenance-close>×</button>
          </div>
          <div class="provenance-modal__body" data-provenance-body></div>
        </section>
      </div>`;
  }

  function mountModal() {
    if (modalMounted) return;
    document.body.insertAdjacentHTML('beforeend', modalMarkup());
    modalMounted = true;
  }

  function setBodyLock(locked) {
    if (locked) document.body.dataset.provenancePreviousOverflow = document.body.style.overflow || '';
    document.body.style.overflow = locked ? 'hidden' : (document.body.dataset.provenancePreviousOverflow || '');
    if (!locked) delete document.body.dataset.provenancePreviousOverflow;
  }

  function openModal(title, html) {
    mountModal();
    const overlay = document.querySelector('[data-provenance-overlay]');
    const titleNode = document.querySelector('[data-provenance-title]');
    const bodyNode = document.querySelector('[data-provenance-body]');
    if (titleNode) titleNode.textContent = title;
    if (bodyNode) bodyNode.innerHTML = html;
    overlay?.classList.add('is-open');
    overlay?.setAttribute('aria-hidden', 'false');
    setBodyLock(true);
  }

  function closeModal() {
    const overlay = document.querySelector('[data-provenance-overlay]');
    if (!overlay?.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    setBodyLock(false);
  }

  function detailRow(labelText, value, { raw = false } = {}) {
    if (value === null || value === undefined || value === '') return '';
    return `<div class="provenance-detail-row"><span>${escapeHTML(labelText)}</span><strong>${raw ? value : escapeHTML(value)}</strong></div>`;
  }

  function sourceDetailsHTML(sourceId, context = {}) {
    const source = get(sourceId);
    if (!source) {
      return `<div class="state-box">Source metadata is not available for <strong>${escapeHTML(sourceId)}</strong>. The underlying page can still use the record-level source ID.</div>`;
    }

    const sourceUrl = context.sourceUrl || source.base_url;
    const link = sourceUrl && sourceUrl !== '#'
      ? `<a class="text-link" href="${escapeHTML(sourceUrl)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a>`
      : '<span class="muted-text">No public source URL is attached to this source definition.</span>';

    return `
      <div class="provenance-source-head">
        <span class="source-tag">${escapeHTML(labelize(source.source_type))}</span>
        <h3>${escapeHTML(source.name)}</h3>
        <p>${escapeHTML(source.notes || '')}</p>
      </div>
      <div class="provenance-detail-grid">
        ${detailRow('Source ID', source.id)}
        ${detailRow('Priority', `P${source.source_priority} · lower number = higher sourcing priority`)}
        ${detailRow('Language', String(source.language || '').toUpperCase())}
        ${detailRow('Collection', labelize(source.collection_method))}
        ${detailRow('Update frequency', labelize(source.fetch_frequency))}
        ${detailRow('Data / source date', formatDate(context.sourceDate))}
        ${detailRow('Data period', context.period)}
        ${detailRow('Published', formatDate(context.publishedAt))}
        ${detailRow('Methodology note', context.methodology)}
      </div>
      <div class="provenance-link-row">${link}</div>`;
  }

  function registryHTML() {
    if (!sourceRecords.length) {
      return '<div class="state-box">Source Registry is unavailable. Existing records will continue to display their source IDs.</div>';
    }

    const groups = new Map();
    sourceRecords
      .filter(source => source.active !== false)
      .sort((a, b) => (a.source_priority - b.source_priority) || a.name.localeCompare(b.name))
      .forEach(source => {
        const key = source.source_type || 'other';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(source);
      });

    return `
      <div class="provenance-registry-intro">
        <p><strong>${sourceRecords.length} source definitions</strong> resolve source IDs used across demo, curated and controlled-production records. The registry is provenance metadata; canonical status is determined by each dataset and its production gate.</p>
        <p class="muted-text">Priority is a sourcing preference, not a quality score. P1 is used for primary official sources; lower-priority evidence is retained rather than discarded.</p>
      </div>
      ${[...groups.entries()].map(([type, sources]) => `
        <section class="provenance-registry-group">
          <h3>${escapeHTML(labelize(type))}</h3>
          <div class="provenance-registry-list">
            ${sources.map(source => `
              <button type="button" class="provenance-registry-item" data-provenance-source-id="${escapeHTML(source.id)}">
                <div><strong>${escapeHTML(source.name)}</strong><span>${escapeHTML(source.id)} · P${escapeHTML(source.source_priority)}</span></div>
                <span>View ›</span>
              </button>`).join('')}
          </div>
        </section>`).join('')}`;
  }

  async function openSource(sourceId, context = {}) {
    await load();
    openModal(label(sourceId), sourceDetailsHTML(sourceId, context));
  }

  async function openRegistry() {
    await load();
    openModal('Data Sources', registryHTML());
  }

  function bindEvents() {
    document.addEventListener('click', event => {
      const sourceTrigger = event.target.closest('[data-provenance-source-id]');
      if (sourceTrigger) {
        event.preventDefault();
        openSource(sourceTrigger.dataset.provenanceSourceId, contextFromElement(sourceTrigger));
        return;
      }

      if (event.target.closest('[data-source-registry-open]')) {
        event.preventDefault();
        openRegistry();
        return;
      }

      if (event.target.closest('[data-provenance-close]')) {
        closeModal();
        return;
      }

      const overlay = event.target.closest('[data-provenance-overlay]');
      if (overlay && event.target === overlay) closeModal();
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeModal();
    });
  }

  window.Provenance = {
    load,
    get,
    label,
    sourceButton,
    openSource,
    openRegistry,
    closeModal
  };

  document.addEventListener('DOMContentLoaded', () => {
    mountModal();
    bindEvents();
    load();
  });
})();
