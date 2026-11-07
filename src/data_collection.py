"""
data_collection.py

PASSU 1: DATA COLLECTION (Rekolla dadus)

Fonte dadus 5 (5 data sources):
    1. Open-Meteo Historical Weather API -> klima loron-loron
    2. NASA POWER API -> fonte alternativa
    3. World Bank Open Data API -> indikadór agrikultura anuál
    4. Web scraping (Wikipedia) -> populasaun no área munisípiu
    5. RSS feeds (Google News, ReliefWeb) -> notísia

Support SKIP: --skip municipality_info climate weather world_bank news
"""

import argparse
import json
import time
from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests

from. import config, sample_data

def http_get(url, params=None, retries=3, backoff=3):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=config.HTTP_HEADERS,
                             timeout=config.REQUEST_TIMEOUT)
            if r.status_code == 429:
                print("! Rate limit (429). Hein 65 s...")
                time.sleep(65)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_err = e
            print(f"! Koko {attempt}/{retries} falla: {e}")
            time.sleep(backoff * attempt)
    raise last_err or requests.HTTPError("Rate limit la remata")

def fetch_open_meteo(name, lat, lon, start, end):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(config.OPEN_METEO_DAILY_VARS),
        "timezone": "Asia/Dili",
    }
    js = http_get(config.OPEN_METEO_URL, params=params).json()
    df = pd.DataFrame(js["daily"]).rename(columns={"time": "date"})
    df["municipality"] = name
    return df

def fetch_nasa_power(name, lat, lon, start, end):
    params = {
        "parameters": ",".join(config.NASA_POWER_PARAMS),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": start.replace("-", ""),
        "end": end.replace("-", ""),
        "format": "JSON",
    }
    js = http_get(config.NASA_POWER_URL, params=params).json()
    p = js["properties"]["parameter"]
    df = pd.DataFrame(p)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999, pd.NA).reset_index(names="date")
    df = df.rename(columns={
        "T2M": "temperature_2m_mean", "T2M_MAX": "temperature_2m_max", "T2M_MIN": "temperature_2m_min",
        "PRECTOTCORR": "precipitation_sum", "RH2M": "relative_humidity_2m_mean",
        "ALLSKY_SFC_SW_DWN": "shortwave_radiation_sum",
    })
    df["municipality"] = name
    return df

