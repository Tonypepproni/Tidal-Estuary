import dataretrieval.nwis as nwis
import pandas as pd
import numpy as np

parameter_codes = [
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

possible_nulls=["","NaN","null","None","--","999999",999999,-999999,'-999999']


def get_station_data(site_code):

    df = nwis.get_record(sites=site_code,service='iv',start='2025-9-21',end='2025-9-28')

    df = df.rename(columns=lambda c: c if c == "site_no" else c.replace("_hrecos", "").replace("_cd", "cd") if c.endswith("cd") else {
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
        "63680": "wind_speed",
        "75969": "chlorophyll_a",
        "82127": "FDOM",
        "90860": "battery_voltage"
    }.get(c.replace("_hrecos", "").replace("_cd", ""), c))

    for column_name in df.columns:
        df[column_name] = df[column_name].replace(possible_nulls, np.nan)
        df[column_name] = df[column_name].ffill().bfill()
    
    print(df[["gage_height","water_temperature"]].head(10))

    df.to_json(f'data{site_code}.json',indent=4)


sitenum='01376520'

get_station_data(sitenum)
