#!/usr/bin/env python3
"""


What this script does:
1. Downloads USGS instantaneous values (IV) for a site and saves a JSON file.
   - Output filename: data_usgs_{site}.json

2. Downloads NOAA CO-OPS observations and tide predictions for a station and saves a JSON file.
   - We request water level, water temperature, hourly tide predictions, and high/low (hilo) events.
   - Because multiple NOAA sources can share the same timestamp, we collapse duplicate timestamps
     so saving to JSON does not fail.
   - Output filename: noaa_{station}_obs_pred.json

"""

# -------------------------
# Imports: bring in libraries
# -------------------------
# sys   -> handle command-line arguments
# numpy -> numerical helpers (we use np.nan)
# pandas-> data tables (DataFrame) and time handling
# dataretrieval.nwis -> helper library to query USGS NWIS services
# noaa_coops.Station   -> helper class to query NOAA CO-OPS API
import sys
import numpy as np
import pandas as pd
import dataretrieval.nwis as nwis
from noaa_coops import Station

# -------------------------
# Configuration & mapping
# -------------------------
# POSSIBLE_NULLS: values that represent missing or bad data in some datasets.
# We replace them with proper NaN values so pandas can handle them.
POSSIBLE_NULLS = ["", "NaN", "null", "None", "--", "999999", 999999, -999999, "-999999"]

# parameter_map: maps USGS parameter codes (strings like "00010") to friendly names.
# This makes the output columns easier to read (e.g., "water_temperature" instead of "00010").
parameter_map = {
    "00010": "water_temperature", #pulling water temp
    "00011": "air_temperature",    #pulling air temp
    "00300": "dissolved_oxygen",    #how much o2 is in water
    "00301": "dissolved_oxygen_saturation", #% saturation of o2
    "00065": "gage_height",         #river height in feet
    "00480": "salinity",            #amount of dissolved salts present in water
    "00095": "specific_conductance_at_25", #electric conductivity (just indicates salt/ion levels at 25C)
    "62623": "tide_stage_feet", #measured tide in ft 
    "63680": "turbidity_ntu", #how cloudy the water is 
    "82362": "turbidity_fnu",#different turbidity method 
    "00060": "discharge_cfs",#streamflow. how much water moves past the station per second
}

# -------------------------
# Helper functions
# -------------------------
def noaa_date(x):
    """
    NOAA's API expects dates in YYYYMMDD format.
    This helper converts many common formats (like "YYYY-MM-DD") to YYYYMMDD.
    """
    return pd.to_datetime(x).strftime("%Y%m%d")


def ensure_unique_columns(df):
    """
    If the DataFrame has duplicate column names, json() fails.
    This helper keeps only the first occurrence of any duplicate column name.
    """
    if df is None:
        return df
    return df.loc[:, ~df.columns.duplicated()]


def ensure_datetime_index(df):
    """
    Try to make the DataFrame use a DatetimeIndex (index made of timestamps).
    Many APIs put the time in a column; this function looks for common 'time'/'date'
    column names and sets that column as the index (converted to datetimes).
    If that fails, it also tries the first column as a fallback.
    """
    if df is None or df.empty:
        return df

    # If already a datetime index, nothing to do
    if isinstance(df.index, pd.DatetimeIndex):
        return df

    # Look for any column name containing 'time' or 'date'
    time_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
    if time_cols:
        try:
            df.index = pd.to_datetime(df[time_cols[0]], errors="coerce")
            df = df.drop(columns=[time_cols[0]], errors="ignore")
            return df
        except Exception:
            # if conversion fails, fall through to the fallback
            pass

    # Fallback: try converting the first column to datetime
    try:
        first = df.columns[0]
        maybe = pd.to_datetime(df[first], errors="coerce")
        if maybe.notna().any():
            df.index = maybe
            df = df.drop(columns=[first], errors="ignore")
            return df
    except Exception:
        pass

    # If nothing worked, return as-is
    return df

