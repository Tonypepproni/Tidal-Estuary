import dataretrieval.nwis as nwis
import pandas as pd

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

df = nwis.get_record(sites='01376520',service='iv',start='2025-9-21',end='2025-9-28')

df = df.rename(columns=lambda c: c if c == "site_no" else c.replace("_hrecos", "").replace("_cd", "cd") if c.endswith("cd") else {
    "00010": "water_temperature",
    "00020": "air_temperature",
    "00036": "specific_conductance",
    "00045": "precipitation",
    "00052": "turbidity",
    "00095": "specific_conductance",
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


df = df[df["gage_height"].notna()]

print(df.head(10))

#df.to_json('data.json',indent=4)
