# Script Vídeu YouTube Demo (±15 minutu)
**Smart Agriculture Monitoring Dashboard for Timor-Leste**

Rekomendasaun tékniku: grava ho OBS Studio (1080p), mikrofone ho kualidade di'ak, hatudu face-cam ki'ik iha kanto (opsionál). Taka notifikasaun, hamoos desktop, aumenta font terminal/VS Code (zoom 150%). Hala'o pipeline uluk molok grava atu dadus pronto.

Formatu tabela: **[Tempu] Vizuál → Narasaun (ezemplu)**

---

## PARTE 1 — Introduction (0:00 – 1:30)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 0:00 | Slide títulu | "Bondia! Ha'u-nia naran ___, estudante Siencia Komputador iha DIT. Iha vídeu ne'e ha'u sei aprezenta capstone project ba unidade kurikulár Mining and Exploring: *Smart Agriculture Monitoring Dashboard for Timor-Leste*." |
| 0:30 | Foto natar / to'os | "Agrikultura mak moris-fatin ba maioria povu Timor-Leste, maibé depende maka'as ba udan. Bainhira El Niño mai, hanesan iha 2015–2016, maran naruk halo kolleita tun." |
| 1:00 | Slide problema | "Problema mak dadus klima no agrikultura fahe-malu iha fonte oioin. Projetu ne'e kombina fonte hirak ne'e iha dashboard ida, ho previzaun." |

## PARTE 2 — Objectives (1:30 – 2:30)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 1:30 | Slide objetivu | Lee objetivu jerál. "Espesífikamente: rekolla dadus husi API, scraping no RSS; prepara dadus; halo EDA; aplika SARIMA no regression; avalia modelu; no dezenvolve dashboard." |
| 2:10 | Slide pergunta peskiza | Temi pergunta peskiza 4 ho lalais. |

## PARTE 3 — Data Source & Architecture (2:30 – 4:30)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 2:30 | Tabela fonte dadus | Esplika fonte ida-idak: Open-Meteo (klima loron-loron munisípiu 14), World Bank (produtividade serea), Wikipedia (scraping populasaun), Google News/ReliefWeb (RSS). |
| 3:15 | Browser: loke URL API Open-Meteo | "Ne'e ezemplu resposta JSON husi API — ita haree kolun `precipitation_sum` no `temperature_2m_max`." |
| 3:45 | Diagrama arkitetura | "Pipeline iha etapa 4: collection, preprocessing, EDA no mining. Rezultadu rai iha folder `data/outputs`, depois dashboard Streamlit lee husi ne'e. Pipeline bele hala'o automátiku loron-loron ho cron." |
| 4:15 | VS Code: estrutura folder | Hatudu `data/`, `src/`, `notebooks/`, `dashboard/`, `reports/`. |

## PARTE 4 — Collection, Preprocessing & EDA (4:30 – 8:00)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 4:30 | Terminal: `python -m src.data_collection` | "Ha'u hala'o data collection. Haree — kódigu download munisípiu ida-idak. Iha incremental cache, entaun update tuir mai lalais." |
| 5:15 | VS Code: `fetch_open_meteo()` no `scrape_municipalities()` | Esplika badak request → JSON → DataFrame; BeautifulSoup buka tabela. |
| 5:45 | `preprocessing.py` + `preprocessing_report.json` | "Iha dadus raw ita hetan missing values no valór imposível hanesan temperatura 99.9 °C. Temperatura ita interpola, maibé udan la bele interpola — ita uza mediana fulan hanesan. Ita mós kria feature foun: sezaun, Growing Degree Days, water balance." |
| 6:45 | Notebook / figura EDA | Hatudu: (1) boxplot sazonál — "udan barak liu iha Janeiru, maran liu iha Agostu"; (2) trend temperatura + Mann-Kendall; (3) komparasaun munisípiu; (4) heatmap korrelasaun. |

