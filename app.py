import streamlit as st
import streamlit.components.v1 as components

# Configurar la página en modo ancho completo (wide)
st.set_page_config(page_title="Panel de Traslados", layout="wide")

# Ocultar los elementos visuales de la interfaz de Streamlit (barra superior y menú)
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem;}
    iframe {width: 100% !important; height: 100vh !important; border: none !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Cargar e insertar el HTML ocupando toda la pantalla real
with open("index.html", "r", encoding="utf-8") as f:
    html_code = f.read()

components.html(html_code, height=950, scrolling=True)
