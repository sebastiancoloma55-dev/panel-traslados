import streamlit as st
from pathlib import Path

# ============================================================
# PANEL DE TRASLADOS
# Renderizado HTML NATIVO (sin iframe)
#
# La versión anterior usaba st.components.v1.html(), que mete
# la aplicación dentro de un iframe. Ese iframe es precisamente
# el que generaba los márgenes blancos visibles al publicar.
# ============================================================

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS del CONTENEDOR PADRE de Streamlit.
# Al usar st.html(), el HTML queda en el mismo documento y estos
# selectores sí pueden quitar el padding/margen del contenedor.
st.markdown(
    """
    <style>
        /* ===== STREAMLIT: OCULTAR CHROME ===== */
        #MainMenu,
        footer,
        header,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* ===== STREAMLIT: SIN MARGENES ===== */
        html,
        body,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stMainBlockContainer"] > div,
        .main,
        .main .block-container {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
            min-width: 0 !important;
        }

        /* El elemento de st.html también debe ocupar todo el ancho */
        [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        /* Evitar scroll horizontal del wrapper de Streamlit */
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            overflow-x: hidden !important;
        }

        /* Eliminar espacios que puedan quedar alrededor del contenido */
        [data-testid="stElementContainer"] > div,
        [data-testid="stElementContainer"] > div > div {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Leer el HTML original completo.
index_path = Path(__file__).with_name("index.html")
if not index_path.exists():
    st.error("No se encontró index.html en la carpeta del proyecto.")
    st.stop()

html_content = index_path.read_text(encoding="utf-8")

# Refuerzo del documento interno para ocupar el viewport completo.
# No cambiamos la lógica ni el diseño de la aplicación.
viewport_css = """
<style>
    html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        min-width: 100% !important;
    }

    body {
        overflow-x: hidden !important;
    }

    .app-shell {
        width: 100% !important;
        min-height: 100dvh !important;
    }

    .login-screen {
        width: 100vw !important;
        height: 100dvh !important;
        min-height: 100vh !important;
    }
</style>
"""

# Inyectar el refuerzo antes de cerrar <head>.
if "</head>" in html_content.lower():
    html_content = html_content.replace("</head>", viewport_css + "</head>", 1)
else:
    html_content = viewport_css + html_content

# ============================================================
# HTML NATIVO — SIN IFRAME
# Streamlit actual permite JS explícitamente con esta opción.
# Esto mantiene funcionando los botones, IndexedDB, Excel, etc.
# ============================================================
st.html(
    html_content,
    width="stretch",
    unsafe_allow_javascript=True,
)
