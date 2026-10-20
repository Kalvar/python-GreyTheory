'use strict';
const $ = id => document.getElementById(id);
let config, dataset, result, running = false;
const colors = ['#67e8c0','#7ab8ff','#f3bc72','#c7a1ff','#f48ca8','#90c9e8','#b6dc88','#e5a7df','#82d6d1'];
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function status(message, state='') { $('status').textContent = message; $('status').className = state; }
function svgEl(tag, attributes={}) { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); Object.entries(attributes).forEach(([k,v]) => node.setAttribute(k,v)); return node; }
function textAt(svg, x, y, text, extra={}) { const n=svgEl('text',{x,y,...extra}); n.textContent=text; svg.append(n); }
function range(values) { let lo=Infinity,hi=-Infinity; for (const v of values) {lo=Math.min(lo,v);hi=Math.max(hi,v);} if (hi===lo) return [lo-1,hi+1]; const p=(hi-lo)*.08; return [lo-p,hi+p]; }
function chartFrame(id, xs, ys, xName, yName, signal=false) {
  const box=$(id); box.replaceChildren(); box.classList.remove('placeholder');
  const W=480,H=280,p={l:52,r:18,t:18,b:42}, xr=range(xs),yr=range(ys);
  if(signal){xr[0]=Math.min(...xs);xr[1]=Math.max(...xs);if(xr[0]===xr[1])xr[1]+=1;yr[0]=0;yr[1]=Math.max(1,...ys)*1.08;}
  const x=v=>p.l+(v-xr[0])/(xr[1]-xr[0])*(W-p.l-p.r), y=v=>H-p.b-(v-yr[0])/(yr[1]-yr[0])*(H-p.t-p.b);
  const svg=svgEl('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':`${xName} / ${yName}`});
  for(let i=0;i<5;i++) { const xx=p.l+i*(W-p.l-p.r)/4,yy=p.t+i*(H-p.t-p.b)/4;
    svg.append(svgEl('line',{x1:xx,x2:xx,y1:p.t,y2:H-p.b,class:'axis',opacity:.35}));
    svg.append(svgEl('line',{x1:p.l,x2:W-p.r,y1:yy,y2:yy,class:'axis',opacity:.35}));
    textAt(svg,xx,H-p.b+18,(xr[0]+i*(xr[1]-xr[0])/4).toPrecision(3),{'text-anchor':'middle'});
    textAt(svg,p.l-8,yy+3,(yr[1]-i*(yr[1]-yr[0])/4).toPrecision(3),{'text-anchor':'end'});
  }
  textAt(svg,W/2,H-3,xName,{'text-anchor':'middle'}); textAt(svg,p.l,11,yName);
  box.append(svg); return {svg,x,y};
}
function drawSignal() {
  const s=dataset.spectrum; $('signalPanel').hidden=!s; $('mapChart').replaceChildren(); if(!s) return;
  const ys=[...s.mean,...s.traces.flat()]; const {svg,x,y}=chartFrame('spectrumChart',s.x,ys,s.unit,'Counts',true);
  function line(values, cls, color) {const path=svgEl('path',{d:values.map((v,i)=>`${i?'L':'M'}${x(s.x[i]).toFixed(2)},${y(v).toFixed(2)}`).join(' '),class:cls}); if(color)path.setAttribute('stroke',color); svg.append(path);}
  s.traces.forEach((v,i)=>line(v,'signal',colors[i%colors.length])); line(s.mean,'mean');
  if(dataset.positions.length) { const map=el('div',undefined,'map'),lo=Math.min(...s.totals),hi=Math.max(...s.totals);
    dataset.positions.forEach((position,i)=>{const cell=el('div',`${position.join(',')} · ${s.totals[i].toLocaleString()}`,'map-cell');cell.style.background=`hsl(175 45% ${17+24*(s.totals[i]-lo)/Math.max(1,hi-lo)}%)`;map.append(cell);});
    $('mapChart').append(el('p','位置 y,x · 原始總計數（不是濃度）','hint'),map);
  }
}
function drawScatter() {
  const xs=result.coordinates.map(r=>r[0]),ys=result.coordinates.map(r=>r[1]??0);
  const axes=result.coordinate_labels||['PC1','PC2'];const {svg,x,y}=chartFrame('scatter',xs,ys,axes[0],result.components>1?(axes[1]||'第二欄'):'0（僅一維）');
  const target=$('target').value,values=target?dataset.values.map(row=>row[dataset.columns.indexOf(target)]):[],bounds=values.length?range(values):null;
  xs.forEach((v,i)=>{const shade=bounds?(values[i]-bounds[0])/(bounds[1]-bounds[0]):.5;const circle=svgEl('circle',{cx:x(v),cy:y(ys[i]),r:5.5,fill:`hsl(${205-shade*55} 70% ${55+shade*15}%)`,tabindex:0});circle.style.animationDelay=`${Math.min(i*12,350)}ms`;const title=svgEl('title');title.textContent=`${dataset.labels[i]} · PC1 ${v.toPrecision(4)} · PC2 ${ys[i].toPrecision(4)}${target?' · '+target+' '+values[i]:''}`;circle.append(title);svg.append(circle);});
  $('projectionNote').textContent=result.coordinate_labels?`圖軸：${result.coordinate_labels.join(' / ')}；此方法未做 PCA。`:target?`點色依 ${target} 變化；這是同批資料的投影，沒有做預測驗證。`:'點越近，代表在這組主成分中越相似；圖軸正負不代表品質好壞。';
}
function drawRanking() {
  $('ranking').replaceChildren();$('ranking').classList.remove('placeholder');$('rankingLabel').textContent=result.ranking_label;
  result.ranking.forEach((row,i)=>{const line=el('div',undefined,'rank-row'),content=el('div'),bar=el('div',undefined,'rank-bar'),fill=el('i');fill.style.width=`${Math.max(0,Math.min(1,row.score))*100}%`;fill.style.animationDelay=`${Math.min(i*18,400)}ms`;bar.append(fill);content.append(el('span',row.feature,'rank-name'),bar);line.append(el('span',String(i+1).padStart(2,'0'),'rank-no'),content,el('span',row.score.toFixed(3),'rank-score'));$('ranking').append(line);});
}
function renderFeatures() {
  $('features').replaceChildren();const target=$('target').value;
  dataset.columns.forEach(name=>{if(name===target)return;const label=el('label',undefined,'check'),check=el('input');check.type='checkbox';check.value=name;check.checked=(dataset.defaults||dataset.columns).includes(name);check.addEventListener('change',()=>{countFeatures();invalidate();});label.append(check,document.createTextNode(name));$('features').append(label);});countFeatures();
}
function selectedFeatures(){return [...$('features').querySelectorAll('input:checked')].map(n=>n.value);}
function invalidate() {if(!result)return;result=null;$('download').disabled=true;$('selectTop').disabled=true;$('coverage').textContent='—';for(const id of ['scatter','ranking']){$(id).replaceChildren(document.createTextNode('設定已變更，請重新執行分析。'));$(id).classList.add('placeholder');}status('設定已變更，請重新執行分析。');}
function countFeatures(){$('featureCount').textContent=`${selectedFeatures().length} 欄`;}
function preview() {
  const table=el('table'),head=el('tr');['樣本',...dataset.columns].forEach(c=>head.append(el('th',c)));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');dataset.values.slice(0,15).forEach((row,i)=>{const tr=el('tr');tr.append(el('td',dataset.labels[i]));row.forEach(v=>tr.append(el('td',Number(v).toLocaleString(undefined,{maximumFractionDigits:4}))));body.append(tr);});table.append(body);$('preview').replaceChildren(table);
}
function displayDataset(data) {
  const analysis=data.kind==='spectrum'?'多位置分析':'多樣本分析';
  const unit=data.kind==='spectrum'?'個位置':'筆資料';
  const description=data.kind==='spectrum'&&data.rows===1?'單筆光譜':`${data.rows} ${unit}`;
  $('analysisCapability').textContent=`${description} → ${analysis} ${data.rows>=3?'✓':'✗'}${data.rows<3?'（至少需要 3 '+unit+'；目前仍可看光譜或資料表）':''}`;
  dataset=data;result=null;$('orderedRows').checked=false;$('dataName').textContent=data.name;$('rows').textContent=data.rows.toLocaleString();$('cols').textContent=data.columns.length;$('coverage').textContent='—';$('dataNote').textContent=data.note+(data.excluded.length?` 排除的非數值／缺值欄：${data.excluded.join(', ')}。`:'');
  $('target').replaceChildren(el('option','不指定目標 · 看資料差異'));$('target').firstChild.value='';
  data.columns.forEach(name=>{const option=el('option',name);option.value=name;$('target').append(option);});
  $('target').value=data.targets[0]||'';$('normalize').disabled=data.kind!=='spectrum';$('analyze').disabled=data.rows<3;$('download').disabled=true;$('selectTop').disabled=true;
  $('components').max=Math.min(8,data.rows-1,data.columns.length);$('components').value=Math.max(1,Math.min(2,data.rows-1,data.defaults.length));
  for(const id of ['scatter','ranking']){$(id).classList.add('placeholder');$(id).replaceChildren(document.createTextNode(data.rows<3?'單筆光譜可看圖；需至少 3 筆資料才能分析。':'按「執行分析」顯示結果。'));}
  $('warnings').textContent='尚未執行分析。';renderFeatures();if(config.engines)engineChanged();preview();drawSignal();
}
async function request(path,body) {
  return workbenchCall(path,body);
}
async function task(message,fn) {
  if(running)return;running=true;status(message,'busy');document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{await fn();status(config.mode==='preview'?'已顯示 Python 預先計算的展示結果；變更參數請使用本機視窗或匯出運算請求。':'完成。可以調整參數再運算。');}catch(error){status(error.message,'error');}
  finally{running=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);$('analyze').disabled=!dataset||dataset.rows<3;$('download').disabled=!result;$('selectTop').disabled=!result||(result.ranking_type&&result.ranking_type!=='features');$('scenarioDownload').disabled=!scenarioResult;$('exportRequest').disabled=!pendingRequest;}
}
function fileObject(file,limit=32*1024*1024) {return new Promise((resolve,reject)=>{if(!file)return reject(new Error('請先選擇檔案。'));if(file.size>limit)return reject(new Error('檔案過大。'));const reader=new FileReader();reader.onload=()=>resolve({name:file.name,data:reader.result.split(',')[1]});reader.onerror=()=>reject(new Error('讀取檔案失敗'));reader.readAsDataURL(file);});}
function loadOptions(){return {id:$('dataset').value,detector:Number($('detector').value),spectrum_index:Number($('spectrumIndex').value)};}
async function loadSelectedData(options) {
  try { displayDataset(await request('/api/load',options)); }
  catch (error) {
    const retained=dataset?`畫面仍顯示先前的「${dataset.name}」，不是這次選取的檔案。`:'尚未載入資料。';
    throw new Error(`載入失敗：${error.message} ${retained}`);
  }
}
$('load').onclick=()=>task('正在讀取資料…',()=>loadSelectedData(loadOptions()));
$('file').onchange=async()=>{const file=$('file').files[0];if(!file)return;await task('正在讀取你選擇的檔案…',async()=>loadSelectedData({...loadOptions(),id:'',upload:await fileObject(file)}));$('file').value='';};
$('target').onchange=()=>{if(dataset){renderFeatures();invalidate();status('目標已變更，請重新執行分析。');}};
$('all').onclick=()=>{invalidate();$('features').querySelectorAll('input').forEach(n=>n.checked=true);countFeatures();if($('engine').value==='quality')qualityForm();};
$('defaults').onclick=()=>{invalidate();renderFeatures();if($('engine').value==='quality')qualityForm();};
for(const id of ['method','components','normalize'])$(id).addEventListener('change',invalidate);
$('analyze').onclick=()=>task('Python 正在分析…部份 PCA 方法需要較久時間。',async()=>{
  result=await request('/api/analyze',{dataset:dataset.id,features:selectedFeatures(),target:$('target').value,method:$('method').value,components:Number($('components').value),normalize_counts:$('normalize').checked,...extraOptions()});
  drawScatter();drawRanking();$('coverage').textContent=result.variance?`${(result.variance.reduce((a,b)=>a+b,0)*100).toFixed(1)}%`:'不提供';$('warnings').textContent=result.warnings.join(' ')+(result.component_scores?' 主成分 GRA 分數：'+result.component_scores.map(v=>v.toFixed(3)).join(', ')+'；保留 PC '+result.selected_components.map(v=>v+1).join(', '):'');
});
$('selectTop').onclick=()=>{if(!result)return;const n=Number($('topK').value);if(!Number.isInteger(n)||n<1||n>result.ranking.length){status('請輸入有效的保留特徵數。','error');return;}const keep=new Set(result.ranking.slice(0,n).map(row=>row.feature));$('features').querySelectorAll('input').forEach(input=>input.checked=keep.has(input.value));countFeatures();invalidate();$('components').value=Math.min(Number($('components').value),n);};
$('download').onclick=()=>{if(!result)return;const output={dataset:dataset.name,synthetic_note:dataset.note,options:{normalize_counts:$('normalize').checked},...result};downloadJson(output,'greytheory-analysis.json');};
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));$('dataPanel').hidden=button.dataset.tab!=='data';$('imagesPanel').hidden=button.dataset.tab!=='images';$('labPanel').hidden=button.dataset.tab!=='lab';});
function displayImages(value){const grid=el('div',undefined,'image-grid'),query=el('div',undefined,'image-card'),image=el('img');image.src=value.query;image.alt='待比較圖片';query.append(el('strong','待比較圖片'),image);grid.append(query);value.matches.forEach(m=>{const card=el('div',undefined,'image-card'),img=el('img');img.src=m.image;img.alt=m.name;card.append(el('strong',`#${m.rank} ${m.name}`),img,el('p',`距離 ${m.distance.toFixed(5)}`));grid.append(card);});$('imageResults').replaceChildren(el('p',value.note,'hint'),grid);}
$('imageDemo').onclick=()=>task('正在擷取 AI 筆跡特徵並比對…',async()=>displayImages(await request('/api/handwriting',{demo:true,method:$('imageMethod').value,method_params:formValues('imageParams')})));
$('compareImages').onclick=()=>task('正在處理圖片並比較…',async()=>{const refs=[...$('references').files];if(refs.length<3||refs.length>30)throw new Error('請選擇 3–30 張參考圖片。');const query=await fileObject($('query').files[0],8*1024*1024),references=await Promise.all(refs.map(f=>fileObject(f,8*1024*1024)));displayImages(await request('/api/handwriting',{query,references,method:$('imageMethod').value,method_params:formValues('imageParams')}));});
$('imageMethod').replaceChildren(...[...$('method').options].map(option=>option.cloneNode(true)));
function showUnavailableFiles(items) {
  $('unavailableFiles').hidden=!items.length;
  $('unavailableSummary').textContent=`未支援或無法讀取的檔案（${items.length}）`;
  $('unavailableList').replaceChildren();
  for(const item of items){const row=el('div',undefined,'unavailable-file');row.append(el('strong',item.name),el('p',item.reason,'hint'));$('unavailableList').append(row);}
}
(async()=>{try{config=await workbenchConfig();showUnavailableFiles(config.unavailable||[]);if(config.mode==='desktop')$('modeNotice').hidden=true;config.catalog.forEach(item=>{const option=el('option',item.name);option.value=item.id;$('dataset').append(option);});initWorkbenchExtensions();await task('載入 PVD 模擬 DOE…',async()=>displayDataset(await request('/api/load',{id:'doe:pvd'})));}catch(error){status(error.message,'error');}})();
