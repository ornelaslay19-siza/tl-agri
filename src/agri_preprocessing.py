"""
agri_preprocessing.py
=====================
PASSU 2 (extension): HISTORICAL DATA -> dadus mos ba análize

FOLIN (WFP):
  1. Hasai liña HXL (#date, #adm1 ...) ne'ebé HDX hatama iha liña 2
  2. Tipu dadus (data, numériku), filtru folin "Retail"
  3. Standardiza unidade: "50 KG" -> folin per 1 KG
  4. Duplikadu -> média; outlier (folin > 3x ka < 1/3 mediana série) -> hasai
  5. Folin REAL = folin nominál / CPI x CPI tinan ikus (hasai efeitu inflasaun)
  6. Série nasionál = mediana merkadu hotu per fulan
  7. Feature: tempu hamlaha, anomalia udan (husi dadus klima)

PRODUSAUN (FAOSTAT):  long -> wide (area, yield, production) + kombina ho klima anuál
LOKALIZASAUN: merkadu (lat/lon, munisípiu) + produsaun per munisípiu

Uza:  python -m src.agri_preprocessing
"""
import json
import re

import numpy as np
import pandas as pd

from . import config


# ==========================================================================
# FOLIN
# ==========================================================================
def _unit_factor(unit):
    """'50 KG' -> (50, 'KG'); 'KG' -> (1, 'KG'); '30 pcs' -> (30, 'pcs')."""
    m = re.match(r"^\s*([\d.]+)\s*(.*)$", str(unit))
    if m and m.group(2):
        return float(m.group(1)), m.group(2).strip()
    return 1.0, str(unit).strip()


def clean_prices(raw, report):
    df = raw.copy()
    report["price_rows_raw"] = int(len(df))
    # (1) Liña HXL
    df = df[~df["date"].astype(str).str.startswith("#")]
    # (2) Tipu dadus no filtru
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    price_col = "usdprice" if "usdprice" in df.columns else "price"
    df["price"] = pd.to_numeric(df[price_col], errors="coerce")
    for c in ("latitude", "longitude"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    if "pricetype" in df.columns and (df["pricetype"] == "Retail").any():
        df = df[df["pricetype"] == "Retail"]
    if "priceflag" in df.columns:
        df = df[df["priceflag"].astype(str).str.contains("actual|aggregate", case=False, na=True)]
    df = df.dropna(subset=["date", "price", "commodity", "market"])
    df = df[df["price"] > 0]

    # (3) Unidade standard
    fu = df["unit"].map(_unit_factor)
    df["price"] = df["price"] / fu.map(lambda x: x[0])
    df["unit_std"] = fu.map(lambda x: x[1]).str.upper().replace({"PCS": "UNIT"})
    df["series"] = df["commodity"] + " (USD/" + df["unit_std"] + ")"

    # (4) Duplikadu -> média
    before = len(df)
    keep = ["date", "admin1", "market", "latitude", "longitude", "category", "commodity", "unit_std", "series"]
    df = df.groupby([c for c in keep if c in df.columns], dropna=False, as_index=False)["price"].mean()
    report["price_duplicates_merged"] = int(before - len(df))
    # Outlier: kompara ho mediana série (merkadu + commodity)
    med = df.groupby(["market", "series"])["price"].transform("median")
    ratio = df["price"] / med
    out = (ratio > 3) | (ratio < 1 / 3)
    report["price_outliers_removed"] = int(out.sum())
    df = df[~out].copy()
    # Standardiza naran munisípiu ('Lautém' -> 'Lautem', 'Oecussi' -> 'Oecusse', 'Cova Lima' -> 'Covalima')
    from .preprocessing import normalize_name
    lookup = {normalize_name(m): m for m in config.MUNICIPALITIES}
    lookup.update({"oecussi": "Oecusse", "oecusseambeno": "Oecusse", "raeoa": "Oecusse", "covalima": "Covalima"})
    df["admin1"] = df["admin1"].map(lambda a: next((v for k, v in lookup.items() if k in normalize_name(a)),
                                                   str(a).strip()))
    return df.sort_values(["series", "market", "date"])


def add_real_price(df, cpi):
    """Folin real ho base CPI tinan ikus: 'folin iha dólar ohin loron'."""
    c = cpi.copy()
    c["cpi"] = pd.to_numeric(c["cpi"], errors="coerce")
    c = c.dropna().sort_values("year")
    # CPI anuál -> fulan-fulan (interpolasaun); tinan ne'ebé la iha -> ekstende valór ikus
    months = pd.date_range(f"{int(c['year'].min())}-01-01", df["date"].max(), freq="MS")
    cm = pd.Series(np.nan, index=months)
    for _, r in c.iterrows():
        ts = pd.Timestamp(int(r["year"]), 7, 1)          # CPI anuál = meiu tinan
        if ts in cm.index:
            cm[ts] = r["cpi"]
    cm = cm.interpolate().ffill().bfill()
    base = cm.iloc[-1]
    df = df.copy()
    df["cpi"] = df["date"].map(cm)
    df["real_price"] = (df["price"] / df["cpi"] * base).round(3)
    return df


def national_series(df, weather_monthly):
    """Mediana merkadu hotu per fulan + feature klima nasionál."""
    nat = (df.groupby(["series", "commodity", "date"])
           .agg(price=("price", "median"), real_price=("real_price", "median"), n_markets=("market", "nunique"))
           .reset_index())
    if not weather_monthly.empty:
        w = (weather_monthly.groupby("date")
             .agg(rain_mm=("rain_mm", "mean"), rain_anomaly_pct=("rain_anomaly_pct", "mean")).reset_index())
        # Anomalia udan akumula fulan 6 kotuk (efeitu ba kolleita no folin)
        w["rain_anom_6m"] = w["rain_anomaly_pct"].rolling(6, min_periods=3).mean()
        nat = nat.merge(w, on="date", how="left")
    nat["month"] = nat["date"].dt.month
    nat["lean_season"] = nat["month"].isin(config.LEAN_SEASON_MONTHS).astype(int)
    return nat


def market_table(df):
    return (df.groupby(["market", "admin1"])
            .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"), n_obs=("price", "size"),
                 n_commodities=("series", "nunique"), first=("date", "min"), last=("date", "max"))
            .reset_index())


