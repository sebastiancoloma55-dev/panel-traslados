import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Quitamos únicamente el marco de Streamlit.
# La aplicación HTML es la que controla el layout y el scroll.
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

        html,
        body,
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

# IMPORTANTE:
# El iframe ahora sí tiene scrolling=True. Como el documento interno
# crece con su contenido, el navegador muestra la barra vertical del
# propio iframe y la rueda del mouse funciona sobre la aplicación.
st.components.v1.html(
    html_content,
    height=1000,
    scrolling=True,
)
