"""
models.py
=========
PASSU 4-5: DATA MINING (Time Series + Regression) no MODEL EVALUATION

-------------------------------------------------------------------------
MODELU A - TIME SERIES: SARIMA (Seasonal ARIMA) ba udan no temperatura fulan-fulan
-------------------------------------------------------------------------
Tanba sá apropriadu?
  * Klima Timor-Leste iha SAZONALIDADE maka'as (monsaun, perídu 12 fulan).
    SARIMA modela direta: AR (memória fulan kotuk), MA (xoke aleatóriu),
    no komponente sazonál (s=12).
  * Fó INTERVALU KONFIANSA (95%) -> importante ba to'os-na'in/MAP atu hatene risku.
  * Presiza dadus uitoan deit (serie ida ho tinan 20-30) no fasil atu esplika.
  * Udan la normál (skewed, barak 0) -> ita uza transformasaun log1p(udan).
Baseline (atu hatene modelu ne'e di'ak duni ka lae):
  * Seasonal naive: fulan ne'e = fulan hanesan tinan kotuk
  * Climatology  : fulan ne'e = média fulan hanesan iha tinan hotu

-------------------------------------------------------------------------
MODELU B - REGRESSION ho LAG FEATURES (Ridge + Random Forest) ba udan fulan-fulan
-------------------------------------------------------------------------
Tanba sá?
  * Kombina dadus munisípiu HOTU iha modelu ida (pooled) -> dadus barak liu.
  * Feature: lag 12/24/36 fulan, sin/cos fulan, zona, latitude...
    Lag mínimu = 12 -> bele prevee DIRETAMENTE fulan 1-12 ba oin (la presiza rekursivu).
  * Random Forest kaptura relasaun non-linear; Ridge = modelu linear simples no estável.

-------------------------------------------------------------------------
MODELU C - REGRESSION: PRODUTIVIDADE SEREA (kg/ha) husi klima anuál
-------------------------------------------------------------------------
Tanba sá?
  * Objetivu: hatene variavel klima saida mak afeta produsaun ai-han.
  * Linear/Ridge regression fó koefisiente ne'ebé fasil atu interpreta
    ("udan +100 mm -> produtividade +X kg/ha").
  * Dadus anuál ki'ik (n ~ 20-30) -> uza Leave-One-Out Cross Validation (LOOCV)
    no modelu simples (evita overfitting).

METRICS:
  MAE   = média erru absolutu (unidade hanesan dadus, fasil atu komprende)
  RMSE  = kastigu maka'as liu ba erru boot (importante ba udan ekstremu)
  R²    = porsentajen variasaun ne'ebé modelu esplika
  sMAPE = erru persentajen simétriku (di'ak liu MAPE bainhira udan = 0)

Uza:  python -m src.models
"""
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX

from . import config

warnings.filterwarnings("ignore")   # statsmodels hatudu warning konverjénsia barak


# ==========================================================================
# METRICS
# ==========================================================================
def smape(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    denom = (np.abs(y_true) + np.abs(y_pred))
    out = np.where(denom == 0, 0.0, 2 * np.abs(y_pred - y_true) / np.where(denom == 0, 1, denom))
    return float(np.mean(out) * 100)


def evaluate(y_true, y_pred):
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "R2": round(float(r2_score(y_true, y_pred)), 3),
        "sMAPE_%": round(smape(y_true, y_pred), 2),
    }


# ==========================================================================
# MODELU A: SARIMA
# ==========================================================================
SARIMA_GRID = [((1, 0, 0), (0, 1, 1, 12)),
               ((1, 0, 1), (0, 1, 1, 12)),
               ((1, 0, 0), (1, 1, 1, 12)),
               ((2, 0, 0), (0, 1, 1, 12))]


def _transform(y, variable):
    """Udan: log1p (hamenus skewness). Temperatura: la muda."""
    return np.log1p(y) if variable == "rain_mm" else y


