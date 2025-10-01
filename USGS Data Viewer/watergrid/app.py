from flask import Flask, render_template, jsonify
import json
import os
import threading
import atexit
from datetime import datetime, timedelta, timezone

import pandas as pd
import dataretrieval.nwis as nwis
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, static_folder="static", template_folder="templates")

# Hudson River Estuary Sites - Main channel and major tributaries from Troy to NYC
SITE_NUMBERS = [
    "01358000",  # Hudson River at Green Island NY (Troy area) - 42.752°N, -73.689°W
    "01362200",  # Esopus Creek at Allaben NY (tributary) - 42.117°N, -74.380°W
    "01360640",  # Valatie Kill near Nassau NY (tributary) - 42.552°N, -73.591°W
    "01372058",  # Hudson River below Poughkeepsie NY - 41.652°N, -73.953°W
    "01372900",  # Sprout Creek near Fishkill Plains NY (tributary) - 41.597°N, -73.844°W
    "01367625",  # Wallkill River at Sparta NJ (tributary) - 41.040°N, -74.630°W
    "01374680",  # Hudson River south of Hastings-on-Hudson, NY - 40.988°N, -73.887°W
    "01376520",  # Hudson River at Pier 25 at New York NY - 40.722°N, -74.016°W
]

PARAMETER_CODES = [
    "00010",  # Temperature, water (°C)
    "00011",  # Temperature, air (°C)
    "00300",  # Dissolved oxygen (mg/L)
    "00301",  # Dissolved oxygen, percent saturation
    "62620",  # Gage height (ft)
    "62614",  # Tide stage, feet
    "00480",  # Salinity, water (ppt)
    "63680",  # Turbidity, water (NTU)
    "82362",  # Turbidity, FNU
    "00060",  # Discharge, streamflow (cfs)
]

COLUMN_NAME_MAP = {
    "00010": "Water Temperature (°C)",
    "00011": "Air Temperature (°C)",
    "00020": "Air Temperature (°C)",
    "00036": "Specific Conductance (µS/cm)",
    "00045": "Precipitation (inches)",
    "00052": "Turbidity (NTU)",
    "00095": "Specific Conductance (µS/cm @25°C)",
    "00300": "Dissolved Oxygen (mg/L)",
    "00301": "Dissolved Oxygen Saturation (%)",
    "00400": "pH (std units)",
    "00480": "Salinity (ppt)",
    "61727": "Salinity (ppt)",
    "62614": "Tide Stage (ft)",
    "62620": "Gage Height (ft)",
    "63680": "Turbidity (NTU)",
    "75969": "Chlorophyll a (µg/L)",
    "82127": "FDOM (ppb QSU)",
    "82362": "Turbidity (FNU)",
    "90860": "Battery Voltage (V)",
}

DATA_DIR = os.path.join(app.root_path, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "waterservices.usgs.gov.json")

DATA_LOCK = threading.Lock()
UPDATE_STATUS = {"last_success": None, "last_error": None}

scheduler = BackgroundScheduler(timezone="UTC")


def _shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def _clean_column_name(column: str) -> str:
    if column == "site_no":
        return column

    cleaned = column.replace("_hrecos", "")
    if cleaned.endswith("_cd"):
        return cleaned.replace("_cd", "_cd:")

    return COLUMN_NAME_MAP.get(cleaned, COLUMN_NAME_MAP.get(cleaned.replace("_cd", ""), cleaned))


