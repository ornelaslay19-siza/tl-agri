# Estrutura Final Report — Smart Agriculture Monitoring Dashboard for Timor-Leste

**Páɡina preliminár:** Kapa · Deklarasaun autentisidade · Aprovasaun orientadór · Agradesimentu · Abstract (Inglés, 200–300 liafuan) · Rezumu (Tetun) · Índise · Lista tabela · Lista figura · Lista abreviatura (API, EDA, SARIMA, RMSE, ET0, GDD, MAP...)

Tamañu rekomendadu: 40–60 pájina (la inklui apéndise).

---

## CHAPTER 1 — INTRODUCTION (±5 pájina)
1.1 Background — importánsia agrikultura ba Timor-Leste; dependénsia ba udan; impaktu El Niño/La Niña; nesesidade monitorizasaun bazeia ba dadus.
1.2 Problem Statement — (haree `01_problem_statement_and_data_sources.md`)
1.3 Research Questions (4)
1.4 Objectives — Jerál + Espesífiku (7)
1.5 Scope and Limitations — munisípiu 14, períodu 1995–2026, dadus reanalysis, produtividade nível nasionál
1.6 Significance of the Study
1.7 Report Organization — deskrisaun badak kada kapítulu

## CHAPTER 2 — LITERATURE REVIEW (±8 pájina)
2.1 Agriculture and Climate in Timor-Leste — sezaun monsaun, sistema kuda, relatóriu FAO/WFP/MAP, Seeds of Life.
2.2 Climate Variability and Crop Yield — relasaun udan/temperatura ho produtividade; El Niño 2015–16.
2.3 Data Sources for Agro-climate Monitoring — reanalysis (ERA5), satélite (NASA POWER, CHIRPS), open data (World Bank, FAOSTAT).
2.4 Data Mining Process — CRISP-DM ka KDD (Knowledge Discovery in Databases).
2.5 Time Series Forecasting — komponente (trend, sazonalidade, residual), ARIMA/SARIMA (Box-Jenkins), baseline (seasonal naive, climatology), alternativa (Prophet, LSTM).
2.6 Regression Methods — Linear, Ridge (regularization), Random Forest; problema dadus ki'ik no overfitting; cross-validation.
2.7 Dashboards for Agricultural Decision Support — ezemplu sistema early-warning (FEWS NET, GIEWS), prinsípiu dashboard di'ak.
2.8 Related Works — tabela komparasaun estudu 5–8 (autór, tinan, dadus, métodu, rezultadu, gap).
2.9 Research Gap — la iha dashboard integradu ho previzaun ba nível munisípiu iha Timor-Leste.

## CHAPTER 3 — METHODOLOGY (±6 pájina)
3.1 Research Framework — figura CRISP-DM adapta ba projetu.
3.2 System Architecture — diagrama: Fonte (API/Scraping/RSS) → Collection → Raw storage → Preprocessing → EDA → Models → Outputs → Streamlit Dashboard; agendamentu (cron).
3.3 Tools and Technologies — Python, pandas, requests, BeautifulSoup, feedparser, statsmodels, scikit-learn, Plotly, Streamlit, Git/GitHub.
3.4 Method 1: SARIMA — ekuasaun SARIMA(p,d,q)(P,D,Q)s; transformasaun log1p; seleksaun modelu ho AIC; justifikasaun.
3.5 Method 2: Regression — (a) lag-feature regression ba udan; (b) regression produtividade serea; ekuasaun Ridge; Random Forest.
3.6 Evaluation Design — hold-out temporal 12 fulan (tanba sá la bele random split iha time series), LOOCV ba dadus anuál, baseline.
3.7 Evaluation Metrics — fórmula MAE, RMSE, R², sMAPE no interpretasaun.

## CHAPTER 4 — DATA COLLECTION AND PREPROCESSING (±7 pájina)
4.1 Data Sources — tabela fonte 5–7 (URL, formatu, períodu, variavel, frekuénsia).
4.2 Data Collection Implementation — API request, scraping, RSS; incremental cache; rate limit; screenshot kódigu importante.
4.3 Dataset Description — tabela variavel (naran, tipu, unidade, deskrisaun); númeru liña/kolun.
4.4 Data Quality Assessment — missing values, duplikadu, valór imposível (antes).
4.5 Data Cleaning — tipu dadus, duplikadu, limite fíziku.
4.6 Handling Missing Values — interpolasaun linear (temperatura), klimatolojia mediana (udan) + justifikasaun.
4.7 Data Transformation & Feature Engineering — sezaun, tinan agríkola, GDD, water balance, loron maran, udan boot, log1p.
4.8 Data Aggregation & Integration — loron → fulan → tinan; merge ho World Bank.
4.9 Summary — tabela antes/depois (`preprocessing_report.json`).

## CHAPTER 5 — EDA AND MINING RESULTS (±10 pájina)
5.1 Descriptive Statistics — tabela per munisípiu.
5.2 Distribution Analysis — histograma udan (skewness) no temperatura.
5.3 Seasonal Patterns — boxplot fulan, seasonal decomposition Dili.
5.4 Trend Analysis — trend anuál + Mann-Kendall + Sen's slope.
5.5 Comparison between Municipalities — bar chart, mapa, heatmap munisípiu × fulan; foho vs tasi-ibun.
5.6 Correlation Analysis — heatmap, scatter udan vs produtividade.
5.7 Time Series Mining Results — ordem SARIMA hili, gráfiku previzaun + intervalu 95%.
5.8 Regression Results — koefisiente Ridge, feature importance Random Forest, what-if.
5.9 Text Mining Results (RSS) — distribuisaun topiku notísia.
5.10 Key Findings — lista achado prinsipál 5–7.

## CHAPTER 6 — EVALUATION AND DISCUSSION (±6 pájina)
6.1 Time Series Model Evaluation — tabela MAE/RMSE/R²/sMAPE: SARIMA vs Seasonal naive vs Climatology vs Ridge/RF (lag); per munisípiu no média.
6.2 Regression Model Evaluation — tabela LOOCV; gráfiku atuál vs prevee.
6.3 Discussion — responde pergunta peskiza 1–4 ida-idak; tanba sá modelu ida di'ak liu (ex. klimatolojia forte tebes ba udan tanba sazonalidade domina; SARIMA forte ba temperatura).
6.4 Dashboard Evaluation — funsionalidade vs rekizitu; (opsionál) teste uzabilidade ho uzuáriu 5 (SUS questionnaire).
6.5 Limitations — rezolusaun dadus, dadus produtividade ki'ik, la iha dadus estasaun lokál, inserteza previzaun.
6.6 Ethical Considerations — scraping responsável, lisensa dadus (CC-BY), la uza previzaun hanesan konsellu ofisiál.

## CHAPTER 7 — CONCLUSION AND RECOMMENDATIONS (±3 pájina)
7.1 Conclusion — rezumu rezultadu tuir objetivu espesífiku ida-idak.
7.2 Contributions
7.3 Recommendations — ba MAP/ekstensionista; ba peskiza futuru (CHIRPS, NDVI satélite, dadus FAOSTAT per kultura, LSTM/Prophet, ENSO index hanesan feature, SMS alert).
7.4 Final Remarks

**References** — APA 7th (minimu 15–20; inklui dokumentasaun API no artigu jornál).

**Appendices** — A: Kódigu importante · B: Screenshot dashboard · C: Tabela metrics kompletu per munisípiu · D: Link GitHub no YouTube · E: Manuál instalasaun.