def _inverse(y, variable):
    return np.clip(np.expm1(y), 0, None) if variable == "rain_mm" else y


def fit_sarima(series, variable, order=None, seasonal_order=None):
    """Se order la fó, buka kombinasaun di'ak liu ho AIC (Akaike Information Criterion)."""
    y = _transform(series, variable)
    candidates = [(order, seasonal_order)] if order else SARIMA_GRID
    best = None
    for o, so in candidates:
        try:
            res = SARIMAX(y, order=o, seasonal_order=so,
                          enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
            if best is None or res.aic < best[0].aic:
                best = (res, o, so)
        except Exception:  # noqa: BLE001
            continue
    return best  # (result, order, seasonal_order)


def sarima_forecast(res, steps, variable):
    fc = res.get_forecast(steps=steps)
    ci = fc.conf_int(alpha=0.05)
    return (_inverse(fc.predicted_mean, variable),
            _inverse(ci.iloc[:, 0], variable),
            _inverse(ci.iloc[:, 1], variable))


def seasonal_naive(train, steps):
    last_year = train.iloc[-12:].values
    return np.resize(last_year, steps)


def climatology(train, test_index):
    clim = train.groupby(train.index.month).mean()
    return np.array([clim.loc[d.month] for d in test_index])


def run_time_series(monthly):
    """Avalia modelu iha fulan TEST_MONTHS ikus, depois prevee FORECAST_HORIZON ba oin."""
    eval_rows, pred_rows, fc_rows, chosen = [], [], [], {}
    H, T = config.FORECAST_HORIZON, config.TEST_MONTHS

    for variable in ["rain_mm", "tmean_c"]:
        for muni in sorted(monthly["municipality"].unique()):
            s = (monthly[monthly["municipality"] == muni].set_index("date")[variable]
                 .asfreq("MS").interpolate())
            if s.notna().sum() < 60:
                continue
            train, test = s.iloc[:-T], s.iloc[-T:]

            # --- Treinu no teste (hold-out) ---
            best = fit_sarima(train, variable)
            if best is None:
                continue
            res, order, sorder = best
            sar, _, _ = sarima_forecast(res, T, variable)
            preds = {
                "SARIMA": np.asarray(sar),
                "Seasonal naive": seasonal_naive(train, T),
                "Climatology": climatology(train, test.index),
            }
            for model, p in preds.items():
                eval_rows.append({"variable": variable, "municipality": muni, "model": model,
                                  **evaluate(test.values, p)})
                pred_rows += [{"variable": variable, "municipality": muni, "model": model,
                               "date": d, "actual": a, "predicted": round(float(v), 2)}
                              for d, a, v in zip(test.index, test.values, p)]

            # --- Refit ho dadus HOTU, depois prevee fulan H ba oin ---
            full = fit_sarima(s, variable, order, sorder)[0]
            mean, lo, hi = sarima_forecast(full, H, variable)
            clim = s.groupby(s.index.month).mean()
            for d, m_, l_, h_ in zip(mean.index, mean, lo, hi):
                fc_rows.append({"variable": variable, "municipality": muni, "model": "SARIMA",
                                "date": d, "forecast": round(float(m_), 2),
                                "lower_95": round(float(l_), 2), "upper_95": round(float(h_), 2),
                                "climatology": round(float(clim.loc[d.month]), 2)})
            chosen[f"{variable}|{muni}"] = {"order": order, "seasonal_order": sorder,
                                            "aic": round(float(res.aic), 2)}
            print(f"   SARIMA {variable:8s} {muni:10s} order={order} seasonal={sorder}")

    return pd.DataFrame(eval_rows), pd.DataFrame(pred_rows), pd.DataFrame(fc_rows), chosen


# ==========================================================================
# MODELU B: REGRESSION HO LAG FEATURES (udan fulan-fulan)
# ==========================================================================
LAG_FEATURES = ["month_sin", "month_cos", "lag12", "lag24", "lag36", "same_month_mean_3y",
                "rolling12_lag12", "lat", "lon", "is_highland"]


def build_lag_features(monthly, variable="rain_mm"):
    df = monthly[["municipality", "date", variable]].copy().sort_values(["municipality", "date"])
    g = df.groupby("municipality")[variable]
    for k in (12, 24, 36):
        df[f"lag{k}"] = g.shift(k)
    df["same_month_mean_3y"] = df[["lag12", "lag24", "lag36"]].mean(axis=1)
    # Udan total 12 fulan ne'ebé remata fulan 12 liu ba (indikadór tinan maran/bokon)
    df["rolling12_lag12"] = g.transform(lambda s: s.shift(12).rolling(12).sum())
    df["month_sin"] = np.sin(2 * np.pi * df["date"].dt.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["date"].dt.month / 12)
    df["lat"] = df["municipality"].map(lambda m: config.MUNICIPALITIES[m]["lat"])
    df["lon"] = df["municipality"].map(lambda m: config.MUNICIPALITIES[m]["lon"])
    df["is_highland"] = df["municipality"].map(lambda m: int(config.MUNICIPALITIES[m]["zone"] == "highland"))
    return df


def run_lag_regression(monthly):
    variable = "rain_mm"
    df = build_lag_features(monthly, variable).dropna(subset=LAG_FEATURES + [variable])
    test_start = df["date"].max() - pd.DateOffset(months=config.TEST_MONTHS - 1)
    train, test = df[df["date"] < test_start], df[df["date"] >= test_start]

    models = {
        "Ridge (lag)": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "Random Forest (lag)": RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                                                     random_state=config.RANDOM_STATE, n_jobs=-1),
    }
    eval_rows, pred_rows, importances = [], [], {}
    for name, model in models.items():
        model.fit(train[LAG_FEATURES], train[variable])
        p = np.clip(model.predict(test[LAG_FEATURES]), 0, None)
        t = test.assign(pred=p)
        for muni, g in t.groupby("municipality"):
            eval_rows.append({"variable": variable, "municipality": muni, "model": name,
                              **evaluate(g[variable], g["pred"])})
        pred_rows += [{"variable": variable, "municipality": r.municipality, "model": name,
                       "date": r.date, "actual": getattr(r, variable), "predicted": round(float(r.pred), 2)}
                      for r in t.itertuples()]
        if hasattr(model, "feature_importances_"):
            importances[name] = dict(zip(LAG_FEATURES, np.round(model.feature_importances_, 4)))
    # Rai Random Forest (treinu ho dadus hotu) ba uza iha futuru
    rf = models["Random Forest (lag)"].fit(df[LAG_FEATURES], df[variable])
    joblib.dump(rf, config.DATA_OUTPUTS / "rf_rain_lag_model.joblib", compress=3)
    return pd.DataFrame(eval_rows), pd.DataFrame(pred_rows), importances


