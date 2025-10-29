import dataretrieval.nwis as nwis
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
#It pulls instantaneous (iv) data from USGS NWIS for one site (01376520) over 2025-09-21 →
# 2025-09-28, tries to make the column names human-readable, fills in missing values, prints two columns,
# then saves everything to a JSON file named data01376520.json.
#calling pier 25
parameter_codes = [
    "00010",  # Temperature, water (°C)
    "00011",  # Temperature, air (°C)
    "00300",  # Dissolved oxygen (mg/L)
    "00301",  # Dissolved oxygen, percent saturation
    "00065",  # Gage height (ft)  <-- fixed (was 62620)
    "62620",  # added 62620 b/c gage height wasn't reporting
    "62623",  # Tide stage, feet  <-- fixed (was 62614)
    "00480",  # Salinity, water (ppt)
    "63680",  # Turbidity, water (NTU)
    "82362",  # Turbidity, FNU
    "00060",  # Discharge, streamflow (cfs)
]

possible_nulls=["","NaN","null","None","--","999999",999999,-999999,'-999999'] #possible nulls youll see 
site_num = ['01376520']

# updated it to allow optional date window + per-day filenames
def get_station_data(site_code, start_date_str=None, end_date_str=None):
   
    # choose the date window — either the provided one (for scheduler) or your original fixed week
    start = start_date_str or '2025-9-21'
    end   = end_date_str   or '2025-9-28'

    df = nwis.get_record(sites=site_code,service='iv',start=start,end=end, parameterCd=",".join(parameter_codes)) 
    #creates a df, pull from nwis and pulls from get_record

    df = df.rename(columns=lambda c: c if c == "site_no" else c.replace("_hrecos", "").replace("_cd", "cd") if c.endswith("cd") else {
        "00010": "water_temperature",
        "00020": "air_temperature",
        "00045": "precipitation",
        "00052": "turbidity",
        "00095": "specific_conductance_at_25",
        "00300": "dissolved_oxygen",
        "00301": "dissolved_oxygen_saturation",
        "00400": "pH",
        "00480": "salinity",          # <-- fixed (was 61727)
        "00065": "gage_height",       # <-- fixed (was 62620)
        "63680": "turbidity_ntu",     # <-- fixed (was wind_speed)
        "75969": "chlorophyll_a",
        "82127": "FDOM",
        "90860": "battery_voltage"
    }.get(c.replace("_hrecos", "").replace("_cd", ""), c)) 
    #replaces the parameter codes with word meanings so we can comprehend what the codea are 

     # 1) Drop battery voltage (and its flag), if present
    df = df.drop(columns=[c for c in df.columns if c in ["battery_voltage","site_no"]], errors="ignore")


    # 2) Drop columns that are entirely empty (all NaN)
    df = df.dropna(axis="columns", how="all")

    # 3) Drop orphan flag columns: columns that end with _cd like (water_temp_cd)
    #when the matching measurement column (water_temp) is missing
    #water_temp = numbers 
    #water_temp_cd = the status codes for the numbers. Theyre not useful, theyre just labels with no data 
    flag_cols = [c for c in df.columns if c.endswith("_cd")]
    #for any column in df.columns that ends with cd is a cd column
    #it would make a list of those cd columns 
    orphans = [c for c in flag_cols if c[:-3] not in df.columns]
    #finds the orphan among those flags. those r the cd colums whose matching measurements r missing    
    if orphans:
        df = df.drop(columns=orphans)
        
    for column_name in df.columns:
        df[column_name] = df[column_name].replace(possible_nulls, np.nan)
        #removes possible nulls 
        df[column_name] = df[column_name].ffill().bfill() 
        #if theres a null it will fill in from the code above it or below it 

    #df = df.replace(possible_nulls, np.nan).ffill().bfill()
    df = df.dropna(axis="columns", how="all")
        
        
    print(df[[c for c in ["gage_height","water_temperature"] if c in df.columns]].head(10))
# prints the first 10 lines of code. Selects columns present 
# b/c df doesnt have columns for gage_height

    # per-day snapshot + pulling latest ===
    ymd = start.replace("-", "")                            # use start date for filename tag (YYYYMMDD)
    df.to_json(f'data{site_code}_{ymd}.json',indent=4)      #  dated snapshot
    df.to_json(f'data{site_code}_latest.json',indent=4)     # pulling latest

def noaa(station):
    print('H')



 # calling from a specific site since we are only calling from one site currently 
# run once immediately for "yesterday" instead of a fixed date  
def _yesterday_window():
    """
    ADDED: Return date strings for [yesterday, today) in local time as ('YYYY-MM-DD', 'YYYY-MM-DD').
    """
    today = datetime.now().date()
    start = today - timedelta(days=1)
    end = today
    return start.isoformat(), end.isoformat()  # 'YYYY-MM-DD'

# ADDED: simple helper to compute sleep time until next 07:00:00 local
def _seconds_until(hour=7, minute=0, second=0):
   
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()

# ADDED: run a single “yesterday” pull for all configured sites
def run_yesterday_for_all_sites():
    """
 Compute yesterday’s window, log it, and call get_station_data(site, start, end) for each site.
    """
    start_str, end_str = _yesterday_window()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pulling {start_str} → {end_str}")
    for site in site_num: 
        get_station_data(site, start_str, end_str)
    print("Done.\n")

#  proper entry-point & daily schedule ===
if __name__ == "__main__":
    # run once immediately for yesterday (so you get data right away when you start the script)
    run_yesterday_for_all_sites()

    # Then run every day at 07:00 local time forever
    while True:
        wait = int(_seconds_until(7, 0, 0))
        print(f"Sleeping {wait} seconds until next 07:00 run…")
        time.sleep(wait)
        try:
            run_yesterday_for_all_sites()
        except Exception as e:
            print(f"Scheduled run failed: {e}")
        # Buffer so it doesn't re-trigger within the same minute
        time.sleep(60)
