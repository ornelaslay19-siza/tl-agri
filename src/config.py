"""
config.py
=========
Konfigurasaun sentrál ba projetu tomak (Central configuration for the whole project).

Se ita hakarak muda munisípiu, períodu dadus, ka fonte dadus, muda iha ne'e deit.
All other modules import from here, so there is ONE place to change settings.
"""
from datetime import date, timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# 1. PATHS (Dalan ba folder sira)
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]          # project root folder
DATA_RAW = ROOT / "data" / "raw"                     # dadus orijinál husi API/web
DATA_PROCESSED = ROOT / "data" / "processed"         # dadus ne'ebé mos ona
DATA_OUTPUTS = ROOT / "data" / "outputs"             # rezultadu modelu (forecast, metrics)
FIG_DIR = ROOT / "reports" / "figures"               # gráfiku EDA ba relatóriu

for _p in (DATA_RAW, DATA_PROCESSED, DATA_OUTPUTS, FIG_DIR):
    _p.mkdir(parents=True, exist_ok=True)

METADATA_FILE = DATA_RAW / "_metadata.json"          # rai "last updated" + fonte dadus

# --------------------------------------------------------------------------
# 2. MUNISÍPIU TIMOR-LESTE (koordenada aproximadu husi sidade kapitál munisípiu)
#    zone: lowland (tasi-ibun / planísie) ka highland (foho)
#    main_crop: produtu agríkola prinsipál (atu uza iha dashboard)
# --------------------------------------------------------------------------
MUNICIPALITIES = {
    "Dili":      {"lat": -8.556, "lon": 125.578, "zone": "lowland",  "main_crop": "Vegetables"},
    "Aileu":     {"lat": -8.728, "lon": 125.567, "zone": "highland", "main_crop": "Vegetables/Maize"},
    "Ainaro":    {"lat": -8.992, "lon": 125.508, "zone": "highland", "main_crop": "Coffee/Maize"},
    "Atauro":    {"lat": -8.230, "lon": 125.580, "zone": "lowland",  "main_crop": "Maize/Cassava"},
    "Baucau":    {"lat": -8.466, "lon": 126.450, "zone": "lowland",  "main_crop": "Rice/Maize"},
    "Bobonaro":  {"lat": -8.991, "lon": 125.220, "zone": "lowland",  "main_crop": "Rice"},
    "Covalima":  {"lat": -9.313, "lon": 125.256, "zone": "lowland",  "main_crop": "Rice/Maize"},
    "Ermera":    {"lat": -8.723, "lon": 125.437, "zone": "highland", "main_crop": "Coffee"},
    "Lautem":    {"lat": -8.520, "lon": 127.000, "zone": "lowland",  "main_crop": "Rice/Maize"},
    "Liquica":   {"lat": -8.587, "lon": 125.341, "zone": "lowland",  "main_crop": "Maize"},
    "Manatuto":  {"lat": -8.512, "lon": 126.013, "zone": "lowland",  "main_crop": "Rice"},
    "Manufahi":  {"lat": -9.000, "lon": 125.650, "zone": "highland", "main_crop": "Maize/Coffee"},
    "Oecusse":   {"lat": -9.200, "lon": 124.380, "zone": "lowland",  "main_crop": "Rice/Maize"},
    "Viqueque":  {"lat": -8.858, "lon": 126.364, "zone": "lowland",  "main_crop": "Rice"},
}

# --------------------------------------------------------------------------
# 3. PERÍODU DADUS
#    Open-Meteo archive iha atraso ~5 loron, entaun ita hasai to'o loron 7 liu ba.
# --------------------------------------------------------------------------
START_DATE = "1995-01-01"
END_DATE = (date.today() - timedelta(days=7)).isoformat()

# --------------------------------------------------------------------------
# 4. FONTE DADUS (Data sources)
# --------------------------------------------------------------------------
# 4a. Open-Meteo Historical Weather API (gratuitu, la presiza API key)
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "et0_fao_evapotranspiration",   # evapotranspirasaun referénsia (FAO-56)
    "shortwave_radiation_sum",
]

# 4b. NASA POWER (fonte alternativa / validasaun) - komunidade "AG" = Agroclimatology
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"]

# 4c. World Bank Open Data API (indikadór agrikultura Timor-Leste, kódigu nasaun = TLS)
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/TLS/indicator/{indicator}"
WORLD_BANK_INDICATORS = {
    "AG.YLD.CREL.KG": "cereal_yield_kg_ha",        # Produtividade serea (kg/ha)
    "AG.PRD.CREL.MT": "cereal_production_t",       # Produsaun serea (tonelada)
    "AG.LND.CREL.HA": "cereal_land_ha",            # Área serea (ha)
    "AG.PRD.CROP.XD": "crop_production_index",     # Crop production index (2014-2016=100)
    "SL.AGR.EMPL.ZS": "agri_employment_pct",       # % empregu iha agrikultura
    "AG.LND.AGRI.ZS": "agri_land_pct",             # % rai agríkola
}

