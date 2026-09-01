// Performance tab — reliability, skill-vs-baselines, feature importance, per-class, all-clear.
(function(){
let rendered = false;
const NAVY='#1a3a5c', ORANGE='#d35400', GREY='#a7b6c6', GREEN='#2e8b74';
const PL = {displayModeBar:false, responsive:true};
const base = plotLayout({margin:{l:54,r:16,t:14,b:46},
              xaxis:plotAxis(), yaxis:plotAxis()});

window.addEventListener('tabchange', e=>{ if(e.detail!=='performance') return;
  render();
  // charts already drawn → just re-fit them to the container on re-entry
  if(rendered) setTimeout(()=>{ ['relChart','tssChart','impChart'].forEach(id=>{
    try{ Plotly.Plots.resize(id); }catch(_){} }); }, 90);
});

async function render(){
  if(rendered) return;
  let m;
  try { m = await fetchJSON('/api/metrics'); } catch(err){ showError('metrics: '+err.message); return; }
  rendered = true;
  reliability(m); tssBars(m); importance(m); perClass(m); allClear(m);
}

// ── reliability diagram ──────────────────────────────────────────────────
function reliability(m){
  const clean = o => { const p=[],q=[]; o.pred.forEach((x,i)=>{ if(x!=null&&o.obs[i]!=null){p.push(x);q.push(o.obs[i]);} }); return {p,q}; };
  const b=clean(m.reliability.before), a=clean(m.reliability.after);
  const traces=[
    {x:[0,1],y:[0,1],mode:'lines',line:{color:'#aab6c4',dash:'dash',width:1},name:'perfect',hoverinfo:'skip'},
    {x:b.p,y:b.q,mode:'lines+markers',line:{color:ORANGE,width:2},marker:{size:7},name:'XGBoost (uncalibrated)'},
    {x:a.p,y:a.q,mode:'lines+markers',line:{color:GREEN,width:2},marker:{size:7,symbol:'square'},name:'XGBoost + isotonic'},
  ];
  Plotly.react('relChart', traces, Object.assign({}, base, {
    xaxis:plotAxis({title:axisTitle('predicted probability'),range:[0,1]}),
    yaxis:plotAxis({title:axisTitle('observed frequency'),range:[0,1]}),
    legend:{x:.03,y:.97,font:{size:11},bgcolor:'rgba(255,255,255,.82)',
            bordercolor:'#e4e9f0',borderwidth:1}}), PL);
  const c=m.calibration.y_15min;
  document.getElementById('relCap').innerHTML =
    `Isotonic calibration pulls the curve onto the diagonal. <b>ECE ${c.ece_before.toFixed(3)} → ${c.ece_after.toFixed(3)}</b>, `+
    `Brier ${c.brier_before.toFixed(3)} → ${c.brier_after.toFixed(3)} (15-min). TSS is preserved — isotonic is monotonic, so it fixes <i>reliability</i>, not ranking.`;
}

// ── TSS vs baselines ─────────────────────────────────────────────────────
function tssBars(m){
  const H=['y_15min','y_30min','y_60min'], xl=['15 min','30 min','60 min'];
  const mk=(name,src,color)=>({type:'bar',name,x:xl,y:H.map(h=>src[h]),marker:{color},
    text:H.map(h=>src[h].toFixed(2)),textposition:'outside',textfont:{size:11,color:'#43566a'},
    cliponaxis:false});
  const traces=[
    mk('Climatology', m.baselines.climatology, GREY),
    mk('Persistence', m.baselines.persistence, '#c98a12'),
    mk('XGBoost (calibrated)', m.forecast_tss, NAVY),
  ];
  Plotly.react('tssChart', traces, Object.assign({}, base, {
    barmode:'group', bargap:.32, bargroupgap:.12,
    xaxis:plotAxis({title:axisTitle('forecast horizon',11.5)}),
    yaxis:plotAxis({title:axisTitle('TSS'),range:[0,0.46]}),
    legend:{orientation:'h',y:1.16,x:0,font:{size:11}}}), PL);
  document.getElementById('tssCap').innerHTML =
    `<div class="nowcast-badge"><span>NOWCASTING (separate task)</span> Detection TSS `+
    `<b>${m.detection.tss}</b> — concurrent detection, not prediction. Off this axis (much easier than forecasting).</div>`+
    `<b>Forecast (prediction)</b> beats both operational baselines at every horizon — strongest at 15 min (Sarwade's target). `+
    `Climatology = base-rate (no skill); persistence = recent activity continues. A TFT was evaluated and honestly bested (15-min TSS ${m.tft_tss.y_15min}).`;
}

// ── feature importance ───────────────────────────────────────────────────
function importance(m){
  const f=[...m.feature_importance].reverse();   // horizontal: top at top
  const traces=[{type:'bar',orientation:'h',x:f.map(d=>d.gain),y:f.map(d=>d.name),
    marker:{color:f.map(d=>d.physics?ORANGE:NAVY)},
    text:f.map(d=>d.physics?'physics':''),textposition:'inside',insidetextanchor:'start',
    textfont:{size:10,color:'#fff'},hoverinfo:'x+y'}];
  Plotly.react('impChart', traces, Object.assign({}, base, {
    margin:{l:150,r:16,t:12,b:44},
    xaxis:plotAxis({title:axisTitle('XGBoost gain')}),
    yaxis:plotAxis({automargin:true,tickfont:{size:10.5,color:'#5a6b7d'}})}), PL);
}

// ── per-class table ──────────────────────────────────────────────────────
function perClass(m){
  const pc=m.per_class_15min, order=['X','M','C','B'];
  let rows = `<tr><th>Class</th><th>15-min recall</th><th>caught / windows</th></tr>`;
  order.forEach(c=>{
    const [hit,n,r]=pc[c];
    const pct=(r*100).toFixed(0);
    rows += `<tr class="${c==='X'?'x':''}"><td class="k">${c}</td>`+
      `<td><span class="bar" style="width:${Math.max(4,r*90)}px"></span>${pct}%</td>`+
      `<td class="denom">${hit} / ${n}</td></tr>`;
  });
  const f=m.forecast_15min, cal=m.calibration.y_15min;
  document.getElementById('pclassTable').innerHTML = rows +
    `<tr><td colspan="3" class="denom" style="border:0;padding-top:.5rem">`+
    `<b>15-min (test):</b> TSS ${f.tss} · HSS ${f.hss} · POD ${f.pod} · FAR ${f.far} · precision ${f.precision} · Brier ${cal.brier_after} · ECE ${cal.ece_after}</td></tr>`+
    `<tr><td colspan="3" class="denom" style="border:0">`+
    `Bigger flares are easier to forecast (stronger precursors). <b>X-class denominator = ${m.x_test_denominator} test events</b> `+
    `(${pc.X[1]} pre-flare windows) — promising, small sample.</td></tr>`;
}

// ── all-clear ────────────────────────────────────────────────────────────
function allClear(m){
  const ac=m.all_clear, miss=ac.no_coverage;
  document.getElementById('allClear').innerHTML =
    `<h4>Quiet → X-class "all-clear" test (Camporeale 2025 failure mode)</h4>`+
    `<div><span class="big">${ac.quiet_to_x}</span> quiet→X transitions flagged ~15 min before peak — the model does <b>not</b> issue a false all-clear when the Sun is calm then erupts.</div>`+
    `<div style="margin-top:.4rem"><span class="big">${ac.all_x}</span> of all test X-flares flagged in the pre-peak window.</div>`+
    `<div class="note">The ${miss} miss${miss===1?'':'es'} had <b>no in-GTI coverage</b> in [peak−15min, peak] (instrument gaps, not model failures) → <b>${ac.observed_x}</b> of X-flares the instruments actually observed were flagged. `+
    `Operating points: Watch ${(m.alert_operating_points.watch_tss_optimal*100).toFixed(0)}% (TSS-optimal, FAR ${m.alert_operating_points.far_at_tss_optimal} — the documented rare-event challenge), Warning ${(m.alert_operating_points.warning_high_precision*100).toFixed(0)}% (raised for precision).</div>`;
}
})();
