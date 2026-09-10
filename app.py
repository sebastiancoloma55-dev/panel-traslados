import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# STREAMLIT LIMPIO
# ============================================================
st.markdown(
    """
    <style>
        #MainMenu,
        footer,
        header,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
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

        /*
         * SEGUNDO SCROLLBAR:
         * El iframe de la aplicación tiene su propio scroll.
         * Este espacio mantiene además el documento exterior de
         * Streamlit con una altura mayor que el viewport, creando
         * una segunda barra de desplazamiento del navegador.
         */
        [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }

        #outer-scroll-spacer {
            width: 1px;
            height: 200vh;
            opacity: 0;
            pointer-events: none;
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

# Aplicación interna: PRIMER scrollbar.
st.components.v1.html(
    html_content,
    height=1000,
    scrolling=False,
)

# Documento exterior: SEGUNDO scrollbar.
st.markdown(
    '<div id="outer-scroll-spacer" aria-hidden="true"></div>',
    unsafe_allow_html=True,
)
