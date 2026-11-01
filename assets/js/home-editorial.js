/* Home editorial ranking — source-backed headlines, not generic publisher recency.
 * Applies to the Home digest only; source archives and original articles stay intact.
 * Browser/CommonJS for automated headline QA.
 */
((root) => {
  'use strict';
  const DAY = 86400000;
  const normalize = value => String(value || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, ' ').trim();
  const has = (t, terms) => terms.some(w => (' '+t+' ').includes(' '+normalize(w)+' '));
  const patterns = {
    market: {
      subject:['bat dong san','nha dat','nha o','can ho','chung cu','nha pho','biet thu','dat nen',
        'khu do thi','thi truong nha','thi truong dia oc','chu dau tu bat dong san',
        'du an nha','nha o xa hoi','gia ban nha','gia ban dat','gia can ho','gia nha dat',
        'van phong cho thue','bat dong san cong nghiep','phat trien do thi',
        'izumi','aqua city','springville','nam long','novaland','vinhomes','masterise',
        'gamuda','mizuki','can tho','dong nai','long an','binh duong'],
      material:['gia ban','gia nha','gia dat','gia can ho','gia thue','giao dich','thanh khoan',
        'nguon cung','hap thu','tieu thu','mo ban','ban giao','dau tu','phat trien',
        'thi truong','chinh sach','du an','khu do thi','nha o xa hoi','quy hoach',
        'phap ly','mo rong','tai cau truc','chuyen nhuong','mua ban sap nhap','ton kho',
        'gia tang','giam gia','xu huong','doanh so','nguon von'],
      high:['gia ban','gia can ho','nguon cung','hap thu','mo ban','ban giao',
        'giao dich','ton kho','thanh khoan','chuyen nhuong','nha o xa hoi']
    },
    legal: {
      subject:['dat dai','thu hoi dat','boi thuong','tai dinh cu','quy hoach',
        'nha o','bat dong san','chung cu','so hong','so do','nha dat',
        'tien su dung dat','giay chung nhan','cap phep xay dung','dau gia dat',
        'su dung dat','gia dat','du an do thi','phat trien do thi'],
      material:['luat','nghi dinh','thong tu','quy dinh','de xuat','chinh sach',
        'quoc hoi','bo truong','thu hoi','boi thuong','ban hanh','cap so',
        'cap phep','su doi','sua doi','quy hoach','quyet dinh','thu tuc','phap ly'],
      high:['luat','nghi dinh','thong tu','ban hanh','quy dinh','quyet dinh','boi thuong','thu hoi']
    },
    infrastructure: {
      subject:['vanh dai','cao toc','metro','duong sat','san bay','duong bo',
        'cau can tho','cau dong nai','cau cat lai','cau phu my','cau rach',
        'cau','quoc lo','tuyen duong','nut giao','giao thong','duong lien vung',
        'ha tang','du an giao thong','ham chui','duong tinh','dai lo'],
      material:['du an','dau tu','khoi cong','thong xe','hoan thanh','thi cong',
        'tien do','quy hoach','phe duyet','bo tri von','giai ngan','ket noi',
        'mo rong','xay dung','thiet ke','dau thau','giai phong mat bang','nghiem thu',
        'khoi dong','du kien','tu van'],
      high:['khoi cong','thong xe','hoan thanh','tien do','phe duyet','xay dung',
        'giai ngan','ket noi','dau thau']
    },
    macro: {
      subject:['tin dung','lai suat','lai vay','ty gia','usd vnd','cpi','lam phat','gdp',
        'tang truong kinh te','tang truong tin dung','ngan hang nha nuoc','ngan hang',
        'chinh sach tien te','trai phieu','dau tu cong','von dau tu','ty le du tru',
        'gia vang','vang sjc','fed','federal reserve','pho wall','thi truong tai chinh',
        'thanh khoan','loi suat','nang suat','trai phieu doanh nghiep'],
      material:['tang','giam','cham','thay doi','dieu chinh','cong bo','thong ke',
        'du bao','chinh sach','du kien','muc','trien vong','cho','phe duyet',
        'kinh te','phat hanh','dat','tai tro','lai suat','tin dung','ty gia','gia vang','fed','cpi'],
      high:['tin dung','lai suat','cpi','lam phat','gdp','ty gia',
        'ngan hang nha nuoc','chinh sach tien te','trai phieu doanh nghiep','dau tu cong']
    }
  };
  const exclude = {
    market:['meo','noi that','trang tri','phong thuy','mau sac','bep dep','phong ngu',
      'ghe sofa','cho thue phong tro gia re','gia dung','sua nha','nha dep',
      'cat giam nhan su','giam nhan su','sa thai','tai nan','bi bat','hanh hung'],
    legal:['xo so','doc dac','lo de','giai tri','ca si','dien vien'],
    infrastructure:['tai nan','tu vong','bi can','va cham','mau thuan','xe ben can',
      'tai xe','xu phat','vi pham giao thong','chay xe','diem den','nguy hiem','keo xe'],
    macro:['showbiz','nguoi dep','trung so','xem boi','meo mua','meo tiet kiem']
  };
  const isRSS = row => row?.content_type==='publisher-rss' || String(row?.id || '').startsWith('article:');
  function topic(category,title) {
    const t=normalize(title);
    if (category==='macro') {
      if (has(t,['gia vang','vang sjc','vang hom nay','gold']))return 'gold';
      if (has(t,['fed','pho wall','federal reserve']))return 'global-rates';
      if (has(t,['tin dung','cho vay','trai phieu']))return 'credit';
      if (has(t,['lai suat','lai vay','ngan hang']))return 'interest';
      if (has(t,['ty gia','usd vnd']))return 'fx';
      if (has(t,['cpi','lam phat']))return 'inflation';
      return 'macro-general';
    }
    if (category==='market') {
      if (has(t,['gia ban','gia nha','gia dat','gia can ho','gia thue','giam gia']))return 'prices';
      if (has(t,['mo ban','nguon cung','ban giao','du an','khu do thi']))return 'projects';
      if (has(t,['giao dich','hap thu','thanh khoan','doanh so','ton kho']))return 'transactions';
      if (has(t,['nha o xa hoi']))return 'affordable';
      return 'market-general';
    }
    if (category==='infrastructure') {
      if (has(t,['san bay']))return 'airport';
      if (has(t,['metro','duong sat']))return 'rail';
      if (has(t,['cau']))return 'bridge';
      if (has(t,['cao toc','vanh dai','quoc lo']))return 'road';
      return 'transport';
    }
    if (category==='legal') {
      if (has(t,['thu hoi','boi thuong','tai dinh cu']))return 'compensation';
      if (has(t,['quy hoach']))return 'planning';
      if (has(t,['gia dat','tien su dung dat']))return 'land-finance';
      if (has(t,['so hong','so do','cap giay']))return 'titles';
      return 'legal';
    }
    return 'other';
  }
  const topicNames = {
    vi:{prices:'Giá bán',projects:'Dự án',transactions:'Giao dịch',affordable:'Nhà ở xã hội',
      'market-general':'Thị trường',compensation:'Thu hồi đất',planning:'Quy hoạch',
      'land-finance':'Tài chính đất',titles:'Sổ hồng',legal:'Chính sách',
      airport:'Hàng không',rail:'Đường sắt',bridge:'Cầu đường',road:'Đường bộ',
      transport:'Hạ tầng',credit:'Tín dụng',interest:'Lãi suất',fx:'Tỷ giá',
      inflation:'Lạm phát','global-rates':'Quốc tế',gold:'Giá vàng','macro-general':'Kinh tế'},
    en:{prices:'Pricing',projects:'Projects',transactions:'Sales',affordable:'Social housing',
      'market-general':'Property',compensation:'Land recovery',planning:'Planning',
      'land-finance':'Land costs',titles:'Land titles',legal:'Regulation',
      airport:'Airports',rail:'Rail',bridge:'Bridges',road:'Roads',
      transport:'Infrastructure',credit:'Credit',interest:'Rates',fx:'FX',
      inflation:'Inflation','global-rates':'Global',gold:'Gold','macro-general':'Economy'}
  };
  function inspect(row) {
    const title=row?.display_title||row?.title||'';
    const t=normalize(title), category=row?.category;
    if (!title || !patterns[category]) return {eligible:false,reason:'no-topic'};
    const p=patterns[category];
    const blocked=has(t,exclude[category]||[]);
    if (blocked) return {eligible:false,reason:'noise-or-lifestyle'};
    let subject=has(t,p.subject), material=has(t,p.material);
    // Historic data releases and official documents have explicit structured evidence;
    // topic cues are required only for the broad, mixed-quality publisher RSS feeds.
    if (!isRSS(row)) {
      const tp=topic(category,title);
      return {eligible:true,score:62+Math.min(15,Number(row.attention_score||0)/10),
        topic:tp,reason:'structured-evidence'};
    }
    // Categorization from a broad publisher feed is not evidence that a
    // headline is about property/investment. Ignore a project name alone.
    if (category==='market' && !subject) return {eligible:false,reason:'not-property-market'};
    if (category==='market' && !material)return {eligible:false,reason:'no-market-signal'};
    if ((category==='legal'||category==='infrastructure') && (!subject||!material))
      return {eligible:false,reason:'not-material-to-sector'};
    if (category==='macro' && !subject)return {eligible:false,reason:'not-economic-signal'};
    const tp=topic(category,title);
    let score=50 + (subject?14:0)+(material?10:0)+(has(t,p.high)?14:0);
    if (category==='market' && has(t,['nam long','izumi','aqua city','springville',
      'can tho','dong nai','binh duong','long an']))score+=8;
    if (category==='macro' && tp==='gold')score-=22;
    if (category==='macro' && tp==='global-rates')score-=12;
    if (category==='infrastructure' && tp==='airport' && has(t,['nhan su','cong nhan']))score-=24;
    return {eligible:score>=58,score,topic:tp,reason:'editorial-qualification'};
  }
  function dayAge(row,referenceDate) {
    const raw=row?.ranking_evidence?.evidence_date||row?.date||row?.published_at||'';
    const d=String(raw).slice(0,10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d))return null;
    const age=Math.floor((Date.parse(referenceDate+'T00:00:00Z')-Date.parse(d+'T00:00:00Z'))/DAY);
    return age>=0?age:null;
  }
  function curated(rows,referenceDate,{max=3,minWindow=7,extendedWindow=30}={}) {
    const eligible=(rows||[]).map(row=>({...inspect(row),row,age:dayAge(row,referenceDate)}))
      .filter(x=>x.eligible && x.age!==null && x.age<=extendedWindow);
    const sort=(a,b)=>b.score-a.score || a.age-b.age ||
      Number(b.row.attention_score||0)-Number(a.row.attention_score||0) ||
      String(a.row.id||'').localeCompare(String(b.row.id||''));
    const candidates=[eligible.filter(x=>x.age<minWindow).sort(sort),
      eligible.filter(x=>x.age>=minWindow).sort(sort)];
    const seen=new Set(),topics=new Map(),selected=[];
    const normTitle=x=>normalize(x.row.display_title||x.row.title).split(' ').slice(0,11).join(' ');
    // First pass: maximize distinct topics. Second pass: allow two per topic,
    // except repetitive gold-price headlines, always capped at one.
    for(const maxTopic of [1,2]) {
      for(const group of candidates) {
        for(const x of group) {
          const sig=normTitle(x); if(!sig || seen.has(sig))continue;
          const cap=x.topic==='gold'?1:maxTopic;
          if((topics.get(x.topic)||0)>=cap)continue;
          if(selected.includes(x))continue;
          selected.push(x);seen.add(sig);topics.set(x.topic,(topics.get(x.topic)||0)+1);
          if(selected.length>=max)return selected;
        }
      }
    }
    return selected;
  }
  function label(topicId,lang='vi') {
    const l=lang==='en'?'en':'vi';return topicNames[l][topicId]||topicId||'';
  }
  const api={normalize,inspect,curated,label,topic};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.HomeEditorial=api;
})(typeof window!=='undefined' ? window : globalThis);