# -------------------------
# USGS fetch function
# -------------------------
def fetch_usgs(site="01376520", start="2025-09-21", end="2025-09-28"):
    """
    Fetch USGS instantaneous-values (IV) data for `site` between `start` and `end`.
    Saves the result to data_usgs_{site}.json and returns the DataFrame.

    - site: USGS site number (string like "01376520")
    - start / end: dates in "YYYY-MM-DD" (or other parseable) format
    """
    site = str(site)
    print(f"[USGS] Requesting site {site} {start} → {end}")

    # Ask the dataretrieval library for NWIS IV records for this site and date range.
    # If the request fails, print the error and return an empty DataFrame.
    try:
        df = nwis.get_record(sites=site, service="iv", start=start, end=end)
    except Exception as exc:
        print("[USGS] request error:", exc)
        return pd.DataFrame()

    # Rename known parameter codes to friendly names using parameter_map.
    # Example: "00010" -> "water_temperature"
    df = df.rename(
        columns=lambda c: parameter_map.get(
            c.replace("_hrecos", "").replace("_cd", ""),  # normalize field names
            c.replace("_hrecos", "").replace("_cd", "")
        )
    )

    # Replace sentinel/missing values with true NaN, then forward/backfill
    # so small gaps can be filled by nearby measurements.
    df = df.replace(POSSIBLE_NULLS, np.nan)
    for col in df.columns:
        try:
            df[col] = df[col].ffill().bfill()
        except Exception:
            # some columns may be non-fillable; ignore those
            pass

    # Remove columns we don't want (like battery_voltage or site_no), and drop columns entirely empty
    df = df.drop(columns=[c for c in ["battery_voltage", "site_no"] if c in df.columns], errors="ignore")
    df = df.dropna(axis="columns", how="all")

    # Remove flag columns (ending with "_cd") that don't have matching data columns.
    # Flags are metadata, we only keep them if the main data column exists.
    flag_cols = [c for c in df.columns if c.endswith("_cd")]
    orphans = [c for c in flag_cols if c[:-3] not in df.columns]
    if orphans:
        df = df.drop(columns=orphans, errors="ignore")

    # Ensure column names are unique (prevents errors when saving to JSON)
    df = ensure_unique_columns(df)

    # Print a small preview if common columns (like salinity or temperature) are present
    preview = [
        c for c in ["salinity", "specific_conductance_at_25", "water_temperature", "gage_height"]
        if c in df.columns
    ]
    if preview:
        print("[USGS] preview columns:", preview)
        print(df[preview].head(10))

    # Try to make the DataFrame index a datetime index, and set timezone to UTC if needed
    df = ensure_datetime_index(df)
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is None:
        try:
            df.index = df.index.tz_localize("UTC")
        except Exception:
            # if timezone localization fails, continue without failing
            pass

    # Add a prefix so USGS columns are easy to identify in outputs
    if not df.empty:
        df = df.add_prefix("usgs_")

    # Save cleaned USGS data to JSON
    out = f"data_usgs_{site}.json"
    try:
        df.to_json(out, indent=2, date_format="iso")
        print(f"[USGS] saved {out} (shape: {df.shape})")
    except Exception as exc:
        print("[USGS] save error:", exc)

    return df



#water level- observed tide high in ft
# water temp- water temp measured at the station in celsius 
#tide level prediction - future tide predicitions in ft
#hilo predicitions - high and low tide events + height in ft  


