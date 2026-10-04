(() => {
  'use strict';

  const NAV_ITEMS = [
    { key: 'home', label: 'Home', href: 'index.html' },
    { key: 'market', label: 'Market', href: 'market.html' },
    { key: 'legal', label: 'Legal', href: 'legal.html' },
    { key: 'infrastructure', label: 'Infrastructure', href: 'infrastructure.html' },
    { key: 'macro', label: 'Macro', href: 'macro.html' }
  ];

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
          <button class="icon-button mobile-menu-button" type="button" aria-label="Open menu" data-mobile-menu-button>☰</button>

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
      <div class="mobile-nav-panel" data-mobile-nav>
        <div class="container">${navMarkup('mobile-nav-link')}</div>
      </div>
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
            <a href="#">Methodology</a>
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
            <span data-global-search-status>Search across the structured demo research database.</span>
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

    menuButton?.addEventListener('click', () => {
      mobileNav?.classList.toggle('is-open');
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
      mobileNav?.classList.remove('is-open');
    });
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
    closeSearch
  };

  document.addEventListener('DOMContentLoaded', () => {
    mountShell();
    bindShellEvents();
  });
})();
