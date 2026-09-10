import streamlit as st
import streamlit.components.v1 as components

# Configurar la página para que ocupe todo el ancho
st.set_page_config(page_title="Panel de Traslados", layout="wide")

# Leer el archivo HTML
with open("index.html", "r", encoding="utf-8") as f:
    html_code = f.read()

# Renderizar el HTML en Streamlit con la misma altura de tus otras apps
components.html(html_code, height=900, scrolling=True)