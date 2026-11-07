"""
eda.py
======
PASSU 3: EXPLORATORY DATA ANALYSIS (EDA)

Pergunta EDA sira ne'ebé ita responde:
  Q1. Statistics  : Oinsá média, desviu padraun, min/max ba klima kada munisípiu?
  Q2. Distribution: Oinsá distribuisaun udan fulan-fulan? (skewed / la normál?)
  Q3. Seasonality : Fulan saida mak udan barak / maran? (padraun monsaun)
  Q4. Trend       : Temperatura no udan sa'e ka tun durante tinan 30?  (Mann-Kendall)
  Q5. Comparison  : Munisípiu ne'ebé mak udan barak liu / maran liu?
  Q6. Correlation : Variavel klima saida mak iha relasaun ho produtividade serea?

Output: gráfiku PNG iha reports/figures/ + data/outputs/eda_summary.json

Uza:  python -m src.eda
"""
import json

import matplotlib
matplotlib.use("Agg")          # la presiza ekran (bele hala'o iha server)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose

from . import config

# Paleta kór konsistente ho dashboard
C_RAIN, C_TEMP, C_SOIL, C_DRY = "#2F5D7C", "#B5462E", "#3E6B48", "#C9A227"
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3})


def savefig(name):
    path = config.FIG_DIR / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"   figura -> {path.relative_to(config.ROOT)}")


def mann_kendall(series):
    """
    Teste trend Mann-Kendall (non-paramétriku, la presiza distribuisaun normál).
    Uza Kendall tau entre tempu no valór. p < 0.05 -> trend signifikativu.
    Sen's slope = mediana husi inklinasaun hotu (robust ba outlier).
    """
    y = np.asarray(series.dropna(), dtype=float)
    x = np.arange(len(y))
    tau, p = stats.kendalltau(x, y)
    slope = stats.theilslopes(y, x)[0]
    return {"tau": round(float(tau), 3), "p_value": round(float(p), 4),
            "sen_slope_per_year": round(float(slope), 4),
            "trend": ("increasing" if tau > 0 else "decreasing") if p < 0.05 else "no significant trend"}


