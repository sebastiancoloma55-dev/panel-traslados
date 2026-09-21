import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        #MainMenu,
        footer,
        header,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        html, body,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        .main,
        .main .block-container,
        [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        [data-testid="stAppViewContainer"] {
            overflow: visible !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('\n<style id="streamlit-background-final">\nhtml,body,\n[data-testid="stApp"],\n[data-testid="stAppViewContainer"],\n[data-testid="stMain"],\n[data-testid="stMainBlockContainer"],\n.main,.main .block-container{\n  background:#eef8f2 !important;\n  margin:0 !important;\n  padding:0 !important;\n}\n[data-testid="stVerticalBlock"]{\n  gap:0 !important;\n}\niframe{\n  display:block !important;\n  width:100% !important;\n  border:0 !important;\n}\n</style>\n', unsafe_allow_html=True)

index_path = Path(__file__).with_name("index.html")
if not index_path.exists():
    st.error("No se encontró index.html junto a app.py.")
    st.stop()

html_content = index_path.read_text(encoding="utf-8")
html_content = html_content.replace("</head>", '\n<style id="iframe-fill-final">\nhtml,body{\n  background:#eef8f2 !important;\n  min-height:100vh !important;\n}\n.app-shell{\n  min-height:100vh !important;\n  background:#eef8f2 !important;\n}\n.main{\n  min-height:calc(100vh - 18px) !important;\n  background:#eef8f2 !important;\n}\n.main > .tab-panel{\n  min-height:calc(100vh - 110px) !important;\n}\n</style>\n', 1)

# El login y almacenamiento central se inyectan dentro del mismo IIFE
# del index para poder reemplazar las funciones internas sin rehacer la UI.
central_sync = r"""

/* ====== SINCRONIZACION CENTRAL PANEL-TRASLADOS ====== */
var CENTRAL_API = 'https://yloqgvpgtbbjzogkxfic.supabase.co/functions/v1/panel-api';
var CENTRAL_TOKEN = null;
var CENTRAL_USER_KEY = 'panelCentralUser';
var CENTRAL_TOKEN_KEY = 'panelCentralToken';

function centralStorageGet(key){
  try { return localStorage.getItem(key) || sessionStorage.getItem(key) || ''; } catch(e){ return ''; }
}
function centralStorageSet(key, value, remember){
  try {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
    (remember ? localStorage : sessionStorage).setItem(key, value);
  } catch(e) {}
}
function centralStorageClear(){
  try { localStorage.removeItem(CENTRAL_TOKEN_KEY); localStorage.removeItem(CENTRAL_USER_KEY); sessionStorage.removeItem(CENTRAL_TOKEN_KEY); sessionStorage.removeItem(CENTRAL_USER_KEY); } catch(e) {}
}
function centralTokenPayload(token){
  try {
    var p = token.split('.')[1];
    var b = p.replace(/-/g,'+').replace(/_/g,'/').padEnd(Math.ceil(p.length/4)*4,'=');
    return JSON.parse(atob(b));
  } catch(e){ return null; }
}
function centralTokenValid(token){
  var p = centralTokenPayload(token);
  return !!(p && p.exp && p.exp > Date.now());
}
function centralHeaders(extra){
  var h = { 'Content-Type':'application/json' };
  if(CENTRAL_TOKEN) h.Authorization = 'Bearer ' + CENTRAL_TOKEN;
  if(extra) Object.keys(extra).forEach(function(k){ h[k] = extra[k]; });
  return h;
}
function centralRequest(path, options){
  options = options || {};
  return fetch(CENTRAL_API + path, {
    method: options.method || 'GET',
    headers: centralHeaders(options.headers),
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  }).then(function(r){
    return r.text().then(function(text){
      var data = {};
      try { data = text ? JSON.parse(text) : {}; } catch(e) { data = { error:text || 'Respuesta inválida' }; }
      if(!r.ok){
        var err = new Error(data.error || ('HTTP ' + r.status));
        err.status = r.status;
        throw err;
      }
      return data;
    });
  });
}
function centralStoreName(storeName){ return storeName; }

var _localDbGetAll = dbGetAll;
var _localDbPut = dbPut;
var _localDbBulkPut = dbBulkPut;
var _localDbClear = dbClear;

function centralLoadState(){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return Promise.reject(new Error('NO_CENTRAL_SESSION'));
  return centralRequest('/state').then(function(result){
    var s = result.state || {};
    state.colaboradores = s.colaboradores || [];
    state.sucursales = s.sucursales || [];
    state.traslados = s.traslados || [];
    state.licencias = s.licencias || [];
    state.vacaciones = s.vacaciones || [];
    state.usuarios = s.usuarios || [];
    state.auditoria = s.auditoria || [];
    if(result.user && currentUser) currentUser = Object.assign({}, currentUser, result.user);
    return sincronizarTrasladosConColaboradores();
  });
}

/* Desde que existe sesión central, las lecturas salen de PostgreSQL. */
dbGetAll = function(storeName){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbGetAll(storeName);
  return centralRequest('/state').then(function(result){
    var rows = (result.state || {})[centralStoreName(storeName)] || [];
    return rows;
  });
};

dbPut = function(storeName, obj){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbPut(storeName, obj);
  return centralRequest('', { method:'POST', body:{ action:'upsert', table:centralStoreName(storeName), record:obj } }).then(function(){ return obj; });
};

dbBulkPut = function(storeName, arr){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbBulkPut(storeName, arr);
  if(!arr || !arr.length) return Promise.resolve();
  return centralRequest('', { method:'POST', body:{ action:'bulkUpsert', table:centralStoreName(storeName), records:arr } }).then(function(){ return arr; });
};

dbClear = function(storeName){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbClear(storeName);
  return centralRequest('', { method:'POST', body:{ action:'clear', table:centralStoreName(storeName) } }).then(function(){ return true; });
};

/* Recarga central: reemplaza por completo el estado que usa la interfaz. */
reloadStateFromDB = function(){
  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)){
    return _localDbGetAll(STORES.COLAB).then(function(colab){
      return Promise.all([
        Promise.resolve(colab), _localDbGetAll(STORES.SUC), _localDbGetAll(STORES.TRAS), _localDbGetAll(STORES.LIC), _localDbGetAll(STORES.VAC), _localDbGetAll(STORES.USERS), _localDbGetAll(STORES.AUDIT)
      ]).then(function(results){
        state.colaboradores=results[0]; state.sucursales=results[1]; state.traslados=results[2]; state.licencias=results[3]; state.vacaciones=results[4]; state.usuarios=results[5]; state.auditoria=results[6]||[];
        return sincronizarTrasladosConColaboradores();
      });
    });
  }
  return centralLoadState().catch(function(err){
    if(err && err.status === 401){
      CENTRAL_TOKEN = null;
      centralStorageClear();
      currentUser = null;
      showLogin();
    }
    throw err;
  });
};

/* Login centralizado contra PostgreSQL/Supabase. */
loginUser = function(){
  var username = document.getElementById('loginUsername').value.trim();
  var password = document.getElementById('loginPassword').value;
  var remember = document.getElementById('loginRemember').checked;
  if(!username || !password){ showLogin('Ingrese usuario y contraseña.'); return; }
  var btn = document.getElementById('btnLogin');
  if(btn) btn.disabled = true;
  centralRequest('/login', { method:'POST', body:{ username:username, password:password } }).then(function(result){
    CENTRAL_TOKEN = result.token;
    currentUser = result.user;
    centralStorageSet(CENTRAL_TOKEN_KEY, CENTRAL_TOKEN, remember);
    centralStorageSet(CENTRAL_USER_KEY, JSON.stringify(currentUser), remember);
    return centralLoadState();
  }).then(function(){
    hideLogin();
    updateSessionUI();
    rerenderAll();
    if(typeof bootAdv === 'function') bootAdv();
    switchTab('resumen');
    showToast('Bienvenido, ' + (currentUser.nombre || currentUser.username) + '.', 'success');
  }).catch(function(err){
    console.error('Login central:', err);
    var msg = (err && err.message) ? String(err.message) : '';
    if(/sesión no válida|sesion no valida|sesión expiró|sesion expiro|expirada|expired/i.test(msg)){
      msg = 'No fue posible validar el acceso. Intente nuevamente.';
    }
    showLogin(msg || 'No fue posible iniciar sesión.');
  }).finally(function(){ if(btn) btn.disabled = false; });
};

restoreSession = function(){
  var token = centralStorageGet(CENTRAL_TOKEN_KEY);
  var rawUser = centralStorageGet(CENTRAL_USER_KEY);
  if(!token || !centralTokenValid(token) || !rawUser){
    CENTRAL_TOKEN = null;
    centralStorageClear();
    return false;
  }
  try {
    CENTRAL_TOKEN = token;
    currentUser = JSON.parse(rawUser);
    if(!currentUser || !currentUser.username){ throw new Error('bad session'); }
    hideLogin();
    updateSessionUI();
    return true;
  } catch(e){
    CENTRAL_TOKEN = null;
    centralStorageClear();
    currentUser = null;
    return false;
  }
};

logout = function(){
  currentUser = null;
  CENTRAL_TOKEN = null;
  centralStorageClear();
  updateSessionUI();
  var u=document.getElementById('loginUsername'); var p=document.getElementById('loginPassword');
  if(u) u.value=''; if(p) p.value='';
  showLogin();
};

/* Eliminaciones directas para no borrar y reconstruir tablas completas. */
deleteColaborador = function(rut){
  if(!confirm('¿Eliminar este colaborador?')) return;
  centralRequest('', {method:'POST', body:{action:'delete', table:'colaboradores', record:{rut:rut}}}).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Colaborador eliminado.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar el colaborador.','error');});
};
deleteSucursal = function(codigo){
  if(!confirm('¿Eliminar esta sucursal?')) return;
  centralRequest('', {method:'POST', body:{action:'delete', table:'sucursales', record:{codigo:codigo}}}).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Sucursal eliminada.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar la sucursal.','error');});
};
eliminarTraslado = function(id){
  if(!confirm('¿Eliminar este traslado?')) return;
  centralRequest('', {method:'POST', body:{action:'delete', table:'traslados', record:{id:id}}}).then(reloadStateFromDB).then(function(){return sincronizarTrasladosConColaboradores();}).then(function(){rerenderAll();showToast('Traslado eliminado.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar el traslado.','error');});
};

/* El respaldo conserva su exportación local, pero la restauración queda centralizada. */
var _localImportBackup = importBackup;
importBackup = function(file){
  var reader = new FileReader();
  reader.onload = function(){
    try {
      var d = JSON.parse(reader.result);
      if(!d || !Array.isArray(d.colaboradores) || !Array.isArray(d.sucursales)) throw new Error('Formato inválido');
      if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) throw new Error('Debe iniciar sesión nuevamente.');
      Promise.all([
        centralRequest('',{method:'POST',body:{action:'clear',table:'colaboradores'}}),
        centralRequest('',{method:'POST',body:{action:'clear',table:'sucursales'}}),
        centralRequest('',{method:'POST',body:{action:'clear',table:'traslados'}}),
        centralRequest('',{method:'POST',body:{action:'clear',table:'vacaciones'}}),
        centralRequest('',{method:'POST',body:{action:'clear',table:'licencias'}}),
        centralRequest('',{method:'POST',body:{action:'clear',table:'auditoria'}})
      ]).then(function(){
        return Promise.all([
          dbBulkPut(STORES.COLAB,d.colaboradores), dbBulkPut(STORES.SUC,d.sucursales), dbBulkPut(STORES.TRAS,d.traslados||[]), dbBulkPut(STORES.VAC,d.vacaciones||[]), dbBulkPut(STORES.LIC,d.licencias||[]), dbBulkPut(STORES.AUDIT,d.auditoria||[])
        ]);
      }).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Respaldo restaurado correctamente.','success');}).catch(function(err){console.error(err);showToast(err.message||'No fue posible restaurar el respaldo.','error');});
    } catch(e){ showToast(e.message||'El archivo no tiene un respaldo válido.','error'); }
  };
  reader.readAsText(file);
};


/* ====== TEMA VERDE PASTEL + EXPERIENCIA INTERACTIVA ====== */
(function(){
  var style=document.createElement('style');
  style.id='panelPastelGreenTheme';
  style.textContent=`
    :root{
      --ink:#164437 !important;
      --ink-2:#205B48 !important;
      --ink-3:#2D705A !important;
      --paper:#F2F8F4 !important;
      --surface:#FFFFFF !important;
      --amber:#D6A23A !important;
      --amber-dark:#9A6B12 !important;
      --amber-soft:#FFF1CC !important;
      --teal:#58A982 !important;
      --teal-dark:#277454 !important;
      --teal-soft:#DDF3E7 !important;
      --terracotta:#D7655B !important;
      --terracotta-dark:#A83D35 !important;
      --terracotta-soft:#FBE2DF !important;
      --gold:#D6A23A !important;
      --gold-soft:#FFF1CC !important;
      --purple:#7893B5 !important;
      --purple-dark:#526E91 !important;
      --purple-soft:#E8EEF7 !important;
      --slate:#596D66 !important;
      --slate-light:#8A9C95 !important;
      --border:#DDEBE3 !important;
      --border-strong:#C7DDD1 !important;
      --shadow-sm:0 2px 8px rgba(31,84,63,.07) !important;
      --shadow-md:0 10px 28px rgba(31,84,63,.10) !important;
    }
    body{background:linear-gradient(135deg,#F3F9F5 0%,#EDF7F1 100%) !important;}
    .sidebar{background:linear-gradient(180deg,#174A3B 0%,#1F604B 100%) !important;}
    .nav-item.active{background:#DDF3E7 !important;color:#164437 !important;box-shadow:0 5px 18px rgba(50,120,88,.16) !important;}
    .nav-badge{background:rgba(255,255,255,.15) !important;}
    .btn-primary{background:#277454 !important;border-color:#277454 !important;}
    .btn-primary:hover{background:#1F6247 !important;transform:translateY(-1px);}
    .card,.table-wrap,.ticket{border-color:#DDEBE3 !important;box-shadow:0 4px 16px rgba(31,84,63,.07) !important;}
    .kpi-board{background:linear-gradient(135deg,#174A3B,#2D705A) !important;}
    .kpi-value.teal{color:#B9F0D0 !important;}
    .toolbar .input,.toolbar select,.input,select,textarea{border-color:#C7DDD1 !important;}
    .toolbar .input:focus,.input:focus,select:focus,textarea:focus{border-color:#58A982 !important;box-shadow:0 0 0 3px rgba(88,169,130,.14) !important;}
    .tickets-grid{grid-template-columns:repeat(auto-fill,minmax(360px,1fr)) !important;gap:16px !important;}
    .ticket{border-top-width:5px !important;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease !important;}
    .ticket:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(31,84,63,.12) !important;}
    .ticket-aprobado{border-top-color:#58A982 !important;background:linear-gradient(180deg,#FFFFFF,#F7FCF9) !important;}
    .ticket-espera{border-top-color:#D6A23A !important;background:linear-gradient(180deg,#FFFFFF,#FFFDF7) !important;}
    .ticket-rechazado{border-top-color:#D7655B !important;background:linear-gradient(180deg,#FFFFFF,#FFF9F8) !important;}
    .ticket-pendiente{border-top-color:#7893B5 !important;background:linear-gradient(180deg,#FFFFFF,#F9FBFD) !important;}
    .ticket-aprobado .pill-teal{background:#DDF3E7 !important;color:#277454 !important;}
    .ticket-espera .pill-amber{background:#FFF1CC !important;color:#9A6B12 !important;}
    .ticket-rechazado .pill-terracotta{background:#FBE2DF !important;color:#A83D35 !important;}
    .ticket-pendiente .pill-slate{background:#E8EEF7 !important;color:#526E91 !important;}
    .route-arrow{color:#58A982 !important;}
    .icon-btn{border-color:#DDEBE3 !important;background:#F4F9F6 !important;}
    .icon-btn:hover{background:#DDF3E7 !important;color:#277454 !important;}
    .row-vacacion{background:#F0FAF4 !important;}
    .row-ausente{background:#F0F5FB !important;}
    .status-stack .pill-teal{background:#DDF3E7 !important;color:#277454 !important;}
    .tras-interactive-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 16px;}
    .tras-summary-card{background:#fff;border:1px solid #DDEBE3;border-radius:14px;padding:14px 16px;box-shadow:0 4px 14px rgba(31,84,63,.06);cursor:pointer;transition:.18s ease;position:relative;overflow:hidden;}
    .tras-summary-card:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(31,84,63,.10);}
    .tras-summary-card .label{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#71857D;font-weight:700;}
    .tras-summary-card .num{font-size:28px;font-weight:800;line-height:1.1;margin-top:5px;color:#164437;}
    .tras-summary-card.aprobado{border-left:5px solid #58A982;}
    .tras-summary-card.espera{border-left:5px solid #D6A23A;}
    .tras-summary-card.rechazado{border-left:5px solid #D7655B;}
    .tras-summary-card.pendiente{border-left:5px solid #7893B5;}
    .tras-interactive-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 16px;background:rgba(255,255,255,.78);padding:10px;border:1px solid #DDEBE3;border-radius:13px;backdrop-filter:blur(8px);}
    .tras-interactive-toolbar input,.tras-interactive-toolbar select{height:40px;border:1px solid #C7DDD1;border-radius:9px;background:#fff;padding:0 12px;color:#164437;}
    .tras-interactive-toolbar input{flex:1;min-width:240px;}
    .tras-interactive-toolbar select{min-width:190px;}
    .tras-filter-count{font-size:12px;color:#71857D;font-weight:600;margin-left:auto;}
    @media(max-width:850px){.tras-interactive-summary{grid-template-columns:repeat(2,1fr)}.tras-filter-count{width:100%;margin-left:0}.tickets-grid{grid-template-columns:1fr !important;}}
  `;
  document.head.appendChild(style);
})();

(function(){
  /* Usuarios nuevos recuperan inmediatamente TODA la base central al entrar. */
  var _centralRestoreSession = restoreSession;
  restoreSession = function(){
    var ok=_centralRestoreSession();
    if(ok && CENTRAL_TOKEN && centralTokenValid(CENTRAL_TOKEN)){
      centralLoadState().then(function(){
        updateSessionUI();
        rerenderAll();
        if(typeof bootAdv==='function')bootAdv();
      }).catch(function(err){console.error('Carga central inicial:',err);});
    }
    return ok;
  };

  /* Vista interactiva de traslados: filtros + resumen por estado. */
  var _renderTrasladosBase=renderTraslados;
  renderTraslados=function(){
    _renderTrasladosBase();
    var tab=document.getElementById('tab-traslados');
    var grid=document.getElementById('trasladosGrid');
    if(!tab || !grid) return;

    var list=state.traslados||[];
    var counts={total:list.length,pendiente:0,espera:0,aprobado:0,rechazado:0};
    list.forEach(function(t){if(counts[t.estado]!==undefined)counts[t.estado]++;});

    var summary=tab.querySelector('.tras-interactive-summary');
    if(!summary){
      summary=document.createElement('div');
      summary.className='tras-interactive-summary';
      grid.parentNode.insertBefore(summary,grid);
    }
    summary.innerHTML='';
    [
      ['total','Total','tras-summary-card'],
      ['aprobado','Aprobados','tras-summary-card aprobado'],
      ['espera','En observación','tras-summary-card espera'],
      ['rechazado','Rechazados','tras-summary-card rechazado']
    ].forEach(function(item){
      var c=document.createElement('div');c.className=item[2];c.setAttribute('data-status-filter',item[0]);
      c.innerHTML='<div class="label">'+item[1]+'</div><div class="num">'+counts[item[0]]+'</div>';
      c.addEventListener('click',function(){
        var sel=document.getElementById('trasStatusFilter');
        if(sel){sel.value=item[0]==='total'?'':item[0];sel.dispatchEvent(new Event('change'));}
      });
      summary.appendChild(c);
    });

    var bar=tab.querySelector('.tras-interactive-toolbar');
    if(!bar){
      bar=document.createElement('div');
      bar.className='tras-interactive-toolbar';
      var input=document.createElement('input');
      input.id='trasSearch';input.placeholder='Buscar colaborador, RUT, origen o destino...';
      var select=document.createElement('select');select.id='trasStatusFilter';
      select.innerHTML='<option value="">Todos los estados</option><option value="pendiente">Pendientes</option><option value="espera">En observación</option><option value="aprobado">Aprobados</option><option value="rechazado">Rechazados</option>';
      var count=document.createElement('span');count.className='tras-filter-count';count.id='trasFilterCount';
      bar.appendChild(input);bar.appendChild(select);bar.appendChild(count);
      grid.parentNode.insertBefore(bar,grid);
      function apply(){
        var q=(input.value||'').toLowerCase().trim(), st=select.value||'';
        var cards=grid.children, visible=0;
        for(var i=0;i<cards.length;i++){
          var card=cards[i], okText=!q || (card.textContent||'').toLowerCase().indexOf(q)!==-1;
          var okStatus=!st || card.classList.contains('ticket-'+st);
          card.style.display=(okText&&okStatus)?'':'none';
          if(okText&&okStatus)visible++;
        }
        count.textContent='Mostrando '+visible+' de '+list.length+' traslados';
      }
      input.addEventListener('input',apply);select.addEventListener('change',apply);
      bar.__apply=apply;
    }
    var badge=document.getElementById('navBadgeTras');
    if(badge)badge.textContent=String(list.length);
    if(bar.__apply)bar.__apply();
  };
})();

/* ====== FIN SINCRONIZACION CENTRAL ====== */

"""

marker = "function init(){"
if marker not in html_content:
    st.error("No se encontró el punto de integración de sincronización en index.html.")
    st.stop()

html_content = html_content.replace(marker, central_sync + "\n" + marker, 1)
html_content = html_content.replace(
    "Primer acceso: usuario <strong>admin</strong> · contraseña <strong>Admin123!</strong>. Por seguridad, puede cambiarla desde <strong>Usuarios</strong>.",
    "Acceso administrado centralmente. Por seguridad, cambie la contraseña desde <strong>Usuarios</strong>."
)

st.components.v1.html(
    html_content,
    height=1000,
    scrolling=True,
)
