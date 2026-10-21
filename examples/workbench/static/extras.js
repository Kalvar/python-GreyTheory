'use strict';
let scenarioResult=null;
function formFields(id,fields,values={}) {
  const box=$(id);box.replaceChildren();box._fields=fields;
  for(const f of fields){const row=el('div',undefined,'parameter');const label=el('label',f.label);const input=el(f.type==='select'?'select':'input');input.dataset.key=f.key;input.id=`${id}-${f.key}`;label.htmlFor=input.id;
    if(f.type==='select'){for(const v of f.choices){const labels=f.key==='art_source'?{spectral:'合成光譜地圖',ai_images:'AI 絹畫圖片'}:{};const option=el('option',labels[v]||v);option.value=v;input.append(option);}}
    else{input.type='number';input.min=f.min;input.max=f.max;input.step=f.type==='int'?'1':'any';}
    input.value=values[f.key]??f.default;input.title=f.hint;input.addEventListener('change',()=>{if(id.startsWith('scenario'))invalidateScenario();else if(id==='imageParams')$('imageResults').replaceChildren(el('p','參數已變更，請重新比較。','hint'));else invalidate();updateConditionalFields(id);});
    row.append(label,input,el('p',f.hint,'hint param-hint'));box.append(row);
  }
  updateConditionalFields(id);
}
function formValues(id){const box=$(id),values={};for(const f of box._fields||[]){const input=box.querySelector(`[data-key="${f.key}"]`);values[f.key]=f.type==='select'?input.value:Number(input.value);}return values;}
function updateConditionalFields(id){if(id==='scenarioParams'&&$('scenario').value==='research')researchFormState();const box=$(id),source=box.querySelector('[data-key="art_source"]');if(source){$('scenarioHint').textContent=source.value==='ai_images'?'直接讀取專案內的 AI 圖片，經區塊特徵、Grey 窗口與 GreyPCA 比較；不是把圖片當光譜。':config.scenarios.art.hint;for(const key of ['seed','strength']){const input=box.querySelector(`[data-key="${key}"]`);if(input)input.closest('.parameter').hidden=source.value==='ai_images';}}const forecast=box.querySelector('[data-key="forecast_method"]');if(forecast){for(const key of ['window_size','stride']){const input=box.querySelector(`[data-key="${key}"]`);if(input)input.closest('.parameter').hidden=forecast.value!=='convolution';}}const mode=box.querySelector('[data-key="delta_mode"]'),delta=box.querySelector('[data-key="delta"]');if(mode&&delta)delta.disabled=mode.value!=='manual';const kernel=box.querySelector('[data-key="kernel"]'),degree=box.querySelector('[data-key="degree"]');if(kernel&&degree)degree.disabled=kernel.value!=='poly';}
function pcaForm(method,id,hintId){const schema=config.pca_schemas[method];$(hintId).textContent=schema.hint;formFields(id,schema.fields);}
function qualityForm(){const box=$('qualityParams');box.replaceChildren(el('p','初始上下界取本批資料範圍，不是產品規格。請確認每個指標的偏好；目標值須嚴格介於上下界。','hint'));for(const name of selectedFeatures()){
  const idx=dataset.columns.indexOf(name),values=dataset.values.map(row=>row[idx]),lo=Math.min(...values),hi=Math.max(...values);if(hi===lo)continue;
  const row=el('div',undefined,'quality-row');row.dataset.feature=name;row.append(el('strong',name));
  const direction=el('select');direction.dataset.field='direction';['larger','smaller','target'].forEach(v=>{const o=el('option',{larger:'望大',smaller:'望小',target:'目標值'}[v]);o.value=v;direction.append(o);});direction.value=/error|roughness|resistivity|etch/.test(name)?'smaller':/thickness|refractive/.test(name)?'target':'larger';
  const label=el('label','偏好方向');label.append(direction);row.append(label);
  for(const [key,title,value] of [['lower','下界',lo],['upper','上界',hi],['target','目標值',(lo+hi)/2],['weight','權重',1]]){const l=el('label',title),input=el('input');input.type='number';input.step='any';input.dataset.field=key;input.value=Number(value.toPrecision(9));if(key==='weight')input.min=0;l.append(input);row.append(l);input.addEventListener('change',invalidate);}
  function sync(){row.querySelector('[data-field="target"]').disabled=direction.value!=='target';invalidate();}direction.addEventListener('change',sync);sync();box.append(row);
}}
function qualityValues(){return [...$('qualityParams').querySelectorAll('.quality-row')].map(row=>{const value={};for(const input of row.querySelectorAll('[data-field]'))value[input.dataset.field]=input.dataset.field==='direction'?input.value:Number(input.value);return value;});}
function engineChanged(){const engine=$('engine').value,isPca=['pca','window_pca','poisson'].includes(engine);$('methodBlock').hidden=!isPca;$('method').disabled=engine==='poisson';$('orderedBlock').hidden=!['gm0n','gm1n'].includes(engine);$('qualityParams').hidden=engine!=='quality';$('target').disabled=engine==='quality';
  const hints={pca:'投影與特徵排序分開計算；也可以開啟主成分的 GRA 篩選。',gra:'不執行 PCA；指定目標後比較各輸入序列。',gm0n:'係數使用累積序列，單位與列順序會影響結果；無序 DOE 不建議用。',gm1n:'估計發展係數與驅動係數；需要有意義的先後順序。',quality:'對樣本評分，並不是排特徵。逐欄確認方向、上下界和權重。',window_pca:'只接受有連續通道順序的光譜，先擷取窗口特徵再做 PCA。',poisson:'使用非負原始計數及 Anscombe 近似變換；不做總計數或逐欄標準化。'};$('engineHint').textContent=hints[engine];$('graParams').closest('details').hidden=['gm0n','gm1n'].includes(engine);formFields('graParams',engine==='quality'?config.gra_fields.filter(f=>f.key==='rho'):config.gra_fields);$('pcaParams').hidden=engine==='poisson';if(engine==='poisson'){$('method').value='pca';$('methodHint').textContent=hints.poisson;$('normalize').checked=false;}$('normalize').disabled=!dataset||dataset.kind!=='spectrum'||engine==='poisson';
  formFields('engineParams',engine==='window_pca'?config.window_fields:['gm0n','gm1n'].includes(engine)?config.gm_fields:[]);
  if(dataset){if(engine==='quality'){$('target').value='';renderFeatures();if(dataset.targets.length){$('features').querySelectorAll('input').forEach(n=>n.checked=dataset.targets.includes(n.value));countFeatures();}qualityForm();}else{renderFeatures();}}
  invalidate();
}
function extraOptions(){const engine=$('engine').value;const values={engine,gra_params:formValues('graParams')};
 if(['pca','window_pca'].includes(engine))values.method_params=formValues('pcaParams');
 if(['pca','window_pca','poisson'].includes(engine))values.component_top_k=Number($('componentTop').value);
 if(engine==='window_pca')values.window_params=formValues('engineParams');
 if(['gm0n','gm1n'].includes(engine)){values.gm_params=formValues('engineParams');values.ordered_rows=$('orderedRows').checked;}
 if(engine==='quality')values.quality=qualityValues();return values;
}
function initWorkbenchExtensions(){
 for(const [value,label] of Object.entries(config.engines)){const option=el('option',label);option.value=value;$('engine').append(option);}
 formFields('graParams',config.gra_fields);pcaForm($('method').value,'pcaParams','methodHint');pcaForm($('imageMethod').value,'imageParams','imageMethodHint');
 $('engine').onchange=engineChanged;$('method').addEventListener('change',()=>pcaForm($('method').value,'pcaParams','methodHint'));$('imageMethod').onchange=()=>pcaForm($('imageMethod').value,'imageParams','imageMethodHint');$('componentTop').onchange=invalidate;$('orderedRows').onchange=invalidate;
 $('features').addEventListener('change',()=>{if($('engine').value==='quality')qualityForm();});
 for(const [key,scene] of Object.entries(config.scenarios)){const option=el('option',scene.label);option.value=key;$('scenario').append(option);}
 $('scenario').onchange=sceneChanged;sceneChanged();
 const groups=[['Grey 核心','GM11、兩層 Convolution、GM0N、GM1N、GreyGRA、GreyFeatureSelector'],['品質與 PCA','BenefitNormalizer、grade_quality / rank_quality、GreyPCA、PCAAdapter、RobustPCA、RobustSparsePCA、AdvPCA、PoissonPCA'],['特徵擷取','GreyWindowFeatures、TrajectoryFeatures（2D 以上）、ImagePatchFeatures；圖片頁使用區塊 → 窗口 → PCA'],['光譜','AsLS baseline_correct、NMF、MCR-ALS、MNF、MLPCA、fit_peaks、element_lines；SPX / BCF 讀取仍在第一頁'],['半導體','QualityPLS、ProcessMonitor（Q / T²）、rank_features、Latin Hypercube、GP suggest_parameters'],['搭配的最佳化','配送完整枚舉、司機匈牙利指派；Grey 負責偏好評分，不取代路徑或指派求解器']];
 for(const [name,description] of groups){const card=el('div',undefined,'catalog-row');card.append(el('strong',name),el('p',description,'hint'));$('methodCatalog').append(card);}
 engineChanged();
}
function invalidateScenario(){if(!scenarioResult)return;scenarioResult=null;$('scenarioDownload').disabled=true;$('scenarioSummary').textContent='參數已變更，請重新執行情境。';$('scenarioDiagram').replaceChildren();$('scenarioTables').replaceChildren();$('scenarioWarnings').replaceChildren();}
function sceneChanged(){const inputDownload=$('labPanel').querySelector('a.data-link');if(inputDownload)inputDownload.hidden=['optimization','research'].includes($('scenario').value);scenarioResult=null;$('scenarioDownload').disabled=true;const scene=config.scenarios[$('scenario').value];$('scenarioHint').textContent=scene.hint;formFields('scenarioParams',scene.fields);$('seriesBlock').hidden=$('scenario').value!=='forecast';
 const method=$('scenarioParams').querySelector('[data-key="method"]');$('scenarioPca').hidden=!method;
 if(method){const refresh=()=>{pcaForm(method.value,'scenarioPcaParams','scenarioPcaHint');if($('scenario').value==='research')researchFormState();};method.addEventListener('change',refresh);refresh();}
 const tool=$('scenarioParams').querySelector('[data-key="tool"]');if(tool){tool.addEventListener('change',sceneToolHint);sceneToolHint();}
 $('scenarioDiagram').replaceChildren();$('scenarioWarnings').replaceChildren();$('scenarioTables').replaceChildren();$('scenarioTitle').textContent=scene.label;$('scenarioSummary').textContent='調整參數後按「執行情境」。';
}
function sceneToolHint(){const key=$('scenario').value,tool=formValues('scenarioParams').tool;if(key==='research'){researchFormState();return;}
 const hints={nmf:'NMF 需要非負資料；顯示原始與重建曲線。',mcr:'MCR-ALS 需初始純成分；此合成例使用生成器已知峰形，真實材料需參考光譜。',mnf:'MNF 需要足夠空間像素估計噪聲共變異；此例使用 20×20×16 的合成雜訊圖。',mlpca:'MLPCA 需要逐值正方差；此例用生成器已知方差，並非自動猜真實噪聲。',baseline:'AsLS 可能移除真實光譜訊號；不會自動套用至 XRF。',peaks:'擬合固定峰心與峰寬的高斯幅度，不是定量元素分析。',element_lines:'查 xraylib 參考譜線；不會辨識這組任意高斯峰的材料。',pls:'以固定種子分成 11 筆訓練、4 筆保留；看膜厚預測誤差。',monitor:'Q / T² 門檻來自訓練分位數；DOE 本身的參數變化不代表不良。',suggest:'GP 以均勻度誤差望小提出候選，不會盲目最大化膜厚。候選不是可直接上機的配方。',lhs:'只產生界限內試驗設定，沒有量測結果；點數不等於品質。'};
 let note=$('toolHint');if(!note){note=el('p',undefined,'notice');note.id='toolHint';$('scenarioParams').append(note);}note.textContent=hints[tool]||'';
 const allowed=key==='spectral'?{components:['nmf','mcr','mnf','mlpca'],iterations:['nmf','mcr','mlpca'],lam:['baseline'],p:['baseline'],sigma:['peaks'],atomic_number:['element_lines']}:{components:['pls','monitor'],quantile:['monitor'],candidates:['suggest','lhs']};
 for(const [field,tools] of Object.entries(allowed)){const input=$('scenarioParams').querySelector(`[data-key="${field}"]`);if(input)input.closest('.parameter').hidden=!tools.includes(tool);}
}
function sceneSvg(label){const box=$('scenarioDiagram');box.replaceChildren();const svg=svgEl('svg',{viewBox:'0 0 720 370',role:'img','aria-label':label});box.append(svg);return svg;}
function pathSvg(points,x,y){return points.map((point,i)=>`${i?'L':'M'}${x(point[0])},${y(point[1])}`).join(' ');}
function routeDiagram(d){const svg=sceneSvg('模擬配送路線'),x=v=>45+v*62,y=v=>325-v*28;for(let i=0;i<=10;i++)svg.append(svgEl('line',{x1:x(i),x2:x(i),y1:35,y2:325,stroke:'#26384c',opacity:.5}));
 const baseline=svgEl('path',{d:pathSvg(d.baseline.map(i=>d.points[i]),x,y),fill:'none',stroke:'#637589','stroke-dasharray':'5 6','stroke-width':1.5});svg.append(baseline);
 const line=pathSvg(d.route.map(i=>d.points[i]),x,y),p=svgEl('path',{d:line,fill:'none',stroke:'#67e8c0','stroke-width':3,class:'route-path'});svg.append(p);
 d.points.forEach((v,i)=>{svg.append(svgEl('circle',{cx:x(v[0]),cy:y(v[1]),r:i?7:11,fill:i?'#7ab8ff':'#f3bc72'}));textAt(svg,x(v[0])+12,y(v[1])-10,i?`配送 ${i}`:'倉庫');});
 if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches){const dot=svgEl('circle',{r:5,fill:'#fff'}),motion=svgEl('animateMotion',{dur:'8s',repeatCount:'indefinite',path:line});dot.append(motion);svg.append(dot);}
 textAt(svg,40,358,`綠線：選取路線 ${d.route.join(' → ')}　灰虛線：原始順序`);
}
function matchingDiagram(d){const svg=sceneSvg('司機訂單配對'),h=330/Math.max(d.drivers.length,d.jobs.length);for(const [a,b] of d.edges)svg.append(svgEl('path',{d:`M180 ${30+a*h} C330 ${30+a*h},390 ${30+b*h},540 ${30+b*h}`,fill:'none',stroke:'#67e8c0','stroke-width':2,class:'route-path'}));d.drivers.forEach((v,i)=>{svg.append(svgEl('circle',{cx:165,cy:30+i*h,r:6,fill:'#7ab8ff'}));textAt(svg,20,34+i*h,`${v.id} · 載重 ${v.capacity_kg} kg`);});d.jobs.forEach((v,i)=>{svg.append(svgEl('circle',{cx:550,cy:30+i*h,r:6,fill:'#f3bc72'}));textAt(svg,565,34+i*h,`${v.id} · ${v.load_kg} kg`);});}
function heatmapDiagram(d){const svg=sceneSvg('藝術品模擬區域差異與真值'),[h,w]=d.shape,max=Math.max(...d.values,1e-20),cell=23;for(let panel=0;panel<2;panel++){const ox=panel?390:35;textAt(svg,ox,22,panel?'模擬真值（只用於核對）':'重建差異（圈線＝超過門檻）');for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x,value=panel?d.truth[i]:Math.sqrt(d.values[i]/max),rect=svgEl('rect',{x:ox+x*cell,y:40+y*cell,width:cell-2,height:cell-2,rx:2,fill:panel?(value?'#f3bc72':'#20384a'):`hsl(${200-45*value} 65% ${12+57*value}%)`,stroke:!panel&&d.flags[i]?'#f3bc72':'none'});const t=svgEl('title');t.textContent=`位置 ${y},${x} · ${panel?'模擬變更 '+d.truth[i]:'重建誤差 '+d.values[i].toExponential(3)}`;rect.append(t);svg.append(rect);}}}
function artImageDiagram(d){
 const box=$('scenarioDiagram');box.replaceChildren();
 const controls=el('label',undefined,'check'),toggle=el('input');toggle.type='checkbox';toggle.checked=true;
 controls.append(toggle,document.createTextNode('顯示超過門檻的區塊'));box.append(controls);
 const pair=el('div',undefined,'art-image-pair');box.append(pair);
 for(const [key,label] of [['reference','參考圖 · AI 虛構絹畫'],['observed','待比較圖 · AI 模擬局部差異']]){
  const figure=el('figure'),caption=el('figcaption',label),frame=el('div',undefined,'art-image-frame'),image=el('img');
  image.src=d[key];image.alt=label;frame.append(image);figure.append(caption,frame);pair.append(figure);
  if(key==='observed'){
   const overlay=svgEl('svg',{viewBox:'0 0 12 12',role:'img','aria-label':'圖片區塊差異標記'});
   for(let i=0;i<144;i++){if(!d.flags[i])continue;const rect=svgEl('rect',{x:i%12,y:Math.floor(i/12),width:1,height:1,fill:'#f3bc721a',stroke:'#f3bc72','stroke-width':.035});const title=svgEl('title');title.textContent=`${i/12|0}, ${i%12} · ${d.values[i].toExponential(3)}`;rect.append(title);overlay.append(rect);}
   frame.append(overlay);toggle.addEventListener('change',()=>overlay.toggleAttribute('hidden',!toggle.checked));
  }
 }
 box.append(el('p','先關閉標記比較原圖，再開啟標記查看需要查驗的區塊。這裡沒有經驗證的真值圖。','hint'));
 const files=el('a','圖片、數值與案例來源 →');files.href='../../data/demo/artwork/index.html';files.target='_blank';files.rel='noopener';box.append(files);const expert=el('a','專家查看與兩套搭配 →');expert.className='expert-review-link';expert.href='../../data/demo/artwork/review/index.html';expert.target='_blank';expert.rel='noopener';expert.onclick=()=>{expert.href='../../data/demo/artwork/review/index.html?lang='+window.greyLanguage.current;};box.append(expert);
}
function curvesDiagram(d){let xs,curves,names;if(d.type==='series'){xs=Array.from({length:d.observed.length+d.forecast.length},(_,i)=>i+1);curves=[d.observed,Array(d.observed.length-1).fill(null).concat([d.observed.at(-1),...d.forecast]),Array(d.observed.length-d.backtest.length).fill(null).concat(d.backtest)];names=['歷史','未來預測','保留回測'];}else{xs=d.x;curves=d.curves;names=['原始','重建 / 基線','扣除後'];}
 const ys=curves.flat().filter(v=>v!==null);if(!ys.length)return;const {svg,x,y}=chartFrame('scenarioDiagram',xs,ys,d.type==='series'?'期數':'能量 / 通道',d.type==='series'?'訂單量':'強度');
 curves.forEach((values,c)=>{let active=false;const line=values.map((v,i)=>{if(v===null){active=false;return '';}const part=`${active?'L':'M'}${x(xs[i])},${y(v)}`;active=true;return part;}).join(' ');svg.append(svgEl('path',{d:line,fill:'none',stroke:colors[c], 'stroke-width':2,'stroke-dasharray':c?'6 3':'none'}));});$('scenarioDiagram').append(el('p',names.slice(0,curves.length).join(' / '),'hint'));}
