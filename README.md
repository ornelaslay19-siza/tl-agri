# 🌾 Smart Agriculture Monitoring Dashboard for Timor-Leste

Capstone project — unidade kurikulár **Mining and Exploring**, Siencia Komputador, Dili Institute of Technology (DIT).

Dashboard interativu ne'ebé rekolla dadus **klima, produsaun, lokalizasaun no folin** ba **munisípiu 14 Timor-Leste** husi API, web scraping, open data no RSS; halo preprocessing no Exploratory Data Analysis; no aplika **Time Series Forecasting (SARIMA, Holt-Winters)** no **Regression (Linear, Ridge, Random Forest)** atu prevee udan, folin ai-han no produsaun.

**Fluxu:** Agriculture API → Historical Data → EDA → Modeling → Forecast Dashboard

---

## Konteúdu
1. [Problema no objetivu](#problema-no-objetivu)
2. [Fonte dadus](#fonte-dadus)
3. [Arkitetura](#arkitetura)
4. [Estrutura folder](#estrutura-folder)
5. [Instalasaun](#instalasaun)
6. [Oinsá hala'o](#oinsá-halao)
7. [Métodu no justifikasaun](#métodu-no-justifikasaun)
8. [Dashboard](#dashboard)
9. [Atualizasaun automátiku](#atualizasaun-automátiku)
10. [Deploy online](#deploy-online)
11. [Limitasaun](#limitasaun)
12. [Autór no lisensa](#autór-no-lisensa)

---

## Problema no objetivu
Dadus klima no agrikultura Timor-Leste fahe-malu iha fonte oioin, entaun difisil atu monitoriza kondisaun udan per munisípiu, antisipa risku maran/udan boot, no komprende relasaun klima ho produtividade ai-han.

**Objetivu jerál:** dezenvolve dashboard monitorizasaun agro-klima ne'ebé integra dadus online no aplika data mining (Time Series + Regression).

Detalle kompletu (problem statement, pergunta peskiza, objetivu espesífiku 7): [`reports/01_problem_statement_and_data_sources.md`](reports/01_problem_statement_and_data_sources.md)

## Fonte dadus
| Fonte | Tipu | Uza ba |
|---|---|---|
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) | API | Klima loron-loron (udan, temperatura, RH, ET0, radiasaun) — fonte prinsipál |
| [NASA POWER](https://power.larc.nasa.gov/) | API | Fonte alternativa / validasaun klima |
| [World Bank Open Data](https://data.worldbank.org/country/timor-leste) | Open data API | Produtividade serea, produsaun, área, indikadór agrikultura |
| [Wikipedia – Municipalities of East Timor](https://en.wikipedia.org/wiki/Municipalities_of_East_Timor) | Web scraping | Populasaun munisípiu |
| Google News RSS, [ReliefWeb](https://reliefweb.int/country/tls) RSS | RSS | Notísia agrikultura, maran, inundasaun (text mining) |
| [WFP Food Prices – Timor-Leste](https://data.humdata.org/dataset/wfp-food-prices-for-timor-leste) (HDX CKAN API) | API / Open data | **Folin** ai-han fulan-fulan per **merkadu** (lat/lon, munisípiu) |
| [FAOSTAT QCL](https://www.fao.org/faostat/en/#data/QCL) | API (ka CSV manuál) | **Produsaun**, área, produtividade: hare, batar, ai-farina, fehuk midar, kafé |
| World Bank CPI (`FP.CPI.TOTL`) | API | Inflasaun → folin real |
| Censo Agrícola 2019 / MAP | Manuál (template iha `data/templates/`) | Produsaun per **munisípiu** |

Fonte hotu **gratuitu** no **la presiza API key**.

## Arkitetura
```
 ┌──────────────── FONTE ────────────────┐
 │ Open-Meteo / NASA POWER  (API JSON)   │
 │ World Bank API           (Open data)  │
 │ Wikipedia                (Scraping)   │
 │ Google News / ReliefWeb  (RSS)        │
 └───────────────────┬───────────────────┘
                     ▼
     src/data_collection.py  ──►  data/raw/        (+ incremental cache, _metadata.json)
                     ▼
     src/preprocessing.py    ──►  data/processed/  (daily clean, monthly, annual)
                     ▼
     src/eda.py              ──►  reports/figures/ + data/outputs/eda_summary.json
                     ▼
     src/models.py           ──►  data/outputs/    (forecasts, metrics, models)
                     ▼
     ── PRODUSAUN / LOKALIZASAUN / FOLIN ──
     src/agri_collection.py    WFP/HDX, FAOSTAT, CPI   ──► data/raw/
     src/agri_preprocessing.py HXL, unidade, folin real ──► data/processed/
     src/agri_eda.py           trend, sazonalidade, mapa ──► reports/figures/agri_*
     src/agri_models.py        SARIMA, Holt-Winters, Ridge/RF, senáriu ──► data/outputs/
                     ▼
     dashboard/app.py  (router Streamlit, pájina 2)  ◄── utilizadór
        ├── produsaun_folin.py   Produsaun, lokalizasaun & folin
        └── klima.py             Klima & udan
```
`src/pipeline.py` hala'o etapa hotu ho komandu ida.

## Estrutura folder
```
tl-agri/
├── data/
│   ├── raw/                 # dadus orijinál husi API/web/RSS (+ _metadata.json)
│   ├── processed/           # dadus mos: weather_daily_clean, weather_monthly, annual_national, news_clean
│   ├── outputs/             # forecasts, price_forecasts, production_forecasts, metrics, *.joblib
│   └── templates/           # template CSV ba dadus manuál (produsaun munisípiu)
├── src/
│   ├── config.py            # konfigurasaun sentrál (munisípiu, URL, parámetru)
│   ├── data_collection.py   # PASSU 1: API, scraping, RSS
│   ├── preprocessing.py     # PASSU 2: cleaning, missing values, feature engineering
│   ├── eda.py               # PASSU 3: statistics, distribution, trend, correlation
│   ├── models.py            # PASSU 4-5: SARIMA, regression, evaluation
│   ├── sample_data.py       # dadus DEMO (offline fallback)
│   ├── agri_collection.py   # folin (WFP/HDX), produsaun (FAOSTAT), CPI, produsaun munisípiu
│   ├── agri_preprocessing.py
│   ├── agri_eda.py
│   ├── agri_models.py       # forecast folin + regression + senáriu produsaun
│   ├── agri_sample_data.py  # DEMO ba folin/produsaun
│   └── pipeline.py          # hala'o hotu
├── notebooks/
│   ├── 01_pipeline_walkthrough.ipynb
│   └── 02_production_location_price.ipynb
├── dashboard/
│   ├── app.py               # router (st.navigation)
│   ├── produsaun_folin.py   # pájina: produsaun, lokalizasaun & folin
│   ├── klima.py             # pájina: klima & udan
│   └── .streamlit/config.toml
├── reports/
│   ├── figures/             # gráfiku EDA (PNG) ba relatóriu/slide
│   ├── 01_problem_statement_and_data_sources.md
│   ├── 02_final_report_structure.md
│   ├── 03_presentation_outline_16_slides.md
│   ├── 04_youtube_video_script.md
│   └── 05_extension_production_location_price.md
├── requirements.txt
├── .gitignore
└── README.md
```

## Instalasaun
Presiza **Python 3.10+**.
```bash
git clone https://github.com/<username>/tl-agri-dashboard.git
cd tl-agri-dashboard

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

## Oinsá hala'o
Hala'o komandu hotu husi **folder root** projetu.

```bash
# 1) Pipeline kompletu ho dadus LIVE (presiza internet; dala uluk ±5-15 minutu)
python -m src.pipeline

# 1b) Se la iha internet: dadus DEMO sintétiku (ba teste deit)
python -m src.pipeline --demo

# 2) Loke dashboard
streamlit run dashboard/app.py
```
Hala'o passu ida-idak (atu esplika iha aprezentasaun):
```bash
python -m src.data_collection            # ka --source nasa
python -m src.preprocessing
python -m src.eda
python -m src.models
python -m src.agri_collection            # folin, produsaun, CPI
python -m src.agri_preprocessing
python -m src.agri_eda
python -m src.agri_models

# Parte ida deit:
python -m src.pipeline --only agri --skip-collect
```
Ka loke `notebooks/01_pipeline_walkthrough.ipynb` atu haree rezultadu passu-ba-passu.

> **Importante:** Se fonte ida la konsege asesu, kódigu uza dadus DEMO ba fonte ne'e no dashboard hatudu **DEMO DATA**. Molok grava vídeu ka submete relatóriu, asegura dashboard hatudu **LIVE DATA** no uza númeru husi run live.

## Métodu no justifikasaun
**1. SARIMA (Time Series)** — prevee udan no temperatura fulan-fulan, fulan 12 ba oin, ba kada munisípiu.
- Klima Timor-Leste iha sazonalidade monsaun 12 fulan → komponente sazonál SARIMA.
- Fó intervalu konfiansa 95% → importante ba komunika inserteza.
- Udan skewed no barak 0 → transformasaun `log1p`.
- Ordem modelu hili automátiku ho AIC husi grid ki'ik.

**2. Regression ho lag features (Ridge, Random Forest)** — modelu pooled ba munisípiu hotu ho lag 12/24/36, sin/cos fulan, lokalizasaun. Lag mínimu 12 → previzaun direta fulan 1–12.

**3. Regression produtividade serea** — Linear, Ridge, Random Forest prevee `cereal_yield_kg_ha` (World Bank) husi udan tempu udan, loron maran, temperatura, loron udan boot, tinan (trend). Koefisiente Ridge fasil atu interpreta.

**4. Folin — Time Series Forecasting** (per ai-han × merkadu, fulan 12): Naive, Seasonal naive, **Holt-Winters**, **SARIMA** iha log(folin). Modelu di'ak liu hili tuir RMSE hold-out.

**5. Folin — Regression** (fulan tuir mai): Ridge / Random Forest ho lag folin, sezaun, tempu hamlaha, anomalia udan.

**6. Produsaun** (anuál, per kultura): Holt damped + Ridge regression ho **senáriu klima** (Normál / El Niño / La Niña), 3 tinan ba oin.

Detalle: [`reports/05_extension_production_location_price.md`](reports/05_extension_production_location_price.md)

**Avaliasaun**
- Time series: hold-out **temporal** (fulan 12 ikus; la bele random split tanba sei "haree futuru").
- Baseline: *Seasonal naive* no *Climatology* — modelu tenke di'ak liu baseline atu iha valór.
- Produtividade: **Leave-One-Out CV** tanba n ki'ik.
- Metrics: MAE, RMSE, R², sMAPE (sMAPE di'ak liu MAPE bainhira udan = 0).

## Dashboard
Pájina 2: **Produsaun, lokalizasaun & folin** (default) no **Klima & udan**.

**Pájina Produsaun, lokalizasaun & folin:** KPI (folin ikus, mudansa 12 fulan, previzaun, merkadu baratu liu, produsaun), filtru (ai-han, merkadu, nominál/real, períodu, kultura), previzaun + alerta folin, mapa merkadu no produsaun munisípiu, trend no índise sazonál, produsaun ho senáriu, regression folin.

**Pájina Klima & udan:**

| Rekizitu | Implementasaun |
|---|---|
| KPI cards | Udan média, temperatura média, % loron maran, anomalia udan fulan ikus, produtividade serea |
| Trend chart | Tab *Trend*: fulan-fulan + média 12 fulan, total anuál + linha trend, klimatolojia |
| Comparison chart | Tab *Komparasaun*: bar munisípiu (foho vs tasi-ibun), mapa, heatmap munisípiu × fulan |
| Filter | Sidebar: zona, munisípiu, períodu, sezaun, variavel |
| Prediction / mining | Tab *Previzaun klima* (SARIMA + intervalu 95% + alerta + avaliasaun), tab *Produtividade serea* (regression + what-if) |
| Last-updated timestamp | Header (tempu Dili, UTC+9) husi `data/raw/_metadata.json` + badge LIVE/DEMO |
| Extra | Notísia RSS ho topiku, download CSV, butaun "Atualiza dadus agora" |

## Atualizasaun automátiku
Pipeline uza **incremental cache** (`data/raw/weather_open-meteo/`) — update tuir mai download loron foun deit.
```bash
# Linux/Mac cron: loron-loron 06:00
0 6 * * * cd /path/to/tl-agri && /path/to/.venv/bin/python -m src.pipeline >> pipeline.log 2>&1
```
Windows: Task Scheduler → Action: `python -m src.pipeline`, "Start in": folder projetu.

## Deploy online
**Streamlit Community Cloud** (gratuitu):
1. Hala'o `python -m src.pipeline` iha komputadór, depois commit `data/processed/` no `data/outputs/` (file boot iha `.gitignore`).
2. Push ba GitHub.
3. Iha [share.streamlit.io](https://share.streamlit.io) → *New app* → hili repo → main file: `dashboard/app.py`.
4. (Opsionál) GitHub Actions ho `schedule: cron` atu hala'o pipeline no commit dadus foun loron-loron.

## Limitasaun
- Dadus klima husi reanalysis/satélite (rezolusaun ~10–50 km), la'ós estasaun lokál.
- Produtividade iha nível nasionál no anuál deit (n ki'ik) → rezultadu regression tenke interpreta ho kuidadu.
- Previzaun udan fulan-fulan iha inserteza boot; dashboard la substitui previzaun ofisiál husi autoridade meteorolojia nasionál.

## Autór no lisensa
- **Naran:** ___________ · **NIM:** ___________ · **Orientadór:** ___________
- Kódigu: MIT License. Dadus: tuir lisensa fonte ida-idak (Open-Meteo CC BY 4.0, World Bank CC BY 4.0, Wikipedia CC BY-SA).
- Vídeu demo: https://youtube.com/___ · Dashboard: https://___.streamlit.app
