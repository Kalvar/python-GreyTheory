'use strict';
let pendingRequest=null,lastSource=null;
const desktopMode=window.GREY_DESKTOP===true||location.hash==='#desktop';
const same=(a,b)=>JSON.stringify(ordered(a))===JSON.stringify(ordered(b));
function ordered(v){if(Array.isArray(v))return v.map(ordered);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])]));return v;}
async function nativeReady(){if(typeof window.pywebview?.api?.config==='function')return;await new Promise(resolve=>window.addEventListener('pywebviewready',resolve,{once:true}));}
async function workbenchConfig(){if(desktopMode){await nativeReady();const value=await window.pywebview.api.config();value.mode='desktop';return value;}return structuredClone(window.GREY_PREVIEW.config);}
async function workbenchCall(endpoint,body){
  if(endpoint==='/api/load')lastSource=structuredClone(body);
  if(desktopMode){await nativeReady();return window.pywebview.api.request(endpoint,body);}
  const data=window.GREY_PREVIEW;
  if(endpoint==='/api/load'&&data.datasets[body.id]&&!body.upload)return structuredClone(data.datasets[body.id]);
  if(endpoint==='/api/analyze'){
    const d=Object.values(data.datasets).find(d=>d.id===body.dataset),g=body.gra_params||{};
    if(d&&body.method==='pca'&&(body.engine||'pca')==='pca'&&body.components===2&&!body.component_top_k&&body.normalize_counts!==false&&same(body.features,d.defaults)&&body.target===(d.targets[0]||'')&&same(body.method_params||{},{})&&(g.rho??.5)===.5&&(g.normalization??'zscore')==='zscore'&&(g.direction??'either')==='either')return structuredClone(data.analysis[d.id]);
  }
  if(endpoint==='/api/scenario'){
    const value=data.scenarios[body.scenario==='research'?'research_'+body.parameters.tool+(body.parameters.pca_mode==='on'?'_pca':''):body.scenario==='art'&&body.parameters.art_source==='ai_images'?'art_images':body.scenario];if(value&&same(body.parameters,value.parameters)&&same(body.method_params||{},{})&&!body.series)return structuredClone(value);
  }
  if(endpoint==='/api/handwriting'&&body.demo&&body.method==='pca'&&same(body.method_params||{},{}))return structuredClone(data.handwriting);
  pendingRequest={format:'greytheory-request-v1',endpoint,body:structuredClone(body),source:lastSource};
  document.getElementById('exportRequest').disabled=false;
  throw new Error('目前為 HTML 預覽：此設定需要 Python 運算。請用 python3 run.py workbench 開本機視窗；或匯出請求，執行後匯入結果。');
}
window.addEventListener('DOMContentLoaded',()=>{
 document.getElementById('exportRequest').onclick=()=>{if(pendingRequest)downloadJson(pendingRequest,'greytheory-request.json');};
 document.getElementById('importResult').onchange=async event=>{try{const file=event.target.files[0];if(!file)return;const value=JSON.parse(await file.text());if(value.format!=='greytheory-result-v1')throw new Error('請選擇 Python 產生的 .result.json。');if(value.source)lastSource=value.source;
  if(value.dataset)displayDataset(value.dataset);
  if(value.endpoint==='/api/analyze'){result=value.result;$('target').value=result.target||'';renderFeatures();drawScatter();drawRanking();$('warnings').textContent=result.warnings.join(' ');$('coverage').textContent=result.variance?(100*result.variance.reduce((a,b)=>a+b,0)).toFixed(1)+'%':'不提供';$('download').disabled=false;}
  else if(value.endpoint==='/api/scenario'){$('scenario').value=value.result.scenario;sceneChanged();for(const [key,v] of Object.entries(value.result.parameters)){const input=$('scenarioParams').querySelector(`[data-key="${key}"]`);if(input)input.value=v;}displayScenario(value.result);document.querySelector('[data-tab="lab"]').click();}
  else if(value.endpoint==='/api/handwriting'){displayImages(value.result);document.querySelector('[data-tab="images"]').click();}
  status('已匯入 Python 實際計算結果。');
 }catch(error){status(error.message,'error');}};
});
