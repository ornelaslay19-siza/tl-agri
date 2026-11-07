# Extension: Produsaun, Lokalizasaun no Folin
**Métodu:** Regression + Time Series Forecasting
**Fluxu:** Agriculture API → Historical Data → EDA → Modeling → Forecast Dashboard

```
┌──────────── AGRICULTURE API ────────────┐
│ WFP Food Prices (HDX CKAN API)          │ folin + lokalizasaun merkadu (lat/lon, munisípiu)
│ FAOSTAT QCL API                         │ produsaun, área, produtividade per kultura
│ World Bank API (CPI)                    │ inflasaun -> folin real
│ Open-Meteo (husi parte klima)           │ udan, anomalia, klima anuál
│ Manuál: Censo Agrícola 2019 / MAP       │ produsaun per munisípiu
└───────────────────┬─────────────────────┘
                    ▼  src/agri_collection.py
        HISTORICAL DATA  data/raw/  (2008–ohin folin; 1995–ohin produsaun)
                    ▼  src/agri_preprocessing.py
        prices_market_monthly · prices_national_monthly · markets · production_annual · municipal_production
                    ▼  src/agri_eda.py
        EDA: trend, sazonalidade, lokalizasaun, volatilidade, korrelasaun  -> reports/figures/agri_*.png
                    ▼  src/agri_models.py
        MODELING: SARIMA / Holt-Winters (folin) · Ridge / Random Forest (folin 1-step)
                  Holt / Ridge + senáriu klima (produsaun)
                    ▼
        FORECAST DASHBOARD  dashboard/produsaun_folin.py
```

---

## 1. Problem statement (atualiza)

