"""
agri_models.py
==============
PASSU 4-5 (extension): MODELING (Time Series Forecasting + Regression) no EVALUATION

A. FOLIN — TIME SERIES FORECASTING (per ai-han × lokalizasaun)
   Modelu: Naive, Seasonal naive, Holt-Winters (ETS), SARIMA
   * Folin iha TREND (inflasaun) + SAZONALIDADE (tempu hamlaha) -> Holt-Winters no
     SARIMA modela komponente rua ne'e.
   * Ita modela log(folin): mudansa sai persentajen no intervalu la bele negativu.
   * Kada série hili modelu di'ak liu tuir RMSE iha hold-out 12 fulan ikus.

B. FOLIN — REGRESSION (previzaun fulan tuir mai, 1-step ahead)
   Ridge + Random Forest ho feature: lag 1/2/3/12, sazonalidade, tempu hamlaha,
   anomalia udan 6 fulan (klima), tipu ai-han.
   * Objetivu: hatene fatór saida mak esplika mudansa folin (interpretasaun) no
     kompara ho baseline naive (folin fulan kotuk).

C. PRODUSAUN — TIME SERIES + REGRESSION (anuál, per kultura)
   * Time series: Holt damped trend vs naive vs trend linear (hold-out 3 tinan ikus)
   * Regression: Ridge (tinan + udan tempu udan + loron maran + temperatura), LOOCV
   * Previzaun SENÁRIU tinan 3 ba oin: klima normál / maran (El Niño) / udan barak

Uza:  python -m src.agri_models
"""
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from . import config
from .models import _to_native, evaluate

warnings.filterwarnings("ignore")
NATIONAL = "Nasionál (mediana)"


# ==========================================================================
# A. FOLIN - TIME SERIES
# ==========================================================================
def prepare_series(s):
    """Fulan-fulan regular; gap ki'ik (<=3 fulan) interpola; foti parte kontínuu ikus."""
    s = s.sort_index().asfreq("MS")
    s = s.interpolate(limit=3, limit_area="inside")
    # Buka segmentu ikus ne'ebé la iha NaN
    isna = s.isna()
    if isna.any():
        last_nan = isna[isna].index.max()
        s = s[s.index > last_nan]
    return s


def fit_hw(y_log):
    return ExponentialSmoothing(y_log, trend="add", damped_trend=True, seasonal="add",
                                seasonal_periods=12, initialization_method="estimated").fit()


def fit_sarima_price(y_log, grid=True):
    cands = [((0, 1, 1), (0, 1, 1, 12)), ((1, 1, 0), (1, 0, 0, 12))] if grid else [((0, 1, 1), (0, 1, 1, 12))]
    best = None
    for o, so in cands:
        try:
            r = SARIMAX(y_log, order=o, seasonal_order=so, enforce_stationarity=False,
                        enforce_invertibility=False).fit(disp=False)
            if best is None or r.aic < best[0].aic:
                best = (r, o, so)
        except Exception:  # noqa: BLE001
            pass
    return best


def forecast_price_models(train, steps, grid):
    """Fila fali dict {model: (mean, lower, upper)} iha eskala folin (la'ós log)."""
    y = np.log(train)
    out = {"Naive": (np.repeat(train.iloc[-1], steps), None, None),
           "Seasonal naive": (np.resize(train.iloc[-12:].values, steps), None, None)}
    try:
        hw = fit_hw(y)
        out["Holt-Winters"] = (np.exp(hw.forecast(steps)).values, None, None)
    except Exception:  # noqa: BLE001
        pass
    best = fit_sarima_price(y, grid)
    if best:
        fc = best[0].get_forecast(steps)
        ci = fc.conf_int(alpha=0.05)
        out["SARIMA"] = (np.exp(fc.predicted_mean).values, np.exp(ci.iloc[:, 0]).values,
                         np.exp(ci.iloc[:, 1]).values)
    return out


