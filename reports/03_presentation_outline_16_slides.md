# Outline PowerPoint — 16 Slide
**Smart Agriculture Monitoring Dashboard for Timor-Leste**
Durasaun aprezentasaun: 12–15 minutu (±1 minutu per slide). Regra: slide ida = ideia ida, testu máximu 5 liña, vizuál barak liu testu.

Kór sujere: verde natar `#3E6B48`, azul monsaun `#2F5D7C`, kinur bailoron `#C9A227`, fundu mutin.

---

**Slide 1 — Title**
- Títulu: *Smart Agriculture Monitoring Dashboard for Timor-Leste*
- Subtítulu: Time Series & Regression for Agro-climate Monitoring
- Naran estudante, NIM, unidade kurikulár "Mining and Exploring", Siencia Komputador — DIT, orientadór, data
- Vizuál: foto natar hare (ex. Maliana/Baucau) ho overlay escuru

**Slide 2 — Background**
- Maioria povu depende ba agrikultura; irigasaun limitadu → depende ba udan
- Sezaun: udan (Dez–Abr) vs bailoron (Mai–Nov)
- El Niño 2015–16: maran naruk, kolleita tun
- Vizuál: gráfiku sazonál udan (boxplot fulan) husi EDA

**Slide 3 — Problem**
- Dadus fahe-malu iha fonte oioin (API, PDF, notísia)
- La iha monitorizasaun per munisípiu no previzaun simples
- Difisil antisipa risku maran/udan boot
- Vizuál: ikon 3 "fonte fahe-malu → la iha desizaun"

**Slide 4 — Objectives**
- Objetivu jerál (liña 1)
- Objetivu espesífiku 7 → hatudu hanesan fluxu: Collect → Prepare → Explore → Model → Evaluate → Visualize

**Slide 5 — Data Source**
- Tabela: Open-Meteo, NASA POWER, World Bank, Wikipedia (scraping), Google News & ReliefWeb (RSS), FAOSTAT
- Kolun: tipu (API/Scraping/Open data/RSS), dadus, frekuénsia
- Mensajen: "Hotu gratuitu, la presiza API key"

**Slide 6 — Methodology**
- CRISP-DM: Business understanding → Data understanding → Preparation → Modeling → Evaluation → Deployment
- Métodu: SARIMA (time series) + Linear/Ridge/Random Forest (regression)
- Justifikasaun badak: sazonalidade 12 fulan → SARIMA; interpretabilidade → Ridge

**Slide 7 — Architecture**
- Diagrama: Fonte → `data_collection.py` → `data/raw` → `preprocessing.py` → `data/processed` → `eda.py` + `models.py` → `data/outputs` → `dashboard/app.py` (Streamlit)
- Cron job loron-loron + incremental cache

**Slide 8 — Dataset**
- Munisípiu 14 × ~11,500 loron (1995–2026) ≈ 162,000 liña loron-loron → ±5,300 liña fulan-fulan (númeru ikus depende ba run live)
- Variavel: udan, T máx/mín/média, RH, ET0, radiasaun + indikadór World Bank 6
- Vizuál: screenshot `df.head()` + tabela variavel

**Slide 9 — Preprocessing**
- Antes vs depois (tabela husi `preprocessing_report.json`): missing, duplikadu, valór imposível
- Metode: interpolasaun (temperatura), klimatolojia mediana (udan)
- Feature foun: sezaun, GDD, water balance, loron maran, anomalia udan

**Slide 10 — EDA Findings**
- 3–4 achado prinsipál ho gráfiku ida-idak (mini):
  - Fulan udan liu / maran liu
  - Trend temperatura (Mann-Kendall p-value, Sen's slope)
  - Munisípiu udan barak liu vs maran liu (foho vs tasi-ibun)
  - Korrelasaun udan tempu udan ↔ produtividade

**Slide 11 — Mining Model**
- SARIMA: ekuasaun badak, log1p ba udan, seleksaun AIC, horizon 12 fulan, intervalu 95%
- Regression: lag features (lag12/24/36, sin/cos fulan) + regression produtividade (LOOCV)
- Vizuál: gráfiku previzaun Dili ho intervalu konfiansa

**Slide 12 — Evaluation**
- Tabela: MAE, RMSE, R², sMAPE ba modelu hotu (husi `model_comparison.csv`)
- Destaka modelu di'ak liu ba udan no temperatura
- Mensajen onestu: "Baseline klimatolojia forte tebes ba udan — sazonalidade domina"

**Slide 13 — Dashboard**
- Screenshot anotadu: (1) KPI cards (2) filtru sidebar (3) trend chart (4) comparison/map (5) forecast + alerta (6) last-updated timestamp

**Slide 14 — Live Demo**
- Slide simples: "LIVE DEMO" + QR code ba URL dashboard (Streamlit Cloud)
- Planu demo (30–60 s): filtru munisípiu → forecast Baucau → alerta → what-if produtividade
- Backup: vídeu badak/GIF se internet la di'ak

**Slide 15 — Conclusion**
- Responde objetivu 3–4 liña
- Limitasaun 2
- Traballu futuru: CHIRPS, NDVI satélite, dadus FAOSTAT per kultura, alerta SMS

**Slide 16 — YouTube/GitHub Links**
- QR code + link GitHub repository
- QR code + link vídeu YouTube demo
- Link dashboard online
- "Obrigadu barak! Perguntas?"