# 4d. FAOSTAT (download manuál; haree README) - opsionál
FAOSTAT_MANUAL_FILE = DATA_RAW / "faostat_tls_crops.csv"

# 4e. Web scraping: tabela munisípiu husi Wikipedia (populasaun, área)
WIKI_MUNICIPALITIES_URL = "https://en.wikipedia.org/wiki/Municipalities_of_East_Timor"

# 4f. RSS feeds (notísia agrikultura / klima / dezastre ba Timor-Leste)
RSS_FEEDS = {
    "google_news_agri": "https://news.google.com/rss/search?q=Timor-Leste+agriculture&hl=en-US&gl=US&ceid=US:en",
    "google_news_climate": "https://news.google.com/rss/search?q=Timor-Leste+(drought+OR+flood+OR+rainfall+OR+%22El+Nino%22)&hl=en-US&gl=US&ceid=US:en",
    "reliefweb_tls": "https://reliefweb.int/country/tls/rss.xml",
}

# Liafuan-xave (keywords) atu klasifika notísia (text mining simples)
NEWS_KEYWORDS = {
    "drought": ["drought", "dry spell", "el nino", "el niño", "water shortage", "bailoron"],
    "flood":   ["flood", "landslide", "heavy rain", "la nina", "la niña", "inundasaun"],
    "food_security": ["food security", "hunger", "malnutrition", "food insecurity", "ipc"],
    "crops":   ["rice", "maize", "corn", "coffee", "harvest", "crop", "hare", "batar"],
    "pests":   ["locust", "pest", "fall armyworm", "disease", "african swine fever"],
}

HTTP_HEADERS = {"User-Agent": "TL-Agri-Dashboard/1.0 (student capstone project; educational use)"}
REQUEST_TIMEOUT = 60  # segundu

# --------------------------------------------------------------------------
# 5. SEZAUN AGRÍKOLA TIMOR-LESTE
#    Tempu udan (wet season / monsoon): Dezembru - Abríl
#    Tempu bailoron (dry season): Maiu - Novembru
# --------------------------------------------------------------------------
WET_SEASON_MONTHS = [12, 1, 2, 3, 4]

# --------------------------------------------------------------------------
# 6. PARÁMETRU MODELU
# --------------------------------------------------------------------------
FORECAST_HORIZON = 12        # fulan hira ba oin atu prevee
TEST_MONTHS = 12             # fulan ikus hira uza ba teste (hold-out) = horizon, atu justu
RANDOM_STATE = 42
GDD_BASE_TEMP = 10.0         # base temperature ba Growing Degree Days (batar/maize)
DRY_DAY_THRESHOLD_MM = 1.0   # udan < 1 mm = "loron maran"

# ==========================================================================
# 7. PRODUSAUN, LOKALIZASAUN NO FOLIN (extension)
# ==========================================================================
# 7a. WFP Food Prices via HDX (Humanitarian Data Exchange) CKAN API.
#     Ita husu metadata dataset -> buka resource CSV -> download.
#     Dataset: https://data.humdata.org/dataset/wfp-food-prices-for-timor-leste
HDX_PACKAGE_API = "https://data.humdata.org/api/3/action/package_show"
HDX_WFP_DATASET_ID = "wfp-food-prices-for-timor-leste"
WFP_MANUAL_FILE = DATA_RAW / "wfp_food_prices_tls_manual.csv"   # se API la funsiona

# 7b. FAOSTAT API - Produsaun ai-han (domain QCL). Timor-Leste area code = 176.
#     Nota: API uza "filter code" ba element (2312/2413/2510), la'ós display code (5312/5412/5510).
#     Se API presiza token, hatama iha environment variable FAOSTAT_TOKEN.
FAOSTAT_API = "https://faostatservices.fao.org/api/v1/en/data/QCL"
FAOSTAT_AREA_TLS = "176"
FAOSTAT_ITEMS = {"27": "Rice", "56": "Maize", "125": "Cassava", "122": "Sweet potatoes", "656": "Coffee"}
FAOSTAT_ELEMENTS = {"2312": "area_harvested_ha", "2413": "yield_kg_ha", "2510": "production_t"}

# 7c. Produsaun per munisípiu (Censo Agrícola 2019 / MAP) - input manuál
#     Format: municipality, crop, year, production_t, area_ha
MUNICIPAL_PRODUCTION_FILE = DATA_RAW / "municipal_production_manual.csv"

# 7d. Inflasaun (World Bank CPI) atu kalkula folin REAL (hasai efeitu inflasaun)
WB_CPI_INDICATOR = "FP.CPI.TOTL"      # Consumer price index (2010 = 100)

PRICE_FORECAST_HORIZON = 12            # fulan
PRICE_TEST_MONTHS = 12
PRODUCTION_FORECAST_YEARS = 3
MIN_PRICE_OBS = 36                     # mínimu fulan observasaun atu modela série ida
# Tempu "hamlaha" (lean season): folin ai-han lokál sa'e molok kolleita
LEAN_SEASON_MONTHS = [11, 12, 1, 2]
