(() => {
  'use strict';

  // v7.2.0 deliberately translates only static/common UI.
  // It is loaded last and is not required by any v7.1.1 runtime module.
  const STORAGE_KEY = 're-mi-language';
  const DEFAULT_LANG = 'vi';
  const SUPPORTED = new Set(['vi', 'en']);

  const TITLES = {
    home: {
      en: 'Market Intelligence · Vietnam Real Estate',
      vi: 'Thông tin Thị trường · Bất động sản Việt Nam'
    },
    market: {
      en: 'Market · Market Intelligence',
      vi: 'Thị trường · Market Intelligence'
    },
    legal: {
      en: 'Legal · Market Intelligence',
      vi: 'Pháp lý · Market Intelligence'
    },
    infrastructure: {
      en: 'Infrastructure · Market Intelligence',
      vi: 'Hạ tầng · Market Intelligence'
    },
    macro: {
      en: 'Macro & Monetary · Market Intelligence',
      vi: 'Vĩ mô & Tiền tệ · Market Intelligence'
    }
  };

  const COMMON = [
    ['.main-nav a[href="index.html"], .mobile-nav-panel a[href="index.html"]', 'Home', 'Trang chủ'],
    ['.main-nav a[href="market.html"], .mobile-nav-panel a[href="market.html"]', 'Market', 'Thị trường'],
    ['.main-nav a[href="legal.html"], .mobile-nav-panel a[href="legal.html"]', 'Legal', 'Pháp lý'],
    ['.main-nav a[href="infrastructure.html"], .mobile-nav-panel a[href="infrastructure.html"]', 'Infrastructure', 'Hạ tầng'],
    ['.main-nav a[href="macro.html"], .mobile-nav-panel a[href="macro.html"]', 'Macro', 'Vĩ mô'],
    ['.global-search-trigger span:first-child', 'Search research...', 'Tìm kiếm nghiên cứu...'],
    ['[data-global-search-status]', 'Search across the structured demo research database.', 'Tìm kiếm trên toàn bộ cơ sở dữ liệu nghiên cứu có cấu trúc.'],
    ['[data-drawer-title]', 'Details', 'Chi tiết'],
    ['[data-drawer-body] .state-box', 'Select an item to inspect its details.', 'Chọn một mục để xem thông tin chi tiết.'],
    ['[data-source-registry-open]', 'Data Sources', 'Nguồn dữ liệu'],
    ['.footer-links a[href="#"]', 'Methodology', 'Phương pháp'],
    ['.footer-links span', 'Research use only', 'Chỉ dùng cho mục đích nghiên cứu']
  ];

  const HOME = [
    ['.page-kicker', 'Vietnam Real Estate', 'Bất động sản Việt Nam'],
    ['.page-title', 'Market Intelligence', 'Thông tin Thị trường'],
    ['.page-description', 'Monitor what changed today, review the week, and move quickly into structured project, legal, infrastructure and macro research.', 'Theo dõi những thay đổi trong ngày, tổng hợp diễn biến trong tuần và tra cứu nhanh dữ liệu dự án, pháp lý, hạ tầng và vĩ mô có cấu trúc.'],
    ['.demo-banner strong', 'Mixed data mode.', 'Chế độ dữ liệu hỗn hợp.'],
    ['.demo-banner span', 'The Macro snapshot uses controlled production observations where available; remaining Home sections and unpromoted indicators stay clearly illustrative demo data.', 'Phần Tổng quan vĩ mô sử dụng các quan sát production có kiểm soát khi khả dụng; các phần còn lại trên Trang chủ và các chỉ số chưa được promote vẫn được đánh dấu rõ là dữ liệu mô phỏng minh họa.'],
    ['.home-snapshot .eyebrow', 'Market snapshot', 'Tổng quan nhanh'],
    ['#snapshot-title', 'One screen for what matters now', 'Một màn hình cho những thông tin quan trọng nhất'],
    ['.home-snapshot p', 'Use the dashboard for fast monitoring, then move into each module for structured historical research.', 'Dùng dashboard để theo dõi nhanh, sau đó đi sâu vào từng module để nghiên cứu dữ liệu lịch sử có cấu trúc.'],
    ['.home-snapshot [data-search-open]', 'Search research', 'Tìm kiếm nghiên cứu'],
    ['#today-title', 'Today', 'Hôm nay'],
    ['.home-block[aria-labelledby="today-title"] .eyebrow', 'Latest activity', 'Cập nhật mới nhất'],
    ['.home-block[aria-labelledby="today-title"] .home-block__note', 'Newest items by category', 'Thông tin mới nhất theo nhóm'],
    ['#indicators-title', 'Key Indicators', 'Chỉ số chính'],
    ['.home-block[aria-labelledby="indicators-title"] .eyebrow', 'Macro snapshot', 'Tổng quan vĩ mô'],
    ['.home-block[aria-labelledby="indicators-title"] .text-link', 'Open Macro', 'Mở Vĩ mô'],
    ['#changes-title', 'What Changed', 'Điểm thay đổi'],
    ['.home-block[aria-labelledby="changes-title"] .eyebrow', 'Meaningful developments', 'Diễn biến đáng chú ý'],
    ['.home-block[aria-labelledby="changes-title"] .home-block__note', 'Events, not just headlines', 'Sự kiện thực tế, không chỉ tiêu đề tin'],
    ['#weekly-title', 'This Week', 'Tuần này'],
    ['.home-block[aria-labelledby="weekly-title"] .eyebrow', '7-day recap', 'Tổng hợp 7 ngày'],
    ['.home-block[aria-labelledby="weekly-title"] .home-block__note', 'Important developments ranked above pure recency', 'Ưu tiên diễn biến quan trọng hơn việc chỉ sắp theo thời gian'],
    ['#research-title', 'Quick Research', 'Tra cứu nhanh'],
    ['.home-block[aria-labelledby="research-title"] .eyebrow', 'Research shortcuts', 'Lối tắt nghiên cứu'],
    ['.home-block[aria-labelledby="research-title"] [data-search-open]', 'Global search', 'Tìm kiếm toàn hệ thống']
  ];

  const MARKET = [
    ['.page-kicker', 'Research Database', 'Cơ sở dữ liệu nghiên cứu'],
    ['.page-title', 'Market', 'Thị trường'],
    ['.page-description', 'Track projects, developers, supply, sales, absorption and pricing with structured historical data.', 'Theo dõi dự án, chủ đầu tư, nguồn cung, bán hàng, tỷ lệ hấp thụ và giá bán bằng dữ liệu lịch sử có cấu trúc.'],
    ['.demo-banner strong', 'Implementation demo.', 'Bản mô phỏng triển khai.'],
    ['.demo-banner span', 'Project names are used only to demonstrate the research workflow. All metrics, dates, status labels and market observations in this build are illustrative mock data.', 'Tên dự án được sử dụng để mô phỏng quy trình nghiên cứu. Toàn bộ chỉ số, ngày tháng, trạng thái và quan sát thị trường trong phiên bản này là dữ liệu minh họa.'],
    ['[data-market-tabs] [data-view="overview"]', 'Overview', 'Tổng quan'],
    ['[data-market-tabs] [data-view="projects"]', 'Projects', 'Dự án'],
    ['[data-market-tabs] [data-view="supply-sales"]', 'Supply & Sales', 'Nguồn cung & Bán hàng'],
    ['[data-market-tabs] [data-view="pricing"]', 'Pricing', 'Giá bán'],
    ['[data-market-tabs] [data-view="developers"]', 'Developers', 'Chủ đầu tư'],
    ['[data-market-tabs] [data-view="news"]', 'News', 'Tin tức']
  ];

  const LEGAL = [
    ['.page-kicker', 'Official Documents & Changes', 'Văn bản chính thức & Thay đổi'],
    ['.page-title', 'Legal', 'Pháp lý'],
    ['.page-description', 'Monitor real-estate-related laws, decrees, circulars, effective dates, drafts and supporting analysis.', 'Theo dõi luật, nghị định, thông tư, ngày hiệu lực, dự thảo và phân tích liên quan đến bất động sản.'],
    ['.demo-banner strong', 'Curated official registry.', 'Cơ sở dữ liệu văn bản chính thức.'],
    ['.demo-banner span', 'Core real-estate legal documents are linked to official Government sources. Summaries are research notes for navigation only and are not legal advice; always open the official document for interpretation and application.', 'Các văn bản pháp lý bất động sản cốt lõi được liên kết tới nguồn chính thức của Chính phủ. Phần tóm tắt chỉ phục vụ tra cứu nghiên cứu, không phải tư vấn pháp lý; khi áp dụng cần mở văn bản gốc.'],
    ['[data-legal-tabs] [data-view="overview"]', 'Overview', 'Tổng quan'],
    ['[data-legal-tabs] [data-view="documents"]', 'Documents', 'Văn bản'],
    ['[data-legal-tabs] [data-view="effective-soon"]', 'Effective Soon', 'Sắp có hiệu lực'],
    ['[data-legal-tabs] [data-view="topics"]', 'Topics', 'Chủ đề'],
    ['[data-legal-tabs] [data-view="news"]', 'News', 'Tin tức']
  ];

  const INFRASTRUCTURE = [
    ['.page-kicker', 'Projects, Milestones & Schedule', 'Dự án, Mốc tiến độ & Kế hoạch'],
    ['.page-title', 'Infrastructure', 'Hạ tầng'],
    ['.page-description', 'Track infrastructure projects, schedule revisions, milestones, regional connectivity and related real estate markets.', 'Theo dõi dự án hạ tầng, điều chỉnh tiến độ, các mốc triển khai, kết nối vùng và thị trường bất động sản liên quan.'],
    ['.demo-banner strong', 'Curated official registry.', 'Cơ sở dữ liệu hạ tầng chính thức được tuyển chọn.'],
    ['.demo-banner span', 'Core infrastructure projects and milestones are linked to official Government or local-authority sources. Progress snapshots are dated observations, not real-time telemetry; schedule history is preserved when targets change.', 'Các dự án và mốc hạ tầng cốt lõi được liên kết tới nguồn Chính phủ hoặc chính quyền địa phương. Số liệu tiến độ là ảnh chụp tại ngày công bố, không phải dữ liệu thời gian thực; lịch sử mốc tiến độ được giữ lại khi có điều chỉnh.'],
    ['[data-infrastructure-tabs] [data-view="overview"]', 'Overview', 'Tổng quan'],
    ['[data-infrastructure-tabs] [data-view="projects"]', 'Projects', 'Dự án'],
    ['[data-infrastructure-tabs] [data-view="regions"]', 'Regions', 'Khu vực'],
    ['[data-infrastructure-tabs] [data-view="timeline"]', 'Timeline', 'Tiến độ'],
    ['[data-infrastructure-tabs] [data-view="news"]', 'News', 'Tin tức']
  ];

  const MACRO = [
    ['.page-kicker', 'Rates, FX, Gold & Liquidity', 'Lãi suất, Tỷ giá, Vàng & Thanh khoản'],
    ['.page-title', 'Macro & Monetary', 'Vĩ mô & Tiền tệ'],
    ['.page-description', 'Follow rates, foreign exchange, gold, credit, money supply and inflation through comparable historical series.', 'Theo dõi lãi suất, tỷ giá, vàng, tín dụng, cung tiền và lạm phát qua các chuỗi dữ liệu lịch sử có thể so sánh.'],
    ['.demo-banner strong', 'Controlled data mode.', 'Chế độ dữ liệu kiểm soát.'],
    ['.demo-banner span', 'Production observations are shown when available; indicators not yet promoted remain clearly marked illustrative demo data.', 'Các quan sát production được hiển thị khi khả dụng; các chỉ số chưa được promote vẫn được đánh dấu rõ là dữ liệu mô phỏng minh họa.'],
    ['[data-macro-tabs] [data-view="overview"]', 'Overview', 'Tổng quan'],
    ['[data-macro-tabs] [data-view="rates"]', 'Rates', 'Lãi suất'],
    ['[data-macro-tabs] [data-view="fx"]', 'FX', 'Tỷ giá'],
    ['[data-macro-tabs] [data-view="gold"]', 'Gold', 'Vàng'],
    ['[data-macro-tabs] [data-view="liquidity"]', 'Liquidity', 'Thanh khoản'],
    ['[data-macro-tabs] [data-view="inflation"]', 'Inflation', 'Lạm phát'],
    ['[data-macro-tabs] [data-view="news"]', 'News', 'Tin tức']
  ];

  const PAGE_TRANSLATIONS = {
    home: HOME,
    market: MARKET,
    legal: LEGAL,
    infrastructure: INFRASTRUCTURE,
    macro: MACRO
  };

  function readLanguage() {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (SUPPORTED.has(saved)) return saved;
    } catch (_) {}
    return DEFAULT_LANG;
  }

  function saveLanguage(lang) {
    try { window.localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
  }

  function setText(selector, text) {
    if (!selector || text === undefined) return;
    document.querySelectorAll(selector).forEach(node => {
      if (text !== '') node.textContent = text;
    });
  }

  function applyRows(rows, lang) {
    rows.forEach(([selector, en, vi]) => setText(selector, lang === 'vi' ? vi : en));
  }

  function pageKey() {
    return document.body?.dataset.page || 'home';
  }

  function updateAttributes(lang) {
    document.documentElement.lang = lang;

    const searchInput = document.querySelector('[data-global-search-input]');
    if (searchInput) {
      searchInput.placeholder = lang === 'vi'
        ? 'Tìm dự án, chủ đầu tư, pháp lý, hạ tầng, vĩ mô...'
        : 'Search projects, developers, legal, infrastructure, macro...';
      searchInput.setAttribute('aria-label', lang === 'vi' ? 'Tìm kiếm toàn hệ thống' : 'Global search');
    }

    const searchButtons = document.querySelectorAll('[data-search-open]');
    searchButtons.forEach(button => {
      button.setAttribute('aria-label', lang === 'vi' ? 'Mở tìm kiếm nghiên cứu' : 'Open global research search');
    });

    const menu = document.querySelector('[data-mobile-menu-button]');
    if (menu) menu.setAttribute('aria-label', lang === 'vi' ? 'Mở menu' : 'Open menu');

    const drawer = document.querySelector('[data-drawer-overlay] .drawer');
    if (drawer) drawer.setAttribute('aria-label', lang === 'vi' ? 'Bảng chi tiết' : 'Detail panel');

    const searchPanel = document.querySelector('[data-search-overlay] .search-panel');
    if (searchPanel) searchPanel.setAttribute('aria-label', lang === 'vi' ? 'Tìm kiếm nghiên cứu toàn hệ thống' : 'Global research search');
  }

  function ensureToggle() {
    const actions = document.querySelector('.header-actions');
    if (!actions || actions.querySelector('[data-language-toggle]')) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button language-toggle';
    button.setAttribute('data-language-toggle', '');
    button.setAttribute('aria-label', 'Switch language / Chuyển ngôn ngữ');
    button.innerHTML = '<span data-lang-option="vi">VI</span><span class="language-toggle__sep">·</span><span data-lang-option="en">EN</span>';
    button.addEventListener('click', () => {
      const next = currentLanguage === 'vi' ? 'en' : 'vi';
      setLanguage(next, { persist: true });
    });
    actions.prepend(button);
  }

  function updateToggle(lang) {
    const button = document.querySelector('[data-language-toggle]');
    if (!button) return;
    button.querySelectorAll('[data-lang-option]').forEach(node => {
      node.classList.toggle('is-active', node.getAttribute('data-lang-option') === lang);
    });
    button.setAttribute('title', lang === 'vi' ? 'Chuyển sang English' : 'Switch to Vietnamese');
  }

  let currentLanguage = readLanguage();

  function applyLanguage(lang) {
    if (!SUPPORTED.has(lang)) lang = DEFAULT_LANG;
    currentLanguage = lang;
    applyRows(COMMON, lang);
    applyRows(PAGE_TRANSLATIONS[pageKey()] || [], lang);
    updateAttributes(lang);
    updateToggle(lang);
    const title = TITLES[pageKey()]?.[lang];
    if (title) document.title = title;
    document.dispatchEvent(new CustomEvent('app:language-changed', { detail: { language: lang } }));
  }

  function setLanguage(lang, { persist = false } = {}) {
    if (!SUPPORTED.has(lang)) return;
    if (persist) saveLanguage(lang);
    applyLanguage(lang);
  }

  function init() {
    try {
      ensureToggle();
      applyLanguage(currentLanguage);
    } catch (error) {
      // Static localization must never prevent the stable v7.1.1 app from running.
      console.warn('[localization-static] disabled after non-fatal error:', error);
    }
  }

  window.AppLocalization = {
    getLanguage: () => currentLanguage,
    setLanguage
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
