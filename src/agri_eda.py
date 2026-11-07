"""
agri_eda.py

PASSU 3 (extension): EDA ba PRODUSAUN, LOKALIZASAUN no FOLIN
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from. import config
from.eda import mann_kendall, savefig

C = ["#2F5D7C", "#3E6B48", "#C9A227", "#9C3D2E", "#6B7F8E", "#7A5C3E", "#4E8A8A", "#A7A37E"]
MONTHS = ["Jan", "Feb", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

def run():
    print("=" * 60)
    print("AGRI EDA")
    print("=" * 60)
    P = config.DATA_PROCESSED
    prices = pd.read_csv(P / "prices_market_monthly.csv", parse_dates=["date"])
    nat = pd.read_csv(P / "prices_national_monthly.csv", parse_dates=["date"])
    prod = pd.read_csv(P / "production_annual.csv")
    muni = pd.read_csv(P / "municipal_production.csv")
    S = {}

    # ---- P1 trend folin
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=False)
    for i, (s, g) in enumerate(nat.groupby("series")):
        axes[0].plot(g["date"], g["price"], label=s, color=C[i % len(C)], lw=1.2)
        axes[1].plot(g["date"], g["real_price"], color=C[i % len(C)], lw=1.2)
    axes[0].set(title="Folin nominál (mediana nasionál)", ylabel="USD")
    axes[1].set(title="Folin real (dólar tinan ikus)", ylabel="USD")
    axes[0].legend(fontsize=7, ncol=2)
    savefig("agri_01_price_trend")
    S["price_trend_real"] = {s: mann_kendall(g.set_index("date")["real_price"].resample("YS").mean())
                             for s, g in nat.groupby("series")}

    # ---- P2 sazonalidade
    nat = nat.sort_values(["series", "date"])
    nat["idx"] = nat["price"] / nat.groupby("series")["price"].transform(
        lambda s: s.rolling(13, center=True, min_periods=7).mean())
    seas = nat.groupby(["series", "month"])["idx"].mean().unstack() * 100
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for i, (s, row) in enumerate(seas.iterrows()):
        ax.plot(MONTHS, row.values, marker="o", label=s, color=C[i % len(C)])
    ax.axhline(100, color="gray", lw=0.8)
    ax.axvspan(-0.5, 1.5, color="#C9A227", alpha=0.12)
    ax.axvspan(9.5, 11.5, color="#C9A227", alpha=0.12, label="Tempu hamlaha")
    ax.set(title="Índise sazonál folin (100 = média tinan)", ylabel="Índise")
    ax.legend(fontsize=7, ncol=3)
    savefig("agri_02_price_seasonality")

    # FIX: handle all-NA when production is demo
    try:
        S["seasonal_peak_month"] = {s: MONTHS[int(r.idxmax()) - 1] for s, r in seas.iterrows() if not r.isna().all()}
    except (ValueError, AttributeError):
        S["seasonal_peak_month"] = {}
    S["seasonal_amplitude_pct"] = (seas.max(axis=1) - seas.min(axis=1)).round(1).to_dict()

    # ---- P3 lokalizasaun
    last = prices[prices["date"] > prices["date"].max() - pd.DateOffset(months=12)]
    key = "Rice (local) (USD/KG)" if "Rice (local) (USD/KG)" in last["series"].values else last["series"].mode()[0]
    by_mk = last[last["series"] == key].groupby("market")["price"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(by_mk.index, by_mk.values, color="#2F5D7C")
    ax.set(title=f"Folin média 12 fulan ikus per merkadu: {key}", xlabel="USD")
    savefig("agri_03_price_by_market")
    S["price_by_market_series"] = key
    S["cheapest_market"], S["most_expensive_market"] = by_mk.idxmin(), by_mk.idxmax()
    S["market_price_gap_pct"] = round(float((by_mk.max() / by_mk.min() - 1) * 100), 1)
    last = last.assign(zone=last["admin1"].map(lambda m: config.MUNICIPALITIES.get(m, {}).get("zone", "unknown")))
    S["zone_price_ratio_highland_vs_lowland"] = (
        last.groupby(["series", "zone"])["price"].mean().unstack().pipe(
            lambda t: (t["highland"] / t["lowland"]).round(3) if {"highland", "lowland"} <= set(t.columns) else pd.Series(dtype=float)
        ).to_dict())

    # ---- P4 volatilidade
    vol = nat.groupby("series").apply(
        lambda g: (g["price"].pct_change().std() * 100), include_groups=False).round(2).sort_values()
    S["monthly_volatility_pct"] = vol.to_dict()

    # ---- P5 produsaun
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for i, (crop, g) in enumerate(prod.groupby("crop")):
        axes[0].plot(g["year"], g["production_t"] / 1000, label=crop, color=C[i])
        axes[1].plot(g["year"], g["area_harvested_ha"] / 1000, color=C[i])
        axes[2].plot(g["year"], g["yield_kg_ha"], color=C[i])
    axes[0].set(title="Produsaun (rihun tonelada)")
    axes[1].set(title="Área kolleita (rihun ha)")
    axes[2].set(title="Produtividade (kg/ha)")
    axes[0].legend(fontsize=8)
    savefig("agri_04_production_trend")
    S["production_trend"] = {c: mann_kendall(g["production_t"]) for c, g in prod.groupby("crop")}

    # ---- P6 korrelasaun
    ann_price = (nat.assign(year=nat["date"].dt.year).groupby(["commodity", "year"])["real_price"].mean()
                .unstack(0).add_prefix("price_"))
    wide = prod.pivot_table(index="year", columns="crop", values="production_t").add_prefix("prod_")
    clim = prod.groupby("year")[["wet_season_rain_mm", "wet_season_dry_days", "mean_temp_c"]].first()
    comb = clim.join(wide).join(ann_price)
    corr = comb.corr().round(2)
    corr.to_csv(config.DATA_OUTPUTS / "agri_correlation.csv")
    cols = [c for c in corr.columns if c.startswith(("prod_Maize", "prod_Rice", "price_Maize", "price_Rice", "wet_"))]
    sub = corr.loc[cols, cols] if len(cols)>1 else corr
    fig, ax = plt.subplots(figsize=(7.5, 6))
    im = ax.imshow(sub, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(sub)), sub.columns, rotation=60, ha="right")
    ax.set_yticks(range(len(sub)), sub.columns)
    for i in range(len(sub)):
        for j in range(len(sub)):
            ax.text(j, i, f"{sub.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, shrink=0.8)
    ax.set_title("Korrelasaun: udan ↔ produsaun ↔ folin real")
    savefig("agri_05_correlation")
    S["corr_highlights"] = {c: sub[c].drop(c).to_dict() for c in sub.columns if c.startswith("price_")} if len(cols)>1 else {}

    # ---- P7 kontribuisaun munisípiu
    fig, axes = plt.subplots(1, muni["crop"].nunique(), figsize=(14, 4.5))
    for ax, (crop, g) in zip(np.atleast_1d(axes), muni.groupby("crop")):
        g = g.sort_values("share_pct")
        ax.barh(g["municipality"], g["share_pct"], color="#3E6B48")
        ax.set(title=f"{crop}: % produsaun nasionál", xlabel="%")
    savefig("agri_06_municipal_share")
    S["top_municipality_by_crop"] = muni.loc[muni.groupby("crop")["share_pct"].idxmax(),
                                             ["crop", "municipality", "share_pct"]].to_dict(orient="records")

    (config.DATA_OUTPUTS / "agri_eda_summary.json").write_text(json.dumps(S, indent=2, default=str))
    print(json.dumps({k: S[k] for k in ("seasonal_peak_month", "cheapest_market", "most_expensive_market",
                                         "market_price_gap_pct") if k in S}, indent=2, default=str))
    return S

if __name__ == "__main__":
    run()