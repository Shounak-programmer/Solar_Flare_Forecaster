// Catalog & Science tab — hardness chart, master-catalog browser, QPP gallery, subtabs.
(function(){
let inited=false, page=1, demoDates=new Set();
const PL={displayModeBar:false,responsive:true};
const el=id=>document.getElementById(id);

// Sub-tab navigation inside Catalog & Science
document.querySelectorAll('.cat-subtab').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetSubtab = btn.dataset.subtab;
    document.querySelectorAll('.cat-subtab').forEach(t => t.classList.toggle('active', t === btn));
    document.querySelectorAll('.cat-subpane').forEach(p => p.classList.toggle('active', p.id === 'subpane-' + targetSubtab));
    if (targetSubtab === 'cat-science' && inited) {
      setTimeout(() => Plotly.Plots.resize('hardChart'), 50);
    }
  });
});

window.addEventListener('tabchange', e=>{ if(e.detail==='catalog') init(); });

async function init(){
  if(inited){ Plotly.Plots.resize('hardChart'); return; }
  inited=true;
  try{
    const man=await fetchJSON('/api/replay_days');
    demoDates=new Set(man.demo_days.map(d=>`${d.date.slice(0,4)}-${d.date.slice(4,6)}-${d.date.slice(6)}`));
    await hardness();
    el('catStatus').addEventListener('change',()=>{page=1;loadCatalog();});
    el('catClass').addEventListener('change',()=>{page=1;loadCatalog();});
    el('catPrev').addEventListener('click',()=>{if(page>1){page--;loadCatalog();}});
    el('catNext').addEventListener('click',()=>{page++;loadCatalog();});
    await loadCatalog();
    await qppGallery();
  }catch(err){ showError('catalog: '+err.message); }
}

// ── hardness ordering ────────────────────────────────────────────────────
async function hardness(){
  const h=await fetchJSON('/api/hardness');
  const d=h.detectors;
  const colors=d.map(x=>x.band==='soft'?'#1a3a5c':(x.name.includes('CdTe')?'#2e8b74':'#d35400'));
  const traces=[{type:'bar',x:d.map(x=>x.name),y:d.map(x=>x.xc_ratio),marker:{color:colors},
    text:d.map(x=>x.xc_ratio+'×'),textposition:'outside',textfont:{size:12,color:'#43566a'},
    cliponaxis:false,
    customdata:d.map(x=>[Math.round(x.x_recall*100),Math.round(x.c_recall*100)]),
    hovertemplate:'%{x}<br>X-recall %{customdata[0]}%, C-recall %{customdata[1]}%<extra></extra>'}];
  Plotly.react('hardChart',traces,plotLayout({margin:{l:56,r:16,t:14,b:46},bargap:.4,
    yaxis:plotAxis({title:axisTitle('X / C selectivity (×)'),range:[0,9.4]}),
    xaxis:plotAxis()}),PL);
  el('hardCap').innerHTML=`X-over-C detection selectivity rises <b>monotonically soft→hard (1.2× → 8.5×)</b>: `+
    `soft SoLEXS sees thermal flares of all classes; hard CZT preferentially catches impulsive/large events. `+
    `This non-thermal hard-X signature is the empirical justification for the independent 5-detector architecture (and the fusion that recovers 100% X-recall).`;
}

// ── master catalog browser ───────────────────────────────────────────────
async function loadCatalog(){
  const st=el('catStatus').value, cl=el('catClass').value;
  let url=`/api/catalog?page=${page}&page_size=40`;
  if(st) url+=`&status=${st}`; if(cl) url+=`&goes_class=${cl}`;
  const c=await fetchJSON(url);
  el('catTotal').textContent=`— ${c.total.toLocaleString()} flares`;
  el('catPage').textContent=`page ${c.page} / ${c.n_pages}`;
  el('catPrev').disabled=c.page<=1; el('catNext').disabled=c.page>=c.n_pages;
  let rows=`<tr><th>Date</th><th>Peak UTC</th><th>Class</th><th>Detectors</th><th>Confidence</th><th>Status</th></tr>`;
  c.rows.forEach(r=>{
    const isDemo=demoDates.has(r.date);
    const cls=r.goes_class||'—', letter=(r.goes_class||'')[0]||'';
    const peakUT=new Date(r.peak*1000); const ut=String(peakUT.getUTCHours()).padStart(2,'0')+':'+String(peakUT.getUTCMinutes()).padStart(2,'0');
    const sat=r.saturation_flag?`<span class="satflag" title="SoLEXS member: peak amplitude is saturation-limited — do not size by it">▲ sat</span>`:'';
    const demo=isDemo?`<span class="replaybtn">▶ replay</span>`:'';
    rows+=`<tr class="${isDemo?'demo':''}" data-date="${r.date.replace(/-/g,'')}" data-demo="${isDemo}">`+
      `<td>${r.date} ${demo}</td><td>${ut} UT</td>`+
      `<td class="cls ${letter}">${cls}</td>`+
      `<td>${r.n_detectors}/5 ${sat}</td><td>${r.confidence}</td>`+
      `<td><span class="st ${r.status}">${r.status.replace('_',' ')}</span></td></tr>`;
  });
  el('catTable').innerHTML=rows;
  el('catTable').querySelectorAll('tr.demo').forEach(tr=>tr.addEventListener('click',()=>gotoReplay(tr.dataset.date)));
  el('catNote').innerHTML=`3-way status: <b>confirmed</b> ${c.status_counts.confirmed.toLocaleString()} (SWPC) · `+
    `<b>sub-threshold</b> ${c.status_counts.sub_threshold.toLocaleString()} (HEK only, real) · `+
    `<b>candidate-novel</b> ${c.status_counts.candidate_novel.toLocaleString()} (neither). `+
    `Rows on a demo day are clickable → opens in Replay. ▲ sat = SoLEXS-saturation caveat on peak amplitude.`;
}

