((global) => {
  'use strict';

  const isRealSource = id => Boolean(id) && !String(id).startsWith('demo-');
  const compact = (rows, limit) => (rows || []).slice(0, limit);

  function sourceFields(row) {
    const ids=[row?.source_id,...(row?.source_ids || [])].filter(isRealSource);
    return {
      source_ids:[...new Set(ids)],
      source_url:row?.source_url || row?.official_url || null,
      source_date:row?.source_date || row?.published_at || row?.issued_date || row?.announced_date || row?.event_date || null
    };
  }

  function cleanValue(value) {
    if (value === undefined) return null;
    if (Array.isArray(value)) return value.map(cleanValue);
    if (value && typeof value === 'object') {
      const out={};
      Object.entries(value).forEach(([k,v]) => {
        if (v !== undefined && v !== null && v !== '') out[k]=cleanValue(v);
      });
      return out;
    }
    return value;
  }

  function marketRows(ctx, limit) {
    return compact(ctx.marketObservations,limit).map(row=>cleanValue({
      id:row.id,period:row.period,
      average_asp:row.average_asp,asp_unit:row.asp_unit,
      sales_units:row.sales_units,new_supply:row.new_supply,
      absorption_rate:row.absorption_rate,price_basis:row.price_basis,
      methodology_note:row.methodology_note,...sourceFields(row)
    }));
  }

  function listingRows(ctx, limit) {
    return compact(ctx.listingObservations,limit).map(row=>cleanValue({
      id:row.id,observation_date:row.observation_date,asset_type:row.asset_type,
      asking_price_low_vnd_per_m2:row.asking_price_low_vnd_per_m2,
      asking_price_high_vnd_per_m2:row.asking_price_high_vnd_per_m2,
      asking_price_change_1y_pct:row.asking_price_change_1y_pct,
      coverage_status:row.coverage_status,market_layer:row.market_layer,
      methodology_note:row.methodology_note,...sourceFields(row)
    }));
  }

  function legalRows(ctx, limit) {
    return compact(ctx.legalDocuments,limit).map(row=>cleanValue({
      id:row.id,document_number:row.document_number,title:row.title,status:row.status,
      issued_date:row.issued_date,effective_date:row.effective_date,
      topic_ids:row.topic_ids,summary:row.summary,key_changes:row.key_changes,
      source_id:row.primary_source_id,source_url:row.official_url
    }));
  }

  function infrastructureRows(ctx, limit) {
    return compact(ctx.infrastructure,limit).map(row=>cleanValue({
      id:row.id,name:row.name,status:row.status,location_text:row.location_text,
      current_total_investment:row.current_total_investment,
      investment_unit:row.investment_unit,current_expected_completion:row.current_expected_completion,
      current_progress_percent:row.current_progress_percent,
      current_progress_note:row.current_progress_note,
      region_ids:row.region_ids,related_real_estate_project_ids:row.related_real_estate_project_ids
    }));
  }

  function scheduleRows(ctx, limit) {
    return compact(ctx.infrastructureSchedules,limit).map(row=>cleanValue({
      id:row.id,infrastructure_project_id:row.infrastructure_project_id,
      schedule_type:row.schedule_type,target_period:row.target_period,status:row.status,
      announced_date:row.announced_date,...sourceFields(row)
    }));
  }

  function articleRows(ctx, limit) {
    return compact(ctx.articles,limit)
      .filter(row=>isRealSource(row.source_id))
      .map(row=>cleanValue({
        id:row.id,title:row.title,category:row.category,content_type:row.content_type,
        published_at:row.published_at,summary:row.summary,
        project_ids:row.project_ids,developer_ids:row.developer_ids,region_ids:row.region_ids,
        ...sourceFields(row)
      }));
  }

  function eventRows(ctx, limit) {
    return compact(ctx.events,limit)
      .filter(row=>(row.source_ids || []).some(isRealSource))
      .map(row=>cleanValue({
        id:row.id,category:row.category,event_type:row.event_type,event_date:row.event_date,
        title:row.title,summary:row.summary,entity_type:row.entity_type,entity_id:row.entity_id,
        region_ids:row.region_ids,importance:row.importance,...sourceFields(row)
      }));
  }

  function macroRows(ctx, limit) {
    return compact(ctx.macroContext,limit)
      .filter(row=>isRealSource(row.source_id))
      .map(row=>cleanValue({
        id:row.id,indicator_id:row.indicator_id,period:row.period,data_date:row.data_date,
        value:row.value,unit:row.unit,evidence_status:row.evidence_status,
        observation_status:row.observation_status,...sourceFields(row)
      }));
  }

  function subjectBlock(ctx, type) {
    return {
      type,
      id:ctx.subject?.id || null,
      label:ctx.subject?.name || ctx.subject?.title || ctx.subject?.id || null,
      summary:ctx.subject?.summary || ctx.subject?.description || null,
      related_project_ids:ctx.projectIds || [],
      region_ids:ctx.regionIds || [],
      developer_ids:ctx.developerIds || [],
      legal_topic_ids:ctx.legalTopicIds || [],
      infrastructure_ids:(ctx.infrastructure || []).map(x=>x.id)
    };
  }

  function buildContextPack(contexts, {type='project', action='summarize', question='', maxItems=12}={}) {
    const rows=(contexts || []).filter(Boolean);
    return cleanValue({
      schema_version:1,
      purpose:'optional-ai-analysis-context',
      action,
      question:question || null,
      constraints:{
        canonical_data_only:true,
        no_missing_value_inference:true,
        legal_relevance_is_not_applicability:true,
        listing_asking_is_separate_from_verified_pricing:true,
        no_production_mutation:true
      },
      subjects:rows.map(ctx=>subjectBlock(ctx,type)),
      evidence:rows.map(ctx=>({
        subject_id:ctx.subject?.id || null,
        direct:{
          verified_market:marketRows(ctx,maxItems),
          listing_asking:listingRows(ctx,maxItems),
          infrastructure:infrastructureRows(ctx,maxItems),
          infrastructure_schedules:scheduleRows(ctx,maxItems),
          articles:articleRows(ctx,maxItems),
          events:eventRows(ctx,maxItems)
        },
        contextual:{
          legal_documents:legalRows(ctx,maxItems),
          macro_observations:macroRows(ctx,maxItems)
        },
        relationship_semantics:ctx.semantics || {}
      }))
    });
  }

  const INSTRUCTIONS=[
    'Use only the supplied canonical evidence. Do not introduce unstated facts.',
    'Distinguish direct evidence from contextual relevance.',
    'Keep listing asking prices separate from verified/research project pricing.',
    'Do not infer missing values.',
    'For Legal evidence, relevance does not establish legal applicability; state this explicitly when relevant.',
    'Identify source IDs and source URLs for material factual claims when present.',
    'If sources disagree, describe the disagreement rather than averaging or selecting silently.',
    'Do not modify or propose modifications to canonical data.'
  ];

  function actionInstruction(action,question) {
    if(action==='compare') return 'Compare the selected subjects using like-for-like evidence only. Call out missing/non-comparable fields.';
    if(action==='explain-legal-context') return 'Explain the legal context surfaced for the subject. Do not state that a rule applies to a specific project unless the supplied evidence establishes applicability.';
    if(action==='weekly-brief') return 'Create a concise monitoring brief focused on material source-backed developments and changes.';
    if(action==='ask-database') return 'Answer this question from the supplied evidence only: '+String(question || '').trim();
    return 'Summarize the selected subject(s), prioritizing material Market, Legal, Infrastructure and Macro evidence.';
  }

  function buildPrompt(pack) {
    const action=pack?.action || 'summarize';
    const question=pack?.question || '';
    return [
      'You are analyzing a normalized Vietnam real-estate intelligence context pack.',
      actionInstruction(action,question),
      '',
      'Rules:',
      ...INSTRUCTIONS.map(x=>'- '+x),
      '',
      'Context JSON:',
      JSON.stringify(pack,null,2)
    ].join('\n');
  }

  const api={buildContextPack,buildPrompt,actionInstruction,cleanValue,isRealSource};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  global.AnalysisContextPack=api;
})(typeof window!=='undefined' ? window : globalThis);
