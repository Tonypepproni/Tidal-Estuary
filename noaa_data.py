
import dataretrieval.nwis as nwis      
from noaa_coops import Station          
import pandas as pd                     




parameter_codes = [
    "00010",  # Temperature, water (°C)
    "00011",  # Temperature, air (°C)
    "00300",  # Dissolved oxygen (mg/L)
    "00301",  # Dissolved oxygen, percent saturation
    "00065",  # Gage height (ft)
    "62623",  # Tide stage, feet
    "00480",  # Salinity, water (ppt)
    "63680",  # Turbidity, water (NTU)
    "82362",  # Turbidity, FNU
    "00060",  # Discharge, streamflow (cfs)
]


possible_nulls = ["", "NaN", "null", "None", "--", "999999", 999999, -999999, "-999999"]

# The USGS site number we want to pull data from.
site_num = ["01376520"]


def get_station_data(site_code):
    # get data from USGS for the given site, service type, and date range
    df = nwis.get_record(sites=site_code, service="iv", start="2025-9-21", end="2025-9-28")

    # rename complicated parameter codes into simple names
    df = df.rename(
        columns=lambda c: c
        if c == "site_no"
        else c.replace("_hrecos", "").replace("_cd", "cd") if c.endswith("cd") else {
            "00010": "water_temperature",
            "00020": "air_temperature",
            "00045": "precipitation",
            "00052": "turbidity",
            "00095": "specific_conductance_at_25",
            "00300": "dissolved_oxygen",
            "00301": "dissolved_oxygen_saturation",
            "00400": "pH",
            "61727": "salinity",
            "62620": "gage_height",
            "63680": "turbidity_ntu",
            "75969": "chlorophyll_a",
            "82127": "FDOM",
            "90860": "battery_voltage",
        }.get(c.replace("_hrecos", "").replace("_cd", ""), c)
    )

    # clean and fill in missing data for every column
    for column_name in df.columns:
        df[column_name] = df[column_name].replace(possible_nulls, np.nan)  # replace "bad" values with NaN
        df[column_name] = df[column_name].ffill().bfill()  # fill missing values using nearby data

    # drop columns we don’t need (like battery voltage or site number)
    df = df.drop(columns=[c for c in df.columns if c in ["battery_voltage", "site_no"]], errors="ignore")

    # drop empty columns that only have missing values
    df = df.dropna(axis="columns", how="all")

    # drop flag columns (ending with _cd) that don’t have matching data
    flag_cols = [c for c in df.columns if c.endswith("_cd")]
    orphans = [c for c in flag_cols if c[:-3] not in df.columns]
    if orphans:
        df = df.drop(columns=orphans)

    # print a small preview of gage height and water temp (if they exist)
    cols_to_show = [c for c in ["gage_height", "water_temperature"] if c in df.columns]
    if cols_to_show:
        print(df[cols_to_show].head(10))  # show first 10 rows

    # save the cleaned data as a JSON file (example: data01376520.json)
    df.to_json(f"data{site_code}.json", indent=4)

# -----------------------------------------------------------

# pulls ocean water and tide data from NOAA and saves as JSON

def noaa(station, start, end):
    # create a NOAA station object so we can access its data
    st = Station(str(station))

    # helper function to clean NOAA data and standardize its format
    def tidy(df, name):
        if not isinstance(df, pd.DataFrame):   # make sure it’s a DataFrame
            df = pd.DataFrame(df)
        # find which column has the time info
        if "t" in df.columns:
            time = df["t"]
        elif "time" in df.columns:
            time = df["time"]
        else:
            df = df.reset_index()
            time = df.iloc[:, 0]
        # find which column has the data values
        if "v" in df.columns:
            val = df["v"]
        elif "value" in df.columns:
            val = df["value"]
        else:
            val = df.select_dtypes(include="number").iloc[:, 0]
        # make a clean DataFrame with datetime and value
        out = pd.DataFrame({
            "datetime": pd.to_datetime(time, errors="coerce"),
            name: pd.to_numeric(val, errors="coerce"),
        })
        return out.dropna().set_index("datetime").sort_index()

    # get water level, temperature, and salinity data from NOAA
    water_level = st.get_data(product="water_level",
                              begin_date=start, end_date=end,
                              units="english", time_zone="gmt", datum="MLLW")
    water_temp = st.get_data(product="water_temperature",
                             begin_date=start, end_date=end,
                             units="metric", time_zone="gmt")
    water_salinity = st.get_data(product="salinity",
                                 begin_date=start, end_date=end,
                                 units="metric", time_zone="gmt")

    # clean up the NOAA data
    water_level = tidy(water_level, "water_level")         # measured water level (feet)
    water_temp = tidy(water_temp, "water_temperature")     # measured water temperature (°C)
    water_salinity = tidy(water_salinity, "salinity")      # measured salinity (PSU)

    # gets the tide predictions 
    tide_pred = st.get_data(product="predictions",
                            begin_date=start, end_date=end,
                            units="english", datum="MLLW",
                            time_zone="gmt", interval="h")
    tide_pred = tidy(tide_pred, "predicted_tide_level")     # predicted tide height in feet

    # get high and low tide events (H or L)
    hilo_pred = st.get_data(product="predictions",
                            begin_date=start, end_date=end,
                            units="english", datum="MLLW",
                            time_zone="gmt", interval="hilo")
    # turn this into a clean table
    hilo_pred = (pd.DataFrame(hilo_pred)
                 .rename(columns={"t": "datetime", "v": "tide_height_ft", "type": "tide"}) #renames columns t-time, v-value for tide,type- high or loe
                 .assign(datetime=lambda d: pd.to_datetime(d["datetime"], errors="coerce"),#modifies columns into floats
                         tide_height_ft=lambda d: pd.to_numeric(d["tide_height_ft"], errors="coerce"))
                 .dropna(subset=["datetime", "tide_height_ft", "tide"])#drops any mys 
                 .set_index("datetime") 
                 .sort_index())#chronological order

    # combine all the NOAA data into one big table
    df = water_level.join([water_temp, water_salinity, tide_pred, hilo_pred], how="outer").sort_index()

    # save the combined NOAA data as a JSON file
    df.to_json(f"noaa_{station}_obs_pred.json", indent=2, date_format="iso")

  
    print("Saved:", f"noaa_{station}_obs_pred.json")

    return df 


