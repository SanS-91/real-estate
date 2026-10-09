(() => {
  'use strict';

  const NAV_ITEMS = [
    { key: 'home', label: 'Home', href: 'index.html' },
    { key: 'research', label: 'Research', href: 'research.html' },
    { key: 'market', label: 'Market', href: 'market.html' },
    { key: 'legal', label: 'Legal', href: 'legal.html' },
    { key: 'infrastructure', label: 'Infrastructure', href: 'infrastructure.html' },
    { key: 'macro', label: 'Macro', href: 'macro.html' },
    { key: 'maintenance', label: 'Data Status', href: 'maintenance.html' }
  ];

  // Keep a single, bilingual taxonomy for sourced article TYPES. These are
  // descriptive labels, never a change to the data's original content_type.
  const NEWS_KIND_LABELS = {
    'analysis': { vi: 'Phân tích', en: 'Analysis' },
    'news': { vi: 'Tin tức', en: 'News' },
    'research': { vi: 'Nghiên cứu', en: 'Research' },
    'official-update': { vi: 'Cập nhật chính thức', en: 'Official update' },
    'data-release': { vi: 'Công bố dữ liệu', en: 'Data release' },
    'publisher-rss': { vi: 'Tin từ nguồn', en: 'Publisher news' },
    'developer-update': { vi: 'Tin chủ đầu tư', en: 'Developer update' }
  };
  const NEWS_VIEW_COPY = {
    legal: {
      vi: {
        eyebrow: 'Nguồn & diễn giải', title: 'Tin tức & phân tích pháp lý',
        description: 'Tin tức hỗ trợ theo dõi và diễn giải; khi áp dụng cần đối chiếu văn bản pháp luật gốc và hiệu lực thực tế.'
      },
      en: {
        eyebrow: 'Evidence & context', title: 'Legal news & analysis',
        description: 'News supports research and interpretation; consult the original legal documents and their effective status before applying them.'
      }
    },
    infrastructure: {
      vi: {
        eyebrow: 'Cập nhật dự án', title: 'Tin tức & tiến độ hạ tầng',
        description: 'Tin tức giúp theo dõi diễn biến; mốc tiến độ chính thức và lịch sử điều chỉnh được lưu riêng trong hồ sơ dự án.'
      },
      en: {
        eyebrow: 'Project developments', title: 'Infrastructure news & milestones',
        description: 'News provides context; official milestones and schedule revisions remain separately recorded in each project dossier.'
      }
    },
    macro: {
      vi: {
        eyebrow: 'Nội dung minh họa', title: 'Tin tức & nghiên cứu vĩ mô (minh họa)',
        description: 'Các bài viết tại đây chỉ để minh họa, không phải số liệu chính thức. Chỉ số được xác minh hiển thị riêng trong các bảng dữ liệu.'
      },
      en: {
        eyebrow: 'Illustrative material', title: 'Illustrative macro news & research',
        description: 'These articles are illustrative, not official observations. Verified indicators are published separately in the data views.'
      }
    }
  };
  function newsLanguage() {
    return window.AppLocalization?.getLanguage?.() === 'en' ? 'en'
      : document.documentElement.lang === 'en' && !window.AppLocalization ? 'en' : 'vi';
  }
  function newsKindLabel(kind) {
    return NEWS_KIND_LABELS[kind]?.[newsLanguage()] || String(kind || '—');
  }
  function newsViewCopy(section) {
    return NEWS_VIEW_COPY[section]?.[newsLanguage()] || NEWS_VIEW_COPY.legal.vi;
  }
  function refreshArticleLabels() {
    document.querySelectorAll('[data-news-kind]').forEach(node => {
      node.textContent = newsKindLabel(node.dataset.newsKind);
    });
    document.querySelectorAll('[data-news-view-label]').forEach(node => {
      const [section, field] = String(node.dataset.newsViewLabel || '').split('.');
      const copy = NEWS_VIEW_COPY[section]?.[newsLanguage()];
      if (copy && copy[field]) node.textContent = copy[field];
    });
  }

  function currentPageKey() {
    const file = window.location.pathname.split('/').pop() || 'index.html';
    if (file === 'index.html' || file === '') return 'home';
    return file.replace('.html', '');
  }

  function navMarkup(className = 'nav-link') {
    const active = currentPageKey();
    return NAV_ITEMS.map(item => `
      <a class="${className}${item.key === active ? ' is-active' : ''}" href="${item.href}">${item.label}</a>
    `).join('');
  }

  function headerMarkup() {
    return `
      <header class="site-header">
        <div class="container header-row">
          <button class="icon-button mobile-menu-button" type="button" aria-label="Open menu" aria-controls="site-mobile-navigation" aria-expanded="false" data-mobile-menu-button>☰</button>

          <a class="brand" href="index.html" aria-label="Vietnam Real Estate Market Intelligence home">
            <span class="brand-mark">RE</span>
            <span>Market Intelligence</span>
          </a>

          <nav class="main-nav" aria-label="Primary navigation">
            ${navMarkup()}
          </nav>

          <div class="header-actions">
            <button class="button global-search-trigger" type="button" data-search-open aria-label="Open global research search">
              <span>Search research...</span><span>⌕</span>
            </button>
            <button class="icon-button" type="button" aria-label="Search" data-search-open>⌕</button>
          </div>
        </div>
      </header>
      <nav id="site-mobile-navigation" class="mobile-nav-panel" data-mobile-nav aria-label="Mobile navigation">
        <div class="container">${navMarkup('mobile-nav-link')}</div>
      </nav>
    `;
  }

  function footerMarkup() {
    const year = new Date().getFullYear();
    return `
      <footer class="site-footer">
        <div class="container footer-row">
          <div>© ${year} Vietnam Real Estate Market Intelligence</div>
          <div class="footer-links">
            <button class="footer-link-button" type="button" data-source-registry-open>Data Sources</button>
            <a href="maintenance.html#maintenance-rules-title">Methodology &amp; data</a>
            <a href="maintenance.html">Data Status</a>
            <span>Research use only</span>
          </div>
        </div>
      </footer>
    `;
  }

  function overlaysMarkup() {
    return `
      <div class="overlay" data-drawer-overlay aria-hidden="true">
        <aside class="drawer" role="dialog" aria-modal="true" aria-label="Detail panel">
          <div class="drawer-header">
            <strong data-drawer-title>Details</strong>
            <button class="icon-button" type="button" aria-label="Close details" data-drawer-close>×</button>
          </div>
          <div class="drawer-body" data-drawer-body>
            <div class="state-box">Select an item to inspect its details.</div>
          </div>
        </aside>
      </div>
      <div class="search-overlay" data-search-overlay aria-hidden="true">
        <div class="search-panel" role="dialog" aria-modal="true" aria-label="Global research search">
          <div class="search-row">
            <input class="search-input" type="search" placeholder="Search projects, developers, legal, infrastructure, macro..." aria-label="Global search" autocomplete="off" spellcheck="false" data-global-search-input>
            <button class="icon-button" type="button" aria-label="Close search" data-search-close>×</button>
          </div>
          <div class="search-hint-row">
            <span data-global-search-status>Search across Market, Legal, Infrastructure and controlled Macro data.</span>
            <span class="search-shortcut">Ctrl / ⌘ K</span>
          </div>
          <div class="search-results" data-global-search-results aria-live="polite"></div>
        </div>
      </div>
    `;
  }

  function mountShell() {
    const header = document.querySelector('[data-site-header]');
    const footer = document.querySelector('[data-site-footer]');
    const overlays = document.querySelector('[data-site-overlays]');
    if (header) header.innerHTML = headerMarkup();
    if (footer) footer.innerHTML = footerMarkup();
    if (overlays) overlays.innerHTML = overlaysMarkup();
  }

  function setBodyLock(locked) {
    document.body.style.overflow = locked ? 'hidden' : '';
  }

  function openSearch() {
    const mobileNav = document.querySelector('[data-mobile-nav]');
    const searchOverlay = document.querySelector('[data-search-overlay]');
    const searchInput = document.querySelector('[data-global-search-input]');
    mobileNav?.classList.remove('is-open');
    document.querySelector('[data-mobile-menu-button]')?.setAttribute('aria-expanded', 'false');
    searchOverlay?.classList.add('is-open');
    searchOverlay?.setAttribute('aria-hidden', 'false');
    setBodyLock(true);
    document.dispatchEvent(new CustomEvent('app:search-opened'));
    setTimeout(() => searchInput?.focus(), 0);
  }

  function closeSearch() {
    const searchOverlay = document.querySelector('[data-search-overlay]');
    if (!searchOverlay?.classList.contains('is-open')) return;
    searchOverlay.classList.remove('is-open');
    searchOverlay.setAttribute('aria-hidden', 'true');
    setBodyLock(false);
    document.dispatchEvent(new CustomEvent('app:search-closed'));
  }

  function closeDrawer() {
    const drawerOverlay = document.querySelector('[data-drawer-overlay]');
    const wasOpen = drawerOverlay?.classList.contains('is-open');
    drawerOverlay?.classList.remove('is-open');
    drawerOverlay?.setAttribute('aria-hidden', 'true');
    setBodyLock(false);
    if (wasOpen) document.dispatchEvent(new CustomEvent('app:drawer-closed'));
  }

  function bindShellEvents() {
    const menuButton = document.querySelector('[data-mobile-menu-button]');
    const mobileNav = document.querySelector('[data-mobile-nav]');
    const drawerOverlay = document.querySelector('[data-drawer-overlay]');

    const toggleMobileNav = open => {
      mobileNav?.classList.toggle('is-open', open);
      menuButton?.setAttribute('aria-expanded', String(!!open));
    };
    menuButton?.addEventListener('click', () => {
      toggleMobileNav(!mobileNav?.classList.contains('is-open'));
    });
    document.addEventListener('click', event => {
      if (!mobileNav?.classList.contains('is-open')) return;
      if (!mobileNav.contains(event.target) && !menuButton?.contains(event.target)) toggleMobileNav(false);
    });

    document.querySelectorAll('[data-search-open]').forEach(button => {
      button.addEventListener('click', openSearch);
    });

    document.querySelector('[data-search-close]')?.addEventListener('click', closeSearch);
    document.querySelector('[data-drawer-close]')?.addEventListener('click', closeDrawer);

    drawerOverlay?.addEventListener('click', event => {
      if (event.target === drawerOverlay) closeDrawer();
    });

    document.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        openSearch();
        return;
      }
      if (event.key !== 'Escape') return;
      closeSearch();
      closeDrawer();
      toggleMobileNav(false);
    });
  }

  // Preserve touch-driven horizontal swiping; after each module sets its
  // active tab, reveal that tab WITHOUT vertical page scrolling or DOM reorder.
  function bindHorizontalNavigation() {
    const tabs = [...document.querySelectorAll('.tabs')];
    if (!tabs.length) return;
    const align = tabbar => {
      if ((window.innerWidth || 1440) >= 1200 || tabbar.scrollWidth <= tabbar.clientWidth) return;
      const active = tabbar.querySelector('.tab-link.is-active, [aria-current="page"]');
      if (!active) return;
      const view = tabbar.getBoundingClientRect();
      const rect = active.getBoundingClientRect();
      const gap = 12;
      if (rect.left < view.left + gap) tabbar.scrollLeft -= (view.left + gap - rect.left);
      else if (rect.right > view.right - gap) tabbar.scrollLeft += rect.right - (view.right - gap);
    };
    for (const tabbar of tabs) {
      align(tabbar);
      if (typeof MutationObserver === 'function') {
        new MutationObserver(() => align(tabbar)).observe(tabbar, {
          attributes: true, attributeFilter: ['class', 'aria-current'],
          subtree: true
        });
      }
    }
    document.addEventListener('app:language-changed', () => tabs.forEach(align));
    window.addEventListener('resize', () => tabs.forEach(align));
  }

  function getQueryParam(name) {
    return new URL(window.location.href).searchParams.get(name);
  }

  function setQueryParam(name, value, { push = false } = {}) {
    const url = new URL(window.location.href);
    if (value === null || value === undefined || value === '') url.searchParams.delete(name);
    else url.searchParams.set(name, value);
    window.history[push ? 'pushState' : 'replaceState']({}, '', url);
  }

  function removeQueryParam(name, options) {
    setQueryParam(name, null, options);
  }

  function formatDate(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
  }

  function openDrawer({ title = 'Details', html = '' } = {}) {
    const overlay = document.querySelector('[data-drawer-overlay]');
    const titleNode = document.querySelector('[data-drawer-title]');
    const bodyNode = document.querySelector('[data-drawer-body]');
    if (titleNode) titleNode.textContent = title;
    if (bodyNode) bodyNode.innerHTML = html || '<div class="state-box">No detail content.</div>';
    overlay?.classList.add('is-open');
    overlay?.setAttribute('aria-hidden', 'false');
    setBodyLock(true);
  }

  window.App = {
    NAV_ITEMS,
    getQueryParam,
    setQueryParam,
    removeQueryParam,
    formatDate,
    openDrawer,
    closeDrawer,
    openSearch,
    closeSearch,
    newsKindLabel,
    newsViewCopy
  };

  document.addEventListener('DOMContentLoaded', () => {
    mountShell();
    bindShellEvents();
    bindHorizontalNavigation();
    document.addEventListener('app:language-changed', refreshArticleLabels);
  });
})();