# -------------------------
# NOAA helpers: tidy and hilo
# -------------------------
def tidy_noaa(table_like, name):
    """
    Standardize NOAA table-like results into a single-column DataFrame with a datetime index.
    - table_like: the raw response from noaa_coops (often list/dict or DataFrame)
    - name: friendly column name to use for the data values (e.g., "water_level")
    """
    if table_like is None:
        # return an empty DataFrame with a named column so callers can join/concatenate safely
        return pd.DataFrame(columns=[name]).set_index(pd.Index([]))

    # Ensure we have a DataFrame
    tbl = pd.DataFrame(table_like) if not isinstance(table_like, pd.DataFrame) else table_like.copy()
    if tbl.empty:
        return pd.DataFrame(columns=[name]).set_index(pd.Index([]))

    # Detect common time column names: 't' (NOAA uses 't') or 'time'
    if "t" in tbl.columns:
        time = tbl["t"]
    elif "time" in tbl.columns:
        time = tbl["time"]
    else:
        # otherwise reset the index and assume the first column is time
        tbl = tbl.reset_index()
        time = tbl.iloc[:, 0]

    # Detect common value column names: 'v' (NOAA uses 'v') or 'value'
    if "v" in tbl.columns:
        val = tbl["v"]
    elif "value" in tbl.columns:
        val = tbl["value"]
    else:
        # fallback: pick the first numeric column
        nums = tbl.select_dtypes(include="number")
        if nums.shape[1] == 0:
            # no numeric column found -> return empty
            return pd.DataFrame(columns=[name]).set_index(pd.Index([]))
        val = nums.iloc[:, 0]

    # Build a tidy DataFrame and drop rows that couldn't be converted to datetime/value
    out = pd.DataFrame({
        "datetime": pd.to_datetime(time, errors="coerce"),
        name: pd.to_numeric(val, errors="coerce"),
    }).dropna()

    if out.empty:
        return pd.DataFrame(columns=[name]).set_index(pd.Index([]))

    # Use the datetime column as the index and sort chronologically
    return out.set_index("datetime").sort_index()


def process_hilo(hilo_raw):
    if hilo_raw is None:
        return pd.DataFrame()

    # Convert to DataFrame if necessary
    df = pd.DataFrame(hilo_raw) if not isinstance(hilo_raw, pd.DataFrame) else hilo_raw.copy()
    if df.empty:
        return pd.DataFrame()

    # Find the time column by checking common names, otherwise use the first column
    time_col = next((c for c in ("t", "time", "datetime", "date") if c in df.columns), None)
    if time_col is None:
        time_col = df.columns[0]

    # Find value column (height) by checking common names
    value_col = next((c for c in ("v", "value", "tide_height_ft", "height", "tide_height") if c in df.columns), None)
    if value_col is None:
        nums = df.select_dtypes(include="number")
        value_col = nums.columns[0] if nums.shape[1] > 0 else None

    # Find the type column (H/L) by checking common names
    type_col = next((c for c in ("type", "tide", "type_of_tide", "hl") if c in df.columns), None)

    # Build the output DataFrame with fallback strategies
    out = pd.DataFrame()
    # datetime: try time_col, else first column
    out["datetime"] = pd.to_datetime(df[time_col] if time_col in df.columns else df.iloc[:, 0], errors="coerce")
    # tide_height_ft: numeric value if available, else NaN
    out["tide_height_ft"] = pd.to_numeric(df[value_col], errors="coerce") if (value_col and value_col in df.columns) else np.nan

    # tide type: use type_col if present, else fallback to first text column, else None
    if type_col and type_col in df.columns:
        out["tide"] = df[type_col].astype(str)
    else:
        strcols = [c for c in df.columns if df[c].dtype == object]
        out["tide"] = df[strcols[0]].astype(str) if strcols else None

    # Drop rows without a valid datetime, set datetime as index, sort, and coerce numeric heights
    out = out.dropna(subset=["datetime"]).set_index("datetime").sort_index()
    out["tide_height_ft"] = pd.to_numeric(out["tide_height_ft"], errors="coerce")
    return out
    