def run():
    print("=" * 60)
    print("EXPLORATORY DATA ANALYSIS")
    print("=" * 60)
    monthly = pd.read_csv(config.DATA_PROCESSED / "weather_monthly.csv", parse_dates=["date"])
    annual = pd.read_csv(config.DATA_PROCESSED / "annual_national.csv")
    summary = {}

    # ---------------- Q1. DESCRIPTIVE STATISTICS ----------------
    desc = (monthly.groupby("municipality")[["rain_mm", "tmean_c", "rh_pct", "dry_days"]]
            .agg(["mean", "std", "min", "max"]).round(2))
    desc.to_csv(config.DATA_OUTPUTS / "descriptive_stats_by_municipality.csv")
    summary["overall_stats"] = monthly[["rain_mm", "tmean_c", "tmax_c", "tmin_c", "rh_pct"]].describe().round(2).to_dict()

    # ---------------- Q2. DISTRIBUTION ----------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(monthly["rain_mm"], bins=50, color=C_RAIN, alpha=0.85)
    axes[0].set(title="Distribuisaun udan fulan-fulan", xlabel="Udan (mm/fulan)", ylabel="Frekuénsia")
    axes[1].hist(monthly["tmean_c"], bins=40, color=C_TEMP, alpha=0.85)
    axes[1].set(title="Distribuisaun temperatura média", xlabel="°C", ylabel="Frekuénsia")
    savefig("02_distribution")
    summary["rain_skewness"] = round(float(stats.skew(monthly["rain_mm"])), 3)   # > 1 = skewed maka'as

    # ---------------- Q3. SEASONALITY (boxplot per fulan) ----------------
    fig, ax = plt.subplots(figsize=(11, 4))
    data = [monthly.loc[monthly["month"] == m, "rain_mm"] for m in range(1, 13)]
    ax.boxplot(data, patch_artist=True, boxprops=dict(facecolor=C_RAIN, alpha=0.5))
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
    ax.set(title="Padraun sazonál udan (munisípiu hotu)", ylabel="Udan (mm/fulan)")
    savefig("03_seasonality_boxplot")
    clim = monthly.groupby("month")["rain_mm"].mean().round(1)
    summary["wettest_month"] = int(clim.idxmax())
    summary["driest_month"] = int(clim.idxmin())

    # Seasonal decomposition (trend + seasonal + residual) ba Dili
    dili = monthly[monthly["municipality"] == "Dili"].set_index("date")["rain_mm"].asfreq("MS")
    if dili.notna().sum() >= 48:
        dec = seasonal_decompose(dili.interpolate(), model="additive", period=12)
        fig = dec.plot()
        fig.set_size_inches(11, 7)
        fig.suptitle("Seasonal decomposition: udan Dili", y=1.01)
        savefig("03b_decomposition_dili")

    # ---------------- Q4. TREND ----------------
    nat_year = (monthly.groupby(["year", "municipality"])
                .agg(rain=("rain_mm", "sum"), temp=("tmean_c", "mean"), n=("month", "count"))
                .reset_index())
    nat_year = nat_year[nat_year["n"] == 12].groupby("year")[["rain", "temp"]].mean()
    summary["trend_annual_rain"] = mann_kendall(nat_year["rain"])
    summary["trend_annual_temp"] = mann_kendall(nat_year["temp"])

    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax, col, color, label in [(axes[0], "rain", C_RAIN, "Udan anuál (mm)"),
                                  (axes[1], "temp", C_TEMP, "Temperatura média (°C)")]:
        ax.plot(nat_year.index, nat_year[col], marker="o", color=color)
        z = np.polyfit(nat_year.index, nat_year[col], 1)
        ax.plot(nat_year.index, np.polyval(z, nat_year.index), "--", color="gray",
                label=f"Trend linear: {z[0]:+.3f}/tinan")
        ax.set_ylabel(label)
        ax.legend()
    axes[0].set_title("Trend klima nasionál (média munisípiu)")
    savefig("04_trend_national")

    # ---------------- Q5. COMPARISON ENTRE MUNISÍPIU ----------------
    comp = (monthly.groupby(["municipality", "year"])["rain_mm"].sum()
            .groupby("municipality").mean().sort_values())
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [C_SOIL if config.MUNICIPALITIES[m]["zone"] == "highland" else C_RAIN for m in comp.index]
    ax.barh(comp.index, comp.values, color=colors)
    ax.set(title="Média udan anuál per munisípiu (verde = foho, azul = tasi-ibun)", xlabel="mm/tinan")
    savefig("05_comparison_municipality")
    summary["wettest_municipality"] = comp.idxmax()
    summary["driest_municipality"] = comp.idxmin()

    # ---------------- Q6. CORRELATION ----------------
    num = annual.select_dtypes("number").drop(columns=["year"], errors="ignore").dropna(axis=1, how="all")
    corr = num.corr(method="pearson").round(2)
    corr.to_csv(config.DATA_OUTPUTS / "correlation_matrix.csv")
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=90)
    ax.set_yticks(range(len(corr)), corr.columns)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Korrelasaun (Pearson): klima anuál vs indikadór agrikultura")
    savefig("06_correlation_heatmap")
    if "cereal_yield_kg_ha" in corr:
        summary["corr_with_yield"] = corr["cereal_yield_kg_ha"].drop("cereal_yield_kg_ha").sort_values().to_dict()

    # Scatter: udan tempu udan vs produtividade
    if {"wet_season_rain_mm", "cereal_yield_kg_ha"} <= set(annual.columns):
        a = annual.dropna(subset=["wet_season_rain_mm", "cereal_yield_kg_ha"])
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(a["wet_season_rain_mm"], a["cereal_yield_kg_ha"], color=C_SOIL)
        for _, r in a.iterrows():
            ax.annotate(int(r["year"]), (r["wet_season_rain_mm"], r["cereal_yield_kg_ha"]), fontsize=7)
        ax.set(xlabel="Udan tempu udan (mm, Dez-Abr)", ylabel="Produtividade serea (kg/ha)",
               title="Udan tempu udan vs produtividade serea")
        savefig("06b_scatter_rain_yield")

    (config.DATA_OUTPUTS / "eda_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "overall_stats"}, indent=2, default=str))
    return summary


if __name__ == "__main__":
    run()
