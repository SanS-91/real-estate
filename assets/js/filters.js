(() => {
  'use strict';

  function normalizeText(value) {
    return String(value ?? '')
      .toLowerCase()
      .replace(/đ/g, 'd')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s/-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function textMatch(record, query, fields = []) {
    const q = normalizeText(query);
    if (!q) return true;
    const haystack = fields.map(field => {
      const value = typeof field === 'function' ? field(record) : record[field];
      return Array.isArray(value) ? value.join(' ') : value;
    }).join(' ');
    return normalizeText(haystack).includes(q);
  }

  function arrayContainsAny(recordValue, selected) {
    if (!selected || selected.length === 0) return true;
    const values = Array.isArray(recordValue) ? recordValue : [recordValue].filter(Boolean);
    return selected.some(value => values.includes(value));
  }

  function apply(records, state, config) {
    return (records || []).filter(record => {
      return (config || []).every(rule => {
        const selected = state[rule.id];
        if (selected === undefined || selected === null || selected === '' || (Array.isArray(selected) && !selected.length)) return true;
        const value = typeof rule.getValue === 'function' ? rule.getValue(record) : record[rule.field];
        if (rule.type === 'contains-any') return arrayContainsAny(value, Array.isArray(selected) ? selected : [selected]);
        if (rule.type === 'equals') return value === selected;
        if (rule.type === 'text') return textMatch(record, selected, rule.fields || []);
        return true;
      });
    });
  }

  window.FilterEngine = { normalizeText, textMatch, arrayContainsAny, apply };
})();
