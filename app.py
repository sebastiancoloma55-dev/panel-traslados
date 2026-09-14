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
\n/* ====== SINCRONIZACION CENTRAL PANEL-TRASLADOS ====== */\nvar CENTRAL_API = 'https://yloqvgptbbjzogkxfic.supabase.co/functions/v1/panel-api';\nvar CENTRAL_TOKEN = null;\nvar CENTRAL_USER_KEY = 'panelCentralUser';\nvar CENTRAL_TOKEN_KEY = 'panelCentralToken';\n\nfunction centralStorageGet(key){\n  try { return localStorage.getItem(key) || sessionStorage.getItem(key) || ''; } catch(e){ return ''; }\n}\nfunction centralStorageSet(key, value, remember){\n  try {\n    localStorage.removeItem(key);\n    sessionStorage.removeItem(key);\n    (remember ? localStorage : sessionStorage).setItem(key, value);\n  } catch(e) {}\n}\nfunction centralStorageClear(){\n  try { localStorage.removeItem(CENTRAL_TOKEN_KEY); localStorage.removeItem(CENTRAL_USER_KEY); sessionStorage.removeItem(CENTRAL_TOKEN_KEY); sessionStorage.removeItem(CENTRAL_USER_KEY); } catch(e) {}\n}\nfunction centralTokenPayload(token){\n  try {\n    var p = token.split('.')[1];\n    var b = p.replace(/-/g,'+').replace(/_/g,'/').padEnd(Math.ceil(p.length/4)*4,'=');\n    return JSON.parse(atob(b));\n  } catch(e){ return null; }\n}\nfunction centralTokenValid(token){\n  var p = centralTokenPayload(token);\n  return !!(p && p.exp && p.exp > Date.now());\n}\nfunction centralHeaders(extra){\n  var h = { 'Content-Type':'application/json' };\n  if(CENTRAL_TOKEN) h.Authorization = 'Bearer ' + CENTRAL_TOKEN;\n  if(extra) Object.keys(extra).forEach(function(k){ h[k] = extra[k]; });\n  return h;\n}\nfunction centralRequest(path, options){\n  options = options || {};\n  return fetch(CENTRAL_API + path, {\n    method: options.method || 'GET',\n    headers: centralHeaders(options.headers),\n    body: options.body === undefined ? undefined : JSON.stringify(options.body)\n  }).then(function(r){\n    return r.text().then(function(text){\n      var data = {};\n      try { data = text ? JSON.parse(text) : {}; } catch(e) { data = { error:text || 'Respuesta inválida' }; }\n      if(!r.ok){\n        var err = new Error(data.error || ('HTTP ' + r.status));\n        err.status = r.status;\n        throw err;\n      }\n      return data;\n    });\n  });\n}\nfunction centralStoreName(storeName){ return storeName; }\n\nvar _localDbGetAll = dbGetAll;\nvar _localDbPut = dbPut;\nvar _localDbBulkPut = dbBulkPut;\nvar _localDbClear = dbClear;\n\nfunction centralLoadState(){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return Promise.reject(new Error('NO_CENTRAL_SESSION'));\n  return centralRequest('/state').then(function(result){\n    var s = result.state || {};\n    state.colaboradores = s.colaboradores || [];\n    state.sucursales = s.sucursales || [];\n    state.traslados = s.traslados || [];\n    state.licencias = s.licencias || [];\n    state.vacaciones = s.vacaciones || [];\n    state.usuarios = s.usuarios || [];\n    state.auditoria = s.auditoria || [];\n    if(result.user && currentUser) currentUser = Object.assign({}, currentUser, result.user);\n    return sincronizarTrasladosConColaboradores();\n  });\n}\n\n/* Desde que existe sesión central, las lecturas salen de PostgreSQL. */\ndbGetAll = function(storeName){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbGetAll(storeName);\n  return centralRequest('/state').then(function(result){\n    var rows = (result.state || {})[centralStoreName(storeName)] || [];\n    return rows;\n  });\n};\n\ndbPut = function(storeName, obj){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbPut(storeName, obj);\n  return centralRequest('', { method:'POST', body:{ action:'upsert', table:centralStoreName(storeName), record:obj } }).then(function(){ return obj; });\n};\n\ndbBulkPut = function(storeName, arr){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbBulkPut(storeName, arr);\n  if(!arr || !arr.length) return Promise.resolve();\n  return centralRequest('', { method:'POST', body:{ action:'bulkUpsert', table:centralStoreName(storeName), records:arr } }).then(function(){ return arr; });\n};\n\ndbClear = function(storeName){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) return _localDbClear(storeName);\n  return centralRequest('', { method:'POST', body:{ action:'clear', table:centralStoreName(storeName) } }).then(function(){ return true; });\n};\n\n/* Recarga central: reemplaza por completo el estado que usa la interfaz. */\nreloadStateFromDB = function(){\n  if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)){\n    return _localDbGetAll(STORES.COLAB).then(function(colab){\n      return Promise.all([\n        Promise.resolve(colab), _localDbGetAll(STORES.SUC), _localDbGetAll(STORES.TRAS), _localDbGetAll(STORES.LIC), _localDbGetAll(STORES.VAC), _localDbGetAll(STORES.USERS), _localDbGetAll(STORES.AUDIT)\n      ]).then(function(results){\n        state.colaboradores=results[0]; state.sucursales=results[1]; state.traslados=results[2]; state.licencias=results[3]; state.vacaciones=results[4]; state.usuarios=results[5]; state.auditoria=results[6]||[];\n        return sincronizarTrasladosConColaboradores();\n      });\n    });\n  }\n  return centralLoadState().catch(function(err){\n    if(err && err.status === 401){\n      CENTRAL_TOKEN = null;\n      centralStorageClear();\n      currentUser = null;\n      showLogin('La sesión expiró. Inicie sesión nuevamente.');\n    }\n    throw err;\n  });\n};\n\n/* Login centralizado contra PostgreSQL/Supabase. */\nloginUser = function(){\n  var username = document.getElementById('loginUsername').value.trim();\n  var password = document.getElementById('loginPassword').value;\n  var remember = document.getElementById('loginRemember').checked;\n  if(!username || !password){ showLogin('Ingrese usuario y contraseña.'); return; }\n  var btn = document.getElementById('btnLogin');\n  if(btn) btn.disabled = true;\n  centralRequest('', { method:'POST', body:{ username:username, password:password } }).then(function(result){\n    CENTRAL_TOKEN = result.token;\n    currentUser = result.user;\n    centralStorageSet(CENTRAL_TOKEN_KEY, CENTRAL_TOKEN, remember);\n    centralStorageSet(CENTRAL_USER_KEY, JSON.stringify(currentUser), remember);\n    return centralLoadState();\n  }).then(function(){\n    hideLogin();\n    updateSessionUI();\n    rerenderAll();\n    if(typeof bootAdv === 'function') bootAdv();\n    switchTab('resumen');\n    showToast('Bienvenido, ' + (currentUser.nombre || currentUser.username) + '.', 'success');\n  }).catch(function(err){\n    console.error('Login central:', err);\n    showLogin(err && err.message ? err.message : 'No fue posible iniciar sesión.');\n  }).finally(function(){ if(btn) btn.disabled = false; });\n};\n\nrestoreSession = function(){\n  var token = centralStorageGet(CENTRAL_TOKEN_KEY);\n  var rawUser = centralStorageGet(CENTRAL_USER_KEY);\n  if(!token || !centralTokenValid(token) || !rawUser){\n    CENTRAL_TOKEN = null;\n    return false;\n  }\n  try {\n    CENTRAL_TOKEN = token;\n    currentUser = JSON.parse(rawUser);\n    if(!currentUser || !currentUser.username){ throw new Error('bad session'); }\n    hideLogin();\n    updateSessionUI();\n    return true;\n  } catch(e){\n    CENTRAL_TOKEN = null;\n    centralStorageClear();\n    currentUser = null;\n    return false;\n  }\n};\n\nlogout = function(){\n  currentUser = null;\n  CENTRAL_TOKEN = null;\n  centralStorageClear();\n  updateSessionUI();\n  var u=document.getElementById('loginUsername'); var p=document.getElementById('loginPassword');\n  if(u) u.value=''; if(p) p.value='';\n  showLogin();\n};\n\n/* Eliminaciones directas para no borrar y reconstruir tablas completas. */\ndeleteColaborador = function(rut){\n  if(!confirm('¿Eliminar este colaborador?')) return;\n  centralRequest('', {method:'POST', body:{action:'delete', table:'colaboradores', record:{rut:rut}}}).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Colaborador eliminado.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar el colaborador.','error');});\n};\ndeleteSucursal = function(codigo){\n  if(!confirm('¿Eliminar esta sucursal?')) return;\n  centralRequest('', {method:'POST', body:{action:'delete', table:'sucursales', record:{codigo:codigo}}}).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Sucursal eliminada.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar la sucursal.','error');});\n};\neliminarTraslado = function(id){\n  if(!confirm('¿Eliminar este traslado?')) return;\n  centralRequest('', {method:'POST', body:{action:'delete', table:'traslados', record:{id:id}}}).then(reloadStateFromDB).then(function(){return sincronizarTrasladosConColaboradores();}).then(function(){rerenderAll();showToast('Traslado eliminado.','success');}).catch(function(err){console.error(err);showToast('No fue posible eliminar el traslado.','error');});\n};\n\n/* El respaldo conserva su exportación local, pero la restauración queda centralizada. */\nvar _localImportBackup = importBackup;\nimportBackup = function(file){\n  var reader = new FileReader();\n  reader.onload = function(){\n    try {\n      var d = JSON.parse(reader.result);\n      if(!d || !Array.isArray(d.colaboradores) || !Array.isArray(d.sucursales)) throw new Error('Formato inválido');\n      if(!CENTRAL_TOKEN || !centralTokenValid(CENTRAL_TOKEN)) throw new Error('Debe iniciar sesión nuevamente.');\n      Promise.all([\n        centralRequest('',{method:'POST',body:{action:'clear',table:'colaboradores'}}),\n        centralRequest('',{method:'POST',body:{action:'clear',table:'sucursales'}}),\n        centralRequest('',{method:'POST',body:{action:'clear',table:'traslados'}}),\n        centralRequest('',{method:'POST',body:{action:'clear',table:'vacaciones'}}),\n        centralRequest('',{method:'POST',body:{action:'clear',table:'licencias'}}),\n        centralRequest('',{method:'POST',body:{action:'clear',table:'auditoria'}})\n      ]).then(function(){\n        return Promise.all([\n          dbBulkPut(STORES.COLAB,d.colaboradores), dbBulkPut(STORES.SUC,d.sucursales), dbBulkPut(STORES.TRAS,d.traslados||[]), dbBulkPut(STORES.VAC,d.vacaciones||[]), dbBulkPut(STORES.LIC,d.licencias||[]), dbBulkPut(STORES.AUDIT,d.auditoria||[])\n        ]);\n      }).then(reloadStateFromDB).then(function(){rerenderAll();showToast('Respaldo restaurado correctamente.','success');}).catch(function(err){console.error(err);showToast(err.message||'No fue posible restaurar el respaldo.','error');});\n    } catch(e){ showToast(e.message||'El archivo no tiene un respaldo válido.','error'); }\n  };\n  reader.readAsText(file);\n};\n/* ====== FIN SINCRONIZACION CENTRAL ====== */\n
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