> Folin ai-han iha Timor-Leste muda tuir sezaun (sa'e iha tempu hamlaha Nov–Fev), tuir lokalizasaun (merkadu izoladu karun liu), no tuir produsaun ne'ebé depende ba udan. Dadus folin merkadu (WFP), produsaun (FAOSTAT/MAP) no klima iha fonte la hanesan no seidauk integra. Tanba ne'e, difisil ba governu, ONG no komunidade atu **antisipa folin sa'e** no **identifika munisípiu/merkadu ne'ebé vulneravel**. Projetu ne'e integra dadus hirak ne'e no uza Time Series Forecasting no Regression atu prevee folin no produsaun.

**Pergunta peskiza foun:**
- RQ5. Oinsá trend, sazonalidade no volatilidade folin ai-han prinsipál iha merkadu Timor-Leste?
- RQ6. Merkadu/munisípiu ne'ebé mak folin as liu, no munisípiu ne'ebé mak produz liu?
- RQ7. Modelu time series saida (SARIMA, Holt-Winters) mak prevee folin fulan 12 ba oin ho di'ak liu kompara ho baseline?
- RQ8. Fatór saida (folin kotuk, sezaun, udan) mak esplika mudansa folin, no oinsá senáriu klima (El Niño/La Niña) afeta produsaun?

## 2. Objetivu espesífiku foun
8. Rekolla dadus folin merkadu ho lokalizasaun (WFP/HDX), produsaun per kultura (FAOSTAT) no CPI (World Bank) liuhusi API.
9. Prepara dadus: hasai liña HXL, standardiza unidade, trata duplikadu/outlier, kalkula folin real, agrega ba série nasionál no per merkadu.
10. Halo EDA ba trend, índise sazonál, komparasaun merkadu (foho vs tasi-ibun), volatilidade no korrelasaun udan–produsaun–folin.
11. Prevee folin fulan 12 ba oin per ai-han no per merkadu ho SARIMA no Holt-Winters; kompara ho Naive no Seasonal naive.
12. Aplika regression (Ridge, Random Forest) ba folin fulan tuir mai no ba produsaun ho senáriu klima.
13. Integra rezultadu iha pájina dashboard "Produsaun, lokalizasaun & folin" ho mapa, alerta folin no previzaun.

---

## 3. Fonte dadus no oinsá asesu

| Fonte | Asesu | Dadus | Nota |
|---|---|---|---|
| **WFP Food Prices – Timor-Leste** (HDX) | CKAN API: `https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-timor-leste` → hetan URL CSV → download | Folin retail fulan-fulan per merkadu: `date, admin1, market, latitude, longitude, category, commodity, unit, pricetype, price, usdprice` | Lisensa CC BY-IGO. Liña 2 CSV mak **tag HXL** (`#date`, `#adm1+name`) → tenke hasai. |
| **FAOSTAT QCL** | `https://faostatservices.fao.org/api/v1/en/data/QCL?area=176&item=27,56,125,122,656&element=2312,2413,2510` | Área kolleita, produtividade, produsaun: hare, batar, ai-farina, fehuk midar, kafé | Timor-Leste = área 176. API uza *filter code* (2312/2413/2510), la'ós display code (5312/5412/5510). Se API la funsiona → download manuál CSV → `data/raw/faostat_tls_crops.csv`. |
| **World Bank CPI** | `https://api.worldbank.org/v2/country/TLS/indicator/FP.CPI.TOTL?format=json` | Índise folin konsumidór anuál | Ba folin real. |
| **Censo Agrícola 2019 / MAP** | Manuál (PDF/Excel) → prenxe `data/templates/municipal_production_manual_TEMPLATE.csv` → rai hanesan `data/raw/municipal_production_manual.csv` | Produsaun per munisípiu | Dimensaun lokalizasaun ba produsaun. |
| **Open-Meteo** (parte klima) | Haree `01_problem_statement_and_data_sources.md` | Anomalia udan, udan tempu udan, loron maran | Feature ba regression. |

Hotu iha **fallback**: se API falla → file manuál → dadus DEMO (dashboard hatudu "DEMO DATA").

---

## 4. Preprocessing (`src/agri_preprocessing.py`)

| Problema | Solusaun |
|---|---|
| Liña HXL iha CSV HDX | Hasai liña ne'ebé `date` hahú ho `#` |
| Tipu folin oioin (Retail/Wholesale) | Filtru `pricetype == "Retail"` |
| Unidade la hanesan ("KG", "50 KG", "30 pcs") | Fahe folin ho númeru iha unidade → folin per 1 unidade |
| Duplikadu (merkadu+ai-han+fulan) | Média |
| Outlier (erru hatama dadus) | Hasai folin > 3× ka < ⅓ husi mediana série |
| Naran munisípiu la konsistente ("Lautém", "Oecussi") | Normaliza ba naran standard |
| Inflasaun | `real_price = price / CPI × CPI_tinan_ikus` |
| Merkadu la reporta fulan hotu | Série nasionál = **mediana** merkadu; gap ≤ 3 fulan interpola iha modelu |
| Feature | tempu hamlaha, anomalia udan 6 fulan, mudansa produsaun % |

---

## 5. EDA (`src/agri_eda.py`)
1. Trend folin nominál vs real + Mann-Kendall
2. **Índise sazonál** (folin / média 13 fulan) → fulan pico no amplitude
3. **Lokalizasaun**: folin per merkadu, rasiu foho vs tasi-ibun, "gap" merkadu karun vs baratu
4. **Volatilidade**: desviu padraun mudansa fulan-fulan (%)
5. Trend produsaun, área, produtividade per kultura
6. Korrelasaun udan tempu udan ↔ produsaun ↔ folin real
7. Kontribuisaun munisípiu ba produsaun nasionál

---

## 6. Modeling no justifikasaun (`src/agri_models.py`)

### A. Time Series Forecasting — folin (fulan 12 ba oin)
| Modelu | Ideia | Tanba sá |
|---|---|---|
| Naive | Folin futuru = folin ikus | Baseline mínimu |
| Seasonal naive | Folin = fulan hanesan tinan kotuk | Baseline sazonál |
| **Holt-Winters (ETS)** | Nível + trend (damped) + sazonalidade | Folin iha trend inflasaun no sazonalidade hamlaha; damped evita trend la realístiku |
| **SARIMA** | ARIMA + komponente sazonál, iha log(folin) | Modela autokorrelasaun + sazonalidade; fó intervalu 95% |

Hold-out: fulan 12 ikus. Kada kombinasaun ai-han × merkadu hili modelu ho RMSE ki'ik liu → dashboard hatudu modelu ne'e hanesan "di'ak liu".

### B. Regression — folin fulan tuir mai
Ridge no Random Forest ho `lag1, lag2, lag3, lag12, mom_change, month_sin/cos, lean_season, rain_anom_6m_lag1` + tipu ai-han. Target = log(folin real). Kompara ho Naive (lag1). **Valór:** interpretasaun (feature importance) — hatudu se udan no sezaun iha efeitu liu folin kotuk.

### C. Produsaun (anuál)
- Time series: Holt damped vs Naive vs Linear trend (hold-out 3 tinan ikus).
- Regression Ridge: `production ~ year + wet_season_rain_mm + wet_season_dry_days + mean_temp_c` (LOOCV).
- **Previzaun senáriu** 3 tinan: Normál (mediana), Maran/El Niño (udan P10, loron maran P90), Udan barak/La Niña (udan P90).

### Metrics
MAE, RMSE (unidade USD ka tonelada), sMAPE (%), R² (produsaun). Tanba escala folin oioin (USD/kg vs USD/L), kompara modelu ho **sMAPE** bainhira kombina ai-han oioin.

---

## 7. Dashboard — pájina "Produsaun, lokalizasaun & folin"
| Rekizitu | Implementasaun |
|---|---|
| KPI cards | Folin ikus (+ mudansa fulan kotuk), mudansa 12 fulan, previzaun fulan tuir mai, merkadu baratu liu, produsaun kultura ikus |
| Filter | Ai-han, lokalizasaun (Nasionál ka merkadu), nominál/real, períodu, kultura |
| Trend | Folin per merkadu + mediana nasionál; índise sazonál; komparasaun ai-han (índise) |
| Comparison / lokalizasaun | Mapa merkadu (kór = folin); bar merkadu (foho vs tasi-ibun); mapa + bar produsaun munisípiu |
| Forecast | Previzaun modelu di'ak liu + intervalu 95% + modelu alternativu; **alerta folin** fulan 3; tabela avaliasaun; atuál vs prevee |
| Regression | Avaliasaun 1-step, feature importance; produsaun ho senáriu klima + koefisiente |
| Last updated | Header (tempu Dili) + LIVE/DEMO |

---

## 8. Aumenta ba Final Report
- **Ch.1:** RQ5–RQ8, objetivu 8–13.
- **Ch.2:** 2.10 Food prices & market integration (lean season, transport cost); 2.11 Exponential smoothing (Holt-Winters); 2.12 Crop production forecasting & climate scenarios.
- **Ch.3:** Arkitetura foun (diagrama iha leten); modelu A/B/C.
- **Ch.4:** 4.10 Price data (HXL, unidade, folin real); 4.11 Production data; 4.12 Location data.
- **Ch.5:** 5.11 Price trend & seasonality; 5.12 Spatial comparison (mapa); 5.13 Production trend & municipal share; 5.14 Forecast results.
- **Ch.6:** 6.7 Price model evaluation (tabela modelu × ai-han); 6.8 Production scenarios discussion.
- **Ch.7:** Rekomendasaun: sistema alerta folin ba MAP/MCI; stock estratéjiku tempu hamlaha.

## 9. Aumenta ba slide (16 slide mantein — troka konteúdu)
- **Slide 5 Data Source:** aumenta WFP/HDX, FAOSTAT, CPI.
- **Slide 7 Architecture:** uza diagrama "Agriculture API → Historical Data → EDA → Modeling → Forecast Dashboard".
- **Slide 8 Dataset:** tabela 3 — klima, folin (merkadu × ai-han × fulan), produsaun (kultura × tinan).
- **Slide 10 EDA:** gráfiku índise sazonál folin + mapa folin merkadu.
- **Slide 11 Mining Model:** SARIMA/Holt-Winters (folin), Ridge/RF, produsaun senáriu.
- **Slide 12 Evaluation:** tabela sMAPE modelu folin + RMSE produsaun.
- **Slide 13 Dashboard:** screenshot pájina 2 ho anotasaun.

## 10. Aumenta ba script vídeu (±3 minutu)
- **Parte 3 (Data Source):** hatudu HDX iha browser, esplika CKAN API no liña HXL (+30 s).
- **Parte 4 (EDA):** índise sazonál — "folin batar sa'e iha tempu hamlaha"; mapa merkadu (+45 s).
- **Parte 5 (Mining):** Holt-Winters vs SARIMA; senáriu El Niño ba produsaun (+45 s).
- **Parte 6 (Demo):** pájina "Produsaun, lokalizasaun & folin" → hili "Maize (white)" → merkadu Maliana → previzaun + alerta → tab Lokalizasaun (mapa) → tab Produsaun (senáriu) (+60 s).
