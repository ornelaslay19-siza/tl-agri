import argparse
import json
import os
from io import StringIO
import pandas as pd
from. import agri_sample_data as demo
from. import config
from.data_collection import http_get
from dotenv import load_dotenv
load_dotenv()

def fetch_wfp_prices():
    url = config.HDX_PACKAGE_API
    params = {"id": config.HDX_WFP_DATASET_ID}
    response = http_get(url, params=params)
    meta = response.json()
    resources = meta["result"]["resources"]
    csvs = [r for r in resources if str(r.get("format", "")).lower() == "csv" and "quickchart" not in (r.get("name", "") + r.get("url", "")).lower()]
    url = csvs[0].get("download_url") or csvs[0]["url"]
    return pd.read_csv(StringIO(http_get(url).text))

def collect_prices():
    print(" - WFP food prices (HDX)")
    try:
        return fetch_wfp_prices(), "live"
    except Exception as e:
        print(f" x Falla: {e}")
    if config.WFP_MANUAL_FILE.exists():
        return pd.read_csv(config.WFP_MANUAL_FILE), "manual"
    return demo.generate_wfp_prices(), "demo"

def collect_production():
    print(" - FAOSTAT production (QCL)")
    try:
        import faostat
        faostat.set_requests_args(username=os.getenv("FAOSTAT_USER"), password=os.getenv("FAOSTAT_PASSWORD"))
        df = faostat.get_data_df("QCL", pars={"area": [config.FAOSTAT_AREA_TLS], "item": list(config.FAOSTAT_ITEMS.keys()), "element": list(config.FAOSTAT_ELEMENTS.keys()), "year": list(range(1990, pd.Timestamp.today().year + 1))})
        element_map = {"Area harvested": "area_harvested_ha", "Yield": "yield_kg_ha", "Production": "production_t"}
        df["element"] = df["Element"].map(lambda e: next((v for k, v in element_map.items() if k in e), None))
        df["crop"] = df["Item"].map(lambda s: next((v for v in config.FAOSTAT_ITEMS.values() if v.split()[0].lower() in s.lower()), s))
        out = df.dropna(subset=["element"])[["crop", "Year", "element", "Value", "Unit"]]
        out.columns = ["crop", "year", "element", "value", "unit"]
        m = (out["element"] == "yield_kg_ha") & out["unit"].astype(str).str.contains("100 g")
        out.loc[m, "value"] = pd.to_numeric(out.loc[m, "value"]) / 10
        return out.drop(columns="unit"), "live"
    except Exception as e:
        print(f" x Falla: {e}")
    if config.FAOSTAT_MANUAL_FILE.exists():
        raw = pd.read_csv(config.FAOSTAT_MANUAL_FILE)
        element_map = {"Area harvested": "area_harvested_ha", "Yield": "yield_kg_ha", "Production": "production_t"}
        raw["element"] = raw["Element"].map(lambda e: next((v for k, v in element_map.items() if k in str(e)), None))
        raw["crop"] = raw["Item"].map(lambda s: next((v for v in config.FAOSTAT_ITEMS.values() if v.split()[0].lower() in str(s).lower()), s))
        out = raw.dropna(subset=["element"]).rename(columns={"Year": "year", "Value": "value"})
        m = (out["element"] == "yield_kg_ha") & out["Unit"].astype(str).str.contains("100 g")
        out.loc[m, "value"] = out.loc[m, "value"] / 10
        return out[["crop", "year", "element", "value"]], "manual"
    return demo.generate_faostat(), "demo"

def collect_cpi():
    print(" - World Bank CPI")
    try:
        url = config.WORLD_BANK_URL.format(indicator=config.WB_CPI_INDICATOR)
        js = http_get(url, params={"format": "json", "per_page": 200}).json()
        df = pd.DataFrame([{"year": int(r["date"]), "cpi": r["value"]} for r in js[1]]).dropna()
        if len(df):
            return df, "live"
    except Exception as e:
        print(f" x Falla: {e}")
    return demo.generate_cpi(), "demo"

def collect_municipal_production():
    print(" - Municipal production (manual file)")
    if config.MUNICIPAL_PRODUCTION_FILE.exists():
        return pd.read_csv(config.MUNICIPAL_PRODUCTION_FILE), "manual"
    return demo.generate_municipal_production(), "demo"

def run(demo_mode=False, skip=None):
    print("="*60)
    print("AGRICULTURE DATA COLLECTION")
    print("="*60)
    skip = set(skip or [])
    if skip:
        print(f" Skip: {', '.join(skip)}")

    if demo_mode:
        prices, sp = demo.generate_wfp_prices(), "demo"
        prod, sprod = demo.generate_faostat(), "demo"
        cpi, sc = demo.generate_cpi(), "demo"
        muni, sm = demo.generate_municipal_production(), "demo"
    else:
        if "wfp_prices" in skip:
            print(" SKIP WFP prices")
            prices_path = config.DATA_RAW / "wfp_prices_raw.csv"
            prices = pd.read_csv(prices_path) if prices_path.exists() else demo.generate_wfp_prices()
            sp = "skipped"
        else:
            prices, sp = collect_prices()

        if "faostat" in skip:
            print(" SKIP FAOSTAT")
            fao_path = config.DATA_RAW / "faostat_production_raw.csv"
            prod = pd.read_csv(fao_path) if fao_path.exists() else demo.generate_faostat()
            sprod = "skipped"
        else:
            prod, sprod = collect_production()

        if "cpi" in skip:
            print(" SKIP CPI")
            cpi_path = config.DATA_RAW / "cpi_raw.csv"
            cpi = pd.read_csv(cpi_path) if cpi_path.exists() else demo.generate_cpi()
            sc = "skipped"
        else:
            cpi, sc = collect_cpi()

        if "municipal_production" in skip:
            print(" SKIP municipal_production - pakai file REAL 58k ton!")
            muni_path = config.DATA_RAW / "municipal_production_raw.csv"
            if muni_path.exists():
                muni = pd.read_csv(muni_path)
                sm = "skipped-existing"
                print(f" -> kept: {len(muni)} rows")
            else:
                muni, sm = collect_municipal_production()
        else:
            muni, sm = collect_municipal_production()

    if "wfp_prices" not in skip:
        prices.to_csv(config.DATA_RAW / "wfp_prices_raw.csv", index=False)
    if "faostat" not in skip:
        prod.to_csv(config.DATA_RAW / "faostat_production_raw.csv", index=False)
    if "cpi" not in skip:
        cpi.to_csv(config.DATA_RAW / "cpi_raw.csv", index=False)
    if "municipal_production" not in skip:
        muni.to_csv(config.DATA_RAW / "municipal_production_raw.csv", index=False)

    meta = json.loads(config.METADATA_FILE.read_text()) if config.METADATA_FILE.exists() else {}
    meta.setdefault("status", {}).update({"prices": sp, "production": sprod, "cpi": sc, "municipal_production": sm})
    meta["agri_last_updated_utc"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    meta.setdefault("rows", {}).update({"prices": len(prices), "production": len(prod)})
    config.METADATA_FILE.write_text(json.dumps(meta, indent=2))
    print("Status:", {"prices": sp, "production": sprod, "cpi": sc, "municipal_production": sm})
    return meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[])
    args = ap.parse_args()
    run(demo_mode=args.demo, skip=set(args.skip))