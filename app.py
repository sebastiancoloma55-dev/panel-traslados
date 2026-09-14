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

index_path = Path(__file__).with_name("index.html")
if not index_path.exists():
    st.error("No se encontró index.html junto a app.py.")
    st.stop()

html_content = index_path.read_text(encoding="utf-8")

# El login y almacenamiento central se inyectan dentro del mismo IIFE
# del index para poder reemplazar las funciones internas sin rehacer la UI.
central_sync = r"""

/* ====== SINCRONIZACION CENTRAL PANEL-TRASLADOS ====== */
var CENTRAL_API = 'https://yloqvgpgtbbjzogkxfic.supabase.co/functions/v1/panel-api';
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
      showLogin('La sesión expiró. Inicie sesión nuevamente.');
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
    showLogin(err && err.message ? err.message : 'No fue posible iniciar sesión.');
  }).finally(function(){ if(btn) btn.disabled = false; });
};

restoreSession = function(){
  var token = centralStorageGet(CENTRAL_TOKEN_KEY);
  var rawUser = centralStorageGet(CENTRAL_USER_KEY);
  if(!token || !centralTokenValid(token) || !rawUser){
    CENTRAL_TOKEN = null;
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
