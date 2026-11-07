import argparse
import time
from. import (agri_collection, agri_eda, agri_models, agri_preprocessing, data_collection, eda, models, preprocessing)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--skip-collect", action="store_true")
    ap.add_argument("--source", choices=["open-meteo", "nasa"], default="open-meteo")
    ap.add_argument("--only", choices=["climate", "agri"])
    ap.add_argument("--skip", nargs="*", default=[], choices=["municipality_info", "municipal_production", "wfp_prices", "faostat", "cpi", "climate", "weather", "world_bank", "news"])
    args = ap.parse_args()
    t0 = time.time()
    skip_set = set(args.skip)
    if args.only in (None, "climate"):
        if not args.skip_collect:
            data_collection.run(demo=args.demo, source=args.source, skip=skip_set)
        preprocessing.run()
        eda.run()
        models.run()
    if args.only in (None, "agri"):
        if not args.skip_collect:
            agri_collection.run(demo_mode=args.demo, skip=skip_set)
        agri_preprocessing.run()
        agri_eda.run()
        agri_models.run()
    print(f"\nPipeline remata iha {time.time() - t0:.0f} segundu.")
    print("Loke dashboard: streamlit run dashboard/app.py")

if __name__ == "__main__":
    main()