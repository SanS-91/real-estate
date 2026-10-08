((global) => {
  'use strict';

  function safeConfig(config={}) {
    const forbidden=['api_key','apikey','token','secret','authorization','password'];
    const text=JSON.stringify(config).toLowerCase();
    const found=forbidden.filter(key=>text.includes('"'+key+'"'));
    if(found.length) throw new Error('Unsafe AI config: browser secrets are not allowed');
    return config;
  }

  function canRunRemote(config={}) {
    safeConfig(config);
    if(!config.enabled || !config.external_requests || !config.endpoint) return false;
    try {
      const url=new URL(config.endpoint,global.location?.href || 'https://local.invalid/');
      if(config.same_origin_only!==false && global.location?.origin && url.origin!==global.location.origin) return false;
      return true;
    } catch (_) {
      return false;
    }
  }

  function status(config={}) {
    const cfg=safeConfig(config);
    if(canRunRemote(cfg)) return {mode:'remote',label:'AI available'};
    if(cfg.enabled) return {mode:'context-only',label:'AI context-only'};
    return {mode:'off',label:'AI off'};
  }

  async function run({config,pack,prompt}={}) {
    if(!canRunRemote(config)) {
      return {
        executed:false,
        mode:status(config).mode,
        reason:'Remote AI analysis is disabled. No network request was sent.',
        pack,
        prompt
      };
    }
    const endpoint=new URL(config.endpoint,global.location.href).toString();
    const response=await fetch(endpoint,{
      method:'POST',
      credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        schema_version:1,
        action:pack?.action || 'summarize',
        question:pack?.question || null,
        context:pack,
        prompt
      })
    });
    if(!response.ok) throw new Error('AI analysis endpoint failed ('+response.status+')');
    const payload=await response.json();
    return {executed:true,mode:'remote',payload};
  }

  const api={safeConfig,canRunRemote,status,run};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  global.OptionalAIAnalysis=api;
})(typeof window!=='undefined' ? window : globalThis);
