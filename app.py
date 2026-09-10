import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Panel de Traslados",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Remove Streamlit's own chrome and outer spacing.
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

        .main .block-container,
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

# The index itself controls the fullscreen iframe and now explicitly
# restores a visible vertical scrollbar for long pages.
st.components.v1.html(
    html_content,
    height=1000,
    scrolling=False,
)

