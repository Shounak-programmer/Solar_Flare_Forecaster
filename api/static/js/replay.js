// Replay Theater — animates pre-computed replay JSON (no live inference).
(function(){
const DETS = [
  {key:'solexs_sdd2',  label:'SoLEXS SDD2 (soft)', color:DET_COLORS.solexs_sdd2},
  {key:'hel1os_cdte1', label:'HEL1OS CdTe1',       color:DET_COLORS.hel1os_cdte1},
  {key:'hel1os_cdte2', label:'HEL1OS CdTe2',       color:DET_COLORS.hel1os_cdte2},
  {key:'hel1os_czt1',  label:'HEL1OS CZT1 (hard)', color:DET_COLORS.hel1os_czt1},
  {key:'hel1os_czt2',  label:'HEL1OS CZT2 (hard)', color:DET_COLORS.hel1os_czt2},
];
const IMPACT = {
  quiet:   {pill:'NOMINAL',  text:'No significant flare expected in the next 15 minutes. Normal operations; no action required.'},
  watch:   {pill:'WATCH',    text:'Elevated flare risk. Satellite operators and HF-radio users placed on notice; monitor for escalation.'},
  warning: {pill:'WARNING',  text:'High flare risk within ~15 minutes. Possible HF radio degradation/blackout on sunlit &amp; polar routes; satellite operators advised to defer sensitive operations — a 10–15 min protective lead.'},
  nocov:   {pill:'NO DATA',  text:'Insufficient detector coverage — <b>no forecast issued</b>. The system does not guess during data gaps.'},
};

let S = null;          // current day state
let timer = null;

const el = id => document.getElementById(id);

async function init(){
  let manifest;
  try { manifest = await fetchJSON('/api/replay_days'); }
  catch(e){ showError('Cannot load demo days: '+e.message); return; }
  S = {manifest};
  const sel = el('daySelect');
  const roleLabel = {showstopper:'⭐ Showstopper', allclear:'🎯 Quiet→X (all-clear)',
                     famous:'Famous flare', anchor:'Anchor', quiet:'Quiet day', gti_miss:'Coverage-gap miss',
                     xclass:'X-class flare', mclass:'M-class flare'};
  const splitTag = {TEST:' [TEST — held-out]', VAL:' [VAL — tuning]', TRAIN:' [TRAIN — in-sample]'};
  // group the picker by demo category (spec: Showstoppers / M-class / Quiet / Honest failures)
  const groupOf = r => (r==='gti_miss') ? 'Honest failures (coverage-gap miss)'
                     : (r==='quiet')    ? 'Quiet days (FAR behaviour)'
                     : (r==='mclass')   ? 'M-class days'
                     :                    'Showstoppers — X-class';
  const groups = new Map();
  manifest.demo_days.forEach(d=>{
    const g=groupOf(d.role);
    if(!groups.has(g)) groups.set(g,[]);
    groups.get(g).push(d);
  });
  const groupOrder=['Showstoppers — X-class','M-class days','Quiet days (FAR behaviour)',
                    'Honest failures (coverage-gap miss)'];
  sel.innerHTML = groupOrder.filter(g=>groups.has(g)).map(g=>
    `<optgroup label="${g}">`+groups.get(g).map(d=>
      `<option value="${d.date}">${d.label} · ${roleLabel[d.role]||d.role}${splitTag[d.split]||''}</option>`
    ).join('')+`</optgroup>`).join('');
  sel.addEventListener('change', ()=>loadDay(sel.value));
  // controls
  el('playBtn').addEventListener('click', togglePlay);
  el('restartBtn').addEventListener('click', ()=>{ seek(0); });
  document.querySelectorAll('.spd').forEach(b=>b.addEventListener('click',()=>{
    document.querySelectorAll('.spd').forEach(x=>x.classList.toggle('active',x===b));
    if(S) S.speed = +b.dataset.spd;
  }));
  el('scrubber').addEventListener('input', e=>{ pause(); seek(+e.target.value); });
  await loadDay(manifest.demo_days[0].date);   // X8.1 showstopper first
}

async function loadDay(date){
  pause();
  let d;
  try { d = await fetchJSON('/api/replay/'+date); }
  catch(e){ showError('Cannot load '+date+': '+e.message); return; }
  const meta = S.manifest.demo_days.find(x=>x.date===date) || {};
  // precompute naive-UTC x strings (Plotly renders these verbatim → true UTC)
  const lcStr = d.lc_t.map(isoNaive);
  S = Object.assign(S, {
    date, d, meta,
    lcStr,
    t0: d.forecast.t[0], t1: d.forecast.t[d.forecast.t.length-1]+60,
    speed: +document.querySelector('.spd.active').dataset.spd,
    minIdx: 0, lastFlareShown: -1,
  });
  // day metadata + split badge
  const cls = d.label;
  el('dayMeta').innerHTML = `${pretty(date)} · ${d.actual_flares.length} catalogued flare(s) · ` +
    `Warning ≥ ${(d.forecast.thresholds.warning*100).toFixed(0)}% risk`;
  const badge = el('splitBadge');
  if(d.split==='TEST'){ badge.className='badge test'; badge.textContent='TEST — HELD-OUT (genuine forecast)'; }
  else if(d.split==='VAL'){ badge.className='badge val'; badge.textContent='VAL — TUNING PERIOD (not held-out test)'; }
  else { badge.className='badge insample'; badge.textContent='TRAIN — IN-SAMPLE ILLUSTRATION'; }
  el('scrubber').max = d.forecast.t.length-1;
  buildChart();
  seek(0);
}

function pretty(date){ return `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}`; }

// ── chart ────────────────────────────────────────────────────────────────
function buildChart(){
  const traces = DETS.map(dd=>({
    type:'scattergl', mode:'lines', name:dd.label, x:[], y:[],
    line:{color:dd.color, width:1.9}, connectgaps:false, hoverinfo:'name+y',
  }));
  const layout = baseLayout();
  Plotly.react('mainChart', traces, layout, {displayModeBar:false, responsive:true});
}
function baseLayout(){
  return plotLayout({
    margin:{l:62,r:18,t:16,b:58},
    xaxis:plotAxis({type:'date', range:[S.lcStr[0], S.lcStr[S.lcStr.length-1]],
           tickformat:'%H:%M', title:axisTitle('Time (UT)')}),
    yaxis:plotAxis({type:'log', title:axisTitle('counts s⁻¹'),
           rangemode:'tozero', autorange:true}),
    legend:{orientation:'h', y:-0.16, x:.5, xanchor:'center', yanchor:'top',
            font:{size:11.5}, bgcolor:'rgba(255,255,255,0)'},
    shapes:[], annotations:[],
  });
}

// ── playback ─────────────────────────────────────────────────────────────
// Note: the play loop tracks a CONTINUOUS simulated clock (`S.simUnix`).
// Anchoring on `S.d.forecast.t[S.minIdx]` each tick (1-min grid) caused sub-minute
// accumulations to be discarded, so the clock never advanced.
function togglePlay(){ S && (timer ? pause() : play()); }
function play(){
  if(!S) return;
  if(S.simUnix == null || S.simUnix >= S.t1 - 60) S.simUnix = S.t0;
  el('playBtn').textContent = '⏸ Pause';
  let last = performance.now();
  timer = setInterval(()=>{
    const now = performance.now(); const dtReal = (now-last)/1000; last = now;
    S.simUnix += dtReal * S.speed;
    if(S.simUnix >= S.t1){ S.simUnix = S.t1; render(S.simUnix); pause(); return; }
    render(S.simUnix);
  }, 80);
}
function pause(){ if(timer){ clearInterval(timer); timer=null; } el('playBtn').textContent='▶ Play'; }
function seek(minIdx){
  S.minIdx = Math.max(0, Math.min(minIdx, S.d.forecast.t.length-1));
  S.simUnix = S.d.forecast.t[S.minIdx];
  render(S.simUnix);
}

// ── render a frame at simulated time tNow (unix sec) ───────────────────────
function render(tNow){
  const d = S.d;
  S.minIdx = Math.max(0, Math.min(Math.floor((tNow - S.t0)/60), d.forecast.t.length-1));
  // Update the clock/scrubber FIRST: a chart redraw hiccup must never be able to
  // freeze the readout (that is what "the play button looks broken" looks like).
  el('playClock').textContent = fmtUT(tNow)+' UT';
  el('scrubLabel').textContent = fmtUT(tNow)+' UT';
  el('scrubber').value = S.minIdx;
  // reveal light curves up to tNow (guarded so a Plotly hiccup can't stop playback)
  try {
    const li = upperBound(d.lc_t, tNow);
    const xs = S.lcStr.slice(0, li);
    const upd = {x:[], y:[]};
    DETS.forEach(dd=>{ upd.x.push(xs); upd.y.push(d.detectors[dd.key].rate.slice(0, li)); });
    Plotly.restyle('mainChart', upd, [0,1,2,3,4]);
    showFlares(tNow);                       // flare markers for flares peaked so far
  } catch(e){ /* keep the clock and forecast advancing regardless */ }
  try { updateForecast(); } catch(e){ /* forecast panel hiccup must not freeze playback */ }
}

function updateForecast(){
  const d = S.d, i = S.minIdx;
  const p15 = d.forecast.y_15min[i], p30 = d.forecast.y_30min[i], p60 = d.forecast.y_60min[i];
  const alert = d.forecast.alert[i];
  const thr = d.forecast.thresholds;
  const banner = el('alertBanner');
  banner.className = 'alert-banner '+alert;
  const states = {quiet:['QUIET','Nominal — low flare risk'], watch:['WATCH','Elevated risk — monitoring'],
                  warning:['WARNING','High flare risk in next 15 min'], nocov:['NO DATA','Insufficient coverage']};
  el('alertState').textContent = states[alert][0];
  el('alertDesc').textContent = states[alert][1];
  if(p15==null){            // GTI gap → no forecast
    el('riskBig').textContent='— —';
    el('riskBig').style.color='var(--nocov)';
    el('riskBand').textContent='insufficient coverage — no forecast';
    el('gaugeFill').style.width='0%';
    el('risk30').textContent='—'; el('risk60').textContent='—';
  } else {
    el('riskBig').textContent = (p15*100).toFixed(0)+'%';
    el('riskBig').style.color = alert==='warning'?'var(--warn)':(alert==='watch'?'#9a6f12':'var(--navy)');
    const lo=d.forecast.y_15min_lo[i], hi=d.forecast.y_15min_hi[i];
    el('riskBand').textContent = `90% band: ${(lo*100).toFixed(0)}% – ${(hi*100).toFixed(0)}%`;
    el('gaugeFill').style.width = Math.min(100, (p15/0.6)*100).toFixed(1)+'%';   // gauge spans 0–60% risk
    el('risk30').textContent = (p30*100).toFixed(0)+'%';
    el('risk60').textContent = (p60*100).toFixed(0)+'%';
  }
  // gauge threshold ticks (scaled to 0–60% gauge span)
  el('tickWatch').style.left = Math.min(100,(thr.watch/0.6)*100)+'%';
  el('tickWarn').style.left  = Math.min(100,(thr.warning/0.6)*100)+'%';
  // operational impact
  const imp = IMPACT[alert] || IMPACT.quiet;
  el('impactText').innerHTML = `<span class="pill">${imp.pill}</span>${imp.text}`;
  updateLead();
}

// lead-time callout: live countdown to the next upcoming flagged flare, then a won badge
function updateLead(){
  const d = S.d, tNow = d.forecast.t[S.minIdx];
  const lead = d.lead_times;
  // most recent flare with peak <= tNow
  let past = lead.filter(l=>l.peak <= tNow);
  let upcoming = lead.filter(l=>l.peak > tNow);
  const box = el('leadCallout');
  // live: an upcoming flare within 15 min that is flagged AND we are in warning now
  const alert = d.forecast.alert[S.minIdx];
  const nextFlagged = upcoming.find(l=>l.flagged && (l.peak - tNow) <= 900 && (l.peak - tNow) >= 0);
  if(alert==='warning' && nextFlagged){
    const mins = Math.ceil((nextFlagged.peak - tNow)/60);
    box.innerHTML = `<span class="live">⚠ WARNING ISSUED — ${nextFlagged.goes_class} flare peak in ~${mins} min</span>`;
    return;
  }
  // frozen badge: the most recent past flare
  if(past.length){
    const last = past[past.length-1];
    if(last.flagged){
      box.innerHTML = `<span class="won">✓ Warned ${last.lead_min} min ahead of ${last.goes_class} peak (${fmtUT(last.peak)} UT)</span>`;
    } else if(last.reason==='no_coverage'){
      box.innerHTML = `<span class="nocov">— ${last.goes_class} at ${fmtUT(last.peak)} UT: no detector coverage in pre-peak window (honest miss)</span>`;
    } else {
      box.innerHTML = `<span class="nocov">— ${last.goes_class} at ${fmtUT(last.peak)} UT: below Warning threshold</span>`;
    }
    return;
  }
  box.innerHTML = '';
}

// add vertical markers + GOES-class labels for flares that have peaked
function showFlares(tNow){
  const d = S.d;
  const peaked = d.actual_flares.filter(f=>f.peak <= tNow);
  if(peaked.length === S.lastFlareShown) return;
  S.lastFlareShown = peaked.length;
  const shapes = peaked.map(f=>({type:'line', xref:'x', yref:'paper',
    x0:isoNaive(f.peak), x1:isoNaive(f.peak), y0:0, y1:1,
    line:{color:f.letter==='X'?'#d35400':(f.letter==='M'?'#e0a526':'#cdd6e0'),
          width:f.letter==='X'?2.2:1, dash:'dot'}}));
  // label only X-class to avoid clutter on busy days (M/C shown as faint lines)
  const anns = peaked.filter(f=>f.letter==='X').map(f=>({
    x:isoNaive(f.peak), y:1, yref:'paper', yanchor:'bottom', text:'◆ '+f.goes_class,
    showarrow:false, font:{size:12,color:'#d35400',family:'Segoe UI'}, bgcolor:'rgba(255,255,255,.85)',
    bordercolor:'#d35400', borderpad:2}));
  Plotly.relayout('mainChart', {shapes, annotations:anns});
}

// utils
function upperBound(arr, val){ let lo=0, hi=arr.length; while(lo<hi){const m=(lo+hi)>>1; if(arr[m]<=val) lo=m+1; else hi=m;} return lo; }

// Re-size the light-curve chart to its container whenever Replay is (re)shown,
// so it always fills the card after a viewport/layout change.
function fitMainChart(){ const c=document.getElementById('mainChart');
  if(c && c.offsetParent!==null){ try{ Plotly.Plots.resize(c); }catch(_){} } }
window.addEventListener('tabchange', e=>{ if(e.detail!=='replay') return;
  requestAnimationFrame(()=>requestAnimationFrame(fitMainChart));
  setTimeout(fitMainChart, 250); });

init();
})();
