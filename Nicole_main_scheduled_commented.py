import dataretrieval.nwis as nwis
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys  

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

#possible nulls youll see 
possible_nulls=["","NaN","null","None","--","999999",999999,-999999,'-999999'] 

# list of sites we want to pull (right now just Pier 25)
site_num = ['01376520']

# updated it to allow optional date window + per-day filenames
def get_station_data(site_code, start_date_str=None, end_date_str=None):
    """
    Pulls data for ONE USGS site and ONE date window.
    If no dates are given, it uses the old example window.
    Then it:
    - renames raw USGS column names to human-readable ones
    - drops useless columns
    - cleans nulls
    - saves 2 JSON files (one dated, one “latest”)
    """

    # choose the date window
    # If not, we fall back to the example Sept 21–28 window.
    start = start_date_str or '2025-9-21'
    end   = end_date_str   or '2025-9-28'

    #creates a df, pull from nwis and pulls from get_record
    # This is the IMPORTANT line that actually talks to USGS.
    # service='iv' means “instantaneous values”
    df = nwis.get_record(
        sites=site_code,
        service='iv',
        start=start,
        end=end,
        parameterCd=",".join(parameter_codes)
    ) 

    #replaces the parameter codes with word meanings so we can comprehend what the codea are 
    # USGS column names can look like "00010_hrecos_cd". We want to map them to nice names.
    # Your logic:
    # - keep "site_no"
    # - if it ends with cd, keep it as a flag
    # - otherwise, try to map 00010 → water_temperature, etc.
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

     # 1) Drop battery voltage (and its flag), if present
    # We don’t really need battery info or site_no in our final JSON.
    df = df.drop(columns=[c for c in df.columns if c in ["battery_voltage","site_no"]], errors="ignore")

    # 2) Drop columns that are entirely empty (all NaN)
    # Sometimes USGS sends columns with no data at all → just drop them
    df = df.dropna(axis="columns", how="all")

    # 3) Drop orphan flag columns: columns that end with _cd like (water_temp_cd)
    #when the matching measurement column (water_temp) is missing
    #water_temp = numbers 
    #water_temp_cd = the status codes for the numbers. Theyre not useful, theyre just labels with no data 
    # In other words: keep a flag only if the data column exists.
    flag_cols = [c for c in df.columns if c.endswith("_cd")]
    #for any column in df.columns that ends with cd is a cd column
    #it would make a list of those cd columns 
    orphans = [c for c in flag_cols if c[:-3] not in df.columns]
    #finds the orphan among those flags. those r the cd colums whose matching measurements r missing    
    if orphans:
        df = df.drop(columns=orphans)
        
    # we clean each column
    for column_name in df.columns:
        #removes possible nulls 
        # Replace all the weird values we listed at the top with real NaN
        df[column_name] = df[column_name].replace(possible_nulls, np.nan)
        #if theres a null it will fill in from the code above it or below it 
        # ffill = forward fill (take previous value)
        # bfill = backward fill (take next value)
        # Together → try hard not to leave gaps
        df[column_name] = df[column_name].ffill().bfill() 

    #df = df.replace(possible_nulls, np.nan).ffill().bfill()
    df = df.dropna(axis="columns", how="all")
        
    # prints the first 10 lines of code. Selects columns present 
    # b/c df doesnt have columns for gage_height
    # This is just a “peek” so when you run the script manually
    # you can SEE you actually got data.
    print(df[[c for c in ["gage_height","water_temperature"] if c in df.columns]].head(10))

    # per-day snapshot + pulling latest ===
    # ymd = yyyymmdd, example: "2025-09-21" → "20250921"
    ymd = start.replace("-", "")                            # use start date for filename tag (YYYYMMDD)
    df.to_json(f'data{site_code}_{ymd}.json',indent=4)      #  dated snapshot
    df.to_json(f'data{site_code}_latest.json',indent=4)     # pulling latest
    # 👆 So at the end of this function, you always have:
    # - one JSON with a date in the name (for history)
    # - one JSON called ..._latest.json (for the app to always read)


def noaa(station):
    # placeholder for future NOAA logic
    print('H')



 # calling from a specific site since we are only calling from one site currently 
# run once immediately for "yesterday" instead of a fixed date  
def _yesterday_window():
    """
    ADDED: Return date strings for [yesterday, today) in local time as ('YYYY-MM-DD', 'YYYY-MM-DD').
    This is useful because we want to run this script every morning and pull JUST the previous day.
    Example (today = 2025-11-02):
      returns ('2025-11-01', '2025-11-02')
    """
    today = datetime.now().date()
    start = today - timedelta(days=1)
    end = today
    return start.isoformat(), end.isoformat()  # 'YYYY-MM-DD'

#  simple helper to compute sleep time until next 07:00:00 local
def _seconds_until(hour=7, minute=0, second=0):
   
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()

#  run a single “yesterday” pull for all configured sites
def run_yesterday_for_all_sites():
    """
    Compute yesterday’s window, log it, and call get_station_data(site, start, end) for each site.
    This is the MAIN “do the thing” function.
    """
    start_str, end_str = _yesterday_window()
    for site in site_num: 
        get_station_data(site, start_str, end_str)
    print("Done.\n")


# this is the  cron version — run once and exit
def run_once_for_cron():
    """
    This is meant to be called by cron.
    It just runs the daily job ONCE and then the program ends.
    """
    run_yesterday_for_all_sites()
    # no while True, no sleeping — just exit


#  proper entry-point & daily schedule ===
if __name__ == "__main__":
    # check if user / scheduler passed a flag like: python script.py --cron
    # This lets us control HOW the script runs.
    # - if we pass --cron → run once and exit (for real daily scheduling)
    # - if we don’t pass anything → run once and (optionally) stay alive
    if len(sys.argv) > 1 and sys.argv[1] == "--cron":
        # run once for the scheduler and exit
        run_once_for_cron()
    else:
        # run once immediately for yesterday (so you get data right away when you start the script)
        run_yesterday_for_all_sites()

      

        """
        # Then run every day at 07:00 local time forever
        while True:
            wait = int(_seconds_until(7, 0, 0))
            time.sleep(wait)
            try:
                run_yesterday_for_all_sites()
            except Exception as e:
                # you should log e here
                print("Error during daily run:", e)

            # Buffer so it doesn't re-trigger within the same minute
            #is it better to have this file run 24/7 or have another software activate this file every 24 hours
            #chronicle, chronjob - write a fubction as if it was running through chronicle, put it all in one file 
            time.sleep(60)
        """

"""
How you use it now

Keep doing it your old way (script runs forever):

python yourscript.py


Let chronicle/cron call it once at 7am:

python yourscript.py --cron


Then in cron:
"""
