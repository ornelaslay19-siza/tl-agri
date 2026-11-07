"""
dashboard/produsaun_folin.py  (pájina 2)
=======================================
PRODUSAUN, LOKALIZASAUN no FOLIN - Forecast Dashboard

Fluxu:  Agriculture API -> Historical Data -> EDA -> Modeling -> FORECAST DASHBOARD

Komponente:
  * KPI cards      : folin ikus, mudansa 12 fulan, previzaun fulan tuir mai, merkadu baratu liu, produsaun
  * Filter         : ai-han, lokalizasaun (merkadu), nominál/real, períodu, kultura
  * Trend chart    : folin per merkadu, índise sazonál, komparasaun ai-han
  * Comparison     : mapa merkadu, bar merkadu, produsaun per munisípiu
  * Forecast       : SARIMA / Holt-Winters ho intervalu 95% + alerta folin sa'e
  * Regression     : previzaun folin 1-step + produsaun ho senáriu klima
  * Last-updated timestamp
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402

PADDY, MONSOON, DRYSEASON, LATERITE, INK = "#3E6B48", "#2F5D7C", "#C9A227", "#9C3D2E", "#1F2A24"
NATIONAL = "Nasionál (mediana)"
MONTHS = ["Jan", "Feb", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
P, O = config.DATA_PROCESSED, config.DATA_OUTPUTS


def _mt(p):
    return p.stat().st_mtime if p.exists() else 0


@st.cache_data
def _load(path, mtime, dates):
    return pd.read_csv(path, parse_dates=dates)


def read(path, dates=None):
    return _load(str(path), _mt(path), dates) if path.exists() else pd.DataFrame()


prices = read(P / "prices_market_monthly.csv", ["date"])
if prices.empty:
    st.title("Produsaun, lokalizasaun & folin")
    st.warning("Dadus seidauk iha. Hala'o `python -m src.pipeline` (ka `--demo`).")
    st.stop()

nat = read(P / "prices_national_monthly.csv", ["date"])
markets = read(P / "markets.csv")
prod = read(P / "production_annual.csv")
muni = read(P / "municipal_production.csv")
pfc = read(O / "price_forecasts.csv", ["date"])
pev = read(O / "price_eval.csv")
ptest = read(O / "price_test_predictions.csv", ["date"])
rev = read(O / "price_regression_eval.csv")
rpred = read(O / "price_regression_predictions.csv", ["date"])
prev = read(O / "production_eval.csv")
prfc = read(O / "production_forecasts.csv")
prloo = read(O / "production_loocv_predictions.csv")
am = json.loads((O / "agri_metrics.json").read_text()) if (O / "agri_metrics.json").exists() else {}
meta = json.loads(config.METADATA_FILE.read_text()) if config.METADATA_FILE.exists() else {}

# ==========================================================================
# SIDEBAR
# ==========================================================================
st.sidebar.header("Filtru")
series_list = sorted(nat["series"].unique())
default_series = "Rice (local) (USD/KG)" if "Rice (local) (USD/KG)" in series_list else series_list[0]
series = st.sidebar.selectbox("Ai-han (folin)", series_list, index=series_list.index(default_series))
mk_options = [NATIONAL] + sorted(prices.loc[prices["series"] == series, "market"].unique())
location = st.sidebar.selectbox("Lokalizasaun (merkadu)", mk_options)
real = st.sidebar.toggle("Folin real (hasai inflasaun)", value=False,
                         help="Folin iha dólar tinan ikus, atu kompara tinan oioin ho justu")
pcol = "real_price" if real else "price"
y0, y1 = int(prices["date"].dt.year.min()), int(prices["date"].dt.year.max())
yr = st.sidebar.slider("Períodu", y0, y1, (max(y0, y1 - 7), y1))
crops = sorted(prod["crop"].unique()) if not prod.empty else []
crop = st.sidebar.selectbox("Kultura (produsaun)", crops, index=crops.index("Maize") if "Maize" in crops else 0)

# Série ne'ebé hili
if location == NATIONAL:
    ser = nat[nat["series"] == series].set_index("date")[pcol]
else:
    ser = prices[(prices["series"] == series) & (prices["market"] == location)].set_index("date")[pcol]
ser = ser.sort_index()
ser_f = ser[(ser.index.year >= yr[0]) & (ser.index.year <= yr[1])]
unit = series.split("(USD/")[-1].rstrip(")") if "(USD/" in series else ""

# ==========================================================================
# HEADER + LAST UPDATED
# ==========================================================================
st.title("Produsaun, lokalizasaun & folin")
status = meta.get("status", {})
is_demo = any(status.get(k) == "demo" for k in ("prices", "production", "municipal_production"))
flag = '<span class="demo-flag">DEMO DATA</span>' if is_demo else '<span class="live-flag">LIVE DATA</span>'
ts = meta.get("agri_last_updated_utc") or meta.get("last_updated_utc")
ts_txt = datetime.fromisoformat(ts).astimezone(timezone(timedelta(hours=9))).strftime("%d %b %Y, %H:%M") + " (tempu Dili)" if ts else "—"
st.markdown(f"{flag} &nbsp; Atualiza ikus: **{ts_txt}** &nbsp;|&nbsp; Folin ikus: **{prices['date'].max():%b %Y}** "
            f"&nbsp;|&nbsp; Produsaun ikus: **{int(prod['year'].max()) if not prod.empty else '—'}**",
            unsafe_allow_html=True)
st.caption("Fluxu: Agriculture API (WFP/HDX, FAOSTAT, World Bank) → Historical data → EDA → Modeling → Forecast dashboard")
if is_demo:
    st.caption("Status fonte: " + ", ".join(f"{k}={v}" for k, v in status.items()))

# ==========================================================================
# KPI CARDS
# ==========================================================================
k1, k2, k3, k4, k5 = st.columns(5)
if len(ser) >= 2:
    k1.metric(f"Folin ikus ({ser.index[-1]:%b %Y})", f"${ser.iloc[-1]:.2f}/{unit}",
              delta=f"{(ser.iloc[-1] / ser.iloc[-2] - 1) * 100:+.1f}% vs fulan kotuk", delta_color="inverse")
    prev12 = ser[ser.index <= ser.index[-1] - pd.DateOffset(months=12)]
    if len(prev12):
        ch = (ser.iloc[-1] / prev12.iloc[-1] - 1) * 100
        k2.metric("Mudansa 12 fulan", f"{ch:+.1f}%", help="Pozitivu = karun liu (la di'ak ba konsumidór)")
fc_sel = pfc[(pfc["series"] == series) & (pfc["location"] == location)] if not pfc.empty else pd.DataFrame()
best_fc = fc_sel[fc_sel["best_model"]] if not fc_sel.empty else fc_sel
if best_fc.empty and not fc_sel.empty:
    best_fc = fc_sel[fc_sel["model"] == "SARIMA"]
if not best_fc.empty and len(ser):
    nxt = best_fc.iloc[0]
    k3.metric(f"Previzaun {nxt['date']:%b %Y}", f"${nxt['forecast']:.2f}",
              delta=f"{(nxt['forecast'] / ser.iloc[-1] - 1) * 100:+.1f}%", delta_color="inverse",
              help=f"Modelu: {nxt['model']} (nominál)")
last12 = prices[(prices["series"] == series) & (prices["date"] > prices["date"].max() - pd.DateOffset(months=12))]
if not last12.empty:
    mk_mean = last12.groupby("market")[pcol].mean()
    k4.metric("Merkadu baratu liu (12 fulan)", mk_mean.idxmin(), delta=f"${mk_mean.min():.2f} vs ${mk_mean.max():.2f} karun liu",
              delta_color="off")
pc = prod[prod["crop"] == crop].sort_values("year") if not prod.empty else pd.DataFrame()
if len(pc) >= 2:
    k5.metric(f"Produsaun {crop} {int(pc['year'].iloc[-1])}", f"{pc['production_t'].iloc[-1] / 1000:,.1f} rihun t",
              delta=f"{pc['production_change_pct'].iloc[-1]:+.1f}%")

tabs = st.tabs(["Previzaun folin", "Lokalizasaun", "Trend folin", "Produsaun", "Regression folin", "Dadus"])

# ==========================================================================
# TAB 1 - FORECAST FOLIN
# ==========================================================================
with tabs[0]:
    st.subheader(f"{series} — {location}")
    if fc_sel.empty:
        st.info("Previzaun la iha ba kombinasaun ne'e (série badak demais ka la atualiza ona). Hili 'Nasionál'.")
    else:
        fig = go.Figure()
        fig.add_scatter(x=ser_f.index, y=ser_f.values, name="Observasaun" + (" (real)" if real else ""),
                        line=dict(color=INK, width=2))
        b = best_fc
        if b["lower_95"].notna().any():
            fig.add_scatter(x=pd.concat([b["date"], b["date"][::-1]]), y=pd.concat([b["upper_95"], b["lower_95"][::-1]]),
                            fill="toself", fillcolor="rgba(47,93,124,0.18)", line=dict(width=0), name="Intervalu 95%")
        fig.add_scatter(x=b["date"], y=b["forecast"], name=f"Previzaun — {b['model'].iloc[0]} (di'ak liu)",
                        line=dict(color=MONSOON, width=3))
        for m, g in fc_sel[~fc_sel["model"].isin(b["model"].unique())].groupby("model"):
            fig.add_scatter(x=g["date"], y=g["forecast"], name=m, line=dict(color=DRYSEASON, dash="dash"))
        fig.update_layout(height=430, yaxis_title=f"USD/{unit}", margin=dict(t=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
        if real:
            st.caption("Nota: previzaun iha folin NOMINÁL; observasaun iha folin real.")

        # Alerta folin
        base_price = ser.iloc[-1] if not real else prices.loc[prices["series"] == series, "price"].iloc[-1]
        n3 = b.head(3).copy()
        n3["mudansa_%"] = ((n3["forecast"] / base_price - 1) * 100).round(1)
        n3["status"] = np.select([n3["mudansa_%"] > 10, n3["mudansa_%"] < -10],
                                 ["Folin sa'e maka'as — prepara stock/asisténsia", "Folin tun — oportunidade sosa"], "Estável")
        n3["fulan"] = n3["date"].dt.strftime("%b %Y")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("**Alerta folin — fulan 3 ba oin**")
            st.dataframe(n3[["fulan", "forecast", "lower_95", "upper_95", "mudansa_%", "status"]]
                         .rename(columns={"forecast": "Previzaun", "lower_95": "Min 95%", "upper_95": "Max 95%"}),
                         hide_index=True, width="stretch")
        with c2:
            st.markdown("**Avaliasaun modelu** (hold-out 12 fulan)")
            e = pev[(pev["series"] == series) & (pev["location"] == location)]
            st.dataframe(e[["model", "MAE", "RMSE", "sMAPE_%"]].sort_values("RMSE"), hide_index=True, width="stretch")
        t = ptest[(ptest["series"] == series) & (ptest["location"] == location)]
        if not t.empty:
            with st.expander("Teste: atuál vs prevee (12 fulan ikus)"):
                fig = px.line(t, x="date", y="predicted", color="model", labels={"predicted": f"USD/{unit}", "date": ""})
                a = t.drop_duplicates("date")
                fig.add_scatter(x=a["date"], y=a["actual"], name="Atuál", line=dict(color=INK, width=3))
                fig.update_layout(height=320, margin=dict(t=10))
                st.plotly_chart(fig, width="stretch")

# ==========================================================================
# TAB 2 - LOKALIZASAUN
# ==========================================================================
with tabs[1]:
    c1, c2 = st.columns([3, 2])
    mk = last12.groupby(["market", "admin1"]).agg(price=(pcol, "mean")).reset_index().merge(
        markets[["market", "latitude", "longitude"]], on="market", how="left")
    mk["zona"] = mk["admin1"].map(lambda m: config.MUNICIPALITIES.get(m, {}).get("zone", "—"))
    with c1:
        st.markdown(f"**Mapa folin média 12 fulan ikus — {series}**")
        if mk["latitude"].notna().any():
            fig = px.scatter_map(mk, lat="latitude", lon="longitude", color="price", size=mk["price"] / mk["price"].min(),
                                 hover_name="market", hover_data={"admin1": True, "price": ":.2f", "latitude": False, "longitude": False},
                                 color_continuous_scale="YlOrRd", zoom=6.8, center={"lat": -8.8, "lon": 125.8},
                                 labels={"price": f"USD/{unit}"})
            fig.update_layout(height=450, margin=dict(t=10, l=0, r=0, b=0))
            st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown("**Komparasaun merkadu**")
        fig = px.bar(mk.sort_values("price"), x="price", y="market", color="zona", orientation="h",
                     color_discrete_map={"lowland": MONSOON, "highland": PADDY}, labels={"price": f"USD/{unit}", "market": ""})
        fig.update_layout(height=450, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

    st.markdown(f"**Produsaun per munisípiu** (Censo/MAP, tinan {int(muni['year'].max()) if not muni.empty else '—'})")
    mc = muni[muni["crop"] == crop] if crop in set(muni.get("crop", [])) else muni[muni["crop"] == muni["crop"].iloc[0]]
    c1, c2 = st.columns([2, 3])
    with c1:
        fig = px.scatter_map(mc, lat="lat", lon="lon", size="production_t", color="share_pct", hover_name="municipality",
                             color_continuous_scale="Greens", zoom=6.8, center={"lat": -8.8, "lon": 125.8},
                             labels={"share_pct": "% nasionál"})
        fig.update_layout(height=380, margin=dict(t=10, l=0, r=0, b=0))
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.bar(mc.sort_values("production_t"), x="production_t", y="municipality", orientation="h",
                     color_discrete_sequence=[PADDY], labels={"production_t": "Tonelada", "municipality": ""},
                     title=f"{mc['crop'].iloc[0]}")
        fig.update_layout(height=380, margin=dict(t=30))
        st.plotly_chart(fig, width="stretch")

# ==========================================================================
# TAB 3 - TREND FOLIN
# ==========================================================================
with tabs[2]:
    d = prices[(prices["series"] == series) & prices["date"].dt.year.between(*yr)]
    fig = px.line(d, x="date", y=pcol, color="market", labels={pcol: f"USD/{unit}", "date": ""})
    fig.update_traces(opacity=0.5, line=dict(width=1))
    n = nat[(nat["series"] == series) & nat["date"].dt.year.between(*yr)]
    fig.add_scatter(x=n["date"], y=n[pcol], name=NATIONAL, line=dict(color=INK, width=3))
    fig.update_layout(height=400, margin=dict(t=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Índise sazonál** (100 = média tinan)")
        s = nat[nat["series"] == series].sort_values("date").copy()
        s["idx"] = s["price"] / s["price"].rolling(13, center=True, min_periods=7).mean() * 100
        si = s.groupby("month")["idx"].mean().reindex(range(1, 13))
        fig = go.Figure(go.Bar(x=MONTHS, y=si.values,
                               marker_color=[DRYSEASON if m in config.LEAN_SEASON_MONTHS else MONSOON for m in range(1, 13)]))
        fig.add_hline(y=100, line_color="gray")
        fig.update_layout(height=320, margin=dict(t=10), yaxis_range=[si.min() - 3, si.max() + 3])
        st.plotly_chart(fig, width="stretch")
        st.caption("Kinur = tempu hamlaha (Nov–Fev)")
    with c2:
        st.markdown("**Komparasaun ai-han** (índise folin real, tinan dahuluk períodu = 100)")
        nn = nat[nat["date"].dt.year.between(*yr)].copy()
        base = nn[nn["date"].dt.year == yr[0]].groupby("series")["real_price"].mean()
        nn["index"] = nn["real_price"] / nn["series"].map(base) * 100
        fig = px.line(nn, x="date", y="index", color="series", labels={"index": "Índise", "date": ""})
        fig.update_layout(height=320, margin=dict(t=10), legend=dict(font=dict(size=9)))
        st.plotly_chart(fig, width="stretch")

# ==========================================================================
# TAB 4 - PRODUSAUN
# ==========================================================================
with tabs[3]:
    if pc.empty:
        st.info("Dadus produsaun la iha.")
    else:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**Produsaun {crop}: istória + previzaun {config.PRODUCTION_FORECAST_YEARS} tinan**")
            fig = go.Figure()
            fig.add_scatter(x=pc["year"], y=pc["production_t"], name="Observasaun", line=dict(color=INK, width=2),
                            mode="lines+markers")
            f = prfc[prfc["crop"] == crop]
            h = f[f["model"] == "Holt (damped)"]
            if not h.empty:
                fig.add_scatter(x=pd.concat([h["year"], h["year"][::-1]]), y=pd.concat([h["upper_95"], h["lower_95"][::-1]]),
                                fill="toself", fillcolor="rgba(62,107,72,0.15)", line=dict(width=0), name="Holt 95%")
                fig.add_scatter(x=h["year"], y=h["forecast"], name="Holt (damped)", line=dict(color=PADDY, width=3))
            colors = {"Normál": MONSOON, "Maran (El Niño)": LATERITE, "Udan barak (La Niña)": "#4E8A8A"}
            for m, g in f[f["model"].str.startswith("Regression")].groupby("model"):
                sc = m.split("— ")[-1]
                fig.add_scatter(x=g["year"], y=g["forecast"], name=f"Regression: {sc}", mode="lines+markers",
                                line=dict(dash="dot", color=colors.get(sc)))
            fig.update_layout(height=420, yaxis_title="Tonelada", margin=dict(t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, width="stretch")
        with c2:
            st.markdown("**Avaliasaun modelu**")
            st.dataframe(prev[prev["crop"] == crop][["model", "validation", "MAE", "RMSE", "R2", "sMAPE_%"]]
                         .sort_values("RMSE"), hide_index=True, width="stretch")
            coef = am.get("production_ridge_coef", {}).get(crop)
            if coef:
                s = pd.Series(coef).sort_values()
                fig = px.bar(s, orientation="h", color=s.values > 0, color_discrete_map={True: PADDY, False: LATERITE},
                             labels={"value": "Efeitu (t per 1 SD)", "index": ""})
                fig.update_layout(height=240, showlegend=False, margin=dict(t=10))
                st.plotly_chart(fig, width="stretch")
                st.caption("Koefisiente Ridge standardizadu: pozitivu = aumenta produsaun")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(pc, x="year", y=["area_harvested_ha"], labels={"value": "ha", "year": ""},
                          color_discrete_sequence=[DRYSEASON], title="Área kolleita")
            fig.update_layout(height=280, showlegend=False, margin=dict(t=40))
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = px.line(pc, x="year", y=["yield_kg_ha"], labels={"value": "kg/ha", "year": ""},
                          color_discrete_sequence=[MONSOON], title="Produtividade")
            fig.update_layout(height=280, showlegend=False, margin=dict(t=40))
            st.plotly_chart(fig, width="stretch")

# ==========================================================================
# TAB 5 - REGRESSION FOLIN
# ==========================================================================
with tabs[4]:
    st.markdown("Regression prevee folin real **fulan tuir mai** (1-step ahead) husi folin kotuk, sazonalidade, "
                "tempu hamlaha no anomalia udan. Baseline = *Naive* (folin fulan ne'e).")
    c1, c2 = st.columns([2, 3])
    with c1:
        st.dataframe(rev[rev["series"] == series][["model", "MAE", "RMSE", "sMAPE_%"]].sort_values("RMSE"),
                     hide_index=True, width="stretch")
        imp = am.get("price_regression_interpretation", {}).get("rf_importance", {})
        if imp:
            s = pd.Series(imp)
            s = s[~s.index.str.startswith("c_")].sort_values()
            fig = px.bar(s, orientation="h", color_discrete_sequence=[MONSOON], labels={"value": "Importance", "index": ""})
            fig.update_layout(height=300, showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig, width="stretch")
    with c2:
        rp = rpred[rpred["series"] == series]
        if not rp.empty:
            fig = px.line(rp, x="date", y="predicted", color="model", labels={"predicted": f"Folin real USD/{unit}", "date": ""})
            a = rp.drop_duplicates("date")
            fig.add_scatter(x=a["date"], y=a["actual"], name="Atuál", line=dict(color=INK, width=3))
            fig.update_layout(height=380, margin=dict(t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, width="stretch")

# ==========================================================================
# TAB 6 - DADUS
# ==========================================================================
with tabs[5]:
    view = st.radio("Tabela", ["Folin merkadu", "Produsaun anuál", "Previzaun folin", "Previzaun produsaun"], horizontal=True)
    tbl = {"Folin merkadu": prices[prices["series"] == series], "Produsaun anuál": prod,
           "Previzaun folin": pfc, "Previzaun produsaun": prfc}[view]
    st.dataframe(tbl, width="stretch", height=380)
    st.download_button("Download CSV", tbl.to_csv(index=False).encode(), f"{view.replace(' ', '_')}.csv", "text/csv")
    st.markdown("<p class='source-note'>Fonte: WFP Food Prices (HDX, CC BY-IGO), FAOSTAT QCL, World Bank CPI, "
                "Censo Agrícola 2019 / MAP (produsaun munisípiu).</p>", unsafe_allow_html=True)