function gotoReplay(date){
  document.querySelector('.tab[data-tab="replay"]').click();
  const sel=document.getElementById('daySelect'); sel.value=date; sel.dispatchEvent(new Event('change'));
}

// ── QPP gallery ──────────────────────────────────────────────────────────
async function qppGallery(){
  const q=await fetchJSON('/api/qpp');
  const cand=q.by_tier_candidates||q.by_tier, evb=q.by_tier_events||{};
  const sumEl=el('qppSummary');
  if(sumEl) sumEl.innerHTML=`<b>${(q.total_candidates??q.total).toLocaleString()}</b> candidate detections across `+
    `<b>${q.total_events??'—'}</b> flare events. Tier counts below are <b>candidates</b> (events in parentheses).`;
  const tiers=[['classic',cand.classic],['intermediate',cand.intermediate],['short',cand.short]];
  el('qppTiers').innerHTML=tiers.map(([t,n])=>`<div class="qpp-tier ${t}"><div class="n">${n}`+
    `${evb[t]!=null?`<span class="ev"> (${evb[t]})</span>`:''}</div>`+
    `<div class="lab">${q.tier_labels[t]}</div></div>`).join('');
  const idx=await fetchJSON('/api/qpp_wavelets');
  // order: LEAD with classic >=16s X-class, then the X-class short (caveated), then classic, then short
  const order={classic_x:0,featured_x:1,classic_1:2,classic_2:3,short_1:4};
  const feats=idx.featured.slice().sort((a,b)=>(order[a.id]??9)-(order[b.id]??9));
  el('qppGallery').innerHTML=feats.map(f=>`<div class="qpp-card"><div id="wv_${f.id}"></div></div>`).join('');
  for(const f of feats){ await drawWavelet(f); }
  initBrowser();
}

// Navy->orange brand colorscale for wavelet power (dark = background, hot = power)
const WV_SCALE=[[0,'#0d1f33'],[0.35,'#1a3a5c'],[0.6,'#3d6b96'],[0.78,'#d35400'],[1,'#ffce6a']];

async function drawWavelet(meta){
  const w=await fetchJSON('/api/qpp_wavelet/'+meta.id);
  const host=document.getElementById('wv_'+meta.id); if(!host) return;
  const tierBadge=meta.regime==='classic'?'<span class="qpp-badge classic">classic ≥16s</span>':
    (meta.regime==='short'?'<span class="qpp-badge short">short 4–8s · pending</span>':'');
  const xb=meta.goes_class==='X'?'<span class="qpp-badge xclass">X-class</span>':'';
  host.innerHTML=`<h4>${meta.date} · ${meta.detector.replace('hel1os_','').toUpperCase()} ${xb}${tierBadge}</h4>`+
    `<div class="sub">period ${meta.period_s}s · ${meta.significance}σ (global red-noise test) · `+
    `${meta.n_cycles} coherent cycles · ${meta.tier_label}</div>`+
    `<div class="wv" id="wvplot_${meta.id}"></div>`;
  const pmax=w.periods[w.periods.length-1];
  const traces=[
    // (a) Morlet power map, normalised to the Vaughan red-noise continuum
    {type:'heatmap',z:w.znorm,x:w.t,y:w.periods,colorscale:WV_SCALE,zmin:0,zmax:Math.max(6,w.sig_level*2),
     showscale:false,hovertemplate:'t=%{x}s · P=%{y:.1f}s · %{z:.1f}× background<extra></extra>'},
    // (b) 95% red-noise significance contour (Vaughan-fitted continuum)
    {type:'contour',z:w.znorm,x:w.t,y:w.periods,showscale:false,hoverinfo:'skip',
     contours:{start:w.sig_level,end:w.sig_level,size:0,coloring:'none'},
     line:{color:'#ff9d4d',width:1.6}},
    // (d) cone of influence: shade the edge-affected region (period > COI)
    {type:'scatter',x:w.t,y:w.t.map(()=>pmax),mode:'lines',line:{width:0},hoverinfo:'skip',showlegend:false},
    {type:'scatter',x:w.t,y:w.coi,mode:'lines',line:{color:'rgba(255,255,255,.55)',width:1,dash:'dot'},
     fill:'tonexty',fillcolor:'rgba(13,31,51,.45)',hoverinfo:'skip',showlegend:false},
  ];
  Plotly.react('wvplot_'+meta.id,traces,plotLayout({margin:{l:50,r:10,t:10,b:40},
    xaxis:plotAxis({title:axisTitle('s into impulsive phase',11),range:[w.t[0],w.t[w.t.length-1]]}),
    yaxis:plotAxis({type:'log',title:axisTitle('period (s)',11),range:[Math.log10(w.periods[0]),Math.log10(pmax)]}),
    showlegend:false,
    shapes:[
      // (c) detected period band (significant Fourier run; min visual thickness)
      {type:'rect',xref:'paper',x0:0,x1:1,yref:'y',y0:Math.min(w.band_lo,meta.period_s*0.95),
       y1:Math.max(w.band_hi,meta.period_s*1.05),fillcolor:'rgba(255,206,106,.14)',line:{width:0}},
      {type:'line',xref:'paper',x0:0,x1:1,yref:'y',y0:meta.period_s,y1:meta.period_s,
       line:{color:'#ffce6a',dash:'dash',width:1.6}}]}),PL);
}

