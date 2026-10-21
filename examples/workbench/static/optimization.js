'use strict';
function optimizationDiagram(data) {
  const box=$('scenarioDiagram');box.replaceChildren();
  const tabs=el('div',undefined,'optimization-tabs');tabs.setAttribute('role','group');tabs.setAttribute('aria-label','快速分析步驟');
  const plot=el('div');plot.id='optimizationPlot';const hint=el('p',undefined,'hint');
  box.append(tabs,plot,hint);
  const stages=[['stability','1 排序穩定性'],['calibration','2 差異門檻'],['search','3 自動選組合'],['pareto','4 多目標方案']];
  function dot(svg,x,y,color,title,r=4){const point=svgEl('circle',{cx:x,cy:y,r,fill:color,class:'optimization-dot'}),tip=svgEl('title');tip.textContent=title;point.append(tip);svg.append(point);}
  function draw(stage){
    tabs.querySelectorAll('button').forEach(button=>{const active=button.dataset.stage===stage;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    plot.replaceChildren();
    if(stage==='stability'){
      const svg=svgEl('svg',{viewBox:'0 0 720 330',role:'img','aria-label':'特徵排名穩定性'});plot.append(svg);
      textAt(svg,170,25,'入選前兩名的頻率');
      data.ranking.forEach((row,i)=>{const y=52+i*40; textAt(svg,155,y+15,row.feature,{'text-anchor':'end'});
        svg.append(svgEl('rect',{x:170,y,width:450,height:22,rx:5,fill:'#20384a'}));
        const bar=svgEl('rect',{x:170,y,width:450*row.selection_frequency,height:22,rx:5,fill:colors[0],class:'optimization-bar'});
        const title=svgEl('title');title.textContent=`${row.feature} · ${row.mean_rank.toFixed(2)} ± ${row.rank_std.toFixed(2)}`;bar.append(title);svg.append(bar);
        textAt(svg,635,y+15,`${(row.selection_frequency*100).toFixed(1)}%`);
      });hint.textContent='頻率高表示不同抽樣下較常入選，不是因果關係的機率。詳細名次變動見下方表格。';
    }else if(stage==='calibration'){
      const d=data.calibration,xs=d.scores.map((_,i)=>i+1),ys=[0,...d.scores];if(d.threshold!==null)ys.push(d.threshold);
      const {svg,x,y}=chartFrame('optimizationPlot',xs,ys,'測試樣本序號','重建差異分數');
      if(d.threshold!==null)svg.append(svgEl('line',{x1:x(1),x2:x(xs.length),y1:y(d.threshold),y2:y(d.threshold),stroke:'#f3bc72','stroke-dasharray':'5 4'}));
      d.scores.forEach((score,i)=>{dot(svg,x(i+1),y(score),d.flags[i]?'#f3bc72':'#67e8c0',`${i+1} · ${score.toPrecision(4)}`,d.injected[i]?5:3);if(d.injected[i])svg.lastChild.setAttribute('stroke','#c7a1ff');});
      hint.textContent='虛線是正常校正資料的門檻。橘點超過門檻；紫邊是刻意偏移的最後 12 筆。兩者不一定一致。';
    }else if(stage==='search'){
      const valid=data.trials.filter(row=>row.status==='ok'&&row.validation_rmse!==null);
      const {svg,x,y}=chartFrame('optimizationPlot',data.trials.map(row=>row.trial),[0,...valid.map(row=>row.validation_rmse)],'候選編號','驗證 RMSE（越小越好）');
      valid.forEach(row=>{svg.append(svgEl('line',{x1:x(row.trial),x2:x(row.trial),y1:y(0),y2:y(row.validation_rmse),stroke:'#7ab8ff','stroke-width':8}));dot(svg,x(row.trial),y(row.validation_rmse),colors[0],`${row.method} · ${row.components} PC · ${row.validation_rmse.toPrecision(4)}`);});
      hint.textContent='用相同訓練切分比較候選；未收斂者不會勝出。測試 RMSE 另列在摘要，不用來挑設定。';
    }else{
      const rows=data.pareto,{svg,x,y}=chartFrame('optimizationPlot',rows.map(row=>row.cost),rows.map(row=>row.quality_loss),'模擬成本（越小越好）','品質損失（越小越好）');
      rows.forEach(row=>dot(svg,x(row.cost),y(row.quality_loss),!row.feasible?'#506071':row.selected?'#f3bc72':'#67e8c0',`${row.name} · ${row.cost.toFixed(3)} / ${row.quality_loss.toFixed(3)}`,row.selected?6:4));
      hint.textContent='橘點是 Pareto 折衷方案；灰點超過成本上限。左下較好，但通常沒有同時最省又最好的唯一方案。';
    }
  }
  for(const [stage,label] of stages){const button=el('button',label,'secondary small');button.dataset.stage=stage;button.onclick=()=>draw(stage);tabs.append(button);}
  draw('stability');
}
