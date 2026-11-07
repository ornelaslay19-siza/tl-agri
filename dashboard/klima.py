"""
dashboard/klima.py  (pájina 1)
==============================
Pájina KLIMA: monitorizasaun udan/temperatura + previzaun SARIMA + produtividade serea.
Loke liuhusi router:  streamlit run dashboard/app.py

Komponente (tuir rekizitu capstone):
  * KPI cards              -> st.metric (udan, temperatura, loron maran, anomalia, produtividade)
  * Trend chart            -> tab "Trend"
  * Comparison chart       -> tab "Komparasaun" (munisípiu, zona, mapa)
  * Filter                 -> sidebar (munisípiu, tinan, sezaun, variavel)
  * Prediction / mining    -> tab "Previzaun" (SARIMA) + tab "Produtividade" (Regression)
  * Last-updated timestamp -> header (husi data/raw/_metadata.json)
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402

# Kór: verde natar, azul monsaun, kinur tempu bailoron, mean rai
PADDY, MONSOON, DRYSEASON, LATERITE, INK = "#3E6B48", "#2F5D7C", "#C9A227", "#9C3D2E", "#1F2A24"
VAR_LABELS = {
    "rain_mm": "Udan (mm/fulan)",
    "tmean_c": "Temperatura média (°C)",
    "tmax_c": "Temperatura máx (°C)",
    "rh_pct": "Umidade relativa (%)",
    "et0_mm": "Evapotranspirasaun ET0 (mm/fulan)",
    "water_balance": "Water balance: udan − ET0 (mm)",
    "dry_days": "Loron maran (loron/fulan)",
}
MONTHS_TET = ["Jan", "Feb", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ==========================================================================
# LOAD DATA (cache ho "mtime" -> bainhira file muda, cache atualiza)
# ==========================================================================
def _mtime(p):
    return p.stat().st_mtime if p.exists() else 0


@st.cache_data
def load_csv(path_str, mtime, parse_dates=None):
    return pd.read_csv(path_str, parse_dates=parse_dates)


def read(path, parse_dates=None):
    return load_csv(str(path), _mtime(path), parse_dates) if path.exists() else pd.DataFrame()


P, O = config.DATA_PROCESSED, config.DATA_OUTPUTS
monthly = read(P / "weather_monthly.csv", ["date"])

if monthly.empty:
    st.title("Smart Agriculture Monitoring — Timor-Leste")
    st.warning("Dadus seidauk iha. Hala'o pipeline uluk: `python -m src.pipeline` "
               "(ka `python -m src.pipeline --demo` bainhira la iha internet).")
    st.stop()

annual = read(P / "annual_national.csv")
news = read(P / "news_clean.csv", ["published"])
forecasts = read(O / "forecasts.csv", ["date"])
test_preds = read(O / "test_predictions.csv", ["date"])
evals = read(O / "model_evaluation_by_municipality.csv")
yield_preds = read(O / "yield_loocv_predictions.csv")
metrics = json.loads((O / "metrics.json").read_text()) if (O / "metrics.json").exists() else {}
meta = json.loads(config.METADATA_FILE.read_text()) if config.METADATA_FILE.exists() else {}

# ==========================================================================
# SIDEBAR FILTERS
# ==========================================================================
st.sidebar.header("Filtru")
all_munis = sorted(monthly["municipality"].unique())
zone_choice = st.sidebar.radio("Zona", ["Hotu", "Tasi-ibun (lowland)", "Foho (highland)"], horizontal=False)
zone_map = {"Tasi-ibun (lowland)": "lowland", "Foho (highland)": "highland"}
pool = [m for m in all_munis if zone_choice == "Hotu" or config.MUNICIPALITIES[m]["zone"] == zone_map[zone_choice]]
munis = st.sidebar.multiselect("Munisípiu", pool, default=pool)
y_min, y_max = int(monthly["year"].min()), int(monthly["year"].max())
years = st.sidebar.slider("Períodu (tinan)", y_min, y_max, (max(y_min, y_max - 14), y_max))
season = st.sidebar.selectbox("Sezaun", ["Hotu", "Tempu udan (Dez–Abr)", "Tempu bailoron (Mai–Nov)"])
var_options = [v for v in VAR_LABELS if v in monthly.columns]
variable = st.sidebar.selectbox("Variavel", var_options, format_func=VAR_LABELS.get)

if not munis:
    st.info("Hili munisípiu ida ka liu iha filtru.")
    st.stop()

f = monthly[monthly["municipality"].isin(munis) & monthly["year"].between(*years)].copy()
if season.startswith("Tempu udan"):
    f = f[f["month"].isin(config.WET_SEASON_MONTHS)]
elif season.startswith("Tempu bailoron"):
    f = f[~f["month"].isin(config.WET_SEASON_MONTHS)]

st.sidebar.divider()
if st.sidebar.button("Atualiza dadus agora", help="Hala'o pipeline: collect → preprocess → EDA → models"):
    with st.spinner("Rekolla no prosesa dadus... (bele to'o minutu balun)"):
        out = subprocess.run([sys.executable, "-m", "src.pipeline"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode == 0:
        st.sidebar.success("Dadus atualiza ona.")
        st.rerun()
    else:
        st.sidebar.error("Pipeline falla. Haree log iha terminal.")
        st.sidebar.code(out.stderr[-1500:])

# ==========================================================================
# HEADER + LAST UPDATED
# ==========================================================================
st.title("Klima no udan — Timor-Leste")
status = meta.get("status", {})
is_demo = "demo" in status.values()
flag = '<span class="demo-flag">DEMO DATA</span>' if is_demo else '<span class="live-flag">LIVE DATA</span>'
ts = meta.get("last_updated_utc")
ts_txt = "—"
if ts:
    dili = datetime.fromisoformat(ts).astimezone(timezone(timedelta(hours=9)))  # Dili = UTC+9
    ts_txt = dili.strftime("%d %b %Y, %H:%M") + " (tempu Dili)"
st.markdown(
    f"{flag} &nbsp; Atualiza ikus: **{ts_txt}** &nbsp;|&nbsp; Dadus klima to'o: "
    f"**{monthly['date'].max():%b %Y}** &nbsp;|&nbsp; Fonte klima: {meta.get('weather_source', '—')}",
    unsafe_allow_html=True)
if is_demo:
    st.caption("Fonte ruma la konsege asesu no uza dadus sintétiku. Hala'o `python -m src.pipeline` "
               "ho internet atu hetan dadus loos. Status: " + ", ".join(f"{k}={v}" for k, v in status.items()))

# ==========================================================================
# KPI CARDS
# ==========================================================================
full_years = f.groupby(["municipality", "year"])["month"].count()
annual_rain = (f.groupby(["municipality", "year"])["rain_mm"].sum()[full_years >= (12 if season == "Hotu" else 5)]
               .groupby("municipality").mean().mean())
latest_month = monthly["date"].max()
latest = monthly[(monthly["date"] == latest_month) & monthly["municipality"].isin(munis)]
anom = latest["rain_anomaly_pct"].mean()
dry_share = f["dry_days"].sum() / (f["month"].count() * 30.4) * 100

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Udan média per tinan" if season == "Hotu" else "Udan média per sezaun",
          f"{annual_rain:,.0f} mm" if pd.notna(annual_rain) else "—")
k2.metric("Temperatura média", f"{f['tmean_c'].mean():.1f} °C")
k3.metric("Loron maran", f"{dry_share:.0f}%", help="Loron ho udan < 1 mm")
k4.metric(f"Anomalia udan {latest_month:%b %Y}", f"{anom:+.0f}%",
          help="Kompara ho média fulan hanesan iha tinan hotu", delta=f"{anom:+.0f}%",
          delta_color="normal")
if not annual.empty and "cereal_yield_kg_ha" in annual:
    yy = annual.dropna(subset=["cereal_yield_kg_ha"]).sort_values("year")
    if len(yy) >= 2:
        k5.metric(f"Produtividade serea {int(yy['year'].iloc[-1])}",
                  f"{yy['cereal_yield_kg_ha'].iloc[-1]:,.0f} kg/ha",
                  delta=f"{yy['cereal_yield_kg_ha'].iloc[-1] - yy['cereal_yield_kg_ha'].iloc[-2]:+,.0f} kg/ha")

# ==========================================================================
# TABS
# ==========================================================================
t_trend, t_comp, t_fc, t_yield, t_news, t_data = st.tabs(
    ["Trend", "Komparasaun", "Previzaun klima", "Produtividade serea", "Notísia & alerta", "Dadus"])

# ---------------- TREND ----------------
with t_trend:
    st.subheader(f"{VAR_LABELS[variable]} — fulan-fulan")
    smooth = st.toggle("Hatudu média 12 fulan (trend)", value=True)
    fig = px.line(f, x="date", y=variable, color="municipality", labels={variable: VAR_LABELS[variable], "date": ""})
    fig.update_traces(line=dict(width=1), opacity=0.45 if smooth else 1)
    if smooth:
        nat = (monthly[monthly["municipality"].isin(munis) & monthly["year"].between(*years)]
               .groupby("date")[variable].mean().rolling(12).mean())
        fig.add_scatter(x=nat.index, y=nat.values, name="Média munisípiu (12 fulan)", line=dict(color=INK, width=3))
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.2), margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Total anuál / média anuál**")
        agg = "sum" if variable in ("rain_mm", "et0_mm", "water_balance", "dry_days") else "mean"
        yearly = f.groupby(["year", "municipality"])[variable].agg(agg).groupby("year").mean().reset_index()
        fig = px.bar(yearly, x="year", y=variable, labels={variable: VAR_LABELS[variable], "year": ""},
                     color_discrete_sequence=[MONSOON])
        if len(yearly) > 2:
            z = np.polyfit(yearly["year"], yearly[variable], 1)
            fig.add_scatter(x=yearly["year"], y=np.polyval(z, yearly["year"]), name=f"Trend {z[0]:+.2f}/tinan",
                            line=dict(color=LATERITE, dash="dash"))
        fig.update_layout(height=340, margin=dict(t=10), legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown("**Padraun sazonál (klimatolojia)**")
        clim = f.groupby("month")[variable].mean().reindex(range(1, 13))
        fig = go.Figure(go.Bar(x=MONTHS_TET, y=clim.values,
                               marker_color=[PADDY if m in config.WET_SEASON_MONTHS else DRYSEASON for m in range(1, 13)]))
        fig.update_layout(height=340, margin=dict(t=10), yaxis_title=VAR_LABELS[variable])
        st.plotly_chart(fig, width="stretch")
        st.caption("Verde = tempu udan (Dez–Abr), kinur = tempu bailoron (Mai–Nov)")

# ---------------- COMPARISON ----------------
with t_comp:
    c1, c2 = st.columns([3, 2])
    agg = "sum" if variable in ("rain_mm", "et0_mm", "water_balance", "dry_days") else "mean"
    per = (f.groupby(["municipality", "year"])[variable].agg(agg).groupby("municipality").mean()
           .sort_values().reset_index())
    per["zone"] = per["municipality"].map(lambda m: config.MUNICIPALITIES[m]["zone"])
    with c1:
        st.markdown(f"**{VAR_LABELS[variable]} per munisípiu** ({'total' if agg == 'sum' else 'média'} per tinan)")
        fig = px.bar(per, x=variable, y="municipality", color="zone", orientation="h",
                     color_discrete_map={"lowland": MONSOON, "highland": PADDY},
                     labels={variable: VAR_LABELS[variable], "municipality": ""})
        fig.update_layout(height=460, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown("**Mapa munisípiu**")
        per["lat"] = per["municipality"].map(lambda m: config.MUNICIPALITIES[m]["lat"])
        per["lon"] = per["municipality"].map(lambda m: config.MUNICIPALITIES[m]["lon"])
        per["crop"] = per["municipality"].map(lambda m: config.MUNICIPALITIES[m]["main_crop"])
        size = per[variable].abs() + 1
        try:
            fig = px.scatter_map(per, lat="lat", lon="lon", size=size, color=variable, hover_name="municipality",
                                 hover_data={"crop": True, "lat": False, "lon": False},
                                 color_continuous_scale="YlGnBu", zoom=6.8, center={"lat": -8.8, "lon": 125.8})
        except AttributeError:   # plotly tuan
            fig = px.scatter_mapbox(per, lat="lat", lon="lon", size=size, color=variable, hover_name="municipality",
                                    color_continuous_scale="YlGnBu", zoom=6.8, center={"lat": -8.8, "lon": 125.8},
                                    mapbox_style="open-street-map")
        fig.update_layout(height=460, margin=dict(t=10, l=0, r=0, b=0))
        st.plotly_chart(fig, width="stretch")

    st.markdown("**Heatmap: munisípiu × fulan**")
    hm = f.pivot_table(index="municipality", columns="month", values=variable, aggfunc="mean").reindex(columns=range(1, 13))
    fig = px.imshow(hm, x=MONTHS_TET, aspect="auto", color_continuous_scale="YlGnBu" if variable != "tmean_c" else "YlOrRd",
                    labels=dict(color=VAR_LABELS[variable]))
    fig.update_layout(height=420, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")

# ---------------- FORECAST (TIME SERIES) ----------------
with t_fc:
    if forecasts.empty:
        st.info("Previzaun seidauk iha. Hala'o `python -m src.models`.")
    else:
        c1, c2 = st.columns(2)
        fm = c1.selectbox("Munisípiu ba previzaun", munis, index=munis.index("Dili") if "Dili" in munis else 0)
        fv = c2.selectbox("Variavel previzaun", ["rain_mm", "tmean_c"], format_func=VAR_LABELS.get)

        # Hatudu tinan 5 ikus (60 fulan) husi observasaun
        hist = monthly[monthly["municipality"] == fm].sort_values("date").set_index("date")[fv].iloc[-60:]
        fc = forecasts[(forecasts["municipality"] == fm) & (forecasts["variable"] == fv)]
        fig = go.Figure()
        fig.add_scatter(x=hist.index, y=hist.values, name="Observasaun", line=dict(color=INK))
        fig.add_scatter(x=pd.concat([fc["date"], fc["date"][::-1]]),
                        y=pd.concat([fc["upper_95"], fc["lower_95"][::-1]]),
                        fill="toself", fillcolor="rgba(47,93,124,0.18)", line=dict(width=0), name="Intervalu 95%")
        fig.add_scatter(x=fc["date"], y=fc["forecast"], name="Previzaun SARIMA", line=dict(color=MONSOON, width=3))
        fig.add_scatter(x=fc["date"], y=fc["climatology"], name="Klimatolojia (média)",
                        line=dict(color=DRYSEASON, dash="dot"))
        fig.update_layout(height=430, yaxis_title=VAR_LABELS[fv], legend=dict(orientation="h", y=-0.15), margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

        # --- Alerta agríkola (regra simples bazeia ba previzaun vs klimatolojia) ---
        if fv == "rain_mm":
            st.markdown("**Alerta agríkola — fulan 3 ba oin**")
            nxt = fc.head(3).copy()
            nxt["ratio"] = nxt["forecast"] / nxt["climatology"].replace(0, np.nan)
            nxt["status"] = np.select([nxt["ratio"] < 0.6, nxt["ratio"] > 1.5],
                                      ["Risku maran — prepara bee/irigasaun", "Risku udan boot — kuidadu inundasaun"],
                                      "Normál")
            nxt["fulan"] = nxt["date"].dt.strftime("%b %Y")
            st.dataframe(nxt[["fulan", "forecast", "climatology", "status"]].rename(
                columns={"forecast": "Previzaun (mm)", "climatology": "Média (mm)", "status": "Status"}),
                hide_index=True, width="stretch")

        st.markdown("**Avaliasaun modelu** (teste iha fulan "
                    f"{metrics.get('test_months', 12)} ikus; RMSE ki'ik = di'ak liu)")
        ev = evals[(evals["variable"] == fv)]
        c1, c2 = st.columns([2, 3])
        with c1:
            tbl = ev.groupby("model")[["MAE", "RMSE", "R2", "sMAPE_%"]].mean().round(2).sort_values("RMSE")
            st.dataframe(tbl, width="stretch")
            st.caption("Média munisípiu hotu. Baseline: Seasonal naive no Climatology.")
        with c2:
            tp = test_preds[(test_preds["municipality"] == fm) & (test_preds["variable"] == fv)]
            if not tp.empty:
                fig = px.line(tp, x="date", y="predicted", color="model", labels={"predicted": VAR_LABELS[fv], "date": ""})
                act = tp.drop_duplicates("date")
                fig.add_scatter(x=act["date"], y=act["actual"], name="Atuál", mode="lines+markers",
                                line=dict(color=INK, width=3))
                fig.update_layout(height=320, margin=dict(t=10), legend=dict(orientation="h", y=-0.3))
                st.plotly_chart(fig, width="stretch")

        imp = metrics.get("lag_regression_importance", {}).get("Random Forest (lag)")
        if imp and fv == "rain_mm":
            with st.expander("Feature importance — Random Forest (lag regression)"):
                s = pd.Series(imp).sort_values()
                st.plotly_chart(px.bar(s, orientation="h", color_discrete_sequence=[PADDY],
                                       labels={"value": "Importance", "index": ""}).update_layout(
                    height=320, showlegend=False, margin=dict(t=10)), width="stretch")

# ---------------- CROP YIELD REGRESSION ----------------
with t_yield:
    yr = metrics.get("yield_regression", {})
    if yield_preds.empty or "metrics" not in yr:
        st.info(yr.get("note", "Modelu produtividade seidauk iha."))
    else:
        st.markdown(f"Regression: **produtividade serea (kg/ha)** husi klima anuál — "
                    f"n = {yr['n_years']} tinan ({yr['years'][0]}–{yr['years'][1]}), validasaun **{yr['cv']}**. "
                    f"Modelu di'ak liu: **{yr['best_model']}**.")
        c1, c2 = st.columns([3, 2])
        with c1:
            long = yield_preds.melt(id_vars="year", var_name="serie", value_name="kg/ha")
            fig = px.line(long, x="year", y="kg/ha", color="serie", markers=True,
                          color_discrete_map={"actual": INK})
            fig.update_layout(height=380, margin=dict(t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, width="stretch")
        with c2:
            st.dataframe(pd.DataFrame(yr["metrics"]).T.sort_values("RMSE"), width="stretch")
            coef = pd.Series(yr["interpretation"]["ridge_standardized_coef"]).sort_values()
            fig = px.bar(coef, orientation="h", color=coef.values > 0,
                         color_discrete_map={True: PADDY, False: LATERITE},
                         labels={"value": "Koefisiente standardizadu (kg/ha per 1 SD)", "index": ""})
            fig.update_layout(height=260, showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig, width="stretch")

        # What-if simulation
        mp = O / "yield_model.joblib"
        if mp.exists():
            st.markdown("**Simulasaun 'what-if'** — muda kondisaun klima no haree produtividade ne'ebé modelu prevee")
            bundle = joblib.load(mp)
            rng = yr["feature_ranges"]
            cols = st.columns(len(bundle["features"]))
            vals = {}
            for c, feat in zip(cols, bundle["features"]):
                lo, hi, med = rng[feat]
                if feat == "year":
                    vals[feat] = c.number_input("Tinan", value=int(hi) + 1, step=1)
                else:
                    vals[feat] = c.slider(feat, float(lo * 0.8), float(hi * 1.2), float(med))
            pred = bundle["model"].predict(pd.DataFrame([vals]))[0]
            st.metric(f"Produtividade prevee ({bundle['name']})", f"{pred:,.0f} kg/ha")
            st.caption("Atensaun: modelu ho dadus anuál uitoan deit — uza ba kompriensaun, la'ós desizaun final. "
                       "Valór li'ur husi dadus treinu (extrapolation) la konfiavel.")

# ---------------- NEWS & ALERTS (RSS + text mining) ----------------
with t_news:
    if news.empty:
        st.info("Notísia la iha.")
    else:
        topics = sorted({t.strip() for ts_ in news["topics"].dropna() for t in ts_.split(",")})
        pick = st.multiselect("Topiku", topics, default=[t for t in topics if t != "other"] or topics)
        nn = news[news["topics"].apply(lambda s: any(t in str(s) for t in pick))]
        counts = pd.Series([t.strip() for s in news["topics"].dropna() for t in s.split(",")]).value_counts()
        c1, c2 = st.columns([1, 3])
        c1.plotly_chart(px.bar(counts, color_discrete_sequence=[MONSOON], labels={"value": "artigu", "index": ""})
                        .update_layout(height=300, showlegend=False, margin=dict(t=10)), width="stretch")
        with c2:
            for r in nn.head(15).itertuples():
                date_txt = f"{r.published:%d %b %Y}" if pd.notna(r.published) else ""
                muni_txt = f" — {r.municipalities_mentioned}" if isinstance(r.municipalities_mentioned, str) and r.municipalities_mentioned else ""
                st.markdown(f"- [{r.title}]({r.link})  \n  <span class='source-note'>{date_txt} · {r.topics}{muni_txt}</span>",
                            unsafe_allow_html=True)

# ---------------- DATA ----------------
with t_data:
    st.markdown("**Dadus fulan-fulan (tuir filtru)**")
    st.dataframe(f.sort_values(["municipality", "date"]), width="stretch", height=380)
    st.download_button("Download CSV", f.to_csv(index=False).encode(), "tl_agri_monthly_filtered.csv", "text/csv")
    st.markdown("<p class='source-note'>Fonte: Open-Meteo Historical Weather API (ERA5), NASA POWER, "
                "World Bank Open Data, Wikipedia (scraping), Google News & ReliefWeb RSS.</p>", unsafe_allow_html=True)