# ==========================================================================
# PRODUSAUN
# ==========================================================================
def clean_production(raw, annual_climate):
    p = raw.copy()
    p["value"] = pd.to_numeric(p["value"], errors="coerce")
    p["year"] = pd.to_numeric(p["year"], errors="coerce").astype("Int64")
    wide = p.pivot_table(index=["crop", "year"], columns="element", values="value", aggfunc="mean").reset_index()
    wide.columns.name = None
    # Recalcula yield se falta (production / area)
    if {"production_t", "area_harvested_ha"} <= set(wide.columns):
        calc = wide["production_t"] / wide["area_harvested_ha"] * 1000
        wide["yield_kg_ha"] = wide.get("yield_kg_ha", calc).fillna(calc)
    wide["year"] = wide["year"].astype(int)
    # Kombina ho klima anuál (husi preprocessing klima)
    if not annual_climate.empty:
        cols = ["year", "annual_rain_mm", "wet_season_rain_mm", "wet_season_dry_days", "dry_days",
                "mean_temp_c", "max_temp_c", "heavy_rain_days"]
        wide = wide.merge(annual_climate[[c for c in cols if c in annual_climate]], on="year", how="left")
    # Mudansa anuál (%)
    wide = wide.sort_values(["crop", "year"])
    wide["production_change_pct"] = (wide.groupby("crop")["production_t"].pct_change() * 100).round(1)
    return wide


def clean_municipal(raw):
    m = raw.copy()
    m["production_t"] = pd.to_numeric(m["production_t"], errors="coerce")
    m["municipality"] = m["municipality"].astype(str).str.strip()
    m["lat"] = m["municipality"].map(lambda x: config.MUNICIPALITIES.get(x, {}).get("lat"))
    m["lon"] = m["municipality"].map(lambda x: config.MUNICIPALITIES.get(x, {}).get("lon"))
    m["share_pct"] = (m["production_t"] / m.groupby(["crop", "year"])["production_t"].transform("sum") * 100).round(1)
    return m.dropna(subset=["lat", "production_t"])


def run():
    print("=" * 60)
    print("AGRI PREPROCESSING: folin, produsaun, lokalizasaun")
    print("=" * 60)
    R, P = config.DATA_RAW, config.DATA_PROCESSED
    report = {}
    weather_m = pd.read_csv(P / "weather_monthly.csv", parse_dates=["date"]) \
        if (P / "weather_monthly.csv").exists() else pd.DataFrame()
    annual = pd.read_csv(P / "annual_national.csv") if (P / "annual_national.csv").exists() else pd.DataFrame()

    prices = clean_prices(pd.read_csv(R / "wfp_prices_raw.csv", low_memory=False), report)
    prices = add_real_price(prices, pd.read_csv(R / "cpi_raw.csv"))
    nat = national_series(prices, weather_m)
    markets = market_table(prices)
    prod = clean_production(pd.read_csv(R / "faostat_production_raw.csv"), annual)
    muni = clean_municipal(pd.read_csv(R / "municipal_production_raw.csv"))

    prices.to_csv(P / "prices_market_monthly.csv", index=False)
    nat.to_csv(P / "prices_national_monthly.csv", index=False)
    markets.to_csv(P / "markets.csv", index=False)
    prod.to_csv(P / "production_annual.csv", index=False)
    muni.to_csv(P / "municipal_production.csv", index=False)

    report.update({"price_rows_clean": int(len(prices)), "price_series": int(prices["series"].nunique()),
                   "markets": int(len(markets)),
                   "price_period": [str(prices["date"].min().date()), str(prices["date"].max().date())],
                   "production_rows": int(len(prod)), "crops": sorted(prod["crop"].unique().tolist())})
    (P / "agri_preprocessing_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
