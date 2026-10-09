/* Chart correctness: project price intervals must not be connected by lines. */
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('assets/js/charts.js','utf8');
let last;
const globals={
  Map,window:{Formatters:{aspVndPerSqm:(v)=>String(v/1e6)+' triệu VND/m²'}},
  document:{getElementById:(id)=>id==='market-pricing'?{id}:null},
  Chart:class {constructor(canvas,config){this.canvas=canvas;this.config=config;last=this}destroy(){}}
};
vm.runInNewContext(code,globals);
const ChartTools=globals.window.ChartTools;
const chart=ChartTools.renderRangeSeries('market-pricing',{
  labels:['Waterpoint · Thấp tầng','Akari City · Căn hộ'],
  lowValues:[38_200_000,54_100_000],
  highValues:[60_200_000,64_700_000],
  lowLabel:'Giá thấp',highLabel:'Giá cao',yFormatter:v=>String(v/1e6)+' triệu'
});
if(!chart || last.config.type!=='bar') throw Error('Project chart must be categorical bars, not a line');
if(last.config.data.datasets.length!==1)throw Error('Project chart must use single interval dataset');
const dataset=last.config.data.datasets[0];
if(dataset.data.length!==2)throw Error('Expected independent project intervals');
if(dataset.data[0][0]!==38_200_000||dataset.data[0][1]!==60_200_000)throw Error('Incorrect first interval');
if(dataset.data[1][0]!==54_100_000||dataset.data[1][1]!==64_700_000)throw Error('Incorrect second interval');
if(last.config.options.plugins.tooltip.callbacks.label({raw:[38_200_000,60_200_000]}).indexOf('Giá thấp')<0)throw Error('Tooltip must show range');
if(!last.config.options.plugins.legend||last.config.options.plugins.legend.display!==false)throw Error('Unnecessary two-series legend');
const market=fs.readFileSync('assets/js/market.js','utf8');
if(!market.includes("item.row.asset_type === 'apartment'")||!market.includes('Không nối thành xu hướng thời gian'))throw Error('Missing chart-scope explanation');
const history=fs.readFileSync('data/mock/market/alternative-monthly-history.json','utf8');
if(JSON.parse(history).record_count!==1)throw Error('Unreviewed history points must not be fabricated');
console.log('PASS: independent category price interval bars; no inter-project trend implied, single reviewed monthly baseline.');