// ── browsable QPP catalog (tier/class filter + row detail) ─────────────────
let Q={rows:[],page:1,per:12};
function initBrowser(){
  const reload=async()=>{
    const tier=el('qppTier').value;
    const q=await fetchJSON('/api/qpp'+(tier?`?tier=${tier}`:''));
    Q.all=q.rows; Q.page=1; applyFilter();
  };
  const applyFilter=()=>{
    const g=el('qppGoes').value;
    Q.rows=Q.all.filter(r=>!g || (g==='none' ? !r.goes_class : r.goes_class===g));
    Q.page=1; renderBrowser();
  };
  el('qppTier').addEventListener('change',reload);
  el('qppGoes').addEventListener('change',applyFilter);
  el('qppPrev').addEventListener('click',()=>{if(Q.page>1){Q.page--;renderBrowser();}});
  el('qppNext').addEventListener('click',()=>{if(Q.page<Q.npages){Q.page++;renderBrowser();}});
  reload();
}
function renderBrowser(){
  Q.npages=Math.max(1,Math.ceil(Q.rows.length/Q.per));
  Q.page=Math.min(Q.page,Q.npages);
  const rows=Q.rows.slice((Q.page-1)*Q.per,Q.page*Q.per);
  el('qppPage').textContent=`${Q.rows.length.toLocaleString()} QPPs · page ${Q.page}/${Q.npages}`;
  el('qppPrev').disabled=Q.page<=1; el('qppNext').disabled=Q.page>=Q.npages;
  let html=`<tr><th>Flare peak (UTC)</th><th>GOES</th><th>Detector</th><th>Period</th><th>σ</th><th>Cycles</th><th>Tier</th></tr>`;
  rows.forEach((r,i)=>{
    const tier=r.regime==='classic'?'<span class="qpp-badge classic">classic</span>':
      r.regime==='short'?'<span class="qpp-badge short">short · pending</span>':
      '<span class="qpp-badge inter">intermediate</span>';
    html+=`<tr class="qrow" data-i="${(Q.page-1)*Q.per+i}"><td>${r.date}</td>`+
      `<td class="cls ${r.goes_class||''}">${r.goes_class||'—'}</td>`+
      `<td>${r.detector.replace('hel1os_','').toUpperCase()}</td>`+
      `<td>${r.period_s} s</td><td>${r.significance}</td><td>${r.n_cycles}</td><td>${tier}</td></tr>`;
  });
  el('qppTable').innerHTML=html;
  el('qppTable').querySelectorAll('tr.qrow').forEach(tr=>tr.addEventListener('click',()=>showDetail(+tr.dataset.i)));
}
function showDetail(i){
  const r=Q.rows[i]; if(!r) return;
  const d=el('qppDetail'); d.hidden=false;
  const attr=r.regime==='short'
    ?'<b class="accent">solar attribution pending instrumental cross-check (Inglis et al. 2011)</b>'
    :(r.regime==='classic'?'<b>classic ≥16 s band — robustly solar</b>':'intermediate 8–16 s band');
  d.innerHTML=`<b>${r.date}</b> · GOES ${r.goes_class||'non-SWPC'} flare · `+
    `${r.detector.replace('hel1os_','').toUpperCase()} (18–160 keV hard X-ray) — `+
    `period <b>${r.period_s} s</b> · significance <b>${r.significance}σ</b> (Vaughan 2005 global red-noise test) · `+
    `<b>${r.n_cycles}</b> coherent cycles · ${attr}`;
}
})();