def collect_weather(source="open-meteo", start=config.START_DATE, end=config.END_DATE):
    fetch = fetch_open_meteo if source == "open-meteo" else fetch_nasa_power
    cache_dir = config.DATA_RAW / f"weather_{source}"
    cache_dir.mkdir(exist_ok=True)
    frames, ok, fails_in_row = [], 0, 0
    for name, info in config.MUNICIPALITIES.items():
        if fails_in_row >= 2 and ok == 0:
            print(" => Falla dala 2 tuir malu. Internet/API karik tun - para.")
            break
        cache = cache_dir / f"{name}.csv"
        old = pd.read_csv(cache) if cache.exists() else pd.DataFrame()
        fetch_start = start
        if not old.empty:
            fetch_start = (pd.to_datetime(old["date"]).max() + pd.Timedelta(days=1)).date().isoformat()
        if fetch_start > end:
            print(f" - {name}: cache atualizadu ona")
            frames.append(old); ok += 1
            continue
        print(f" - {source}: {name} {fetch_start} -> {end}")
        try:
            new = fetch(name, info["lat"], info["lon"], fetch_start, end)
            combined = pd.concat([old, new], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"]).dt.date.astype(str)
            combined = combined.drop_duplicates(subset=["date"], keep="last")
            combined.to_csv(cache, index=False)
            frames.append(combined); ok += 1; fails_in_row = 0
        except Exception as e:
            fails_in_row += 1
            print(f" x La konsege hetan {name}: {e}")
            if not old.empty:
                frames.append(old)
        time.sleep(2.0)

    if len(frames) == 0:
        print(" => Weather API falla hotu. Uza dadus DEMO.")
        return sample_data.generate_weather_daily(start, end), "demo"
    status = "live" if ok == len(config.MUNICIPALITIES) else "partial"
    return pd.concat(frames, ignore_index=True), status

def fetch_world_bank(indicator_code):
    url = config.WORLD_BANK_URL.format(indicator=indicator_code)
    js = http_get(url, params={"format": "json", "per_page": 200}).json()
    if len(js) < 2 or js[1] is None:
        return pd.DataFrame()
    return pd.DataFrame([{"year": int(row["date"]), "value": row["value"]} for row in js[1]])

def collect_world_bank():
    frames = []
    for code, short in config.WORLD_BANK_INDICATORS.items():
        print(f" - World Bank: {code} ({short})")
        try:
            df = fetch_world_bank(code)
            df["indicator"] = short
            frames.append(df)
        except Exception as e:
            print(f" x Falla: {e}")
    if not frames:
        return sample_data.generate_world_bank(), "demo"
    return pd.concat(frames, ignore_index=True)[["year", "indicator", "value"]], "live"

def scrape_municipalities():
    from bs4 import BeautifulSoup
    html = http_get(config.WIKI_MUNICIPALITIES_URL).text
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", class_="wikitable")
    for t in tables:
        header = t.get_text(" ", strip=True).lower()
        if "population" in header and "area" in header:
            df = pd.read_html(StringIO(str(t)))[0]
            df.columns = [" ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in df.columns]
            return df
    raise ValueError("Tabela munisípiu la hetan")

def collect_municipality_info():
    print(" - Web scraping: Wikipedia municipalities table")
    try:
        return scrape_municipalities(), "live"
    except Exception as e:
        print(f" x Scraping falla: {e} -> uza DEMO")
        return sample_data.generate_municipality_info(), "demo"

def fetch_rss(feed_name, url):
    import feedparser
    parsed = feedparser.parse(url, agent=config.HTTP_HEADERS["User-Agent"])
    rows = []
    for e in parsed.entries:
        rows.append({
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "published": e.get("published", e.get("updated", "")),
            "summary": e.get("summary", ""),
            "feed": feed_name,
        })
    return pd.DataFrame(rows)

def collect_news():
    frames = []
    for name, url in config.RSS_FEEDS.items():
        print(f" - RSS: {name}")
        try:
            df = fetch_rss(name, url)
            print(f" {len(df)} artigu")
            if len(df):
                frames.append(df)
        except Exception as e:
            print(f" x RSS falla: {e}")
    if not frames:
        return sample_data.generate_news(), "demo"
    return pd.concat(frames, ignore_index=True), "live"

def load_faostat_if_available():
    if config.FAOSTAT_MANUAL_FILE.exists():
        print(f" - FAOSTAT: hetan {config.FAOSTAT_MANUAL_FILE.name}")
        return pd.read_csv(config.FAOSTAT_MANUAL_FILE)
    print(" - FAOSTAT: la iha file manuál (opsionál)")
    return None

def run(demo=False, source="open-meteo", skip=None):
    print("=" * 60)
    print("DATA COLLECTION - Smart Agriculture Monitoring Timor-Leste")
    print("=" * 60)
    skip = set(skip or [])
    if skip:
        print(f" ⏭️ Skip requested: {', '.join(skip)}")

    status = {}

    def load_existing(path, generator):
        if path.exists():
            print(f" ⏭️ SKIP -> pakai existing {path.name} ({len(pd.read_csv(path))} rows)")
            return pd.read_csv(path), "skipped-existing"
        else:
            print(f" File {path.name} belum ada, pakai DEMO/generator")
            return generator(), "demo"

    if demo:
        weather, status["weather"] = sample_data.generate_weather_daily(), "demo"
        wb, status["world_bank"] = sample_data.generate_world_bank(), "demo"
        muni, status["municipality_info"] = sample_data.generate_municipality_info(), "demo"
        news, status["news"] = sample_data.generate_news(), "demo"
    else:
        # WEATHER / CLIMATE
        if "climate" in skip or "weather" in skip:
            weather_path = config.DATA_RAW / "weather_daily.csv"
            weather, status["weather"] = load_existing(weather_path, lambda: sample_data.generate_weather_daily())
        else:
            weather, status["weather"] = collect_weather(source)

        # WORLD BANK
        if "world_bank" in skip:
            wb_path = config.DATA_RAW / "worldbank_tls.csv"
            wb, status["world_bank"] = load_existing(wb_path, lambda: sample_data.generate_world_bank())
        else:
            wb, status["world_bank"] = collect_world_bank()

        # MUNICIPALITY_INFO - INI YANG LU MAU SKIP
        if "municipality_info" in skip:
            print(" ⏭️ SKIP municipality_info - pakai file REAL existing!")
            muni_path = config.DATA_RAW / "municipality_info.csv"
            if muni_path.exists():
                muni = pd.read_csv(muni_path)
                status["municipality_info"] = "skipped-existing"
                print(f" -> kept: {len(muni)} rows dari {muni_path.name}")
            else:
                print(" -> file belum ada, coba scrape / demo")
                muni, status["municipality_info"] = collect_municipality_info()
        else:
            muni, status["municipality_info"] = collect_municipality_info()

        # NEWS
        if "news" in skip:
            news_path = config.DATA_RAW / "news_rss.csv"
            news, status["news"] = load_existing(news_path, lambda: sample_data.generate_news())
        else:
            news, status["news"] = collect_news()

        fao = load_faostat_if_available()
        if fao is not None:
            fao.to_csv(config.DATA_RAW / "faostat_tls_crops_copy.csv", index=False)

    # Simpan hanya yang tidak di-skip
    weather_path = config.DATA_RAW / "weather_daily.csv"
    if "climate" not in skip and "weather" not in skip:
        weather.to_csv(weather_path, index=False)
    elif not weather_path.exists():
        weather.to_csv(weather_path, index=False)

    wb_path = config.DATA_RAW / "worldbank_tls.csv"
    if "world_bank" not in skip:
        wb.to_csv(wb_path, index=False)
    elif not wb_path.exists():
        wb.to_csv(wb_path, index=False)

    muni_path = config.DATA_RAW / "municipality_info.csv"
    if "municipality_info" not in skip:
        muni.to_csv(muni_path, index=False)
    elif not muni_path.exists():
        muni.to_csv(muni_path, index=False)

    news_path = config.DATA_RAW / "news_rss.csv"
    if "news" not in skip:
        news.to_csv(news_path, index=False)
    elif not news_path.exists():
        news.to_csv(news_path, index=False)

    # Merge dengan metadata agri jika ada
    meta_path = config.METADATA_FILE
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text())
            if "agri_last_updated_utc" in existing:
                merged_status = {**existing.get("status", {}), **status}
                meta = existing
                meta["status"] = merged_status
                meta["last_updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                meta["weather_source"] = source
                meta.setdefault("rows", {}).update({"weather": len(weather), "world_bank": len(wb), "news": len(news)})
                meta["period"] = [config.START_DATE, config.END_DATE]
                meta_path.write_text(json.dumps(meta, indent=2))
                print("\nRezumu:", json.dumps(meta, indent=2))
                return meta
        except:
            pass

    meta = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "weather_source": source,
        "status": status,
        "rows": {"weather": len(weather), "world_bank": len(wb), "news": len(news)},
        "period": [config.START_DATE, config.END_DATE],
    }
    config.METADATA_FILE.write_text(json.dumps(meta, indent=2))
    print("\nRezumu:", json.dumps(meta, indent=2))
    return meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Rekolla dadus agrikultura/klima Timor-Leste")
    ap.add_argument("--demo", action="store_true", help="Uza dadus sintétiku (offline)")
    ap.add_argument("--source", choices=["open-meteo", "nasa"], default="open-meteo")
    ap.add_argument("--skip", nargs="*", default=[], help="Skip: municipality_info climate weather world_bank news")
    args = ap.parse_args()
    run(demo=args.demo, source=args.source, skip=set(args.skip))