# ==========================================================================
# MODELU C: REGRESSION PRODUTIVIDADE SEREA
# ==========================================================================
YIELD_TARGET = "cereal_yield_kg_ha"
YIELD_FEATURES = ["wet_season_rain_mm", "wet_season_dry_days", "mean_temp_c",
                  "max_temp_c", "heavy_rain_days", "year"]   # year = trend teknolojia


def run_yield_regression(annual):
    if YIELD_TARGET not in annual.columns:
        return {"note": "Target la iha (World Bank la fó dadus)."}, pd.DataFrame(), {}
    d = annual.dropna(subset=YIELD_FEATURES + [YIELD_TARGET]).sort_values("year")
    if len(d) < 8:
        return {"note": f"Dadus ki'ik demais (n={len(d)}) ba regression."}, pd.DataFrame(), {}
    X, y = d[YIELD_FEATURES], d[YIELD_TARGET]

    models = {
        "Baseline (mean)": None,
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Ridge Regression": make_pipeline(StandardScaler(), Ridge(alpha=3.0)),
        "Random Forest": RandomForestRegressor(n_estimators=300, max_depth=3,
                                               random_state=config.RANDOM_STATE),
    }
    loo = LeaveOneOut()
    results, preds = {}, pd.DataFrame({"year": d["year"].values, "actual": y.values})
    for name, model in models.items():
        if model is None:   # baseline: prevee média husi dadus seluk
            p = np.array([y.drop(y.index[i]).mean() for i in range(len(y))])
        else:
            p = cross_val_predict(model, X, y, cv=loo)
        preds[name] = np.round(p, 1)
        results[name] = evaluate(y, p)
        print(f"   Yield {name:18s} LOOCV {results[name]}")

    best = min((k for k in results if k != "Baseline (mean)"), key=lambda k: results[k]["RMSE"])
    final = models[best].fit(X, y)
    joblib.dump({"model": final, "features": YIELD_FEATURES, "name": best},
                config.DATA_OUTPUTS / "yield_model.joblib")

    # Interpretasaun: koefisiente standardizadu (Ridge) + importánsia (RF)
    ridge = models["Ridge Regression"].fit(X, y)
    interp = {
        "ridge_standardized_coef": dict(zip(YIELD_FEATURES, np.round(ridge[-1].coef_, 2))),
        "rf_importance": dict(zip(YIELD_FEATURES,
                                  np.round(models["Random Forest"].fit(X, y).feature_importances_, 3))),
    }
    summary = {"n_years": int(len(d)), "years": [int(d["year"].min()), int(d["year"].max())],
               "cv": "Leave-One-Out", "metrics": results, "best_model": best, "interpretation": interp,
               "feature_ranges": {f: [float(X[f].min()), float(X[f].max()), float(X[f].median())]
                                  for f in YIELD_FEATURES}}
    return summary, preds, interp


