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
  bar.textContent = '⚠ ' + msg;
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
// One visual language for every chart in the app: consistent fonts, muted grid,
// visible axis lines/ticks, projector-legible sizing. Used across all tabs.
const PLOT_FONT   = {family:'"Segoe UI", Inter, system-ui, sans-serif', size:12.5, color:'#3a4a5c'};
const PLOT_GRID   = '#e8edf3';
const PLOT_AXIS   = '#c6d0dc';   // axis + tick colour
const PLOT_TICK   = {size:11.5, color:'#5a6b7d'};
// Detector colour family: soft→hard, cohesive (no default plotly blue).
const DET_COLORS  = {solexs_sdd2:'#1a3a5c', hel1os_cdte1:'#2e8b74',
                     hel1os_cdte2:'#4d7ba6', hel1os_czt1:'#d35400', hel1os_czt2:'#9c4a1e'};
function axisTitle(text, size){ return {text, font:{size:size||12.5, color:'#43566a'}, standoff:10}; }
// Base axis object; pass overrides (title, type, range, tickformat…).
function plotAxis(extra){
  return Object.assign({gridcolor:PLOT_GRID, linecolor:PLOT_AXIS, zerolinecolor:'#d7dfe8',
    ticks:'outside', tickcolor:PLOT_AXIS, ticklen:4, tickfont:PLOT_TICK,
    showline:true, mirror:false}, extra||{});
}
// Base layout; merge with chart-specific xaxis/yaxis/legend.
function plotLayout(extra){
  return Object.assign({paper_bgcolor:'#ffffff', plot_bgcolor:'#ffffff', font:PLOT_FONT,
    autosize:true,
    hoverlabel:{font:{family:PLOT_FONT.family,size:12}, bgcolor:'#12293f', bordercolor:'#12293f',
                align:'left'},
    margin:{l:56,r:16,t:14,b:44}}, extra||{});
}

// Resize every VISIBLE Plotly chart to fill its container. Plotly's own
// responsive:true does not reliably fire on programmatic viewport changes
// (projector / screenshot tooling), so we drive it explicitly on resize and
// on tab switch — guarantees charts fill their card rather than rendering tiny.
function resizeAllPlots(){
  if(!window.Plotly) return;
  document.querySelectorAll('.js-plotly-plot').forEach(d=>{
    if(d.offsetParent !== null){ try{ Plotly.Plots.resize(d); }catch(e){} }
  });
}
// Resize across a couple of animation frames + a delayed retry so it lands
// AFTER the browser has reflowed a newly-shown pane (grid columns settle late).
function resizeAllPlotsSoon(){
  requestAnimationFrame(()=>requestAnimationFrame(resizeAllPlots));
  setTimeout(resizeAllPlots, 250);
}
let _resizeTimer;
window.addEventListener('resize', ()=>{ clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(resizeAllPlotsSoon, 100); });
// After a tab becomes visible its charts have a real width — size them then.
window.addEventListener('tabchange', resizeAllPlotsSoon);
// Most robust path: watch the panes themselves. A ResizeObserver fires whenever a
// pane's box actually changes size — catching projector/emulated viewport changes
// that never dispatch a window 'resize' event. Observing the pane (not the plot)
// avoids a feedback loop, since resizing the inner plot doesn't change the pane.
if(window.ResizeObserver){
  const _ro = new ResizeObserver(()=>{ clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(resizeAllPlots, 80); });
  document.querySelectorAll('.tabpane').forEach(p=>_ro.observe(p));
}
