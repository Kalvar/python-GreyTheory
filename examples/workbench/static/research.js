'use strict';
function researchFormState(){
 const box=$('scenarioParams'),tool=box.querySelector('[data-key="tool"]')?.value;
 if(!tool)return;
 const enabled=box.querySelector('[data-key="pca_mode"]')?.value==='on';
 for(const key of ['method','components']){const input=box.querySelector(`[data-key="${key}"]`);if(input)input.closest('.parameter').hidden=!enabled;}
 $('scenarioPca').hidden=!enabled;
 const neural=['ginn','fginn'].includes(tool),rl=tool==='rlfgm',gp=tool==='grey_fuzzy_gpr';
 const fields={order_mode:rl,order:tool==='fginn'||(rl&&box.querySelector('[data-key="order_mode"]')?.value==='fixed'),beta:tool==='fginn',window:neural,grey_weight:neural,iterations:neural,grey_strength:gp};
 for(const [key,shown] of Object.entries(fields)){const input=box.querySelector(`[data-key="${key}"]`);if(input)input.closest('.parameter').hidden=!shown;}
}
function researchGprDiagram(data){
 const row=data.models[1],xs=data.observed.map((_,i)=>i+1),upper=row.prediction.map((v,i)=>v+2*row.std[i]),lower=row.prediction.map((v,i)=>v-2*row.std[i]);
 const box=$('scenarioDiagram');box.replaceChildren();
 const svg=svgEl('svg',{viewBox:'0 0 480 280',role:'img','aria-label':'保留測試樣本 / 品質指標（合成單位）'}),yr=range([...data.observed,...upper,...lower]);box.append(svg);
 const x=v=>52+(v-1)/(xs.length-1)*410,y=v=>238-(v-yr[0])/(yr[1]-yr[0])*220;
 for(let i=0;i<5;i++){const value=Math.round(1+i*(xs.length-1)/4),xx=x(value),yy=18+i*55;
  svg.append(svgEl('line',{x1:xx,x2:xx,y1:18,y2:238,class:'axis',opacity:.35}));svg.append(svgEl('line',{x1:52,x2:462,y1:yy,y2:yy,class:'axis',opacity:.35}));
  textAt(svg,xx,256,String(value),{'text-anchor':'middle'});textAt(svg,44,yy+3,(yr[1]-i*(yr[1]-yr[0])/4).toPrecision(3),{'text-anchor':'end'});
 }textAt(svg,240,277,'保留測試樣本',{'text-anchor':'middle'});textAt(svg,52,11,'品質指標（合成單位）');
 const polygon=xs.map((v,i)=>`${x(v)},${y(upper[i])}`).concat([...xs].reverse().map(v=>`${x(v)},${y(lower[v-1])}`)).join(' ');
 svg.append(svgEl('polygon',{points:polygon,fill:'#7ab8ff',opacity:.15}));
 for(const [values,color] of [[data.observed,colors[0]],[row.prediction,colors[1]]]){const path=values.map((value,i)=>`${i?'L':'M'}${x(i+1)},${y(value)}`).join(' ');svg.append(svgEl('path',{d:path,fill:'none',stroke:color,'stroke-width':2}));}
 $('scenarioDiagram').append(el('p','綠線為實測合成值；藍線為預測，陰影為 ±2 GP 標準差。最後 10 筆是分布偏移測試。','hint'));
}
