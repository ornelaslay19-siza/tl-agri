"""
sample_data.py
==============
Jera dadus SINTÉTIKU (demo) ne'ebé hanesan padraun klima Timor-Leste.

TANBA SÁ?  Bainhira internet la iha (ka API tun), estudante sei bele hala'o
pipeline no dashboard tomak. Dadus ne'e LA'OS dadus loos - uza deit ba
teste / demo. Dashboard sei hatudu "DEMO DATA" bainhira dadus ne'e mak uza.

Padraun ne'ebé simula:
  * Monsaun: udan barak Dezembru-Abríl, maran Maiu-Novembru
  * Foho (highland) malirin liu ~5-6 °C duké tasi-ibun (lowland)
  * Tinan El Niño (ex. 1997, 2015, 2023) maran liu
"""
import numpy as np
import pandas as pd

from . import config

# Tinan El Niño/La Niña prinsipál (aproximadu) atu halo dadus demo realístiku
EL_NINO_YEARS = {1997: 0.55, 2002: 0.8, 2006: 0.8, 2009: 0.8, 2015: 0.55, 2019: 0.8, 2023: 0.65}
LA_NINA_YEARS = {1998: 1.3, 2000: 1.15, 2010: 1.35, 2011: 1.2, 2021: 1.25, 2022: 1.2}

# Média udan fulan-fulan (mm) ba tasi-ibun norte (hanesan Dili) - forma monsaun
_BASE_MONTHLY_RAIN = np.array([150, 140, 130, 90, 60, 25, 15, 8, 10, 20, 60, 130])


