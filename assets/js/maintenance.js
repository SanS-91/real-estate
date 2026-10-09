(() => {
  'use strict';

  const MODULE_ORDER = ['macro', 'legal', 'infrastructure', 'market', 'home', 'search'];
  let lastModel = null;

  const COPY = {
    en: {
      modules: { macro: 'Macro', legal: 'Legal', infrastructure: 'Infrastructure', market: 'Market', home: 'Home', search: 'Search' },
      statuses: { healthy: 'Healthy', running: 'Running', due: 'Due', review: 'Review', degraded: 'Degraded', stale: 'Stale' },
      freshness: { fresh: 'Fresh', due: 'Due', stale: 'Stale', unknown: 'Unknown', derived: 'Derived', current: 'Current' },
      cadence: { daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly', 'on-data-change': 'On data change' },
      modes: {
        'automated-controlled': 'Automated · controlled',
        'corroborated-controlled': 'Corroborated · controlled',
        'two-source-corroborated': 'Two-source corroborated',
        'curated-manual': 'Curated · manual',
        'curated-research': 'Curated · research',
        'automated-candidate-review': 'Automated candidate · review',
        'assisted-browser': 'Assisted browser',
        derived: 'Derived',
        'derived-runtime': 'Derived · runtime'
      },
      labels: { datasets: 'Datasets', healthy: 'Healthy', due: 'Due / Review', stale: 'Stale' },
      latestPeriod: 'Latest period', records: 'Records', lastUpdated: 'Last updated', reviewBy: 'Review by', mode: 'Mode', cadenceLabel: 'Cadence',
      noAttention: 'No dataset currently needs maintenance review.',
      noAttentionNote: 'All source datasets are within their configured freshness windows. Derived Home and Search follow the health of their dependencies.',
      generated: 'Calculated from deployed repository data',
      loadError: 'Unable to calculate maintenance status from the deployed repository.',
      rules: [
        ['Source failure', 'Retain the last good data.'],
        ['Insufficient evidence', 'Do not promote.'],
        ['Missing value', 'Leave blank; do not estimate.'],
        ['History', 'Do not create synthetic history.'],
        ['Derived layers', 'Do not create new facts.']
      ]
    },
    vi: {
      modules: { macro: 'Vĩ mô', legal: 'Pháp lý', infrastructure: 'Hạ tầng', market: 'Thị trường', home: 'Trang chủ', search: 'Tìm kiếm' },
      statuses: { healthy: 'Tốt', running: 'Đang chạy', due: 'Đến hạn', review: 'Cần xem', degraded: 'Suy giảm', stale: 'Quá hạn' },
      freshness: { fresh: 'Mới', due: 'Đến hạn', stale: 'Quá hạn', unknown: 'Chưa rõ', derived: 'Theo dữ liệu nguồn', current: 'Hiện tại' },
      cadence: { daily: 'Hằng ngày', weekly: 'Hằng tuần', monthly: 'Hằng tháng', 'on-data-change': 'Khi dữ liệu thay đổi' },
      modes: {
        'automated-controlled': 'Tự động · có kiểm soát',
        'corroborated-controlled': 'Đối chiếu · có kiểm soát',
        'two-source-corroborated': 'Đối chiếu 2 nguồn',
        'curated-manual': 'Tuyển chọn · thủ công',
        'curated-research': 'Tuyển chọn · nghiên cứu',
        'automated-candidate-review': 'Candidate tự động · cần duyệt',
        'assisted-browser': 'Hỗ trợ qua trình duyệt',
        derived: 'Dẫn xuất',
        'derived-runtime': 'Dẫn xuất · runtime'
      },
      labels: { datasets: 'Bộ dữ liệu', healthy: 'Tốt', due: 'Đến hạn / Cần xem', stale: 'Quá hạn' },
      latestPeriod: 'Kỳ mới nhất', records: 'Bản ghi', lastUpdated: 'Cập nhật cuối', reviewBy: 'Rà soát trước', mode: 'Cách cập nhật', cadenceLabel: 'Tần suất',
      noAttention: 'Hiện không có bộ dữ liệu nào cần rà soát bảo trì.',
      noAttentionNote: 'Tất cả dữ liệu nguồn đang nằm trong ngưỡng freshness đã cấu hình. Trang chủ và Tìm kiếm kế thừa trạng thái từ các dữ liệu nguồn.',
      generated: 'Tính từ dữ liệu đang được triển khai trên website',
      loadError: 'Không thể tính trạng thái bảo trì từ dữ liệu đang triển khai.',
      rules: [
        ['Nguồn lỗi', 'Giữ dữ liệu tốt gần nhất.'],
        ['Chưa đủ bằng chứng', 'Không promote.'],
        ['Thiếu số liệu', 'Để trống, không tự ước tính.'],
        ['Lịch sử', 'Không tạo lịch sử giả.'],
        ['Lớp dẫn xuất', 'Không tạo dữ kiện mới.']
      ]
    }
  };

  function language() {
    return window.AppLocalization?.getLanguage?.() || document.documentElement.lang || 'vi';
  }

  function copy() { return COPY[language()] || COPY.vi; }
  function esc(value) { return window.Components?.escapeHTML ? Components.escapeHTML(value) : String(value ?? ''); }

  async function fetchJSON(path) {
    const response = await fetch(path, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`${path} (${response.status})`);
    return response.json();
  }

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function maxText(values) {
    const clean = values.filter(value => value !== null && value !== undefined && String(value) !== '').map(String);
    return clean.length ? clean.sort().at(-1) : null;
  }

  function formatDateTime(value) {
    const date = value instanceof Date ? value : parseDate(value);
    if (!date) return '—';
    const locale = language() === 'vi' ? 'vi-VN' : 'en-GB';
    return new Intl.DateTimeFormat(locale, {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
      timeZone: 'Asia/Ho_Chi_Minh'
    }).format(date);
  }

  function datasetRow(entry, payload, now) {
    const all = Array.isArray(payload?.data) ? payload.data : [];
    const ids = new Set(entry.indicator_ids || []);
    const selected = ids.size ? all.filter(row => ids.has(row.indicator_id)) : all;
    let refreshText = payload?.generated_at || payload?.updated_at || null;
    if (!refreshText) refreshText = maxText(selected.map(row => row.updated_at));
    const refreshDate = parseDate(refreshText);
    const staleAfter = Number.isFinite(Number(entry.stale_after_hours)) ? Number(entry.stale_after_hours) : null;
    const ageHours = refreshDate ? Math.max(0, (now - refreshDate) / 3600000) : null;

    let freshness = 'unknown';
    let status = 'review';
    if (refreshDate && staleAfter === null) {
      freshness = 'current'; status = 'healthy';
    } else if (refreshDate && ageHours <= staleAfter) {
      freshness = 'fresh'; status = 'healthy';
    } else if (refreshDate && ageHours <= staleAfter * 1.25) {
      freshness = 'due'; status = 'due';
    } else if (refreshDate) {
      freshness = 'stale'; status = 'stale';
    }

    return {
      ...entry,
      status,
      freshness,
      last_updated_at: refreshText,
      latest_observation_period: maxText(selected.map(row => row.period)),
      latest_published_at: maxText(selected.map(row => row.published_at)),
      record_count: selected.length,
      age_hours: ageHours,
      review_by: refreshDate && staleAfter !== null ? new Date(refreshDate.getTime() + staleAfter * 3600000) : null
    };
  }

  function derivedRow(entry, byId) {
    const deps = (entry.depends_on || []).map(id => byId.get(id)).filter(Boolean);
    const states = deps.map(row => row.status);
    let status = 'healthy';
    if (states.includes('stale')) status = 'stale';
    else if (states.some(value => value === 'due' || value === 'review')) status = 'due';
    return {
      ...entry,
      status,
      freshness: 'derived',
      last_updated_at: maxText(deps.map(row => row.last_updated_at)),
      latest_observation_period: null,
      record_count: null,
      age_hours: null,
      review_by: null
    };
  }

  async function buildModel() {
    const matrix = await fetchJSON('config/update_matrix.json');
    const now = new Date();
    const sourceEntries = matrix.datasets.filter(entry => entry.data_path);
    const settled = await Promise.allSettled(sourceEntries.map(entry => fetchJSON(entry.data_path)));
    const rows = [];
    const byId = new Map();

    sourceEntries.forEach((entry, index) => {
      if (settled[index].status !== 'fulfilled') {
        const row = { ...entry, status: 'review', freshness: 'unknown', last_updated_at: null, latest_observation_period: null, record_count: null, age_hours: null, review_by: null };
        rows.push(row); byId.set(row.id, row); return;
      }
      const row = datasetRow(entry, settled[index].value, now);
      rows.push(row); byId.set(row.id, row);
    });

    matrix.datasets.filter(entry => entry.depends_on).forEach(entry => {
      const row = derivedRow(entry, byId);
      rows.push(row); byId.set(row.id, row);
    });

    rows.sort((a, b) => MODULE_ORDER.indexOf(a.module) - MODULE_ORDER.indexOf(b.module));
    const counts = { healthy: 0, due: 0, review: 0, stale: 0 };
    rows.forEach(row => { counts[row.status] = (counts[row.status] || 0) + 1; });
    const overall = counts.stale ? 'stale' : (counts.due || counts.review ? 'due' : 'healthy');
    return { matrix, now, rows, counts, overall };
  }

  function statusBadge(status, freshness) {
    const c = copy();
    const statusText = c.statuses[status] || status;
    const freshText = c.freshness[freshness] || freshness;
    return `<span class="maintenance-status is-${esc(status)}"><span class="maintenance-status__dot"></span>${esc(statusText)}</span><span class="maintenance-freshness">${esc(freshText)}</span>`;
  }

  function summaryCard(label, value, kind, note) {
    return `<article class="maintenance-summary-card is-${esc(kind)}"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`;
  }

  function renderSummary(model) {
    const c = copy();
    const dueCount = (model.counts.due || 0) + (model.counts.review || 0);
    document.querySelector('[data-maintenance-summary]').innerHTML = [
      summaryCard(c.labels.datasets, model.rows.length, 'neutral', language() === 'vi' ? 'đang theo dõi' : 'tracked'),
      summaryCard(c.labels.healthy, model.counts.healthy || 0, 'healthy', language() === 'vi' ? 'trong ngưỡng cập nhật' : 'within freshness window'),
      summaryCard(c.labels.due, dueCount, 'due', language() === 'vi' ? 'cần rà soát sớm' : 'needs review soon'),
      summaryCard(c.labels.stale, model.counts.stale || 0, 'stale', language() === 'vi' ? 'vượt ngưỡng freshness' : 'past freshness window')
    ].join('');
  }

  function renderAttention(model) {
    const c = copy();
    const node = document.querySelector('[data-maintenance-attention]');
    const attention = model.rows.filter(row => ['due', 'review', 'stale'].includes(row.status));
    if (!attention.length) {
      node.innerHTML = `<div class="maintenance-clear"><span class="maintenance-clear__icon">✓</span><div><strong>${esc(c.noAttention)}</strong><p>${esc(c.noAttentionNote)}</p></div></div>`;
      return;
    }
    node.innerHTML = `<div class="maintenance-queue">${attention.map(row => `
      <article class="maintenance-queue__item is-${esc(row.status)}">
        <div>${statusBadge(row.status, row.freshness)}</div>
        <strong>${esc(row.label)}</strong>
        <span>${esc(c.modules[row.module] || row.module)} · ${esc(c.cadence[row.check_frequency] || row.check_frequency)}</span>
        <small>${row.review_by ? `${esc(c.reviewBy)} ${esc(formatDateTime(row.review_by))}` : ''}</small>
      </article>`).join('')}</div>`;
  }

  function renderTable(model) {
    const c = copy();
    const rows = model.rows.map(row => {
      const reviewNote = row.review_by ? `${c.reviewBy} ${formatDateTime(row.review_by)}` : (row.freshness === 'derived' ? (language() === 'vi' ? 'Theo trạng thái dữ liệu nguồn' : 'Follows source datasets') : '');
      return `<tr>
        <td data-label-vi="Module" data-label-en="Module"><span class="maintenance-module">${esc(c.modules[row.module] || row.module)}</span></td>
        <td data-label-vi="Bộ dữ liệu" data-label-en="Dataset"><strong class="maintenance-dataset-name">${esc(row.label)}</strong><span class="table-subtext">${esc(c.modes[row.update_mode] || row.update_mode)}</span></td>
        <td data-label-vi="Trạng thái" data-label-en="Status">${statusBadge(row.status, row.freshness)}</td>
        <td data-label-vi="Tần suất" data-label-en="Cadence">${esc(c.cadence[row.check_frequency] || row.check_frequency)}</td>
        <td data-label-vi="Kỳ dữ liệu" data-label-en="Latest period">${esc(row.latest_observation_period || '—')}</td>
        <td class="numeric" data-label-vi="Số bản ghi" data-label-en="Records">${row.record_count === null || row.record_count === undefined ? '—' : esc(row.record_count)}</td>
        <td data-label-vi="Cập nhật gần nhất" data-label-en="Last updated">${esc(formatDateTime(row.last_updated_at))}<span class="table-subtext">${esc(reviewNote)}</span></td>
      </tr>`;
    }).join('');

    document.querySelector('[data-maintenance-table]').innerHTML = `<div class="table-wrap table-wrap--maintenance"><table class="data-table data-table--maintenance mobile-record-table">
      <thead><tr><th>Module</th><th>Dataset</th><th>Status</th><th>${esc(c.cadenceLabel)}</th><th>${esc(c.latestPeriod)}</th><th class="numeric">${esc(c.records)}</th><th>${esc(c.lastUpdated)}</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  function safeWorkflowRunUrl(value) {
    return /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/actions\/runs\/[0-9]+$/.test(value || '')
      ? value : null;
  }

  async function renderOperations() {
    const node = document.querySelector('[data-maintenance-operations]');
    if (!node) return;
    try {
      const payload = await DataStore.getDataHealth();
      const datasets = payload?.datasets || [];
      const c = copy();
      node.innerHTML = (payload?.modules || []).map(module => {
        const rows = datasets.filter(row => row.module === module.module);
        const access = [...new Set(rows.map(row => row.source_access).filter(Boolean))].join(' · ') || '—';
        const workflows = [...new Set(rows.map(row => row.workflow_status).filter(Boolean))];
        const workflow = workflows.includes('degraded') ? 'degraded'
          : workflows.includes('running') ? 'running'
          : workflows.includes('healthy') ? 'healthy'
          : 'unknown';
        const lastSuccess = module.last_successful_run_at ? formatDateTime(module.last_successful_run_at) : '—';
        const vi = language() !== 'en';
        const failed = rows.filter(row => ['degraded','stale'].includes(row.status));
        const daily = module.module === 'macro' ? rows.find(row => row.id === 'macro-daily-markets') : null;
        const sourceLag = daily && daily.source_business_day_lag != null
          ? `<div class="maintenance-lag${daily.source_freshness === 'late' ? ' is-late' : ''}">
             <strong>${esc(vi ? 'Kỳ tỷ giá/vàng cuối' : 'Last FX/gold source period')}: ${esc(daily.latest_source_period || '—')}</strong>
             <span>${esc(daily.source_business_day_lag)} ${esc(vi ? 'ngày làm việc kể từ kỳ nguồn (không tính lễ)' : 'business days after source period (holidays excluded)')}</span>
           </div>` : '';
        const activeProblem = failed.find(row => safeWorkflowRunUrl(row.last_workflow_run_url)) ||
          rows.find(row => safeWorkflowRunUrl(row.last_workflow_run_url));
        const workflowLink = activeProblem ? safeWorkflowRunUrl(activeProblem.last_workflow_run_url) : null;
        const detail = (failed.length || daily?.source_freshness === 'late') ?
          `<div class="maintenance-ops-detail">${sourceLag}
             <div>${esc(vi ? 'Lần chạy gần nhất' : 'Last run')}: ${esc(activeProblem?.last_workflow_conclusion || (vi ? 'Chưa xác định' : 'Unknown'))}
               ${workflowLink ? ` · <a href="${esc(workflowLink)}" target="_blank" rel="noopener noreferrer">${esc(vi ? 'Mở GitHub Actions' : 'Open GitHub Actions')}</a>` : ''}
             </div>
             <small>${esc(vi ? 'Có kiểm tra nguồn không đồng nghĩa có số liệu mới được xác minh.' : 'A successful source check does not prove a new observation was verified.')}</small>
           </div>` : '';
        return `<article class="maintenance-operation-card is-${esc(module.status || 'review')}">
          <div class="data-health-card__top">
            <h3>${esc(c.modules[module.module] || module.module)}</h3>
            <span class="data-health-status">${esc(c.statuses[module.status] || module.status)}</span>
          </div>
          <dl>
            <div><dt>Workflow</dt><dd>${esc(c.statuses[workflow] || workflow)}</dd></div>
            <div><dt>Source mode</dt><dd>${esc(access)}</dd></div>
            <div><dt>Candidate backlog</dt><dd>${esc(module.candidate_backlog || 0)}</dd></div>
            <div><dt>Last success</dt><dd>${esc(lastSuccess)}</dd></div>
          </dl>
          ${detail}
        </article>`;
      }).join('') || '<div class="state-box">Operational health is not available yet.</div>';
    } catch (error) {
      console.warn('[maintenance] unified operational health unavailable', error);
      node.innerHTML = '<div class="state-box">Operational health is not available yet.</div>';
    }
  }

  async function renderMarketSourceHealth() {
    const node = document.querySelector('[data-market-source-health]');
    if (!node) return;
    const vi = language() !== 'en';
    const labels = vi ? {
      provider: 'Nguồn', project: 'Dự án / Phân khúc', state: 'Khả năng thu thập',
      checks: 'Lượt kiểm tra', good: 'Đọc được nhiều lượt',
      partial: 'Đã đọc được · theo dõi thêm', blocked: 'Không xác minh được',
      unknown: 'Chưa có bằng chứng', listing: 'Chỉ tin đăng', noData: 'Chưa có báo cáo kiểm tra nguồn.',
      note: 'Đọc được nguồn không đồng nghĩa đã có số liệu mới được công bố. Giá dự án và cung/cầu toàn thị trường được theo dõi riêng.'
    } : {
      provider: 'Source', project: 'Project / Segment', state: 'Capture quality',
      checks: 'Checks', good: 'Repeatedly parseable', partial: 'Parseable · monitoring',
      blocked: 'Not verifiable', unknown: 'No verification yet', listing: 'Listing-only',
      noData: 'No source reliability report available.',
      note: 'Source access is not a new verified observation. Project asking prices and market-wide supply/demand remain separate.'
    };
    try {
      const [reliabilityResult, secondaryResult, quarterlyResult, portalResult, reverResult, muabanResult] = await Promise.allSettled([
        fetchJSON('data/state/market-source-reliability.json'),
        fetchJSON('data/state/market-stable-listing-health.json'),
        fetchJSON('data/state/market-cushman-quarterly-verification.json'),
        fetchJSON('data/state/listing-source-coverage.json'),
        fetchJSON('data/state/market-rever-source-health.json'),
        fetchJSON('data/state/market-muaban-source-health.json')
      ]);
      const reliability = reliabilityResult.status === 'fulfilled' ? reliabilityResult.value : {};
      const secondary = secondaryResult.status === 'fulfilled' ? secondaryResult.value : {};
      const quarterly = quarterlyResult.status === 'fulfilled' ? quarterlyResult.value : {};
      const portal = portalResult.status === 'fulfilled' ? portalResult.value : {};
      const rever = reverResult.status === 'fulfilled' ? reverResult.value : {};
      const muaban = muabanResult.status === 'fulfilled' ? muabanResult.value : {};
      const targets = (reliability.targets || []).filter(row => row.mode === 'monthly-price-candidate');
      const rows = targets.map(row => {
        const id = row.target_id || '';
        const project = id.includes('lumiere-boulevard') ? 'Lumière Boulevard'
          : id.includes('masteri-centre-point') ? 'Masteri Centre Point' : 'Vinhomes Grand Park';
        const status = row.classification === 'repeatably-parseable' ? labels.good
          : row.classification === 'source-parseable-not-yet-repeatable' ? labels.partial
          : row.classification === 'not-yet-measured' ? labels.unknown : labels.blocked;
        return ['OneHousing', project, status, String(row.check_count || 0)];
      });
      if ((quarterly.checks || []).length) {
        const recent = quarterly.checks.at(-1) || {};
        const period = String(recent.period || '').replace(/^([0-9]{4})-Q([1-4])$/, 'Q$2/$1');
        const status = quarterly.latest_status === 'matched-source-quarter-and-metrics'
          ? (vi ? 'Đọc được ' : 'Parsed ') + (period || '—')
          : (quarterly.access_status === 'access-blocked'
            ? (vi ? 'Bị chặn truy cập' : 'Access blocked')
            : labels.blocked);
        rows.push(['Cushman & Wakefield', vi ? 'Căn hộ TP.HCM · Cung/Hấp thụ'
          : 'HCMC apartments · Supply/absorption', status, String(quarterly.checks.length)]);
      }
      if (portal.source_access) {
        const detail = portal.source_access === 'blocked'
          ? (vi ? 'Bị hạn chế truy cập (HTTP 403)' : 'Access restricted (HTTP 403)')
          : portal.source_access === 'healthy' ? labels.partial : labels.unknown;
        rows.push(['Batdongsan', vi ? 'Snapshot giá chào bán' : 'Asking-price snapshots',
          detail, String(portal.source_checks || 0)]);
      }
      if (rever.targets_checked) {
        const fresh = Number(rever.source_updates_within_90_days || 0);
        const verified = Number(rever.published_current_individual_listings || 0);
        const latest = (rever.projects || []).map(item => item.latest_publisher_listing_update_date)
          .filter(Boolean).sort().at(-1);
        const status = vi
          ? `${fresh} tin có ngày cập nhật ≤90 ngày · ${verified} tin đã đủ xác minh`
          : `${fresh} publisher-dated within 90 days · ${verified} verified live listings`;
        rows.push(['Rever',
          vi ? `Căn hộ theo từng tin · ${rever.targets_checked} dự án`
             : `Individual apartments · ${rever.targets_checked} projects`,
          status + (latest ? ` · ${vi ? 'Mới nhất' : 'Latest'} ${latest}` : ''),
          String(rever.source_runs_seen || 0)]);
      }
      if (muaban.targets_checked) {
        const valid = Number(muaban.valid_unexpired_project_ads || 0);
        const published = Number(muaban.published_current_individual_listings || 0);
        const state = vi ? `${valid} tin đúng dự án, chưa hết hạn · ${published} đã xác minh`
                         : `${valid} project-matched, unexpired · ${published} verified`;
        rows.push(['Muaban.net',
          vi ? `Tin căn hộ bán · ${muaban.targets_checked} dự án`
             : `Apartment sale ads · ${muaban.targets_checked} projects`,
          state, String(muaban.details_checked || 0)]);
      }
      if (secondary.categories_checked) {
        const blocked = (secondary.status_counts || {})['access-blocked'] || 0;
        const categories = Number(secondary.categories_checked) || 0;
        const status = blocked === categories ? (vi ? 'Bị chặn HTTP 403' : 'HTTP 403 blocked')
          : secondary.new_listing_candidates ? labels.partial : labels.unknown;
        rows.push(['Nhà Tốt', vi ? 'Tin đăng thứ cấp' : 'Secondary listings', status, String(categories)]);
      }
      if (!rows.length) {
        node.innerHTML = `<div class="state-box">${esc(labels.noData)}</div>`;
        return;
      }
      node.innerHTML = `<div class="table-wrap table-wrap--maintenance">
        <table class="data-table data-table--maintenance mobile-record-table">
          <thead><tr><th>${esc(labels.provider)}</th><th>${esc(labels.project)}</th><th>${esc(labels.state)}</th><th class="numeric">${esc(labels.checks)}</th></tr></thead>
          <tbody>${rows.map(row => `<tr>${row.map((cell, i) => `<td${i === 3 ? ' class="numeric"' : ''} data-label-vi="${['Nguồn', 'Dự án / dữ liệu', 'Tình trạng', 'Lượt kiểm tra'][i]}" data-label-en="${['Source', 'Project / dataset', 'Status', 'Checks'][i]}">${esc(cell)}</td>`).join('')}</tr>`).join('')}</tbody>
        </table>
      </div><p class="table-subtext" style="padding:10px 14px">${esc(labels.note)}</p>`;
    } catch (error) {
      console.warn('[maintenance] market source-health unavailable', error);
      node.innerHTML = `<div class="state-box">${esc(labels.noData)}</div>`;
    }
  }

  async function renderActiveListingCoverage() {
    const node = document.querySelector('[data-market-active-coverage]');
    if (!node) return;
    const vi = language() !== 'en';
    const heading = document.querySelector('#market-active-coverage-title');
    if (heading) heading.textContent = vi ? 'Độ phủ giá rao căn hộ theo dự án' : 'Apartment asking-listing coverage by project';
    const note = node.closest('.section')?.querySelector('.home-block__note');
    if (note) note.textContent = vi ? 'Có nguồn ≠ có tin mới ≠ giá đã xác minh' : 'Tracked source ≠ new listing ≠ verified unit price';
    const labels = vi
      ? {project:'Dự án',source:'Nguồn theo dõi',candidate:'Tin đạt điều kiện nguồn',
         published:'Tin đã xác minh',status:'Tình trạng',
         tracked:'dự án có nguồn',verified:'dự án có giá từng căn đã xác minh',
         lack:'chưa có nguồn theo dõi', waiting:'đang theo dõi · chưa có tin mới hợp lệ',
         pending:'tin nguồn đủ điều kiện · chờ xác minh', current:'đã có tin xác minh còn trong hạn',
         stale:'báo cáo nguồn cần cập nhật', date:'Báo cáo độ phủ',
         note:'Chỉ là giá rao của từng căn. Không suy ra ASP dự án, giá giao dịch hay khoảng giá đại diện.',
         empty:'Chưa có snapshot độ phủ từ GitHub Actions. Chờ lượt tự động đầu tiên.'}
      : {project:'Project',source:'Tracked sources',candidate:'Source-qualified ads',
         published:'Verified ads',status:'Status',
         tracked:'projects monitored',verified:'projects with verified unit offers',
         lack:'no tracked unit-listing source',waiting:'monitored · no eligible recent ad',
         pending:'eligible source ad · awaiting verification',current:'current verified unit evidence',
         stale:'source report needs refresh', date:'Coverage snapshot',
         note:'Individual asking listings only; not a project ASP, transaction price or representative range.',
         empty:'No coverage snapshot published yet. Waiting for first scheduled GitHub run.'};
    try {
      const payload = await fetchJSON('data/state/market-active-listing-coverage.json');
      if (!Array.isArray(payload.projects) || payload.schema_version !== 1) throw new Error('Invalid coverage payload');
      const sourceNames = {'muaban-vn':'Muaban.net', 'rever-vn':'Rever'};
      const stateText = {
        'no-verified-unit-source-target':labels.lack,
        'monitored-no-current-verified-offer':labels.waiting,
        'source-qualified-awaiting-verification':labels.pending,
        'published-current-unit-offer':labels.current
      };
      const rows = payload.projects.map(item => {
        const sources = (item.sources || []).map(s =>
          sourceNames[s.source_id] || s.source_id).join(' · ');
        const needsRefresh = (item.sources || []).some(s => !s.source_health_recent);
        const projectLink = 'market.html?view=projects&project=' + encodeURIComponent(item.project_id);
        return `<tr>
          <td data-label-vi="Dự án" data-label-en="Project"><a class="table-link" href="${esc(projectLink)}">${esc(item.project_name)}</a></td>
          <td data-label-vi="Nguồn theo dõi" data-label-en="Tracked sources">${esc(sources || '—')}${needsRefresh ? '<span class="table-subtext">'+esc(labels.stale)+'</span>' : ''}</td>
          <td class="numeric" data-label-vi="Tin đạt điều kiện nguồn" data-label-en="Source-qualified ads">${esc(item.recent_eligible_ads ?? '—')}</td>
          <td class="numeric" data-label-vi="Tin đã xác minh" data-label-en="Verified ads">${esc(item.current_verified_ads ?? '—')}</td>
          <td data-label-vi="Tình trạng" data-label-en="Status">${esc(stateText[item.status] || item.status)}</td>
        </tr>`;
      }).join('');
      node.innerHTML = `<div style="padding:12px 16px">
          <strong>${esc(payload.projects_monitored)}/${esc(payload.project_registry_count)} ${esc(labels.tracked)}</strong>
          · <strong>${esc(payload.projects_with_current_verified_unit_offers)} ${esc(labels.verified)}</strong>
          <span class="table-subtext">${esc(labels.date)}: ${esc(formatDateTime(payload.generated_at))}</span>
        </div>
        <div class="table-wrap">
          <table class="data-table data-table--listing-coverage mobile-record-table">
            <thead><tr><th>${esc(labels.project)}</th><th>${esc(labels.source)}</th>
              <th class="numeric">${esc(labels.candidate)}</th><th class="numeric">${esc(labels.published)}</th><th>${esc(labels.status)}</th></tr></thead>
            <tbody>${rows || '<tr><td colspan="5" class="table-empty">'+esc(labels.empty)+'</td></tr>'}</tbody>
          </table>
        </div><p class="table-subtext" style="padding:8px 16px 14px">${esc(labels.note)}</p>`;
    } catch (error) {
      node.innerHTML = `<div class="state-box">${esc(labels.empty)}</div>`;
    }
  }

  function renderRules() {
    const c = copy();
    document.querySelector('[data-maintenance-rules]').innerHTML = `<div class="maintenance-rules">${c.rules.map(([title, text]) => `<div class="maintenance-rule"><strong>${esc(title)}</strong><span>${esc(text)}</span></div>`).join('')}</div>`;
  }

  function render(model) {
    lastModel = model;
    const c = copy();
    const legend = document.querySelector('[data-maintenance-legend]');
    if (legend) legend.innerHTML = `<span class="maintenance-dot is-healthy"></span> ${esc(c.statuses.healthy)} <span class="maintenance-dot is-due"></span> ${esc(c.statuses.due)} <span class="maintenance-dot is-stale"></span> ${esc(c.statuses.stale)}`;
    renderSummary(model);
    renderAttention(model);
    renderTable(model);
    renderRules();
    const updated = document.querySelector('[data-maintenance-updated]');
    if (updated) updated.textContent = `${c.generated} · ${model.rows.length} ${language() === 'vi' ? 'bộ dữ liệu' : 'datasets'}`;
    const asof = document.querySelector('[data-maintenance-asof]');
    if (asof) asof.textContent = `${language() === 'vi' ? 'Tại' : 'As of'} ${formatDateTime(model.now)}`;
  }

  function renderError(error) {
    console.error('[maintenance] status calculation failed', error);
    const c = copy();
    ['[data-maintenance-summary]', '[data-maintenance-attention]', '[data-maintenance-table]'].forEach(selector => {
      const node = document.querySelector(selector);
      if (node) node.innerHTML = `<div class="state-box state-box--error">${esc(c.loadError)}</div>`;
    });
    renderRules();
  }

  async function init() {
    try {
      render(await buildModel());
      await renderOperations();
      await renderMarketSourceHealth();
      await renderActiveListingCoverage();
    } catch (error) {
      renderError(error);
    }
    document.addEventListener('app:language-changed', () => {
      if (lastModel) render(lastModel);
      else renderRules();
      renderOperations();
      renderMarketSourceHealth();
      renderActiveListingCoverage();
    });
  }

  window.MaintenanceDashboard = { buildModel, render };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
