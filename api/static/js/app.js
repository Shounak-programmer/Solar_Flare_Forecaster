// Shared helpers: fetch, error bar, tab navigation.
async function fetchJSON(path){
  const r = await fetch(path);
  if(!r.ok){
    let detail = r.statusText;
    try{ detail = (await r.json()).detail || detail; }catch(e){}
    throw new Error(`${path}: ${r.status} ${detail}`);
  }
  return r.json();
}

function showError(msg){
  const bar = document.getElementById('errBar');
  bar.textContent = 'SYSTEM NOTIFICATION: ' + msg;
  bar.style.display = 'block';
  clearTimeout(showError._t);
  showError._t = setTimeout(()=>{ bar.style.display='none'; }, 6000);
}

// Tab navigation (panes that exist; placeholders for later stages)
document.querySelectorAll('.tab').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    if(btn.disabled) return;
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t===btn));
    document.querySelectorAll('.tabpane').forEach(p=>p.classList.toggle('active', p.id==='tab-'+tab));
    window.dispatchEvent(new CustomEvent('tabchange',{detail:tab}));
  });
});

function fmtUT(unix){
  const d = new Date(unix*1000);
  return String(d.getUTCHours()).padStart(2,'0')+':'+String(d.getUTCMinutes()).padStart(2,'0');
}

// Naive-UTC datetime string for Plotly x-axes (Plotly renders Date objects in the
// browser's local TZ; a naive string is displayed verbatim → forces true UTC display).
function isoNaive(unix){
  const d = new Date(unix*1000), p = n => String(n).padStart(2,'0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())} `+
         `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

// ── shared Plotly theme ─────────────────────────────────────────────────────
// Clean scientific mission console theme: high contrast light background, subtle grids,
// crisp aerospace telemetry traces.
const PLOT_FONT   = {family:'"Inter", -apple-system, system-ui, sans-serif', size:11.5, color:'#475569'};
const PLOT_GRID   = 'rgba(0, 0, 0, 0.07)';
const PLOT_AXIS   = 'rgba(0, 0, 0, 0.20)';   // axis + tick colour
const PLOT_TICK   = {size:11, color:'#64748b'};
// Coherent scientific trace palette (aerospace telemetry on light backgrounds):
// SoLEXS SDD2 (sky blue), HEL1OS CdTe1 (teal), HEL1OS CdTe2 (indigo),
// HEL1OS CZT1 (warm amber), HEL1OS CZT2 (rose red).
const DET_COLORS  = {
  solexs_sdd2:  '#0284c7',
  hel1os_cdte1: '#0d9488',
  hel1os_cdte2: '#6366f1',
  hel1os_czt1:  '#d97706',
  hel1os_czt2:  '#e11d48'
};
function axisTitle(text, size){ return {text, font:{size:size||11.5, color:'#475569'}, standoff:10}; }
// Base axis object; pass overrides (title, type, range, tickformat…).
function plotAxis(extra){
  return Object.assign({gridcolor:PLOT_GRID, linecolor:PLOT_AXIS, zerolinecolor:'rgba(0, 0, 0, 0.12)',
    ticks:'outside', tickcolor:PLOT_AXIS, ticklen:4, tickfont:PLOT_TICK,
    showline:true, mirror:false}, extra||{});
}
// Base layout; merge with chart-specific xaxis/yaxis/legend.
function plotLayout(extra){
  return Object.assign({paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'#ffffff', font:PLOT_FONT,
    autosize:true,
    hoverlabel:{font:{family:PLOT_FONT.family,size:11.5,color:'#0f172a'}, bgcolor:'#ffffff', bordercolor:'#cbd5e1',
                align:'left'},
    margin:{l:56,r:16,t:14,b:44}}, extra||{});
}

// Resize every VISIBLE Plotly chart to fill its container.
// Uses getBoundingClientRect & offsetWidth for reliable visibility checks across
// Apple Safari / WebKit (where offsetParent can return null for SVG/transformed elements).
function resizeAllPlots(){
  if(!window.Plotly) return;
  document.querySelectorAll('.js-plotly-plot, .chart').forEach(d=>{
    const hasSize = (d.offsetWidth > 0 || d.offsetHeight > 0 ||
      (d.getBoundingClientRect && d.getBoundingClientRect().width > 0));
    if(hasSize && d.classList.contains('js-plotly-plot')){
      try { Plotly.Plots.resize(d); } catch(e){}
    }
  });
}

// Multi-stage resize scheduler: fires on next frame, +120ms (post-reflow),
// and +350ms (post CSS transition/animation) to guarantee Apple Safari/WebKit
// and mobile devices render full-width charts.
function resizeAllPlotsSoon(){
  requestAnimationFrame(()=>requestAnimationFrame(resizeAllPlots));
  setTimeout(resizeAllPlots, 120);
  setTimeout(resizeAllPlots, 350);
}

let _resizeTimer;
window.addEventListener('resize', ()=>{
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(resizeAllPlotsSoon, 60);
});

// Orientation change on phones and tablets
window.addEventListener('orientationchange', ()=>{
  setTimeout(resizeAllPlotsSoon, 150);
});

// Tab visibility changes
window.addEventListener('tabchange', ()=>{
  resizeAllPlotsSoon();
  setTimeout(resizeAllPlots, 500);
});

// Robust ResizeObserver: observes both the tabpanes and individual chart cards
if(typeof window.ResizeObserver !== 'undefined'){
  const _ro = new ResizeObserver(()=>{
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(resizeAllPlots, 50);
  });
  document.querySelectorAll('.tabpane, .chart-card, .chart, .perf-grid, .ops-grid').forEach(p=>_ro.observe(p));
}