def _format_datetime_column(df: pd.DataFrame) -> pd.DataFrame:
    if "datetime" in df.columns:
        df = df.rename(columns={"datetime": "Datetime"})
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
        df["Datetime"] = df["Datetime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def fetch_usgs_dataframe(start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
    end = end or datetime.now(timezone.utc)
    start = start or (end - timedelta(days=7))

    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")

    all_data = []
    
    for site_number in SITE_NUMBERS:
        try:
            df = nwis.get_record(
                sites=site_number,
                service="iv",
                start=start_date,
                end=end_date,
                parameterCd=PARAMETER_CODES,
            )

            if df is None or df.empty:
                print(f"  ⚠ Site {site_number}: No data available")
                continue

            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
            elif "datetime" not in df.columns:
                df = df.reset_index()

            # Keep site_no for this multi-site version
            if "site_no" in df.columns:
                df = df.rename(columns={"site_no": "Site"})
            
            df = df.rename(columns=_clean_column_name)
            df = _format_datetime_column(df)
            
            all_data.append(df)
            print(f"  ✓ Site {site_number}: {len(df)} records")
            
        except Exception as exc:
            print(f"  ✗ Site {site_number}: {exc}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all sites
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Sort by datetime and site
    if "Datetime" in combined_df.columns:
        combined_df = combined_df.sort_values(["Datetime", "Site"] if "Site" in combined_df.columns else ["Datetime"])
    
    return combined_df


def update_data_file() -> None:
    global UPDATE_STATUS

    print("Fetching latest USGS data…")
    try:
        df = fetch_usgs_dataframe()
        if df.empty:
            raise ValueError("USGS returned no data for the requested range")

        with DATA_LOCK:
            df.to_json(DATA_FILE, orient="records", date_format="iso", indent=4)

        UPDATE_STATUS = {
            "last_success": datetime.now(timezone.utc).isoformat() + "Z",
            "last_error": None,
        }
        print(f"✓ Saved {len(df)} records to {DATA_FILE}")
    except Exception as exc:  # pylint: disable=broad-except
        UPDATE_STATUS = {
            "last_success": UPDATE_STATUS.get("last_success"),
            "last_error": {
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }
        print(f"✗ Failed to refresh USGS data: {exc}")


def schedule_updates() -> None:
    if not scheduler.running:
        scheduler.add_job(
            update_data_file,
            "interval",
            minutes=15,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        scheduler.start()
        atexit.register(_shutdown_scheduler)


def ensure_data_available() -> None:
    if os.path.exists(DATA_FILE):
        return
    update_data_file()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sites")
def sites():
    """Return list of monitored sites"""
    return jsonify({"sites": SITE_NUMBERS})


@app.route("/site-info")
def site_info():
    """Return detailed information about each site including location"""
    try:
        # Fetch site information from USGS
        info_df, _ = nwis.get_info(sites=SITE_NUMBERS)
        
        # Build site info dictionary
        site_details = []
        for _, row in info_df.iterrows():
            site_details.append({
                "site_no": row["site_no"],
                "station_nm": row["station_nm"],
                "latitude": float(row["dec_lat_va"]),
                "longitude": float(row["dec_long_va"]),
            })
        
        return jsonify({"sites": site_details})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/data")
def data():
    try:
        ensure_data_available()
    except Exception as exc:  # pylint: disable=broad-except
        return (
            jsonify(
                {
                    "error": "Failed to refresh USGS data",
                    "message": str(exc),
                    "updateStatus": UPDATE_STATUS,
                }
            ),
            503,
        )

    if not os.path.exists(DATA_FILE):
        return (
            jsonify(
                {
                    "error": "USGS data file unavailable",
                    "message": "Automatic refresh has not produced a dataset yet.",
                    "updateStatus": UPDATE_STATUS,
                }
            ),
            503,
        )

    try:
        with DATA_LOCK:
            with open(DATA_FILE, "r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        response = jsonify(payload)
        if UPDATE_STATUS.get("last_success"):
            response.headers["X-Last-Update"] = UPDATE_STATUS["last_success"]
        last_error = UPDATE_STATUS.get("last_error")
        if isinstance(last_error, dict) and last_error.get("timestamp"):
            response.headers["X-Last-Error"] = last_error["timestamp"]
        return response
    except Exception as exc:  # pylint: disable=broad-except
        return (
            jsonify(
                {
                    "error": "Failed to load USGS data",
                    "message": str(exc),
                    "updateStatus": UPDATE_STATUS,
                }
            ),
            500,
        )


if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    schedule_updates()
    try:
        update_data_file()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Initial USGS data refresh failed: {exc}")


if __name__ == "__main__":
    print("Water Grid Application")
    print("=====================")
    print(f"Data output file: {DATA_FILE}")
    print("Scheduling background refresh every 15 minutes…")
    schedule_updates()
    ensure_data_available()
    print("\nStarting server on http://127.0.0.1:5000...")
    
    try:
        app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
    finally:
        _shutdown_scheduler()
        print("Scheduler stopped. Goodbye!")
