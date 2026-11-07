# Smart Agriculture Monitoring Dashboard for Timor-Leste
## Parte 1 — Problem Statement no Objetivu

### 1.1 Kontestu (Background)

Agrikultura mak moris-fatin ba maioria povu Timor-Leste. Uma-kain barak depende ba agrikultura subsisténsia (hare, batar, ai-farina, kafé), no parte boot husi forsa traballu nasionál servisu iha setór ne'e. Maibé agrikultura iha Timor-Leste depende maka'as ba **udan** tanba irigasaun sei limitadu — to'os-na'in barak kuda tuir tempu udan (Dezembru–Abríl) no hein bailoron (Maiu–Novembru).

Variabilidade klima (El Niño / La Niña) no mudansa klima afeta produsaun: El Niño 2015–16 hamosu maran naruk no hamenus kolleita batar no hare; La Niña kria udan boot, inundasaun no rai-halai. Ohin loron, informasaun klima no agríkola iha fatin oioin (API internasionál, relatóriu PDF, website notísia) maibé **la iha plataforma integradu ida** ne'ebé kombina dadus hirak ne'e, hatudu trend, no fó previzaun simples ne'ebé fasil atu komprende ba estudante, ekstensionista agríkola, ka tomador desizaun.

### 1.2 Problem Statement

> Dadus klima no agrikultura ba Timor-Leste fahe-malu iha fonte oioin no la prosesa ba informasaun ne'ebé bele uza. Tanba ne'e, difisil atu (1) monitoriza kondisaun udan no temperatura iha kada munisípiu, (2) antisipa risku maran ka udan boot iha fulan hirak tuir mai, no (3) komprende oinsá klima afeta produtividade ai-han. Projetu ne'e hakarak rezolve problema ne'e liuhusi dashboard monitorizasaun ida ne'ebé integra dadus husi API, web scraping, open data no RSS, no aplika métodu Time Series no Regression.

**Pergunta peskiza (research questions):**
1. Oinsá padraun sazonál no trend udan no temperatura iha munisípiu 14 Timor-Leste durante tinan ~30 ikus?
2. Oinsá modelu time series (SARIMA) bele prevee udan no temperatura fulan-fulan, no to'o ne'ebé di'ak kompara ho baseline simples?
3. Variavel klima saida (udan tempu udan, loron maran, temperatura) mak iha relasaun forte liu ho produtividade serea nasionál?
4. Oinsá aprezenta rezultadu hirak ne'e iha dashboard interativu ne'ebé atualiza automátiku?

### 1.3 Objetivu Jerál (General Objective)

Dezenvolve **Smart Agriculture Monitoring Dashboard** ida ba Timor-Leste ne'ebé rekolla dadus klima no agrikultura husi fonte online automátiku, analiza dadus hirak ne'e ho métodu data mining (Time Series no Regression), no aprezenta trend, komparasaun no previzaun iha forma vizuál ne'ebé fasil atu uza.

### 1.4 Objetivu Espesífiku (Specific Objectives)

1. **Rekolla dadus** klima loron-loron ba munisípiu 14 husi Open-Meteo/NASA POWER API, indikadór agrikultura husi World Bank API, informasaun munisípiu husi web scraping, no notísia husi RSS feed.
2. **Prepara dadus** (cleaning, tratamentu missing values no outlier, feature engineering hanesan sezaun, Growing Degree Days, water balance, loron maran) no agrega ba nível fulan no tinan.
3. **Halo EDA** atu identifika estatístika deskritiva, distribuisaun, padraun sazonál, trend (teste Mann-Kendall), komparasaun munisípiu, no korrelasaun entre klima no produtividade.
4. **Implementa modelu SARIMA** atu prevee udan no temperatura fulan 12 ba oin ba kada munisípiu, no kompara ho baseline (seasonal naive, climatology) no regression ho lag features.
5. **Implementa modelu Regression** (Linear, Ridge, Random Forest) atu estima produtividade serea (kg/ha) husi variavel klima anuál.
6. **Avalia modelu** ho metrics MAE, RMSE, R² no sMAPE, uza hold-out temporal (fulan 12 ikus) no Leave-One-Out Cross-Validation.
7. **Dezenvolve dashboard Streamlit** ho KPI cards, trend chart, comparison chart, filtru, rezultadu previzaun/mining, alerta agríkola, no last-updated timestamp.

### 1.5 Benefísiu (Significance)

- **Ba to'os-na'in no ekstensionista:** alerta simples "risku maran / udan boot" ba fulan 3 tuir mai.
- **Ba Ministériu Agrikultura (MAP) no ONG:** vizaun rápidu ba munisípiu ne'ebé presiza atensaun.
- **Ba akadémiku:** ezemplu pipeline data mining kompletu ho dadus loos Timor-Leste.

### 1.6 Limitasaun (Scope & Limitations)

- Dadus klima husi **reanalysis/satélite** (ERA5 via Open-Meteo, NASA MERRA-2), la'ós estasaun meteorolójika lokál — rezolusaun ~10–50 km, entaun detalle vale ki'ik ka foho la kaptura hotu.
- Dadus produsaun iha nível **nasionál no anuál** deit (n ≈ 20–30 tinan) → modelu regression iha limitasaun estatístika.
- Previzaun klima fulan-fulan iha inserteza boot; dashboard hatudu intervalu konfiansa 95%.

