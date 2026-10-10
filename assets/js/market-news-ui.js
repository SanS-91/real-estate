(() => {
  'use strict';

  // This presentation layer never changes market records; it only filters
  // existing sourced articles for a compact, responsive reading experience.
  const FIRST_PAGE = 16;
  const NEXT_PAGE = 12;
  const DAY_MS = 86400000;
  const DATE_WINDOWS = [['all', 'Tất cả thời gian'], ['7', '7 ngày'], ['30', '30 ngày'], ['90', '90 ngày']];
  function isWithinDays(article, days, now = Date.now()) {
    if (days === 'all') return true;
    const date = Date.parse(article.published_at || '');
    return Number.isFinite(date) && date <= now + DAY_MS && date >= now - Number(days) * DAY_MS;
  }
  function diverseFeatured(rows, count = 3) {
    const selected = [], sources = new Set();
    for (const article of rows) {
      if (selected.length >= count) break;
      if (!sources.has(article.source_id)) { selected.push(article); sources.add(article.source_id); }
    }
    for (const article of rows) {
      if (selected.length >= count) break;
      if (!selected.includes(article)) selected.push(article);
    }
    return selected;
  }
  let visibleCount = FIRST_PAGE;

  const TOPICS = [
    ['all', 'Tất cả'],
    ['pricing', 'Giá bán'],
    ['supply', 'Nguồn cung'],
    ['sales', 'Giao dịch'],
    ['projects', 'Dự án'],
    ['legal', 'Pháp lý'],
    ['infrastructure', 'Hạ tầng'],
    ['research', 'Nghiên cứu']
  ];
  const TOPIC_NAMES = Object.fromEntries(TOPICS);
  const SOURCE_NAMES = {
    'vnexpress-real-estate': 'VnExpress',
    'dantri-real-estate': 'Dân trí',
    'thanhnien-real-estate': 'Thanh Niên',
    'nam-long-official': 'Nam Long',
    'cbre-vietnam-market': 'CBRE',
    'cushman-wakefield-vietnam-market': 'Cushman & Wakefield',
    'jll-vietnam-market': 'JLL',
    'savills-vietnam-market': 'Savills',
    'khang-dien-official': 'Khang Điền',
    'gamuda-land-official': 'Gamuda Land',
    'batdongsan-com-vn': 'Batdongsan.com.vn'
  };

  function esc(value) {
    return window.Components.escapeHTML(String(value ?? ''));
  }
  function sourceName(id) {
    return SOURCE_NAMES[id] || String(id || 'Nguồn khác').replace(/-(market|official|research)$/i, '').replaceAll('-', ' ');
  }
  function topicMatch(article, topic) {
    if (topic === 'all') return true;
    const tags = article.tags || [];
    if (topic === 'projects') {
      return (article.project_ids || []).length > 0 ||
        article.content_type === 'developer-update' ||
        tags.includes('project-update') || tags.includes('launch');
    }
    if (topic === 'research') return article.content_type === 'research';
    return tags.includes(topic);
  }
  function articleTopic(article) {
    for (const id of ['research', 'legal', 'infrastructure', 'pricing', 'supply', 'sales', 'projects']) {
      if (topicMatch(article, id)) return id;
    }
    return 'all';
  }
  // Topic labels reuse exactly the same classifier as the filter. Multiple
  // relevant topics appear on a story, but are limited to two readable chips.
  function articleTopics(article) {
    const primary = articleTopic(article);
    const topics = TOPICS.map(([id]) => id)
      .filter(id => id !== 'all' && topicMatch(article, id));
    return [primary, ...topics].filter((id, index, all) =>
      id !== 'all' && all.indexOf(id) === index).slice(0, 2);
  }
  function excerpt(article, limit) {
    const raw = String(article.summary || '').replace(/\s+/g, ' ').trim();
    if (!raw || raw.toLocaleLowerCase() === String(article.title || '').trim().toLocaleLowerCase()) return '';
    if (raw.length <= limit) return raw;
    return raw.slice(0, limit).replace(/\s+\S*$/, '').trimEnd() + '…';
  }
  function relatedLabel(article) {
    const projects = window.Resolver.getEntities('project', article.project_ids || []).map(p => p.name);
    if (projects.length) return projects.slice(0, 2).join(' · ') + (projects.length > 2 ? ' +' + (projects.length - 2) : '');
    const regions = window.Resolver.getEntities('region', article.region_ids || []).map(p => p.short_name || p.name);
    return regions.slice(0, 2).join(' · ');
  }
  function card(article, variant) {
    const lead = variant === 'lead';
    const topics = articleTopics(article);
    const published = article.published_at || '';
    const summary = excerpt(article, lead ? 290 : 170);
    const context = relatedLabel(article);
    const url = esc(article.url);
    return `<article class="market-news-card market-news-card--${esc(variant)}">
      <div class="market-news-card__meta">
        <span class="market-news-card__source">${esc(sourceName(article.source_id))}</span>
        <span class="market-news-card__dot" aria-hidden="true">·</span>
        <time datetime="${esc(published)}">${esc(window.App.formatDate(published))}</time>
        ${topics.length ? `<span class="market-news-card__topics">${topics.map(topic => `<button type="button" class="market-news-card__topic" data-news-topic="${esc(topic)}" data-topic="${esc(topic)}" aria-label="Lọc tin: ${esc(TOPIC_NAMES[topic])}">${esc(TOPIC_NAMES[topic])}</button>`).join('')}</span>` : ''}
      </div>
      <h3><a href="${url}" target="_blank" rel="noopener noreferrer">${esc(article.title)}</a></h3>
      ${summary ? `<p class="market-news-card__excerpt">${esc(summary)}</p>` : ''}
      <div class="market-news-card__footer">
        <span class="market-news-card__context" title="${esc(context)}">${esc(context)}</span>
        <a class="market-news-card__read" href="${url}" target="_blank" rel="noopener noreferrer" aria-label="Đọc bài gốc: ${esc(article.title)}">Bài gốc <span aria-hidden="true">↗</span></a>
      </div>
    </article>`;
  }

  function newsFilters({articles, regions, developers, state, sourceId, topicId}) {
    const sourceIds = [...new Set(articles.map(a => a.source_id).filter(Boolean))];
    sourceIds.sort((a, b) => sourceName(a).localeCompare(sourceName(b), 'vi'));
    const sourceOptions = sourceIds.map(id =>
      `<option value="${esc(id)}"${id === sourceId ? ' selected' : ''}>${esc(sourceName(id))}</option>`
    ).join('');
    const regionOptions = regions.map(x =>
      `<option value="${esc(x.id)}"${state.region === x.id ? ' selected' : ''}>${esc(x.short_name || x.name)}</option>`
    ).join('');
    const developerOptions = developers.map(x =>
      `<option value="${esc(x.id)}"${state.developer === x.id ? ' selected' : ''}>${esc(x.name)}</option>`
    ).join('');
    const advancedOpen = !!(state.region || state.developer);
    const windowId = window.App.getQueryParam('news-days') || 'all';
    return `<div class="market-news-filters">
      <form class="market-news-search" data-news-search role="search">
        <label for="market-news-q">Tìm tin tức</label>
        <div class="market-news-search__input">
          <input id="market-news-q" type="search" name="q" value="${esc(state.q || '')}" placeholder="Dự án, chủ đầu tư, từ khóa…" autocomplete="off">
          <button type="submit" aria-label="Tìm tin">Tìm</button>
        </div>
      </form>
      <label class="market-news-source-filter" for="market-news-days">
        <span>Thời gian</span>
        <select id="market-news-days" data-news-days>
          ${DATE_WINDOWS.map(([id,label]) => `<option value="${id}"${id === windowId ? ' selected' : ''}>${label}</option>`).join('')}
        </select>
      </label>
      <label class="market-news-source-filter" for="market-news-source">
        <span>Nguồn tin</span>
        <select id="market-news-source" data-news-source>
          <option value="">Tất cả nguồn</option>${sourceOptions}
        </select>
      </label>
      <details class="market-news-advanced"${advancedOpen ? ' open' : ''}>
        <summary>Bộ lọc khác ${advancedOpen ? '• đang chọn' : ''}</summary>
        <div class="market-news-advanced__body">
          <label for="market-news-region">Khu vực
            <select id="market-news-region" data-news-field="region">
              <option value="">Tất cả khu vực</option>${regionOptions}
            </select>
          </label>
          <label for="market-news-developer">Chủ đầu tư
            <select id="market-news-developer" data-news-field="developer">
              <option value="">Tất cả chủ đầu tư</option>${developerOptions}
            </select>
          </label>
        </div>
      </details>
      <button class="market-news-reset" data-news-reset type="button">Xóa lọc</button>
    </div>`;
  }

  function render({ articles, regions, developers, state }) {
    const sourceId = window.App.getQueryParam('news-source') || '';
    const topicParam = window.App.getQueryParam('news-topic') || 'all';
    const daysParam = window.App.getQueryParam('news-days') || 'all';
    const days = DATE_WINDOWS.some(([id]) => id === daysParam) ? daysParam : 'all';
    const topicId = TOPIC_NAMES[topicParam] ? topicParam : 'all';
    const visibleArticles = articles.filter(a => a.url && a.title && (window.DataStore?.isNewsFor ? window.DataStore.isNewsFor(a, 'market') : a.category === 'market') &&
      !String(a.source_id || '').startsWith('demo-') &&
      !/^(demo|illustrative)[\s:–-]/i.test(String(a.title || '')));
    const publishers = new Set(visibleArticles.map(a => a.source_id).filter(Boolean)).size;
    const latestDate = visibleArticles.map(a => a.published_at || '').filter(Boolean).sort().at(-1) || '';
    const sourceRestricted = visibleArticles.filter(a => {
      if (sourceId && a.source_id !== sourceId) return false;
      if (!isWithinDays(a, days)) return false;
      if (state.region && !(a.region_ids || []).includes(state.region)) return false;
      if (state.developer && !(a.developer_ids || []).includes(state.developer)) return false;
      if (state.q && !window.FilterEngine.textMatch(a, state.q, ['title','summary','tags','project_ids','developer_ids'])) return false;
      return true;
    });
    const counts = Object.fromEntries(TOPICS.map(([id]) => [id, sourceRestricted.filter(a => topicMatch(a, id)).length]));
    const list = sourceRestricted.filter(a => topicMatch(a, topicId))
      .sort((a, b) => String(b.published_at || '').localeCompare(String(a.published_at || '')));
    const shown = list.slice(0, visibleCount);
    const focused = !!(state.q || state.region || state.developer || sourceId || topicId !== 'all' || days !== 'all');
    const featured = !focused && shown.length >= 3 ? diverseFeatured(shown) : [];
    const rest = featured.length ? shown.filter(a => !featured.includes(a)) : shown;
    const pills = TOPICS.filter(([id]) => id === 'all' || counts[id] > 0 || topicId === id)
      .map(([id, label]) => `<button type="button" class="market-news-topic" data-news-topic="${esc(id)}" data-topic="${esc(id)}" aria-pressed="${id === topicId}">
        ${esc(label)} <span>${counts[id]}</span>
      </button>`).join('');
    return `<div class="market-news">
      <div class="market-news-heading">
        <div>
          <span class="market-news-heading__eyebrow">MARKET / NEWS</span>
          <h2>Tin tức thị trường</h2>
          <p>Tin từ nguồn công bố · Nhấn tiêu đề để đọc bài gốc.</p>
        </div>
        <div class="market-news-heading__total" aria-label="${visibleArticles.length} bài viết từ ${publishers} nguồn">
          <strong>${visibleArticles.length}</strong><span>bài · ${publishers} nguồn</span>
          ${latestDate ? `<small style="display:block;font-size:11px;font-weight:400;margin-top:4px">Tin mới nhất: ${esc(window.App.formatDate(latestDate))}</small>` : ''}
        </div>
      </div>
      ${newsFilters({articles:visibleArticles, regions, developers, state, sourceId, topicId})}
      <div class="market-news-topics" role="group" aria-label="Lọc theo chủ đề">${pills}</div>
      <div class="market-news-result" aria-live="polite">
        <span><strong>${list.length}</strong> bài phù hợp</span>
        <span>Đang xem ${shown.length}/${list.length}</span>
      </div>
      ${featured.length ? `<section aria-label="Tin mới nhất" class="market-news-feature">
        ${card(featured[0], 'lead')}
        <div class="market-news-feature__side">
          ${card(featured[1], 'side')}
          ${card(featured[2], 'side')}
        </div>
      </section>` : ''}
      ${rest.length ? `<div class="market-news-grid" aria-label="Danh sách tin tức">${rest.map(a => card(a, 'compact')).join('')}</div>` :
        (!featured.length ? '<div class="market-news-empty">Không có tin phù hợp. Hãy thử từ khóa hoặc bộ lọc khác.</div>' : '')}
      ${shown.length < list.length ? `<div class="market-news-more"><button type="button" data-news-more>
        Xem thêm ${Math.min(NEXT_PAGE, list.length - shown.length)} tin <span aria-hidden="true">↓</span>
      </button></div>` : ''}
    </div>`;
  }

  function bind({state, refresh}) {
    const topicBar = document.querySelector('.market-news-topics');
    const selected = topicBar?.querySelector('.market-news-topic[aria-pressed="true"]');
    if (topicBar && selected) {
      const left = selected.offsetLeft - topicBar.offsetLeft;
      if (left < topicBar.scrollLeft || left + selected.offsetWidth > topicBar.scrollLeft + topicBar.clientWidth)
        topicBar.scrollLeft = Math.max(0, left - 12);
    }
    const resetPage = () => { visibleCount = FIRST_PAGE; refresh(); };
    document.querySelector('[data-news-search]')?.addEventListener('submit', event => {
      event.preventDefault();
      state.q = event.currentTarget.elements.q.value.trim();
      window.App.setQueryParam('q', state.q || null);
      resetPage();
    });
    document.querySelector('[data-news-days]')?.addEventListener('change', event => {
      window.App.setQueryParam('news-days', event.target.value === 'all' ? null : event.target.value);
      resetPage();
    });
    document.querySelector('[data-news-source]')?.addEventListener('change', event => {
      window.App.setQueryParam('news-source', event.target.value || null);
      resetPage();
    });
    document.querySelectorAll('[data-news-field]').forEach(element => {
      element.addEventListener('change', () => {
        const field = element.dataset.newsField;
        state[field] = element.value;
        window.App.setQueryParam(field, state[field] || null);
        resetPage();
      });
    });
    document.querySelectorAll('[data-news-topic]').forEach(button => {
      button.addEventListener('click', () => {
        window.App.setQueryParam('news-topic', button.dataset.newsTopic === 'all' ? null : button.dataset.newsTopic);
        resetPage();
      });
    });
    document.querySelector('[data-news-reset]')?.addEventListener('click', () => {
      for (const field of ['q', 'region', 'developer']) {
        state[field] = '';
        window.App.removeQueryParam(field);
      }
      window.App.removeQueryParam('news-source');
      window.App.removeQueryParam('news-days');
      window.App.removeQueryParam('news-topic');
      resetPage();
    });
    document.querySelector('[data-news-more]')?.addEventListener('click', () => {
      visibleCount += NEXT_PAGE;
      refresh();
    });
  }

  window.MarketNewsUI = { render, bind };
})();
