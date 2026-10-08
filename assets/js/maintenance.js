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
        <td><span class="maintenance-module">${esc(c.modules[row.module] || row.module)}</span></td>
        <td><strong class="maintenance-dataset-name">${esc(row.label)}</strong><span class="table-subtext">${esc(c.modes[row.update_mode] || row.update_mode)}</span></td>
        <td>${statusBadge(row.status, row.freshness)}</td>
        <td>${esc(c.cadence[row.check_frequency] || row.check_frequency)}</td>
        <td>${esc(row.latest_observation_period || '—')}</td>
        <td class="numeric">${row.record_count === null || row.record_count === undefined ? '—' : esc(row.record_count)}</td>
        <td>${esc(formatDateTime(row.last_updated_at))}<span class="table-subtext">${esc(reviewNote)}</span></td>
      </tr>`;
    }).join('');

    document.querySelector('[data-maintenance-table]').innerHTML = `<div class="table-wrap table-wrap--maintenance"><table class="data-table data-table--maintenance">
      <thead><tr><th>Module</th><th>Dataset</th><th>Status</th><th>${esc(c.cadenceLabel)}</th><th>${esc(c.latestPeriod)}</th><th class="numeric">${esc(c.records)}</th><th>${esc(c.lastUpdated)}</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
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
        </article>`;
      }).join('') || '<div class="state-box">Operational health is not available yet.</div>';
    } catch (error) {
      console.warn('[maintenance] unified operational health unavailable', error);
      node.innerHTML = '<div class="state-box">Operational health is not available yet.</div>';
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
    } catch (error) {
      renderError(error);
    }
    document.addEventListener('app:language-changed', () => {
      if (lastModel) render(lastModel);
      else renderRules();
      renderOperations();
    });
  }

  window.MaintenanceDashboard = { buildModel, render };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
