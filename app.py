import streamlit as st
from pathlib import Path

# ============================================================
# PANEL DE TRASLADOS — HOST FULLSCREEN
# ============================================================
st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Ocultar el chrome de Streamlit que quedaría detrás del iframe.
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
        [data-testid="stMainBlockContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        .main .block-container {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
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

# El index.html contiene un bootstrap que toma el iframe real
# (window.frameElement) y lo convierte en un elemento fijo de
# 100vw x 100vh. Esto elimina los márgenes exteriores de Streamlit
# sin modificar la lógica de la aplicación.
st.components.v1.html(
    html_content,
    height=1000,
    scrolling=False,
)
