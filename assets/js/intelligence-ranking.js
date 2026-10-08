(() => {
  'use strict';

  const DEFAULT_MAX_SCORE = 100;
  const DAY_MS = 86400000;

  function asNumber(value) {
    return value !== null && value !== undefined && Number.isFinite(Number(value)) ? Number(value) : null;
  }

  function dateKey(value) {
    const text=String(value || '').trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0,10);
    let m=text.match(/^(\d{4})-Q([1-4])$/);
    if (m) {
      const year=Number(m[1]), q=Number(m[2]);
      const month=q*3;
      return new Date(Date.UTC(year,month,0)).toISOString().slice(0,10);
    }
    m=text.match(/^(\d{4})-(\d{2})$/);
    if (m) {
      const year=Number(m[1]), month=Number(m[2]);
      return new Date(Date.UTC(year,month,0)).toISOString().slice(0,10);
    }
    if (/^\d{4}$/.test(text)) return text+'-12-31';
    return '';
  }

  function sourceIds(row) {
    const values=[
      row?.source_id,
      ...(row?.source_ids || []),
      row?.current?.source_id,
      row?.previous?.source_id
    ].filter(Boolean);
    return [...new Set(values)];
  }

  function isDemoSource(id) {
    return String(id || '').startsWith('demo-');
  }

  function sourcePriorityMap(sources) {
    return new Map((sources || []).map(row => [row.id, Number(row.source_priority)]));
  }

  function sourceQuality(row, sources, rules) {
    const ids=sourceIds(row).filter(id => !isDemoSource(id));
    if (!ids.length) return { points:0, source_ids:[], best_priority:null };
    const priorities=sourcePriorityMap(sources);
    const available=ids.map(id => priorities.get(id)).filter(Number.isFinite);
    const best=available.length ? Math.min(...available) : null;
    const table=rules.source_priority_points || {};
    const raw=best === null ? Number(table.default || 0) : Number(table[String(best)] ?? table.default ?? 0);
    const cap=Number(rules.weights?.source_quality ?? raw);
    return { points:Math.min(cap,raw), source_ids:ids, best_priority:best };
  }

  function evidenceDate(row) {
    return dateKey(
      row?.date || row?.event_date || row?.published_at || row?.source_date ||
      row?.data_date || row?.period || row?.current?.source_date ||
      row?.current?.published_at || row?.current?.data_date || row?.current?.period
    );
  }

  function freshness(row, referenceDate, rules) {
    const evidence=evidenceDate(row);
    const ref=dateKey(referenceDate);
    if (!evidence || !ref) return { points:0, age_days:null, evidence_date:evidence || null };
    const age=Math.max(0,Math.floor((Date.parse(ref+'T00:00:00Z')-Date.parse(evidence+'T00:00:00Z'))/DAY_MS));
    const bands=rules.freshness_points || [];
    let points=0;
    for (const band of bands) {
      if (band.max_age_days === null || age <= Number(band.max_age_days)) {
        points=Number(band.points || 0);
        break;
      }
    }
    const cap=Number(rules.weights?.freshness ?? points);
    return { points:Math.min(cap,points), age_days:age, evidence_date:evidence };
  }

  function eventSignificance(row, rules) {
    const category=String(row?.category || 'default');
    const type=String(row?.type || row?.event_type || 'default');
    const table=rules.category_type_points?.[category] || {};
    const raw=Number(table[type] ?? table.default ?? 0);
    const cap=Number(rules.weights?.event_significance ?? raw);
    return { points:Math.min(cap,raw), category, type };
  }

  function entityRelevance(row, rules) {
    const cfg=rules.entity_relevance || {};
    let points=0;
    const details=[];

    const projectIds=[...(row?.project_ids || [])];
    if (row?.entity_type === 'real-estate-project' && row?.entity_id) projectIds.push(row.entity_id);
    if (row?.category === 'market' && row?.project_id) projectIds.push(row.project_id);
    if (projectIds.filter(Boolean).length) {
      points += Number(cfg.explicit_project || 0);
      details.push('project');
    }

    const developerIds=row?.developer_ids || [];
    if (developerIds.length) {
      points += Number(cfg.explicit_developer || 0);
      details.push('developer');
    }

    const regionIds=row?.region_ids || row?.current?.region_ids || [];
    if (regionIds.length || (row?.category === 'market' && String(row?.entity_id || '').includes('hcmc'))) {
      points += Number(cfg.explicit_region || 0);
      details.push('region');
    }

    const infraIds=[...(row?.infrastructure_project_ids || [])];
    if (row?.category === 'infrastructure' && row?.entity_id) infraIds.push(row.entity_id);
    if (row?.entity_type === 'infrastructure-project' && row?.entity_id) infraIds.push(row.entity_id);
    if (infraIds.filter(Boolean).length) {
      points += Number(cfg.explicit_infrastructure || 0);
      details.push('infrastructure');
    }

    const legalIds=[...(row?.legal_document_ids || [])];
    if (row?.category === 'legal' && row?.entity_id) legalIds.push(row.entity_id);
    if (legalIds.filter(Boolean).length) {
      points += Number(cfg.explicit_legal_document || 0);
      details.push('legal-document');
    }

    const cap=Math.min(
      Number(cfg.tracked_entity_cap ?? rules.weights?.entity_relevance ?? points),
      Number(rules.weights?.entity_relevance ?? points)
    );
    return { points:Math.min(cap,points), relation_types:[...new Set(details)] };
  }

  function magnitude(row, rules) {
    const cfg=rules.magnitude_rules || {};
    const cap=Number(rules.weights?.change_magnitude ?? 0);
    let points=0;
    let basis='none';

    const pct=asNumber(row?.pct);
    if (pct !== null) {
      const abs=Math.abs(pct);
      for (const band of (cfg.percent_change || [])) {
        if (abs >= Number(band.min_abs_pct || 0)) {
          points=Math.max(points,Number(band.points || 0));
          basis='percent-change';
          break;
        }
      }
    }

    const type=String(row?.type || row?.event_type || '');
    if (type === 'schedule-change') {
      points=Math.max(points,Number(cfg.schedule_change_points || 0));
      basis='schedule-change';
    }
    if (['amends','replaces','supplements'].includes(type)) {
      points=Math.max(points,Number(cfg.legal_amendment_points || 0));
      basis='legal-change';
    }

    const importance=asNumber(row?.importance);
    if (importance !== null) {
      const eventPoints=Math.min(
        Number(cfg.event_importance_cap || cap),
        importance * Number(cfg.event_importance_multiplier || 0)
      );
      if (eventPoints > points) {
        points=eventPoints;
        basis='source-event-importance';
      }
    }
    return { points:Math.min(cap,points), basis };
  }

  function tierFor(score,rules) {
    const tiers=[...(rules.tiers || [])].sort((a,b)=>Number(b.min_score)-Number(a.min_score));
    return tiers.find(row => score >= Number(row.min_score)) || { id:'context', label:'Context', min_score:0 };
  }

  function rankOne(row,{sources=[],rules={},referenceDate}={}) {
    const source=sourceQuality(row,sources,rules);
    const fresh=freshness(row,referenceDate,rules);
    const significance=eventSignificance(row,rules);
    const relevance=entityRelevance(row,rules);
    const change=magnitude(row,rules);
    const raw=source.points+fresh.points+significance.points+relevance.points+change.points;
    const score=Math.min(Number(rules.max_score || DEFAULT_MAX_SCORE),raw);
    const tier=tierFor(score,rules);
    return {
      ...row,
      attention_score:score,
      attention_tier:tier.id,
      attention_label:tier.label,
      ranking_components:{
        source_quality:source.points,
        freshness:fresh.points,
        event_significance:significance.points,
        entity_relevance:relevance.points,
        change_magnitude:change.points
      },
      ranking_evidence:{
        source_ids:source.source_ids,
        source_priority:source.best_priority,
        evidence_date:fresh.evidence_date,
        age_days:fresh.age_days,
        relation_types:relevance.relation_types,
        magnitude_basis:change.basis
      },
      ranking_semantics:'attention-priority-only'
    };
  }

  function rankAll(rows,{sources=[],rules={},referenceDate,excludeDemo=true}={}) {
    return (rows || [])
      .filter(row => !excludeDemo || sourceIds(row).some(id => id && !isDemoSource(id)))
      .map(row => rankOne(row,{sources,rules,referenceDate}))
      .sort((a,b) => {
        const byScore=Number(b.attention_score)-Number(a.attention_score);
        if (byScore) return byScore;
        const byDate=String(evidenceDate(b)).localeCompare(String(evidenceDate(a)));
        if (byDate) return byDate;
        return String(a.id || '').localeCompare(String(b.id || ''));
      });
  }

  const api={
    dateKey,
    sourceIds,
    isDemoSource,
    sourceQuality,
    freshness,
    eventSignificance,
    entityRelevance,
    magnitude,
    tierFor,
    rankOne,
    rankAll,
    evidenceDate
  };

  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  if (typeof window !== 'undefined') window.IntelligenceRanking=api;
})();
