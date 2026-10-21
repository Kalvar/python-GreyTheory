'use strict';
// Local text only: keep uploaded data, field identifiers and form values intact.
(() => {
  const catalog = window.GREY_LOCALES;
  const original = new WeakMap();
  let language = 'zh-TW';
  try { language = new URLSearchParams(location.search).get('lang') || localStorage.getItem('grey-language') || language; } catch (_) {}
  if (!['zh-TW', 'en', 'ja'].includes(language)) language = 'zh-TW';
  const extra = {
    threshold:['Error threshold','誤差の閾値'], simulated_changed_pixels:['Simulated changed positions','模擬変更位置数'],
    true_positive:['Changed positions detected','検出できた変更位置'], false_positive:['Unchanged positions flagged','未変更位置の誤検出'], missed:['Changed positions missed','見逃した変更位置'],
    'APPLICATION LAB':['APPLICATION LAB','応用ラボ'], 'EXPERIMENT':['EXPERIMENT','実験'], 'DATASET':['DATASET','データセット'],
    '重建差異（圈線＝超過門檻）':['Reconstruction error (outline = above threshold)','再構成誤差（枠線＝閾値超過）'],
    '模擬真值（只用於核對）':['Simulated changes (for checking only)','模擬した変更領域（照合用）'],
    'Workbench 操作手冊':['Workbench manual','Workbench 操作ガイド'], '關閉':['Close','閉じる']
  };
  for (const [key, val] of Object.entries(extra)) catalog[key] = {en:val[0],ja:val[1]};
  for (const [key, label] of Object.entries({threshold:'誤差門檻',simulated_changed_pixels:'模擬變更位置數',true_positive:'正確標記的變更位置',false_positive:'誤報位置',missed:'漏報的變更位置'})) catalog[key]['zh-TW']=label;
  const keys = Object.keys(catalog).sort((a,b)=>b.length-a.length);
  function translate(source) {
    if (language === 'zh-TW') return catalog[source]?.['zh-TW'] || source;
    if (catalog[source]) return catalog[source][language];
    // Replace source fragments once; never translate inserted text again.
    let out='', position=0;
    while (position<source.length) {
      let found=null, index=source.length;
      for (const key of keys) { const at=source.indexOf(key,position); if(at>=0 && at<index) {index=at; found=key;} }
      if (!found) return out+source.slice(position);
      out+=source.slice(position,index)+catalog[found][language]; position=index+found.length;
    }
    return out;
  }
  function update(node, attribute) {
    const current=attribute ? node.getAttribute(attribute) : node.nodeValue;
    const key=node;
    let records=original.get(key); if(!records) {records={};original.set(key,records);}
    const id=attribute || 'text'; let record=records[id];
    if(!record || current!==record.last) record={source:current,last:current};
    const next=translate(record.source); record.last=next; records[id]=record;
    if(current!==next) {if(attribute) node.setAttribute(attribute,next); else node.nodeValue=next;}
  }
  const dialog=document.getElementById('manualDialog');
  const nav=dialog.querySelector('.manual-nav'), article=dialog.querySelector('article');
  const chinese={nav:nav.innerHTML,article:article.innerHTML};
  function apply() {
    observer.disconnect();
    document.documentElement.lang=language==='zh-TW'?'zh-Hant':language;
    document.getElementById('language').value=language;
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    let node;
    while((node=walker.nextNode())) {
      const parent=node.parentElement;
      if(parent.closest('script,style,pre,code,textarea,#features,#language,.rank-name,.manual-body,[data-i18n-skip]')) continue;
      if(parent.matches('#target option') && parent.value) continue;
      if(parent.closest('#preview') && !parent.matches('th:first-child')) continue;
      update(node);
    }
    for(const element of document.querySelectorAll('[title],[placeholder],[aria-label]')) {
      if(element.closest('.manual-body')) continue;
      for(const attr of ['title','placeholder','aria-label']) if(element.hasAttribute(attr)) update(element,attr);
    }
    observer.observe(document.body,{childList:true,subtree:true,characterData:true});
  }
  function manual() {
    if(language==='zh-TW') {nav.innerHTML=chinese.nav;article.innerHTML=chinese.article;return;}
    const sections=window.GREY_MANUAL[language];
    nav.replaceChildren();article.replaceChildren();
    for(const [id,title,body] of sections) {
      const link=document.createElement('a');link.href='#help-'+id;link.dataset.manualSection=id;link.textContent=title;nav.append(link);
      const section=document.createElement('section');section.id='help-'+id;section.tabIndex=-1;
      const heading=document.createElement('h3');heading.textContent=title;section.append(heading);
      for(const paragraph of body.split('\n')) {const p=document.createElement('p');p.textContent=paragraph;section.append(p);}
      article.append(section);
    }
  }
  const observer=new MutationObserver(()=>apply());
  document.getElementById('language').addEventListener('change',event=>{
    language=event.target.value;try{localStorage.setItem('grey-language',language);}catch(_){}
    manual();apply();
  });
  window.greyLanguage={get current(){return language;},translate};
  manual();apply();
})();