# -------------------------
# NOAA fetch function
# -------------------------
def fetch_noaa(station="8454000", start="2025-09-21", end="2025-09-28"):
    """
    Fetch NOAA CO-OPS data:
    - observed water_level
    - observed water_temperature (if available)
    - hourly tide predictions
    - high/low (hilo) events

    The function:
    - standardizes each product to a one-column DataFrame indexed by datetime
    - joins the parts together
    - collapses duplicate timestamps (keeps first non-null per column)
    - saves the final DataFrame to noaa_{station}_obs_pred.json
    """
    station = str(station)
    b = noaa_date(start)  # NOAA requires YYYYMMDD
    e = noaa_date(end)
    print(f"[NOAA] Requesting station {station} {start} → {end} ")

    # Create a Station object (this knows how to call NOAA APIs)
    try:
        st = Station(station)
    except Exception as exc:
        print("[NOAA] Station init error:", exc)
        return pd.DataFrame()

    # safe_get: call st.get_data but catch errors so missing products don't stop the script
    def safe_get(product, **kwargs):
        try:
            return st.get_data(product=product, **kwargs)
        except Exception as exc:
            # print a short helpful message then continue
            print(f"[NOAA] product '{product}' not available or error (continuing): {exc}")
            return None

    # Request products 
    wl_raw = safe_get("water_level", begin_date=b, end_date=e, units="english", time_zone="gmt", datum="MLLW")
    wt_raw = safe_get("water_temperature", begin_date=b, end_date=e, units="metric", time_zone="gmt")
    pred_raw = safe_get(
        "predictions", begin_date=b, end_date=e,
        units="english", datum="MLLW", time_zone="gmt", interval="h"
    )
    hilo_raw = safe_get(
        "predictions", begin_date=b, end_date=e,
        units="english", datum="MLLW", time_zone="gmt", interval="hilo"
    )

    # Convert each product into a tidy one-column DataFrame with a datetime index
    wl = tidy_noaa(wl_raw, "water_level") if wl_raw is not None else pd.DataFrame()
    wt = tidy_noaa(wt_raw, "water_temperature") if wt_raw is not None else pd.DataFrame()
    pred = tidy_noaa(pred_raw, "predicted_tide_level") if pred_raw is not None else pd.DataFrame()
    hilo_df = process_hilo(hilo_raw) if hilo_raw is not None else pd.DataFrame()

    # Join the observation parts (water level, water temp, tide prediction)
    parts = [df for df in [wl, wt, pred] if isinstance(df, pd.DataFrame)]
    df = parts[0].join(parts[1:], how="outer") if parts else pd.DataFrame()

    # If hilo events exist, rename columns so they don't clash and join them too
    if not hilo_df.empty:
        hilo_df = hilo_df.rename(columns={"tide_height_ft": "hilo_tide_height_ft", "tide": "hilo_tide"})
        df = df.join(hilo_df, how="outer")

    # Ensure column names are unique
    df = ensure_unique_columns(df)

    # Collapse duplicate timestamps:
    # Sometimes different products share the exact same timestamp, leading to duplicate rows.
    # groupby(index).first() keeps the first non-null value for each column at each timestamp.
    if not df.empty and df.index.duplicated().any():
        before = df.shape[0]
        df = df.groupby(df.index).first()
        after = df.shape[0]
        print(f"[NOAA] collapsed duplicate timestamps: rows {before} -> {after}")

    # Prefix columns with "noaa_" so we can easily tell NOAA vs USGS data apart
    if not df.empty:
        df = df.add_prefix("noaa_")
        df = ensure_datetime_index(df)
        # localize to UTC if the index is timezone-naive
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is None:
            try:
                df.index = df.index.tz_localize("UTC")
            except Exception:
                pass

    # Save NOAA data to JSON
    out = f"noaa_{station}_obs_pred.json"
    try:
        df.to_json(out, indent=2, date_format="iso")
        print(f"[NOAA] saved {out} (shape: {df.shape})")
    except Exception as exc:
        print("[NOAA] save error:", exc)

    return df

# -------------------------
# Main entry point
# -------------------------
def main():
    """
    Parse command-line arguments (if provided) and run both fetches.
    Defaults are provided so you can run the script without arguments.
    """
    # default values (change these when calling the script if needed)
    usgs_site = "01376520"
    noaa_station = "8454000"
    start = "2025-09-21"
    end = "2025-09-28"

    # Allow overriding defaults using command-line args
    # Usage: python script.py USGS_SITE NOAA_STATION START END
    if len(sys.argv) >= 5:
        usgs_site, noaa_station, start, end = sys.argv[1:5]

    # Run USGS fetch and NOAA fetch
    df_usgs = fetch_usgs(usgs_site, start, end)
    df_noaa = fetch_noaa(noaa_station, start, end)

    # Inform the user which files (if any) were created
    print("Finished. Files created:")
    print(f" - data_usgs_{usgs_site}.json")
    print(f" - noaa_{noaa_station}_obs_pred.json")

# Run main() when the script is executed directly
if __name__ == "__main__":
    main()