---

## Parte 2 — Fonte Dadus Konkretu no Oinsá Asesu

| # | Fonte | Tipu | Dadus | Asesu | Key? |
|---|-------|------|-------|-------|------|
| 1 | **Open-Meteo Historical Weather API** | API (JSON) | Udan, temperatura máx/mín/média, umidade, ET0 (FAO-56), radiasaun — loron-loron, 1940–ohin | `https://archive-api.open-meteo.com/v1/archive` | La presiza |
| 2 | **NASA POWER (Agroclimatology)** | API (JSON) | T2M, PRECTOTCORR, RH2M, radiasaun — loron-loron, 1981–ohin | `https://power.larc.nasa.gov/api/temporal/daily/point` | La presiza |
| 3 | **World Bank Open Data API** | Open data API | Cereal yield (kg/ha), produsaun serea, área, crop production index, % empregu agrikultura — anuál | `https://api.worldbank.org/v2/country/TLS/indicator/{code}?format=json` | La presiza |
| 4 | **FAOSTAT** (opsionál) | Open data (CSV) | Produsaun, área no produtividade hare, batar, kafé, ai-farina — anuál | Download manuál husi `https://www.fao.org/faostat/en/#data/QCL` | La presiza |
| 5 | **Wikipedia — Municipalities of East Timor** | Web scraping (HTML) | Populasaun, área munisípiu | `requests` + `BeautifulSoup` | La presiza |
| 6 | **Google News RSS** | RSS (XML) | Notísia "Timor-Leste agriculture / drought / flood" | `https://news.google.com/rss/search?q=...` | La presiza |
| 7 | **ReliefWeb RSS** | RSS (XML) | Relatóriu umanitáriu (dezastre, seguransa ai-han) ba Timor-Leste | `https://reliefweb.int/country/tls/rss.xml` | La presiza |

### Esplikasaun oinsá asesu (with examples)

**1. Open-Meteo** — Fonte prinsipál ba klima. Ita fó latitude/longitude kada munisípiu (haree `src/config.py`) no lista variavel.
```
https://archive-api.open-meteo.com/v1/archive?latitude=-8.556&longitude=125.578
  &start_date=2020-01-01&end_date=2020-12-31
  &daily=precipitation_sum,temperature_2m_mean&timezone=Asia/Dili
```
Resposta JSON iha `daily.time`, `daily.precipitation_sum`, ... → `pd.DataFrame(js["daily"])`.
*Nota:* versaun gratuita iha limite uzu (per minutu/oras/loron). Kódigu uza **incremental cache** (download períodu tomak dala ida deit, depois loron foun deit) no hein automátiku bainhira hetan erru 429.

**2. NASA POWER** — Fonte alternativa (`python -m src.data_collection --source nasa`) no bele uza atu **valida** Open-Meteo (kompara udan husi fonte rua). Valór `-999` = missing.

**3. World Bank API** — Kódigu nasaun Timor-Leste = `TLS`. Ezemplu:
```
https://api.worldbank.org/v2/country/TLS/indicator/AG.YLD.CREL.KG?format=json&per_page=200
```
Resposta mak lista `[metadata, [ {date, value, ...}, ... ]]`.

**4. FAOSTAT** — API FAOSTAT dala ruma la estável, entaun rekomenda download manuál: *Data → Production → Crops and livestock products → Country: Timor-Leste → Items: Rice, Maize (corn), Coffee green, Cassava → Elements: Area harvested, Yield, Production → Download CSV* → rai iha `data/raw/faostat_tls_crops.csv`. Ho dadus ne'e ita bele troka target regression husi "cereal yield" ba "maize yield" ka "rice yield".

**5. Web scraping Wikipedia** — `requests.get()` download HTML, `BeautifulSoup` buka `<table class="wikitable">` ne'ebé iha liafuan "Population", depois `pandas.read_html()`. **Étika scraping:** haree `robots.txt`, uza User-Agent klaru, la husu repetidamente, no sita fonte.

**6–7. RSS** — `feedparser.parse(url)` fila fali lista artigu (title, link, published, summary). Depois ita halo **text mining simples**: klasifika notísia ba topiku (drought, flood, food security, crops, pests) no identifika munisípiu ne'ebé temi.

### Fonte seluk ne'ebé bele uza (ba ezpansaun)
- **CHIRPS** (Climate Hazards Group) — udan satélite rezolusaun aas (~5 km), di'ak ba mapa udan. `https://www.chc.ucsb.edu/data/chirps`
- **HDX — Humanitarian Data Exchange** (Timor-Leste): boundary munisípiu (shapefile/GeoJSON), dadus seguransa ai-han. `https://data.humdata.org/group/tls`
- **INETL / Censo Agrícola 2019** — estatístika agríkola per munisípiu (PDF/Excel, presiza ekstrai manuál).
- **MAP (Ministério da Agricultura, Pecuária, Pescas e Florestas)** — notísia no relatóriu (web scraping).
- **SEEDS OF LIFE / ACIAR** — relatóriu peskiza variedade batar/hare iha Timor-Leste (literature review).