## PARTE 5 — Mining & Evaluation (8:00 – 11:00)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 8:00 | Slide SARIMA | "Tanba sá SARIMA? Klima Timor-Leste iha sazonalidade 12 fulan maka'as. SARIMA modela memória fulan kotuk no padraun sazonál, no fó intervalu konfiansa. Ba udan, ha'u uza log1p tanba distribuisaun skewed." |
| 8:45 | Kódigu `fit_sarima()` | Esplika seleksaun modelu ho AIC. |
| 9:15 | Slide regression | "Modelu regression rua: primeiru, Random Forest no Ridge ho lag features ba udan; segundu, regression produtividade serea husi klima anuál ho Leave-One-Out cross validation tanba dadus anuál uitoan." |
| 9:50 | Tabela `model_comparison.csv` | "Ita avalia ho MAE, RMSE, R² no sMAPE iha fulan 12 ikus ne'ebé modelu la haree. Achado interesante: ba udan, baseline klimatolojia forte tebes... ba temperatura SARIMA di'ak liu." (Lee rezultadu LOOS husi ita-nia run.) |
| 10:30 | Gráfiku atuál vs prevee | Esplika erru boot iha fulan udan ekstremu. |

## PARTE 6 — Live Demo Dashboard (11:00 – 14:30)
| Tempu | Vizuál | Narasaun / Asaun |
|---|---|---|
| 11:00 | `streamlit run dashboard/app.py` | Loke dashboard. Hatudu **last-updated timestamp** no badge LIVE DATA. |
| 11:20 | KPI cards | Esplika KPI 5: udan média, temperatura, % loron maran, anomalia udan fulan ikus, produtividade serea. |
| 11:50 | Sidebar filtru | Hili zona "Foho", depois munisípiu Ermera no Ainaro; muda períodu; hili sezaun "Tempu udan" — haree KPI muda. |
| 12:30 | Tab Trend | Toggle média 12 fulan; gráfiku anuál ho linha trend. |
| 12:50 | Tab Komparasaun | Bar chart foho vs tasi-ibun; mapa; heatmap munisípiu × fulan. |
| 13:20 | Tab Previzaun | Hili Baucau → previzaun 12 fulan ho intervalu 95%; tabela **alerta agríkola** fulan 3; tabela avaliasaun modelu. |
| 13:50 | Tab Produtividade | Gráfiku LOOCV; simulasaun what-if: hamenus udan tempu udan → produtividade tun. |
| 14:10 | Tab Notísia | Filtru topiku "drought"; link notísia. Tab Dadus: download CSV. |

## PARTE 7 — Conclusion (14:30 – 15:30)
| Tempu | Vizuál | Narasaun |
|---|---|---|
| 14:30 | Slide konkluzaun | "Projetu ne'e konsege integra fonte dadus 5 no aplika time series no regression. Limitasaun: dadus reanalysis no dadus produtividade anuál uitoan. Futuru: CHIRPS, NDVI satélite, alerta SMS ba to'os-na'in." |
| 15:00 | Slide link | "Kódigu kompletu iha GitHub, link iha deskrisaun. Obrigadu barak ba tempu, no favor fó komentáriu!" |

---

### Deskrisaun YouTube (template)
```
Smart Agriculture Monitoring Dashboard for Timor-Leste | Capstone Project – Mining and Exploring (DIT)

Dashboard ne'ebé monitoriza klima no agrikultura iha munisípiu 14 Timor-Leste, ho previzaun SARIMA no regression produtividade serea.

⏱ Capítulo
00:00 Introduction
01:30 Objectives
02:30 Data Source & Architecture
04:30 Data Collection, Preprocessing & EDA
08:00 Mining & Evaluation
11:00 Live Demo
14:30 Conclusion

💻 GitHub: https://github.com/<username>/tl-agri-dashboard
🌐 Dashboard: https://<app-name>.streamlit.app
📊 Fonte dadus: Open-Meteo, NASA POWER, World Bank, Wikipedia, Google News/ReliefWeb RSS
#TimorLeste #DataMining #Streamlit #Python #Agriculture
```

### Checklist molok upload
- [ ] Áudio moos, la iha barullu
- [ ] Rezultadu metrics iha vídeu hanesan ho relatóriu
- [ ] Hatudu dashboard ho LIVE DATA (la'ós DEMO)
- [ ] Chapters (timestamp) iha deskrisaun
- [ ] Thumbnail: títulu + screenshot dashboard
- [ ] Vizibilidade "Unlisted" ka "Public" tuir orientasaun dosente
