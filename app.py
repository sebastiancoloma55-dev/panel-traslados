import streamlit as st

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>

/* ================================
   STREAMLIT -> PANTALLA COMPLETA
   ================================ */

/* Ocultar elementos propios de Streamlit */
#MainMenu,
footer,
header,
[data-testid="stHeader"],
[data-testid="stToolbar"] {
    display: none !important;
}

/* Fondo y documento */
html,
body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
}

/* Contenedor principal */
[data-testid="stMain"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
}

/* Block container de versiones nuevas de Streamlit */
[data-testid="stMainBlockContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
}

/* Compatibilidad con versiones anteriores */
.main,
.main .block-container,
section.main,
.stMainBlockContainer {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
}

/* Contenedor del componente */
[data-testid="stElementContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
}

/* El iframe que contiene tu index.html */
iframe {
    display: block !important;
    border: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 100% !important;
}

/* Quitar cualquier espacio generado por Streamlit */
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] {
    gap: 0 !important;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# CARGAR LA APLICACIÓN HTML
# ==========================================

with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()


st.components.v1.html(
    html_content,
    height=2000,
    scrolling=False
)
