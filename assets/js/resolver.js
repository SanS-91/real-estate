(() => {
  'use strict';

  const indexes = new Map();

  function setData(type, records = []) {
    indexes.set(type, new Map(records.map(record => [record.id, record])));
  }

  function getEntity(type, id) {
    if (!id) return null;
    return indexes.get(type)?.get(id) || null;
  }

  function getEntities(type, ids = []) {
    return (ids || []).map(id => getEntity(type, id)).filter(Boolean);
  }

  function getLabel(type, id, fallback = '—') {
    const entity = getEntity(type, id);
    return entity?.name || entity?.title || fallback;
  }

  function reset() {
    indexes.clear();
  }

  window.Resolver = { setData, getEntity, getEntities, getLabel, reset };
})();
