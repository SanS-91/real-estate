((global) => {
  'use strict';

  const unique = values => [...new Set((values || []).filter(Boolean))];
  const intersects = (a,b) => {
    const s=new Set(a || []);
    return (b || []).some(x => s.has(x));
  };

  function periodEnd(value) {
    if (!value) return null;
    const s=String(value).slice(0,10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    let m=String(value).match(/^(\d{4})-Q([1-4])$/);
    if (m) {
      const y=Number(m[1]), q=Number(m[2]);
      return [`${y}-03-31`,`${y}-06-30`,`${y}-09-30`,`${y}-12-31`][q-1];
    }
    m=String(value).match(/^(\d{4})-(\d{2})$/);
    if (m) {
      const y=Number(m[1]), mo=Number(m[2]);
      const day=new Date(Date.UTC(y,mo,0)).getUTCDate();
      return `${y}-${String(mo).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    }
    if (/^\d{4}$/.test(String(value))) return `${value}-12-31`;
    return null;
  }

  function evidenceDate(row, kind) {
    const fields={
      article:['published_at'],
      event:['event_date'],
      market:['source_date','period'],
      listing:['observation_date'],
      legal:['issued_date','effective_date'],
      infrastructureSchedule:['announced_date','target_period'],
      macro:['data_date','period','published_at']
    }[kind] || [];
    for (const field of fields) {
      const d=periodEnd(row?.[field]);
      if (d) return d;
    }
    return null;
  }

  function inWindow(row, kind, window={}) {
    const from=periodEnd(window.from);
    const to=periodEnd(window.to);
    if (!from && !to) return true;
    const d=evidenceDate(row,kind);
    if (!d) return false;
    if (from && d<from) return false;
    if (to && d>to) return false;
    return true;
  }

  function projectDevelopers(project) {
    return unique([...(project?.developer_ids || []), project?.lead_developer_id]);
  }

  function contextFor(data, type, id) {
    const projects=data.projects || [];
    const regions=data.regions || [];
    const developers=data.developers || [];
    const infrastructure=data.infrastructure || [];
    let subject=null, scopedProjects=[], regionIds=[], developerIds=[];

    if (type==='project') {
      subject=projects.find(x=>x.id===id) || null;
      if (!subject) return null;
      scopedProjects=[subject];
      regionIds=subject.region_ids || [];
      developerIds=projectDevelopers(subject);
    } else if (type==='region') {
      subject=regions.find(x=>x.id===id) || null;
      if (!subject) return null;
      regionIds=[id];
      scopedProjects=projects.filter(x=>(x.region_ids || []).includes(id));
      developerIds=unique(scopedProjects.flatMap(projectDevelopers));
    } else if (type==='developer') {
      subject=developers.find(x=>x.id===id) || null;
      if (!subject) return null;
      developerIds=[id];
      scopedProjects=projects.filter(x=>(x.developer_ids || []).includes(id) || x.lead_developer_id===id);
      regionIds=unique([...(subject.region_ids || []), ...scopedProjects.flatMap(x=>x.region_ids || [])]);
    } else {
      return null;
    }

    const projectIds=scopedProjects.map(x=>x.id);
    const legalTopicIds=unique(scopedProjects.flatMap(x=>x.related_legal_topic_ids || []));
    const projectInfraIds=unique(scopedProjects.flatMap(x=>x.related_infrastructure_ids || []));
    const reverseInfraIds=infrastructure
      .filter(x=>(x.related_real_estate_project_ids || []).some(pid=>projectIds.includes(pid)))
      .map(x=>x.id);
    const regionInfraIds=type==='region'
      ? infrastructure.filter(x=>intersects(x.region_ids,regionIds)).map(x=>x.id)
      : [];
    const infrastructureIds=unique([...projectInfraIds,...reverseInfraIds,...regionInfraIds]);

    return {
      type,id,subject,
      projectIds,regionIds,developerIds,legalTopicIds,infrastructureIds,
      projects:scopedProjects,
      relation_semantics:{
        legal:'topic-relevance',
        infrastructure:type==='region' ? 'direct-and-region-context' : 'direct-project-link',
        macro:'contextual-only'
      }
    };
  }

  function buildEvidence(data, ctx, window={}, options={}) {
    if (!ctx) return null;
    const infraIds=ctx.infrastructureIds;
    const directMarket=(data.marketObservations || [])
      .filter(x=>x.project_id && ctx.projectIds.includes(x.project_id))
      .filter(x=>inWindow(x,'market',window));
    const contextualMarket=(data.marketObservations || [])
      .filter(x=>!x.project_id && intersects(x.region_ids,ctx.regionIds))
      .filter(x=>inWindow(x,'market',window));
    const listing=(data.listingObservations || [])
      .filter(x=>ctx.projectIds.includes(x.project_id))
      .filter(x=>inWindow(x,'listing',window));
    const legal=(data.legal || [])
      .filter(x=>intersects(x.topic_ids,ctx.legalTopicIds))
      .filter(x=>inWindow(x,'legal',window));
    const infra=(data.infrastructure || []).filter(x=>infraIds.includes(x.id));
    const infraSchedules=(data.infrastructureSchedules || [])
      .filter(x=>infraIds.includes(x.infrastructure_project_id))
      .filter(x=>inWindow(x,'infrastructureSchedule',window));
    const articles=(data.articles || [])
      .filter(x=>
        intersects(x.project_ids,ctx.projectIds) ||
        intersects(x.developer_ids,ctx.developerIds) ||
        intersects(x.region_ids,ctx.regionIds) ||
        intersects(x.infrastructure_project_ids,infraIds))
      .filter(x=>inWindow(x,'article',window));
    const events=(data.events || [])
      .filter(x=>
        (x.entity_type==='real-estate-project' && ctx.projectIds.includes(x.entity_id)) ||
        (x.entity_type==='infrastructure-project' && infraIds.includes(x.entity_id)) ||
        intersects(x.region_ids,ctx.regionIds))
      .filter(x=>inWindow(x,'event',window));

    const allowedMacro=new Set(options.macroIndicatorIds || []);
    const macro=options.includeMacroContext
      ? (data.macroRows || [])
          .filter(x=>!allowedMacro.size || allowedMacro.has(x.indicator_id))
          .filter(x=>inWindow(x,'macro',window))
      : [];

    return {
      subject:{ type:ctx.type,id:ctx.id },
      window:{ from:window.from || null,to:window.to || null },
      relations:{
        projectIds:ctx.projectIds,
        regionIds:ctx.regionIds,
        developerIds:ctx.developerIds,
        legalTopicIds:ctx.legalTopicIds,
        infrastructureIds:ctx.infrastructureIds
      },
      direct:{
        projects:ctx.projects,
        marketObservations:directMarket,
        listingObservations:listing,
        infrastructure:infra,
        infrastructureSchedules:infraSchedules,
        articles,
        events
      },
      contextual:{
        regionalMarketObservations:contextualMarket,
        legalDocuments:legal,
        macroObservations:macro
      },
      semantics:ctx.relation_semantics
    };
  }

  function query(data, request={}) {
    const ctx=contextFor(data,request.type,request.id);
    if (!ctx) return null;
    return buildEvidence(data,ctx,{from:request.from,to:request.to},{
      includeMacroContext:Boolean(request.includeMacroContext),
      macroIndicatorIds:request.macroIndicatorIds || []
    });
  }

  const api={ unique, periodEnd, evidenceDate, inWindow, contextFor, buildEvidence, query };
  global.IntelligenceContext=api;
  if (typeof module!=='undefined' && module.exports) module.exports=api;
})(typeof window!=='undefined' ? window : globalThis);