def generate_weather_daily(start=config.START_DATE, end=config.END_DATE, seed=config.RANDOM_STATE):
    """Jera dadus klima loron-loron ba munisípiu hotu."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    frames = []
    for i, (name, info) in enumerate(config.MUNICIPALITIES.items()):
        highland = info["zone"] == "highland"
        # Sul (latitude < -8.9) no foho simu udan barak liu
        rain_factor = (1.8 if highland else 1.0) * (1.4 if info["lat"] < -8.9 else 1.0)
        base_temp = 21.0 if highland else 27.0

        doy = dates.dayofyear.values
        month_idx = dates.month.values - 1
        year = dates.year.values

        # --- Temperatura: sazonalidade + trend aquesimentu global (~0.02 °C/tinan)
        t_mean = (base_temp + 1.2 * np.sin(2 * np.pi * (doy - 300) / 365)
                  + 0.02 * (year - 1995) + rng.normal(0, 0.7, len(dates)))
        t_range = (9 if highland else 7) + rng.normal(0, 1.0, len(dates))
        t_max, t_min = t_mean + t_range / 2, t_mean - t_range / 2

        # --- Udan: probabilidade loron udan + kuantidade (distribuisaun gamma)
        enso = np.array([EL_NINO_YEARS.get(y, LA_NINA_YEARS.get(y, 1.0)) for y in year])
        expected_month = _BASE_MONTHLY_RAIN[month_idx] * rain_factor * enso
        p_rain = np.clip(expected_month / 250, 0.05, 0.85)
        is_rain = rng.random(len(dates)) < p_rain
        # média gamma = shape * scale  ->  scale = (média loron udan) / shape
        mean_wet_day = (expected_month / 30) / p_rain
        amount = rng.gamma(shape=0.8, scale=mean_wet_day / 0.8, size=len(dates))
        precip = np.where(is_rain, amount, 0.0).round(1)

        rh = np.clip(65 + 20 * (precip > 0) + rng.normal(0, 6, len(dates)) + (8 if highland else 0), 30, 100)
        et0 = np.clip(3.2 + 0.12 * (t_mean - base_temp) + 1.0 * np.sin(2 * np.pi * (doy - 280) / 365)
                      - 0.8 * (precip > 5) + rng.normal(0, 0.4, len(dates)), 0.5, 8)
        rad = np.clip(20 + 4 * np.sin(2 * np.pi * (doy - 280) / 365) - 5 * (precip > 5)
                      + rng.normal(0, 2, len(dates)), 3, 32)

        df = pd.DataFrame({
            "date": dates, "municipality": name,
            "temperature_2m_max": t_max.round(1), "temperature_2m_min": t_min.round(1),
            "temperature_2m_mean": t_mean.round(1), "precipitation_sum": precip,
            "relative_humidity_2m_mean": rh.round(0), "et0_fao_evapotranspiration": et0.round(2),
            "shortwave_radiation_sum": rad.round(2),
        })
        # Hatama missing values ~1% (atu estudante bele pratika cleaning)
        for col in ["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean"]:
            df.loc[rng.random(len(df)) < 0.01, col] = np.nan
        # Hatama valór sala ruma (outlier / erru sensor)
        bad = rng.choice(len(df), 5, replace=False)
        df.loc[bad, "temperature_2m_max"] = 99.9
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def generate_world_bank(seed=config.RANDOM_STATE):
    """Jera indikadór agríkola anuál (format hanesan World Bank API)."""
    rng = np.random.default_rng(seed)
    years = np.arange(1995, 2024)
    rows = []
    for y in years:
        enso = EL_NINO_YEARS.get(y, LA_NINA_YEARS.get(y, 1.0))
        # El Niño -> produtividade tun; trend tékniku sa'e neineik
        yield_kgha = 1400 + 25 * (y - 1995) + 900 * (min(enso, 1.2) - 1.0) + rng.normal(0, 120)
        area = 90000 + rng.normal(0, 8000)
        vals = {
            "cereal_yield_kg_ha": yield_kgha,
            "cereal_land_ha": area,
            "cereal_production_t": yield_kgha * area / 1000,
            "crop_production_index": 70 + 1.2 * (y - 1995) + 25 * (min(enso, 1.2) - 1) + rng.normal(0, 4),
            "agri_employment_pct": 70 - 0.9 * (y - 1995) + rng.normal(0, 1),
            "agri_land_pct": 25 + rng.normal(0, 0.5),
        }
        for k, v in vals.items():
            rows.append({"year": y, "indicator": k, "value": round(float(v), 2)})
    return pd.DataFrame(rows)


def generate_news():
    """Notísia ezemplu (DEMO) atu tabela RSS iha dashboard la mamuk."""
    today = pd.Timestamp.today().normalize()
    samples = [
        ("Farmers in Baucau prepare rice fields as wet season begins", "demo"),
        ("El Nino outlook raises drought concerns for Timor-Leste maize harvest", "demo"),
        ("Heavy rain triggers landslides and floods in Dili and Ermera", "demo"),
        ("Coffee harvest in Ermera expected to improve this year", "demo"),
        ("Food security assessment highlights risks in Oecusse and Lautem", "demo"),
        ("Fall armyworm detected in maize fields, ministry warns farmers", "demo"),
    ]
    return pd.DataFrame({
        "title": [s[0] for s in samples],
        "link": ["https://example.org/demo"] * len(samples),
        "published": [today - pd.Timedelta(days=3 * i) for i in range(len(samples))],
        "summary": [s[0] for s in samples],
        "feed": [s[1] for s in samples],
    })


def generate_municipality_info():
    """Informasaun munisípiu (populasaun aproximadu, DEMO) - substitui scraping."""
    pops = {"Dili": 324000, "Aileu": 55000, "Ainaro": 72000, "Atauro": 10000, "Baucau": 133000,
            "Bobonaro": 106000, "Covalima": 73000, "Ermera": 138000, "Lautem": 69000,
            "Liquica": 83000, "Manatuto": 50000, "Manufahi": 60000, "Oecusse": 80000, "Viqueque": 80000}
    return pd.DataFrame({"municipality": list(pops), "population": list(pops.values())})
