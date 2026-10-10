(() => {
  'use strict';
  const DAY = 86400000;
  const MINUTE = 60000;
  // Schedule is expressed in UTC to match GitHub Actions cron.
  function latestSlot(config, now = Date.now()) {
    const hours = Array.isArray(config?.utc_hours) ? config.utc_hours : [];
    if (!hours.length) return null;
    const minute = Number(config.utc_minute);
    if (!Number.isInteger(minute) || minute < 0 || minute > 59) return null;
    const day = Math.floor(now / DAY) * DAY;
    const slots = [-1, 0].flatMap(offset =>
      hours.map(hour => day + offset * DAY + Number(hour) * 3600000 + minute * MINUTE)
    ).filter(time => Number.isFinite(time) && time <= now);
    return slots.length ? Math.max(...slots) : null;
  }

  function evaluate(snapshot, config, now = Date.now()) {
    const checkedAt = Date.parse(snapshot?.checked_at || '');
    const checked = Number.isFinite(checkedAt) ? checkedAt : null;
    const expected = latestSlot(config, now);
    const grace = Math.max(0, Number(config?.max_delay_minutes) || 90) * MINUTE;
    const overdue = expected !== null && now > expected + grace && (checked === null || checked < expected);
    const statuses = Array.isArray(snapshot?.feed_status) ? snapshot.feed_status : [];
    const invalid = statuses.filter(item => item.status !== 'parsed' && item.status !== 'empty-feed');
    const empty = statuses.filter(item => item.status === 'empty-feed');
    const errors = Array.isArray(snapshot?.fetch_errors) ? snapshot.fetch_errors : [];
    const fetched = Number(snapshot?.feeds_fetched) || 0;
    const configured = Number(snapshot?.feeds_configured) || 0;
    const parsed = statuses.filter(item => item.status === 'parsed').length;
    const issues = [...invalid, ...empty];
    const state = checked === null ? 'no-data' : overdue ? 'stale' :
      (errors.length || issues.length || parsed < configured ? 'degraded' : 'healthy');
    return {
      state, checked, expected, overdue, fetched, configured, parsed,
      invalid, empty, errors, issues,
      added: Number(snapshot?.accepted_new) || 0,
      total: Number(snapshot?.article_total) || null,
      duplicate: statuses.reduce((sum, item) => sum + (Number(item.duplicates) || 0), 0),
      filtered: statuses.reduce((sum, item) => sum + (Number(item.filtered) || 0), 0),
    };
  }
  window.NewsAutomationHealth = { latestSlot, evaluate };
})();
