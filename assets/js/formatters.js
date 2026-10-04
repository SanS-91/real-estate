(() => {
  'use strict';

  const NUMBER_LOCALE = 'en-US';

  function isMissing(value) {
    return value === null || value === undefined || value === '' || Number.isNaN(Number(value));
  }

  function number(value, { min = 0, max = min } = {}) {
    if (isMissing(value)) return '—';
    return new Intl.NumberFormat(NUMBER_LOCALE, {
      minimumFractionDigits: min,
      maximumFractionDigits: max
    }).format(Number(value));
  }

  function compact(value, digits = 1) {
    if (isMissing(value)) return '—';
    return new Intl.NumberFormat(NUMBER_LOCALE, {
      notation: 'compact',
      maximumFractionDigits: digits
    }).format(Number(value));
  }

  function areaSqm(value) {
    if (isMissing(value)) return '—';
    const sqm = Number(value);
    if (sqm >= 10_000) {
      const ha = sqm / 10_000;
      return `${number(ha, { min: Number.isInteger(ha) ? 0 : 1, max: 1 })} ha`;
    }
    return `${number(sqm, { max: 0 })} m²`;
  }

  function aspVndPerSqm(value, { short = false } = {}) {
    if (isMissing(value)) return '—';
    const mn = Number(value) / 1_000_000;
    const digits = Number.isInteger(mn) ? 0 : 1;
    return short
      ? `${number(mn, { max: digits })} mn`
      : `${number(mn, { max: digits })} mn VND/m²`;
  }

  function percentDecimal(value, digits = 0) {
    if (isMissing(value)) return '—';
    return `${number(Number(value) * 100, { max: digits })}%`;
  }

  function percentValue(value, { annual = false, max = 2 } = {}) {
    if (isMissing(value)) return '—';
    const n = Number(value);
    const digits = Number.isInteger(n) ? 1 : Math.min(max, 2);
    return `${number(n, { min: digits === 1 ? 1 : 0, max: digits })}%${annual ? ' p.a.' : ''}`;
  }

  function vndPerUsd(value, { short = false } = {}) {
    if (isMissing(value)) return '—';
    return short ? number(value, { max: 0 }) : `${number(value, { max: 0 })} VND/USD`;
  }

  function vndPerTael(value, { short = false } = {}) {
    if (isMissing(value)) return '—';
    const mn = Number(value) / 1_000_000;
    return short ? `${number(mn, { max: 1 })} mn` : `${number(mn, { max: 1 })} mn VND/tael`;
  }

  function usdPerOz(value, { short = false } = {}) {
    if (isMissing(value)) return '—';
    return short ? `${number(value, { max: 0 })}` : `${number(value, { max: 1 })} USD/oz`;
  }

  function vndBn(value, { compactLarge = true } = {}) {
    if (isMissing(value)) return '—';
    const bn = Number(value);
    if (compactLarge && Math.abs(bn) >= 1_000) {
      return `VND ${number(bn / 1_000, { max: 1 })} tn`;
    }
    return `VND ${number(bn, { max: 0 })} bn`;
  }

  function investment(value, currency = 'VND', unit = 'bn') {
    if (isMissing(value)) return '—';
    if (String(currency).toUpperCase() === 'VND' && unit === 'bn') return vndBn(value);
    return `${number(value, { max: 1 })} ${currency || ''} ${unit || ''}`.trim();
  }

  function unitValue(unit, value, { compact: useCompact = false } = {}) {
    if (isMissing(value)) return '—';
    switch (unit) {
      case 'percent': return percentValue(value);
      case 'percent-per-year': return useCompact ? `${number(value, { max: 2 })}%` : percentValue(value, { annual: true });
      case 'vnd-per-usd': return vndPerUsd(value, { short: useCompact });
      case 'vnd-per-tael': return vndPerTael(value, { short: useCompact });
      case 'usd-per-oz': return usdPerOz(value, { short: useCompact });
      case 'vnd-per-m2': return aspVndPerSqm(value, { short: useCompact });
      case 'vnd-bn': return vndBn(value);
      default: return number(value, { max: 2 });
    }
  }

  function chartValue(unit, value) {
    if (isMissing(value)) return '—';
    switch (unit) {
      case 'percent':
      case 'percent-per-year': return `${number(value, { max: 1 })}%`;
      case 'vnd-per-usd': return number(value, { max: 0 });
      case 'vnd-per-tael': return `${number(Number(value) / 1_000_000, { max: 1 })} mn`;
      case 'usd-per-oz': return number(value, { max: 0 });
      case 'vnd-per-m2': return aspVndPerSqm(value, { short: true });
      default: return compact(value);
    }
  }

  window.Formatters = {
    NUMBER_LOCALE,
    number,
    compact,
    areaSqm,
    aspVndPerSqm,
    percentDecimal,
    percentValue,
    vndPerUsd,
    vndPerTael,
    usdPerOz,
    vndBn,
    investment,
    unitValue,
    chartValue
  };
})();
