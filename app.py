import streamlit as st

# Configuración de Streamlit
st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit solo sirve como contenedor del HTML.
# No fijamos el iframe al viewport: eso hacía que la página se desplazara/
# superpusiera de forma incorrecta al publicarla.
st.markdown(
    """
    <style>
        #MainMenu,
        footer,
        header {
            visibility: hidden;
        }

        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stApp"] {
            margin: 0 !important;
            padding: 0 !important;
        }

        [data-testid="stAppViewContainer"] {
            width: 100% !important;
        }

        [data-testid="stMain"] {
            padding: 0 !important;
        }

        .main .block-container {
            width: 100% !important;
            max-width: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        iframe {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
            border: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Cargar el HTML completo de la aplicación
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# Altura amplia para que se vea la aplicación completa sin el iframe
# superpuesto al navegador/Streamlit.
st.components.v1.html(
    html_content,
    height=1400,
    scrolling=False,
)
