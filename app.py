import streamlit as st

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# STREAMLIT COMO CONTENEDOR FULL-BLEED
# El problema de la captura viene del contenedor que Streamlit
# coloca alrededor del iframe de st.components.v1.html.
# ============================================================
st.markdown(
    """
    <style>
        /* Ocultar elementos propios de Streamlit */
        #MainMenu,
        footer,
        header,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            display: none !important;
        }

        /* Documento y aplicación */
        html,
        body,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
        }

        [data-testid="stAppViewContainer"] {
            overflow-x: hidden !important;
        }

        /* Área principal */
        [data-testid="stMain"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        .main,
        .main .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stMainBlockContainer"] > div {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: none !important;
        }

        /* El bloque que contiene el componente HTML:
           lo sacamos del ancho central de Streamlit y lo hacemos
           ocupar exactamente todo el viewport. */
        [data-testid="stElementContainer"]:has(iframe) {
            box-sizing: border-box !important;
            width: 100vw !important;
            max-width: 100vw !important;
            min-width: 100vw !important;
            margin-left: calc(50% - 50vw) !important;
            margin-right: 0 !important;
            padding: 0 !important;
            position: relative !important;
            left: 0 !important;
        }

        [data-testid="stElementContainer"]:has(iframe) > div,
        [data-testid="stElementContainer"]:has(iframe) > div > div {
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Iframe del HTML */
        iframe {
            display: block !important;
            box-sizing: border-box !important;
            width: 100vw !important;
            max-width: 100vw !important;
            min-width: 100vw !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
        }

        /* Evitar espacio vertical del layout de Streamlit */
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        [data-testid="stVerticalBlock"] > div {
            margin-top: 0 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CARGAR LA APLICACIÓN HTML
# ============================================================
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# Una sola instancia del HTML, sin scrolling del iframe.
# La aplicación interna tiene su propio scroll.
st.components.v1.html(
    html_content,
    height=2200,
    scrolling=False,
)