def run_price_ts(prices, nat):
    H, T = config.PRICE_FORECAST_HORIZON, config.PRICE_TEST_MONTHS
    global_last = nat["date"].max()
    ev_rows, test_rows, fc_rows = [], [], []
    tasks = [(s, NATIONAL, g.set_index("date")["price"]) for s, g in nat.groupby("series")]
    tasks += [(s, mk, g.set_index("date")["price"]) for (s, mk), g in prices.groupby(["series", "market"])]
    for series, loc, raw in tasks:
        s = prepare_series(raw)
        if len(s) < config.MIN_PRICE_OBS + T or s.index.max() < global_last - pd.DateOffset(months=12):
            continue          # série badak demais ka la atualiza ona
        grid = loc == NATIONAL           # grid search ba nasionál deit (lalais)
        train, test = s.iloc[:-T], s.iloc[-T:]
        res = forecast_price_models(train, T, grid)
        scores = {}
        for m, (mean, _, _) in res.items():
            sc = evaluate(test.values, mean)
            scores[m] = sc["RMSE"]
            ev_rows.append({"series": series, "location": loc, "model": m, **sc})
            test_rows += [{"series": series, "location": loc, "model": m, "date": d, "actual": a,
                           "predicted": round(float(v), 3)} for d, a, v in zip(test.index, test.values, mean)]
        best_model = min(scores, key=scores.get)
        # Refit ho dadus hotu -> previzaun futuru
        full = forecast_price_models(s, H, grid)
        dates = pd.date_range(s.index.max() + pd.DateOffset(months=1), periods=H, freq="MS")
        sar = full.get("SARIMA")
        for m, (mean, lo, hi) in full.items():
            if m not in ("SARIMA", "Holt-Winters"):
                continue
            # Intervalu: SARIMA iha rasik; Holt-Winters "empresta" largura relativu husi SARIMA
            if lo is None and sar is not None:
                lo, hi = mean * sar[1] / sar[0], mean * sar[2] / sar[0]
            for i, d in enumerate(dates):
                fc_rows.append({"series": series, "location": loc, "model": m, "date": d,
                                "forecast": round(float(mean[i]), 3),
                                "lower_95": round(float(lo[i]), 3) if lo is not None else None,
                                "upper_95": round(float(hi[i]), 3) if hi is not None else None,
                                "best_model": m == best_model})
        print(f"   {series:30s} {loc:20s} di'ak liu: {best_model}")
    return pd.DataFrame(ev_rows), pd.DataFrame(test_rows), pd.DataFrame(fc_rows)


# ==========================================================================
# B. FOLIN - REGRESSION (1-step ahead)
# ==========================================================================
PRICE_FEATURES = ["lag1", "lag2", "lag3", "lag12", "mom_change", "month_sin", "month_cos",
                  "lean_season", "rain_anom_6m_lag1"]


