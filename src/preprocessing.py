"""
preprocessing.py
================
PASSU 2: DATA PREPROCESSING (Prepara dadus)

Etapa sira:
  1. Cleaning      : tipu dadus, duplikadu, valór imposível (erru sensor)
  2. Missing values: interpolasaun (temperatura) no klimatolojia (udan)
  3. Transformation: feature foun (sezaun, GDD, water balance, loron maran)
  4. Aggregation   : loron -> fulan (ba time series) no fulan -> tinan (ba regression)
  5. Integration   : kombina klima + World Bank + info munisípiu

Output (data/processed/):
  weather_daily_clean.csv, weather_monthly.csv, annual_national.csv,
  news_clean.csv, municipality_info_clean.csv, preprocessing_report.json

Uza:  python -m src.preprocessing
"""
import json
import re
import unicodedata

import numpy as np
import pandas as pd

from . import config, sample_data

# Limite fíziku (physical limits) ba klima Timor-Leste. Valór li'ur = erru.
VALID_RANGES = {
    "temperature_2m_max": (5, 45),
    "temperature_2m_min": (-5, 35),
    "temperature_2m_mean": (0, 40),
    "precipitation_sum": (0, 500),          # > 500 mm/loron la realístiku iha TL
    "relative_humidity_2m_mean": (0, 100),
    "et0_fao_evapotranspiration": (0, 15),
    "shortwave_radiation_sum": (0, 40),
}


