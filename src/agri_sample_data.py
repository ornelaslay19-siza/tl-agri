"""
agri_sample_data.py
===================
Dadus DEMO (sintétiku) ba PRODUSAUN, LOKALIZASAUN no FOLIN.
Uza deit bainhira API la bele asesu. Formatu kolun HANESAN ho fonte loos
(WFP/HDX no FAOSTAT) atu preprocessing la muda.

Padraun ne'ebé simula:
  * Folin ai-han lokál (batar, hare lokál, fehuk) sa'e iha tempu hamlaha
    (Nov-Fev) no tun depois kolleita (Abr-Jul).
  * Tinan El Niño -> produsaun tun, folin tinan tuir mai sa'e.
  * Merkadu iha foho/área izoladu folin as liu uitoan (kustu transporte).
  * Foos importadu estável liu (depende ba merkadu internasionál).
"""
import numpy as np
import pandas as pd

from . import config
from .sample_data import EL_NINO_YEARS, LA_NINA_YEARS

# Merkadu (admin1 = munisípiu) - lokalizasaun aproximadu
MARKETS = {
    "Dili (Becora)": "Dili", "Dili (Taibessi)": "Dili", "Baucau": "Baucau", "Maliana": "Bobonaro",
    "Suai": "Covalima", "Viqueque": "Viqueque", "Los Palos": "Lautem", "Gleno": "Ermera",
    "Same": "Manufahi", "Aileu": "Aileu", "Ainaro": "Ainaro", "Pante Macassar": "Oecusse",
}
# commodity: (kategoria, unidade, folin base USD, forsa sazonalidade, lokál?)
COMMODITIES = {
    "Rice (imported)": ("cereals and tubers", "KG", 0.62, 0.02, False),
    "Rice (local)":    ("cereals and tubers", "KG", 0.80, 0.08, True),
    "Maize (white)":   ("cereals and tubers", "KG", 0.55, 0.20, True),
    "Cassava":         ("cereals and tubers", "KG", 0.45, 0.15, True),
    "Beans (red)":     ("pulses and nuts", "KG", 1.60, 0.10, True),
    "Oil (vegetable)": ("oil and fats", "L", 2.10, 0.02, False),
    "Sugar":           ("miscellaneous food", "KG", 1.00, 0.02, False),
    "Eggs":            ("meat, fish and eggs", "30 pcs", 4.50, 0.03, False),
}


def _enso(y):
    return EL_NINO_YEARS.get(y, LA_NINA_YEARS.get(y, 1.0))


def generate_wfp_prices(start="2008-04-01", end=None, seed=config.RANDOM_STATE):
    """Formatu hanesan CSV WFP iha HDX (inklui liña HXL ba teste cleaning)."""
    rng = np.random.default_rng(seed)
    end = end or (pd.Timestamp.today() - pd.DateOffset(months=2)).strftime("%Y-%m-01")
    dates = pd.date_range(start, end, freq="MS") + pd.Timedelta(days=14)   # WFP uza loron 15
    rows = []
    for mk, muni in MARKETS.items():
        info = config.MUNICIPALITIES[muni]
        remote = 1.0 + (0.08 if info["zone"] == "highland" else 0) + (0.06 if muni in ("Oecusse", "Lautem") else 0)
        start_idx = rng.integers(0, 40)       # merkadu balun komesa reporta tarde
        for com, (cat, unit, base, seas, local) in COMMODITIES.items():
            level = np.log(base * remote)
            ar = 0.0
            for i, d in enumerate(dates):
                if i < start_idx:
                    continue
                t = (d.year - 2008) + d.month / 12
                infl = 0.025 * t                                  # inflasaun ~2.5%/tinan
                # Sazonalidade: pico iha Janeiru (tempu hamlaha)
                s = seas * np.cos(2 * np.pi * (d.month - 1) / 12) if local else 0
                # Tinan maran uluk -> folin lokál sa'e
                shock = (0.25 * (1 - _enso(d.year - (1 if d.month < 6 else 0)))) if local else 0
                shock = max(shock, -0.1)
                if d.year in (2008,) or (d.year == 2022):        # krize folin global
                    shock += 0.12
                ar = 0.7 * ar + rng.normal(0, 0.04)
                price = np.exp(level + infl + s + shock + ar)
                if rng.random() < 0.08:                            # dadus falta (gap)
                    continue
                rows.append({
                    "date": d.date().isoformat(), "admin1": muni, "admin2": muni, "market": mk,
                    "latitude": info["lat"] + rng.normal(0, 0.01), "longitude": info["lon"] + rng.normal(0, 0.01),
                    "category": cat, "commodity": com, "unit": unit, "priceflag": "actual",
                    "pricetype": "Retail", "currency": "USD", "price": round(price, 2), "usdprice": round(price, 2),
                })
    df = pd.DataFrame(rows)
    hxl = {c: f"#{c}" for c in df.columns}                   # liña HXL (hanesan HDX)
    return pd.concat([pd.DataFrame([hxl]), df], ignore_index=True)