# ==========================================================================
# MAIN
# ==========================================================================
def _to_native(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def run():
    print("=" * 60)
    print("DATA MINING: TIME SERIES + REGRESSION")
    print("=" * 60)
    monthly = pd.read_csv(config.DATA_PROCESSED / "weather_monthly.csv", parse_dates=["date"])
    annual = pd.read_csv(config.DATA_PROCESSED / "annual_national.csv")

    print("\n[A] SARIMA time series ...")
    ts_eval, ts_pred, forecasts, chosen = run_time_series(monthly)

    print("\n[B] Lag-feature regression ...")
    lag_eval, lag_pred, importances = run_lag_regression(monthly)

    print("\n[C] Crop yield regression ...")
    yield_summary, yield_preds, _ = run_yield_regression(annual)

    evals = pd.concat([ts_eval, lag_eval], ignore_index=True)
    evals.to_csv(config.DATA_OUTPUTS / "model_evaluation_by_municipality.csv", index=False)
    pd.concat([ts_pred, lag_pred]).to_csv(config.DATA_OUTPUTS / "test_predictions.csv", index=False)
    forecasts.to_csv(config.DATA_OUTPUTS / "forecasts.csv", index=False)
    yield_preds.to_csv(config.DATA_OUTPUTS / "yield_loocv_predictions.csv", index=False)

    # Rezumu: média metrics per modelu (munisípiu hotu)
    overall = (evals.groupby(["variable", "model"])[["MAE", "RMSE", "R2", "sMAPE_%"]]
               .mean().round(3).reset_index())
    overall.to_csv(config.DATA_OUTPUTS / "model_comparison.csv", index=False)
    print("\nKomparasaun modelu (média munisípiu hotu):\n", overall.to_string(index=False))

    metrics = {"time_series_overall": overall.to_dict(orient="records"),
               "sarima_orders": chosen, "lag_regression_importance": importances,
               "yield_regression": yield_summary, "test_months": config.TEST_MONTHS,
               "forecast_horizon": config.FORECAST_HORIZON}
    (config.DATA_OUTPUTS / "metrics.json").write_text(json.dumps(metrics, indent=2, default=_to_native))
    return metrics


if __name__ == "__main__":
    run()