def normalize_name(s):
    """'Liquiçá' -> 'liquica', 'Cova Lima' -> 'covalima' (atu kombina naran)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


# ==========================================================================
# 1-2. WEATHER: CLEANING + MISSING VALUES
# ==========================================================================
def clean_weather(df, report):
    df = df.copy()
    report["weather_rows_raw"] = int(len(df))

    # (a) Tipu dadus: data -> datetime, kolun numériku -> float
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    num_cols = [c for c in VALID_RANGES if c in df.columns]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date"])

    # (b) Hasai duplikadu (munisípiu + data hanesan)
    before = len(df)
    df = df.drop_duplicates(subset=["municipality", "date"], keep="last")
    report["duplicates_removed"] = int(before - len(df))

    # (c) Valór imposível -> NaN (depois sei hakonu hanesan missing)
    invalid = {}
    for c in num_cols:
        lo, hi = VALID_RANGES[c]
        mask = (df[c] < lo) | (df[c] > hi)
        invalid[c] = int(mask.sum())
        df.loc[mask, c] = np.nan
    # Temperatura máx tenke >= mín
    swap = df["temperature_2m_max"] < df["temperature_2m_min"]
    df.loc[swap, ["temperature_2m_max", "temperature_2m_min"]] = np.nan
    report["invalid_values_set_to_nan"] = invalid

    report["missing_before"] = {c: int(df[c].isna().sum()) for c in num_cols}

    # (d) MISSING VALUES
    df = df.sort_values(["municipality", "date"]).reset_index(drop=True)
    df["month"] = df["date"].dt.month

    # Temperatura, RH, radiasaun, ET0: muda neineik loron ba loron ->
    #   interpolasaun linear (máximu 7 loron), depois klimatolojia fulan
    smooth_cols = [c for c in num_cols if c != "precipitation_sum"]
    for c in smooth_cols:
        df[c] = df.groupby("municipality")[c].transform(
            lambda s: s.interpolate(method="linear", limit=7, limit_direction="both"))

    # Udan: LA bele interpola (udan la kontínuu). Uza MEDIANA udan iha
    # munisípiu + fulan hanesan (klimatolojia). Mediana udan loron-loron dala barak = 0.
    for c in num_cols:
        clim = df.groupby(["municipality", "month"])[c].transform("median")
        df[c] = df[c].fillna(clim)

    # Mean temperature la iha? kalkula husi (max+min)/2
    m = df["temperature_2m_mean"].isna()
    df.loc[m, "temperature_2m_mean"] = (df.loc[m, "temperature_2m_max"] + df.loc[m, "temperature_2m_min"]) / 2

    report["missing_after"] = {c: int(df[c].isna().sum()) for c in num_cols}
    return df


# ==========================================================================
# 3. TRANSFORMATION / FEATURE ENGINEERING
# ==========================================================================
def add_features(df):
    df = df.copy()
    df["year"] = df["date"].dt.year
    # Sezaun agríkola Timor-Leste
    df["season"] = np.where(df["month"].isin(config.WET_SEASON_MONTHS), "Wet (Tempu udan)", "Dry (Tempu bailoron)")
    # "Tinan agríkola" komesa Novembru (preparasaun rai -> kolleita Abríl/Maiu)
    df["agri_year"] = np.where(df["month"] >= 11, df["year"] + 1, df["year"])
    df["temp_range"] = df["temperature_2m_max"] - df["temperature_2m_min"]
    df["dry_day"] = (df["precipitation_sum"] < config.DRY_DAY_THRESHOLD_MM).astype(int)
    df["heavy_rain_day"] = (df["precipitation_sum"] >= 50).astype(int)   # risku inundasaun
    # Growing Degree Days (GDD): akumulasaun "manas" ne'ebé ai-horis presiza atu moris
    df["gdd"] = (df["temperature_2m_mean"] - config.GDD_BASE_TEMP).clip(lower=0)
    # Water balance: udan - evapotranspirasaun (negativu = rai maran / stress bee)
    if "et0_fao_evapotranspiration" in df.columns:
        df["water_balance"] = df["precipitation_sum"] - df["et0_fao_evapotranspiration"]
    # Info munisípiu husi config
    df["zone"] = df["municipality"].map(lambda m: config.MUNICIPALITIES.get(m, {}).get("zone", "unknown"))
    return df


# ==========================================================================
# 4. AGGREGATION
# ==========================================================================
def to_monthly(daily):
    """Loron -> fulan. Udan = SUM, temperatura = MEAN, loron maran = COUNT."""
    agg = {
        "precipitation_sum": "sum",
        "temperature_2m_mean": "mean",
        "temperature_2m_max": "mean",
        "temperature_2m_min": "mean",
        "relative_humidity_2m_mean": "mean",
        "dry_day": "sum",
        "heavy_rain_day": "sum",
        "gdd": "sum",
    }
    for extra, how in [("et0_fao_evapotranspiration", "sum"), ("water_balance", "sum"),
                       ("shortwave_radiation_sum", "mean")]:
        if extra in daily.columns:
            agg[extra] = how
    monthly = (daily.set_index("date")
               .groupby("municipality")
               .resample("MS")                # MS = Month Start
               .agg(agg)
               .reset_index())
    # Hasai fulan ikus ne'ebé seidauk kompletu (atu la halo udan fulan ne'e ki'ik liu)
    max_date = pd.Timestamp(daily["date"].max())
    if not max_date.is_month_end:
        current_month_start = max_date.to_period("M").to_timestamp()
        monthly = monthly[monthly["date"] < current_month_start]

    monthly = monthly.rename(columns={
        "precipitation_sum": "rain_mm", "temperature_2m_mean": "tmean_c",
        "temperature_2m_max": "tmax_c", "temperature_2m_min": "tmin_c",
        "relative_humidity_2m_mean": "rh_pct", "et0_fao_evapotranspiration": "et0_mm",
        "shortwave_radiation_sum": "radiation_mj", "dry_day": "dry_days",
        "heavy_rain_day": "heavy_rain_days",
    })
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month
    monthly["zone"] = monthly["municipality"].map(lambda m: config.MUNICIPALITIES.get(m, {}).get("zone"))

    # Anomalia udan (%): kompara ho média fulan hanesan iha tinan hotu
    clim = monthly.groupby(["municipality", "month"])["rain_mm"].transform("mean")
    monthly["rain_anomaly_pct"] = np.where(clim > 0, (monthly["rain_mm"] - clim) / clim * 100, 0).round(1)
    return monthly


def to_annual_national(daily, wb_long):
    """
    Dataset REGRESSION: 1 liña = 1 tinan agríkola (média munisípiu hotu).
    Target: cereal_yield_kg_ha (World Bank). Features: klima tinan ne'e.
    """
    d = daily.copy()
    wet = d[d["month"].isin(config.WET_SEASON_MONTHS)]
    # Kalkula per munisípiu depois média nasionál
    per_muni = d.groupby(["agri_year", "municipality"]).agg(
        annual_rain_mm=("precipitation_sum", "sum"),
        mean_temp_c=("temperature_2m_mean", "mean"),
        max_temp_c=("temperature_2m_max", "mean"),
        dry_days=("dry_day", "sum"),
        heavy_rain_days=("heavy_rain_day", "sum"),
        gdd=("gdd", "sum"),
    )
    wet_muni = wet.groupby(["agri_year", "municipality"]).agg(
        wet_season_rain_mm=("precipitation_sum", "sum"),
        wet_season_dry_days=("dry_day", "sum"),
    )
    per_muni = per_muni.join(wet_muni).reset_index()
    # Tinan kompletu deit (loron > 360 ba munisípiu hotu)
    counts = d.groupby("agri_year")["date"].nunique()
    full_years = counts[counts >= 360].index
    annual = (per_muni[per_muni["agri_year"].isin(full_years)]
              .groupby("agri_year").mean(numeric_only=True).reset_index()
              .rename(columns={"agri_year": "year"}))

    # World Bank: long -> wide (kolun ida ba indikadór ida)
    wb = wb_long.copy()
    wb["value"] = pd.to_numeric(wb["value"], errors="coerce")
    wb_wide = wb.pivot_table(index="year", columns="indicator", values="value").reset_index()
    wb_wide.columns.name = None
    annual = annual.merge(wb_wide, on="year", how="left")
    return annual.round(3)


# ==========================================================================
# 5. NEWS (text cleaning + keyword tagging = text mining simples)
# ==========================================================================
def clean_news(news):
    n = news.copy()
    n["title"] = n["title"].fillna("").astype(str).str.strip()
    n["summary"] = (n["summary"].fillna("").astype(str)
                    .str.replace(r"<[^>]+>", " ", regex=True)       # hasai tag HTML
                    .str.replace(r"\s+", " ", regex=True).str.strip())
    n["published"] = pd.to_datetime(n["published"], errors="coerce", utc=True).dt.tz_localize(None)
    n = n.drop_duplicates(subset=["title"]).reset_index(drop=True)

    text = (n["title"] + " " + n["summary"]).str.lower()
    for topic, words in config.NEWS_KEYWORDS.items():
        n[f"topic_{topic}"] = text.apply(lambda t, ws=words: int(any(w in t for w in ws)))
    topic_cols = [c for c in n.columns if c.startswith("topic_")]
    n["topics"] = n[topic_cols].apply(
        lambda r: ", ".join(c.replace("topic_", "") for c in topic_cols if r[c] == 1) or "other", axis=1)
    # Municípiu ne'ebé temi iha notísia
    n["municipalities_mentioned"] = text.apply(
        lambda t: ", ".join(m for m in config.MUNICIPALITIES if normalize_name(m) in normalize_name(t)))
    return n.sort_values("published", ascending=False)


def clean_municipality_info(raw):
    """Buka kolun naran + populasaun husi tabela scraping (estrutura bele muda)."""
    df = raw.copy()
    name_col = next((c for c in df.columns if re.search(r"municipal|name", c, re.I)), df.columns[0])
    pop_col = next((c for c in df.columns if re.search(r"population", c, re.I)), None)
    if pop_col is None:
        return sample_data.generate_municipality_info()
    out = pd.DataFrame({
        "key": df[name_col].map(normalize_name),
        "population": pd.to_numeric(df[pop_col].astype(str).str.replace(r"[^\d]", "", regex=True),
                                    errors="coerce"),
    })
    lookup = {normalize_name(m): m for m in config.MUNICIPALITIES}
    lookup.update({"covalima": "Covalima", "oecussi": "Oecusse", "oecusseambeno": "Oecusse"})
    out["municipality"] = out["key"].map(lambda k: next((v for kk, v in lookup.items() if kk in k), None))
    out = out.dropna(subset=["municipality", "population"]).drop_duplicates("municipality")
    if len(out) < 5:   # scraping la di'ak -> uza demo
        return sample_data.generate_municipality_info()
    return out[["municipality", "population"]]


# ==========================================================================
# MAIN
# ==========================================================================
def run():
    print("=" * 60)
    print("PREPROCESSING")
    print("=" * 60)
    report = {}
    raw = pd.read_csv(config.DATA_RAW / "weather_daily.csv")
    daily = add_features(clean_weather(raw, report))
    monthly = to_monthly(daily)

    wb = pd.read_csv(config.DATA_RAW / "worldbank_tls.csv")
    annual = to_annual_national(daily, wb)

    news = clean_news(pd.read_csv(config.DATA_RAW / "news_rss.csv"))
    muni = clean_municipality_info(pd.read_csv(config.DATA_RAW / "municipality_info.csv"))

    daily.to_csv(config.DATA_PROCESSED / "weather_daily_clean.csv", index=False)
    monthly.to_csv(config.DATA_PROCESSED / "weather_monthly.csv", index=False)
    annual.to_csv(config.DATA_PROCESSED / "annual_national.csv", index=False)
    news.to_csv(config.DATA_PROCESSED / "news_clean.csv", index=False)
    muni.to_csv(config.DATA_PROCESSED / "municipality_info_clean.csv", index=False)

    report.update({
        "daily_rows_clean": int(len(daily)),
        "monthly_rows": int(len(monthly)),
        "annual_rows": int(len(annual)),
        "annual_rows_with_yield": int(annual["cereal_yield_kg_ha"].notna().sum())
        if "cereal_yield_kg_ha" in annual else 0,
        "news_rows": int(len(news)),
    })
    (config.DATA_PROCESSED / "preprocessing_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
