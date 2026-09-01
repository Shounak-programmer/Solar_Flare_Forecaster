// Operations console — snapshot of one active day at a chosen "NOW" (replay-driven).
(function(){
const DETS = [
  {key:'solexs_sdd2',  label:'SoLEXS SDD2', color:DET_COLORS.solexs_sdd2},
  {key:'hel1os_cdte1', label:'CdTe1',       color:DET_COLORS.hel1os_cdte1},
  {key:'hel1os_cdte2', label:'CdTe2',       color:DET_COLORS.hel1os_cdte2},
  {key:'hel1os_czt1',  label:'CZT1',        color:DET_COLORS.hel1os_czt1},
  {key:'hel1os_czt2',  label:'CZT2',        color:DET_COLORS.hel1os_czt2},
];
const IMPACT = {
  quiet:   {pill:'NOMINAL', text:'No significant flare expected in the next 15 minutes. Normal operations.'},
  watch:   {pill:'WATCH',   text:'Elevated flare risk. Satellite operators &amp; HF-radio users on notice; monitor for escalation.'},
  warning: {pill:'WARNING', text:'High flare risk within ~15 minutes. Possible HF radio degradation/blackout on sunlit &amp; polar routes; satellite operators advised to defer sensitive operations — a 10–15 min protective lead.'},
  nocov:   {pill:'NO DATA', text:'Insufficient detector coverage — <b>no forecast issued</b>. The system does not guess during data gaps.'},
};
let inited=false, OD=null;   // current day data
const el=id=>document.getElementById(id);

window.addEventListener('tabchange', e=>{ if(e.detail==='operations') init(); });

async function init(){
  if(inited){ Plotly.Plots.resize('opsChart'); return; }
  let manifest;
  try{ manifest=await fetchJSON('/api/replay_days'); }catch(err){ showError('ops: '+err.message); return; }
  inited=true;
  // prefer the most recent active held-out day as the live "feed"
  const order=['20260201','20260118','20251114','20260204','20260320','20241003','20241001'];
  const days=manifest.demo_days.slice().sort((a,b)=>order.indexOf(a.date)-order.indexOf(b.date));
  el('opsDaySelect').innerHTML=days.map(d=>`<option value="${d.date}">${d.label} · ${d.date.slice(0,4)}-${d.date.slice(4,6)}-${d.date.slice(6)} ${d.in_sample?'[in-sample]':'[held-out]'}</option>`).join('');
  el('opsDaySelect').addEventListener('change',e=>loadDay(e.target.value));
  el('opsScrub').addEventListener('input',e=>renderNow(+e.target.value));
  await loadDay(days[0].date);
}

async function loadDay(date){
  let d;
  try{ d=await fetchJSON('/api/replay/'+date); }catch(err){ showError('ops '+date+': '+err.message); return; }
  OD={d, date, lcStr:d.lc_t.map(isoNaive), t0:d.forecast.t[0]};
  buildChart();
  // default NOW = the peak-risk minute (the most active, always-covered snapshot)
  const p=d.forecast.y_15min.map(v=>v==null?-1:v);
  let nowMin=p.indexOf(Math.max(...p)); if(nowMin<0)nowMin=720;
  el('opsScrub').value=nowMin;
  renderNow(nowMin);
}

function buildChart(){
  const traces=DETS.map(dd=>({type:'scattergl',mode:'lines',name:dd.label,x:[],y:[],
    line:{color:dd.color,width:1.9},connectgaps:false,hoverinfo:'name+y'}));
  Plotly.react('opsChart',traces,layout(),{displayModeBar:false,responsive:true});
}
function layout(){
  return plotLayout({margin:{l:58,r:16,t:14,b:52},
    xaxis:plotAxis({type:'date',tickformat:'%H:%M',title:axisTitle('Time (UT)',11.5)}),
    yaxis:plotAxis({type:'log',title:axisTitle('counts s⁻¹',11.5)}),
    legend:{orientation:'h',y:-0.2,x:.5,xanchor:'center',yanchor:'top',font:{size:11},
            bgcolor:'rgba(255,255,255,0)'},showlegend:true});
}

function renderNow(min){
  const d=OD.d; min=Math.max(0,Math.min(min,d.forecast.t.length-1));
  const nowUnix=d.forecast.t[min];
  // trailing 3 h light-curve window up to NOW
  const lo=nowUnix-3*3600;
  const li0=lowerBound(d.lc_t,lo), li1=upperBound(d.lc_t,nowUnix);
  const xs=OD.lcStr.slice(li0,li1);
  const upd={x:[],y:[]};
  let online=0;
  DETS.forEach(dd=>{ const seg=d.detectors[dd.key].rate.slice(li0,li1); upd.x.push(xs); upd.y.push(seg);
    if(seg.some(v=>v!=null)) online++; });
  Plotly.restyle('opsChart',upd,[0,1,2,3,4]);
  Plotly.relayout('opsChart',{'xaxis.range':[isoNaive(lo),isoNaive(nowUnix)]});
  // forecast + alert
  const p15=d.forecast.y_15min[min], p30=d.forecast.y_30min[min], p60=d.forecast.y_60min[min];
  const alert=d.forecast.alert[min];
  el('opsAlertState').className='ops-alert-state '+alert;
  el('opsAlertState').textContent={quiet:'QUIET',watch:'WATCH',warning:'WARNING',nocov:'NO DATA'}[alert];
  if(p15==null){ el('opsRisk15').textContent='— —'; el('opsBand').textContent='insufficient coverage'; el('opsRisk30').textContent='—'; el('opsRisk60').textContent='—'; }
  else{
    el('opsRisk15').textContent=(p15*100).toFixed(0)+'%';
    el('opsRisk15').style.color=alert==='warning'?'var(--warn)':(alert==='watch'?'#9a6f12':'var(--navy)');
    el('opsBand').textContent=`90% band ${(d.forecast.y_15min_lo[min]*100).toFixed(0)}–${(d.forecast.y_15min_hi[min]*100).toFixed(0)}%`;
    el('opsRisk30').textContent=(p30*100).toFixed(0)+'%'; el('opsRisk60').textContent=(p60*100).toFixed(0)+'%';
  }
  // context
  const c=d.forecast.context;
  el('ctxHard').textContent=fmt(c.hardness_ratio[min],2);
  el('ctxNeu').textContent=fmt(c.neupert_resid[min],0);
  el('ctxTSL').textContent=tsl(c.time_since_last_s[min]);
  el('ctxF107').textContent=fmt(c.f107[min],0);
  el('ctxSSN').textContent=fmt(c.sunspot[min],0);
  el('ctxAR').textContent=c.ar_count[min]==null?'n/a':fmt(c.ar_count[min],0);
  // impact
  const imp=IMPACT[alert]||IMPACT.quiet;
  el('opsImpact').innerHTML=`<span class="pill">${imp.pill}</span>${imp.text}`;
  // status bar
  el('opsClock').textContent=fmtUT(nowUnix)+' UT';
  el('opsScrubLabel').textContent=fmtUT(nowUnix)+' UT';
  el('opsUpdate').textContent=fmtUT(nowUnix)+' UT';
  el('opsCoverage').textContent=(d.forecast.coverage_pct!=null?d.forecast.coverage_pct.toFixed(0):'–')+'%';
  el('opsDetOnline').textContent=online+'/5';
  const led=el('ledDet'); led.className='led '+(online===5?'':(online>0?'partial':'down'));
}

function fmt(v,dp){ return v==null||isNaN(v)?'n/a':(+v).toFixed(dp); }
function tsl(s){ if(s==null||isNaN(s)) return '> 6 h'; s=+s; if(s<60) return Math.round(s)+' s';
  if(s<3600) return Math.round(s/60)+' min'; return (s/3600).toFixed(1)+' h'; }
function lowerBound(a,v){let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<v)lo=m+1;else hi=m;}return lo;}
function upperBound(a,v){let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<=v)lo=m+1;else hi=m;}return lo;}
})();
