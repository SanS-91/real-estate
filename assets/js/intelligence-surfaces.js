((global) => {
  'use strict';

  const DAY_MS = 86400000;

  function dateKey(value) {
    const text=String(value || '').trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0,10);
    let m=text.match(/^(\d{4})-Q([1-4])$/);
    if (m) return [m[1]+'-03-31',m[1]+'-06-30',m[1]+'-09-30',m[1]+'-12-31'][Number(m[2])-1];
    m=text.match(/^(\d{4})-(\d{2})$/);
    if (m) return new Date(Date.UTC(Number(m[1]),Number(m[2]),0)).toISOString().slice(0,10);
    if (/^\d{4}$/.test(text)) return text+'-12-31';
    return '';
  }

  function evidenceDate(row) {
    if (global.IntelligenceRanking?.evidenceDate) return global.IntelligenceRanking.evidenceDate(row);
    return dateKey(row?.date || row?.sort_date || row?.published_at || row?.event_date || row?.source_date || row?.data_date || row?.period);
  }

  function windowFloor(referenceDate, days) {
    const ref=dateKey(referenceDate);
    if (!ref) return '';
    const d=new Date(ref+'T00:00:00Z');
    d.setUTCDate(d.getUTCDate()-Math.max(0,Number(days || 1)-1));
    return d.toISOString().slice(0,10);
  }

  function withinDays(rows, referenceDate, days) {
    const ref=dateKey(referenceDate);
    const floor=windowFloor(ref,days);
    if (!ref || !floor) return [];
    return (rows || []).filter(row => {
      const d=evidenceDate(row);
      return d && d>=floor && d<=ref;
    });
  }

  function today(rows, referenceDate) {
    const ref=dateKey(referenceDate);
    return (rows || []).filter(row => evidenceDate(row)===ref);
  }

  function diverseTop(rows, {limit=6,maxPerCategory=2}={}) {
    const out=[], counts=new Map();
    for (const row of (rows || [])) {
      const category=row.category || 'other';
      const count=counts.get(category) || 0;
      if (count>=maxPerCategory) continue;
      out.push(row);
      counts.set(category,count+1);
      if (out.length>=limit) break;
    }
    return out;
  }

  function thisWeek(rows,{referenceDate,limit=6,maxPerCategory=2}={}) {
    return diverseTop(withinDays(rows,referenceDate,7),{limit,maxPerCategory});
  }

  function topDevelopments(rows,{referenceDate,days=30,limit=6,maxPerCategory=2}={}) {
    return diverseTop(withinDays(rows,referenceDate,days),{limit,maxPerCategory});
  }

  function topPerCategory(rows,categories=['market','legal','infrastructure','macro']) {
    const out=[];
    categories.forEach(category => {
      const row=(rows || []).find(item => item.category===category);
      if (row) out.push(row);
    });
    return out;
  }

  const api={dateKey,evidenceDate,windowFloor,withinDays,today,diverseTop,thisWeek,topDevelopments,topPerCategory};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  global.IntelligenceSurfaces=api;
})(typeof window!=='undefined' ? window : globalThis);
