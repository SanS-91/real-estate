(() => {
  'use strict';

  function escapeHTML(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function metricCard(item) {
    const direction = item.change_direction || 'neutral';
    const changeClass = direction === 'up' ? 'is-up' : direction === 'down' ? 'is-down' : 'is-neutral';
    return `
      <article class="metric-card">
        <div class="metric-card__topline">
          <span class="metric-card__label">${escapeHTML(item.label)}</span>
          <span class="source-tag">${escapeHTML(item.source || 'Demo')}</span>
        </div>
        <div class="metric-card__value">${escapeHTML(item.display_value)}</div>
        ${item.cadence_label ? `<div class="metric-card__cadence">${escapeHTML(item.cadence_label)}</div>` : ''}
        <div class="metric-card__footer">
          <span class="metric-change ${changeClass}">${escapeHTML(item.change_label || '—')}</span>
          <span>${escapeHTML(item.period_label || '')}</span>
        </div>
      </article>
    `;
  }

  function todayCard(group) {
    const items = (group.items || []).slice(0, 3).map(item => `
      <li>
        <a class="compact-link" href="${escapeHTML(item.href || '#')}">
          <span>${escapeHTML(item.title)}</span>
          <span class="compact-link__meta"><time>${escapeHTML(item.date_label || '')}</time>${item.date_label && item.meta ? ' · ' : ''}${escapeHTML(item.meta || '')}</span>
        </a>
      </li>
    `).join('');

    return `
      <article class="today-card">
        <div class="today-card__header">
          <div>
            <div class="eyebrow">${escapeHTML(group.label)}</div>
            <div class="today-card__count">${escapeHTML(group.count_label || `${group.count} updates`)}</div>
          </div>
          <a class="text-link" href="${escapeHTML(group.href || '#')}">View all</a>
        </div>
        <ul class="compact-list">${items || '<li class="muted-text">No updates.</li>'}</ul>
      </article>
    `;
  }

  function changeCard(item) {
    return `
      <article class="change-card">
        <div class="change-card__meta">
          <span class="category-pill category-pill--${escapeHTML(item.category)}">${escapeHTML(item.category_label)}</span>
          <span>${escapeHTML(item.date_label)}</span>
          ${item.importance_label ? `<span class="importance-label">${escapeHTML(item.importance_label)}</span>` : ''}
        </div>
        <h3>${escapeHTML(item.title)}</h3>
        <p>${escapeHTML(item.summary)}</p>
        <a class="text-link" href="${escapeHTML(item.href || '#')}">View context</a>
      </article>
    `;
  }

  function weeklyItem(item) {
    return `
      <article class="weekly-item">
        <div class="weekly-item__date">${escapeHTML(item.date_label)}</div>
        <div class="weekly-item__content">
          <div class="weekly-item__topline">
            <span class="category-pill category-pill--${escapeHTML(item.category)}">${escapeHTML(item.category_label)}</span>
            <span class="importance-label">${escapeHTML(item.importance_label || '')}</span>
          </div>
          <a class="weekly-item__title" href="${escapeHTML(item.href || '#')}">${escapeHTML(item.title)}</a>
          <p>${escapeHTML(item.summary)}</p>
        </div>
      </article>
    `;
  }

  function quickLink(item) {
    return `
      <a class="quick-link-card" href="${escapeHTML(item.href)}">
        <span class="quick-link-card__label">${escapeHTML(item.label)}</span>
        <strong>${escapeHTML(item.title)}</strong>
        <span>${escapeHTML(item.description)}</span>
      </a>
    `;
  }

  function stateBox(message, type = 'empty') {
    return `<div class="state-box state-box--${escapeHTML(type)}">${escapeHTML(message)}</div>`;
  }


  function statusBadge(status) {
    const label = String(status || 'unknown').replaceAll('-', ' ');
    return `<span class="status-badge status-badge--${escapeHTML(status || 'unknown')}">${escapeHTML(label)}</span>`;
  }

  function compactMetric({ label, value, note = '' }) {
    return `
      <div class="compact-metric">
        <span>${escapeHTML(label)}</span>
        <strong>${escapeHTML(value)}</strong>
        ${note ? `<small>${escapeHTML(note)}</small>` : ''}
      </div>
    `;
  }

  window.Components = {
    escapeHTML,
    metricCard,
    todayCard,
    changeCard,
    weeklyItem,
    quickLink,
    stateBox,
    statusBadge,
    compactMetric
  };
})();
