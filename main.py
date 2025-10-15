import dataretrieval.nwis as nwis
from noaa_coops import Station
import pandas as pd
import numpy as np

#It pulls instantaneous (iv) data from USGS NWIS for one site (01376520) over 2025-09-21 →
# 2025-09-28, tries to make the column names human-readable, fills in missing values, prints two columns,
# then saves everything to a JSON file named data01376520.json.

parameter_codes = [
    "00010",  # Temperature, water (°C)
    "00011",  # Temperature, air (°C)
    "00300",  # Dissolved oxygen (mg/L)
    "00301",  # Dissolved oxygen, percent saturation
    "00065",  # Gage height (ft)  <-- fixed (was 62620)
    "62623",  # Tide stage, feet  <-- fixed (was 62614)
    "00480",  # Salinity, water (ppt)
    "63680",  # Turbidity, water (NTU)
    "82362",  # Turbidity, FNU
    "00060",  # Discharge, streamflow (cfs)
]

possible_nulls=["","NaN","null","None","--","999999",999999,-999999,'-999999'] #possible nulls youll see 

site_num=['01376520']

def get_station_data(site_code):

    df = nwis.get_record(sites=site_code,service='iv',start='2025-9-21',end='2025-9-28') #creates a df, pull from nwis and pulls from get_record

    df = df.rename(columns=lambda c: c if c == "site_no" else c.replace("_hrecos", "").replace("_cd", "cd") if c.endswith("cd") else {
        "00010": "water_temperature",
        "00020": "air_temperature",
        "00045": "precipitation",
        "00052": "turbidity",
        "00095": "specific_conductance_at_25",
        "00300": "dissolved_oxygen",
        "00301": "dissolved_oxygen_saturation",
        "00400": "pH",
        "61727": "salinity",          # <-- fixed (was 61727)
        "62620": "gage_height",       # <-- fixed (was 62620)
        "63680": "turbidity_ntu",     # <-- fixed (was wind_speed)
        "75969": "chlorophyll_a",
        "82127": "FDOM",
        "90860": "battery_voltage"
    }.get(c.replace("_hrecos", "").replace("_cd", ""), c)) 
    #replaces the parameter codes with word meanings so we can comprehend what the codea are 

    for column_name in df.columns:
        df[column_name] = df[column_name].replace(possible_nulls, np.nan) #removes possible nulls 
        df[column_name] = df[column_name].ffill().bfill() #if theres a null it will fill in from the code above it or below it 
        
    # 1) Drop battery voltage (and its flag), if present
    df = df.drop(columns=[c for c in df.columns if c in ["battery_voltage","site_no"]], errors="ignore")

    # 2) Drop columns that are entirely empty (all NaN)
    df = df.dropna(axis="columns", how="all")

    # 3) Drop orphan flag columns: columns that end with _cd like (water_temp_cd)
    #when the matching measurement column (water_temp) is missing
    #water_temp = numbers 
    #water_temp_cd = the status codes for the numbers. Theyre not useful, theyre just labels with no data 
    flag_cols = [c for c in df.columns if c.endswith(("cd",'_hrecos'))]
    orphans = [c for c in flag_cols if c[:-3] not in df.columns]
    if orphans:
        df = df.drop(columns=orphans)
        
    print(df[["gage_height","water_temperature"]].head(10))
# prints the first 10 lines of code. Selects columns present 
# b/c df doesnt have columns for gage_height

    df.to_json(f'data{site_code}.json',indent=4)

def noaa(station, start, end):
    st = Station(station)

    # pull  data ( columns are "t" and "v")
    water_level = st.get_data(product="water_level", begin_date=start, end_date=end, units="english", time_zone="gmt", datum="MLLW")
    water_temp = st.get_data(product="water_temperature", begin_date=start, end_date=end, units="metric", time_zone="gmt")
    water_salinity = st.get_data(product="salinity", begin_date=start, end_date=end,units="metric", time_zone="gmt")

    water_level=water_level.rename(columns={'v':'water_level','s':'stnadard_devation','f':'data_flags','q':'error_code'})

    print(water_level.columns)
    print(water_level.head(10))
    print(water_temp.head(10))

    # helper to clean each one
    def tidy(df, name):
        
        #returns columns named time and value 
        df = df.rename(columns={"t": "datetime", "v": name})
        
        #converts datettime strings into datetime objects
        #if anything can't be parsed it becomes NaT meaning not-a-time instead of crashing
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        
        #removes rows, make a time level row index in order
        return df.dropna().set_index("datetime").sort_index()

 # calling from a specific site since we are only calling from one site currently 
noaa(8518962,'10/15/2025','10/16/2025')

'''
for site in site_num:
    get_station_data(site)
'''