def generate_faostat(seed=config.RANDOM_STATE):
    """Produsaun nasionál anuál per kultura (formatu long hanesan FAOSTAT)."""
    rng = np.random.default_rng(seed + 1)
    base = {"Rice": (60000, 2.9), "Maize": (130000, 1.4), "Cassava": (20000, 5.5),
            "Sweet potatoes": (8000, 4.0), "Coffee": (55000, 0.18)}   # (area ha, t/ha)
    rows = []
    for crop, (area0, y0) in base.items():
        sens = 0.2 if crop == "Coffee" else (0.9 if crop in ("Maize", "Rice") else 0.5)
        for y in range(1995, pd.Timestamp.today().year - 1):
            enso = min(_enso(y), 1.2)
            area = area0 * (1 + 0.004 * (y - 1995)) * (1 + 0.3 * (enso - 1)) * rng.normal(1, 0.05)
            yld = y0 * (1 + 0.01 * (y - 1995)) * (1 + sens * (enso - 1)) * rng.normal(1, 0.06)
            for el, val in [("area_harvested_ha", area), ("yield_kg_ha", yld * 1000), ("production_t", area * yld)]:
                rows.append({"crop": crop, "year": y, "element": el, "value": round(float(val), 1)})
    return pd.DataFrame(rows)


def generate_municipal_production(seed=config.RANDOM_STATE):
    """Produsaun per munisípiu (estilu Censo Agrícola 2019), tinan 2019."""
    rng = np.random.default_rng(seed + 2)
    share = {  # parte aproximadu produsaun nasionál per kultura (DEMO)
        "Rice": {"Bobonaro": .22, "Baucau": .18, "Viqueque": .16, "Covalima": .10, "Manatuto": .10,
                 "Lautem": .08, "Oecusse": .08, "Manufahi": .04, "Ermera": .02, "Liquica": .02},
        "Maize": {"Baucau": .12, "Viqueque": .11, "Covalima": .10, "Bobonaro": .10, "Lautem": .09,
                  "Ermera": .08, "Manufahi": .08, "Ainaro": .07, "Oecusse": .07, "Liquica": .06,
                  "Aileu": .05, "Manatuto": .04, "Dili": .02, "Atauro": .01},
        "Coffee": {"Ermera": .55, "Ainaro": .12, "Liquica": .10, "Manufahi": .08, "Aileu": .07,
                   "Bobonaro": .05, "Dili": .03},
    }
    national = {"Rice": 150000, "Maize": 160000, "Coffee": 10000}
    rows = []
    for crop, sh in share.items():
        for muni, s in sh.items():
            prod = national[crop] * s * rng.normal(1, 0.05)
            rows.append({"municipality": muni, "crop": crop, "year": 2019,
                         "production_t": round(prod), "area_ha": round(prod / {"Rice": 2.8, "Maize": 1.3, "Coffee": 0.2}[crop])})
    return pd.DataFrame(rows)


def generate_cpi():
    years = np.arange(2000, pd.Timestamp.today().year)
    return pd.DataFrame({"year": years, "cpi": np.round(100 * 1.035 ** (years - 2010), 2)})
