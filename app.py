import streamlit as st

# Configurar la página en modo ancho completo absoluto
st.set_page_config(page_title="Panel de Traslados", layout="wide", initial_sidebar_state="collapsed")

# Inyectar CSS definitivo para eliminar márgenes y estirar el contenido al 100% de la ventana
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { top: 0px; }
        .main .block-container {
            padding: 0rem !important;
            max-width: 100% !important;
            margin: 0 !important;
        }
        iframe {
            width: 100vw !important;
            height: 100vh !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            border: none !important;
            z-index: 99999;
        }
    </style>
""", unsafe_allow_html=True)

# Leer e incrustar el HTML nativamente sin restricciones
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

st.components.v1.html(html_content, height=1000, scrolling=True)