def run_price_regression(nat):
    d = nat.sort_values(["series", "date"]).copy()
    d["y"] = np.log(d["real_price"])
    g = d.groupby("series")["y"]
    for k in (1, 2, 3, 12):
        d[f"lag{k}"] = g.shift(k)
    d["mom_change"] = d["lag1"] - d["lag2"]
    d["month_sin"] = np.sin(2 * np.pi * d["month"] / 12)
    d["month_cos"] = np.cos(2 * np.pi * d["month"] / 12)
    d["rain_anom_6m_lag1"] = d.groupby("series")["rain_anom_6m"].shift(1) if "rain_anom_6m" in d else 0
    dummies = pd.get_dummies(d["commodity"], prefix="c", dtype=int)
    d = pd.concat([d, dummies], axis=1)
    feats = PRICE_FEATURES + list(dummies.columns)
    d = d.dropna(subset=feats + ["y"])
    # Série ida-idak: 12 fulan ikus = teste
    d["rank_from_end"] = d.groupby("series")["date"].rank(ascending=False)
    train, test = d[d["rank_from_end"] > config.PRICE_TEST_MONTHS], d[d["rank_from_end"] <= config.PRICE_TEST_MONTHS]

    models = {"Ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
              "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                                                     random_state=config.RANDOM_STATE, n_jobs=-1)}
    rows, preds, interp = [], [], {}
    # Baseline naive: folin fulan tuir mai = folin fulan ne'e
    for name in ["Naive (lag1)"] + list(models):
        if name == "Naive (lag1)":
            p = test["lag1"].values
        else:
            models[name].fit(train[feats], train["y"])
            p = models[name].predict(test[feats])
        t = test.assign(pred=np.exp(p), actual=np.exp(test["y"]))
        for s, gg in t.groupby("series"):
            rows.append({"series": s, "model": name, **evaluate(gg["actual"], gg["pred"])})
        preds += [{"series": r.series, "model": name, "date": r.date, "actual": round(r.actual, 3),
                   "predicted": round(r.pred, 3)} for r in t.itertuples()]
    ridge = models["Ridge"][-1]
    interp["ridge_coef"] = dict(zip(feats, np.round(ridge.coef_, 4)))
    interp["rf_importance"] = dict(zip(feats, np.round(models["Random Forest"].feature_importances_, 4)))
    return pd.DataFrame(rows), pd.DataFrame(preds), interp


# ==========================================================================
# C. PRODUSAUN
# ==========================================================================
PROD_FEATURES = ["year", "wet_season_rain_mm", "wet_season_dry_days", "mean_temp_c"]


def _holt(y):
    return ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()


def run_production(prod):
    ev, fc, loo_rows, coefs = [], [], [], {}
    K = config.PRODUCTION_FORECAST_YEARS
    for crop, g in prod.groupby("crop"):
        g = g.dropna(subset=["production_t"]).sort_values("year")
        y = g.set_index("year")["production_t"].astype(float)
        if len(y) < 10:
            continue
        # --- Time series hold-out 3 tinan ikus
        tr, te = y.iloc[:-3], y.iloc[-3:]
        preds = {"Naive": np.repeat(tr.iloc[-1], 3)}
        z = np.polyfit(tr.index, tr.values, 1)
        preds["Linear trend"] = np.polyval(z, te.index)
        try:
            preds["Holt (damped)"] = _holt(tr.values).forecast(3)
        except Exception:  # noqa: BLE001
            pass
        for m, p in preds.items():
            ev.append({"crop": crop, "model": m, "validation": "hold-out 3 tinan", **evaluate(te.values, p)})

        # --- Regression (LOOCV)
        gg = g.dropna(subset=PROD_FEATURES)
        if len(gg) >= 10:
            X, yy = gg[PROD_FEATURES], gg["production_t"]
            reg = make_pipeline(StandardScaler(), Ridge(alpha=2.0))
            p = cross_val_predict(reg, X, yy, cv=LeaveOneOut())
            ev.append({"crop": crop, "model": "Ridge regression (klima)", "validation": "LOOCV", **evaluate(yy, p)})
            base = np.array([yy.drop(yy.index[i]).mean() for i in range(len(yy))])
            ev.append({"crop": crop, "model": "Baseline (mean)", "validation": "LOOCV", **evaluate(yy, base)})
            loo_rows += [{"crop": crop, "year": int(a), "actual": float(b), "predicted": round(float(c), 1)}
                         for a, b, c in zip(gg["year"], yy, p)]
            reg.fit(X, yy)
            coefs[crop] = dict(zip(PROD_FEATURES, np.round(reg[-1].coef_, 1)))
            # Senáriu klima ba tinan futuru
            scen = {
                "Normál": {"wet_season_rain_mm": X["wet_season_rain_mm"].median(),
                           "wet_season_dry_days": X["wet_season_dry_days"].median()},
                "Maran (El Niño)": {"wet_season_rain_mm": X["wet_season_rain_mm"].quantile(0.1),
                                    "wet_season_dry_days": X["wet_season_dry_days"].quantile(0.9)},
                "Udan barak (La Niña)": {"wet_season_rain_mm": X["wet_season_rain_mm"].quantile(0.9),
                                         "wet_season_dry_days": X["wet_season_dry_days"].quantile(0.1)},
            }
            last_year = int(y.index.max())
            for name, sv in scen.items():
                for h in range(1, K + 1):
                    row = {"year": last_year + h, "mean_temp_c": X["mean_temp_c"].iloc[-5:].mean(), **sv}
                    fc.append({"crop": crop, "year": last_year + h, "model": f"Regression — {name}",
                               "forecast": round(float(reg.predict(pd.DataFrame([row])[PROD_FEATURES])[0]), 0)})

        # --- Holt forecast ho intervalu aproximadu (residual std * sqrt(h))
        try:
            h_full = _holt(y.values)
            sd = np.std(y.values - h_full.fittedvalues)
            for h, v in enumerate(h_full.forecast(K), start=1):
                fc.append({"crop": crop, "year": int(y.index.max()) + h, "model": "Holt (damped)",
                           "forecast": round(float(v), 0), "lower_95": round(float(max(v - 1.96 * sd * np.sqrt(h), 0)), 0),
                           "upper_95": round(float(v + 1.96 * sd * np.sqrt(h)), 0)})
        except Exception:  # noqa: BLE001
            pass
    return pd.DataFrame(ev), pd.DataFrame(fc), pd.DataFrame(loo_rows), coefs


# ==========================================================================
def run():
    print("=" * 60)
    print("AGRI MODELING: forecast folin + produsaun")
    print("=" * 60)
    P, O = config.DATA_PROCESSED, config.DATA_OUTPUTS
    prices = pd.read_csv(P / "prices_market_monthly.csv", parse_dates=["date"])
    nat = pd.read_csv(P / "prices_national_monthly.csv", parse_dates=["date"])
    prod = pd.read_csv(P / "production_annual.csv")

    print("\n[A] Price time series ...")
    p_ev, p_test, p_fc = run_price_ts(prices, nat)
    print("\n[B] Price regression ...")
    r_ev, r_pred, r_interp = run_price_regression(nat)
    print("\n[C] Production ...")
    pr_ev, pr_fc, pr_loo, pr_coef = run_production(prod)

    p_ev.to_csv(O / "price_eval.csv", index=False)
    p_test.to_csv(O / "price_test_predictions.csv", index=False)
    p_fc.to_csv(O / "price_forecasts.csv", index=False)
    r_ev.to_csv(O / "price_regression_eval.csv", index=False)
    r_pred.to_csv(O / "price_regression_predictions.csv", index=False)
    pr_ev.to_csv(O / "production_eval.csv", index=False)
    pr_fc.to_csv(O / "production_forecasts.csv", index=False)
    pr_loo.to_csv(O / "production_loocv_predictions.csv", index=False)

    summary = {
        "price_ts_national": p_ev[p_ev["location"] == NATIONAL].groupby("model")[["MAE", "RMSE", "sMAPE_%"]]
        .mean().round(4).to_dict(orient="index"),
        "price_ts_all_series": p_ev.groupby("model")[["MAE", "RMSE", "sMAPE_%"]].mean().round(4).to_dict(orient="index"),
        "price_ts_best_model_counts": p_ev.loc[p_ev.groupby(["series", "location"])["RMSE"].idxmin(), "model"]
        .value_counts().to_dict(),
        "price_regression": r_ev.groupby("model")[["MAE", "RMSE", "sMAPE_%"]].mean().round(4).to_dict(orient="index"),
        "price_regression_interpretation": r_interp,
        "production_eval": pr_ev.groupby(["model", "validation"])[["MAE", "RMSE", "R2", "sMAPE_%"]].mean()
        .round(2).reset_index().to_dict(orient="records"),
        "production_ridge_coef": pr_coef,
    }
    (O / "agri_metrics.json").write_text(json.dumps(summary, indent=2, default=_to_native))
    print("\nFolin (TS, média série hotu):\n", pd.DataFrame(summary["price_ts_all_series"]).T)
    print("\nFolin (regression 1-step):\n", pd.DataFrame(summary["price_regression"]).T)
    print("\nProdusaun:\n", pd.DataFrame(summary["production_eval"]))
    return summary


if __name__ == "__main__":
    run()
