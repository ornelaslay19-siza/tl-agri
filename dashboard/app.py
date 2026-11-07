"""
dashboard/app.py  (ROUTER / entrypoint)
=======================================
Smart Agriculture Monitoring Dashboard - Timor-Leste

Hala'o:   streamlit run dashboard/app.py

Pájina:
  1. Klima no udan          (klima.py)            -> SARIMA udan/temperatura, regression produtividade
  2. Produsaun & folin      (produsaun_folin.py)  -> forecast folin per merkadu, produsaun per kultura,
                                                     mapa lokalizasaun
"""
import streamlit as st

PADDY, DRYSEASON, INK = "#3E6B48", "#C9A227", "#1F2A24"

st.set_page_config(page_title="Agrikultura Timor-Leste", page_icon="🌾", layout="wide")
st.markdown(f"""
<style>
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
  [data-testid="stMetric"] {{ border-left: 4px solid {PADDY}; padding: 0.4rem 0.8rem;
                              background: rgba(62,107,72,0.05); }}
  [data-testid="stMetricLabel"] p {{ font-size: 0.9rem; }}
  .source-note {{ font-size: 0.85rem; color: #55605a; }}
  .demo-flag {{ background:{DRYSEASON}; color:{INK}; padding:2px 8px; font-weight:600; }}
  .live-flag {{ background:{PADDY}; color:white; padding:2px 8px; font-weight:600; }}
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("produsaun_folin.py", title="Produsaun, lokalizasaun & folin", icon="🌾", default=True),
    st.Page("klima.py", title="Klima & udan", icon="🌧️"),
])
pg.run()