function trajectoryDiagram(d){const svg=sceneSvg('軌跡前兩個座標'),points=d.paths.flat(),xr=range(points.map(v=>v[0])),yr=range(points.map(v=>v[1]));const x=v=>35+(v-xr[0])/(xr[1]-xr[0])*640,y=v=>330-(v-yr[0])/(yr[1]-yr[0])*285;d.paths.forEach((points,i)=>svg.append(svgEl('path',{d:pathSvg(points,x,y),fill:'none',stroke:colors[i%colors.length],'stroke-width':2,class:'route-path'})));textAt(svg,35,355,'顯示前 6 條軌跡的前兩維；高維座標也有參與特徵擷取。');}
function displayScenario(value){scenarioResult=value;$('scenarioDownload').disabled=false;$('scenarioTitle').textContent=value.title;$('scenarioSummary').textContent=value.summary;$('scenarioWarnings').textContent=value.warnings.join(' ');$('scenarioDiagram').replaceChildren();const d=value.diagram;if(d){if(d.type==='research_gpr')researchGprDiagram(d);else if(d.type==='optimization')optimizationDiagram(d);else if(d.type==='art_images')artImageDiagram(d);else if(d.type==='route')routeDiagram(d);else if(d.type==='matching')matchingDiagram(d);else if(d.type==='heatmap')heatmapDiagram(d);else if(d.type==='trajectories')trajectoryDiagram(d);else curvesDiagram(d);}
 $('scenarioTables').replaceChildren();for(const block of value.tables){const panel=el('section',undefined,'panel'),wrap=el('div',undefined,'table-wrap'),table=el('table'),headers=Object.keys(block.rows[0]||{}),head=el('tr');headers.forEach(v=>head.append(el('th',v)));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');for(const record of block.rows){const row=el('tr');headers.forEach(key=>{const v=record[key];row.append(el('td',typeof v==='number'?((v!==0&&Math.abs(v)<.001)||Math.abs(v)>=1e6?v.toExponential(3):v.toLocaleString(undefined,{maximumSignificantDigits:6})):v===null?'—':String(v)));});body.append(row);}table.append(body);wrap.append(table);panel.append(el('h2',block.title),wrap);$('scenarioTables').append(panel);}
}
function downloadJson(value,name){if(desktopMode){window.pywebview.api.save_result(value,name).then(path=>{if(path)status('已儲存：'+path);}).catch(error=>status(error.message,'error'));return;}const link=el('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);}
function runScene(){return task('正在執行情境…',async()=>{const parameters=formValues('scenarioParams'),body={scenario:$('scenario').value,parameters};if(parameters.method)body.method_params=formValues('scenarioPcaParams');const text=$('seriesInput').value.trim();if(body.scenario==='forecast'&&text){const series=text.split(/[,，\s]+/).filter(Boolean).map(Number);if(series.some(v=>!Number.isFinite(v)))throw new Error('時間序列請只填數字，以逗號或空白分隔。');body.series=series;}displayScenario(await request('/api/scenario',body));});}
window.addEventListener('DOMContentLoaded',()=>{$('runScenario').onclick=runScene;$('scenarioDownload').onclick=()=>{if(scenarioResult)downloadJson(scenarioResult,'greytheory-scenario.json');};});
