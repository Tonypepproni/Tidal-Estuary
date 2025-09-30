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

df = df.rename(columns=lambda c: c if c == "site_no" else c.replace("_hrecos", "").replace("_cd", "_cd:") if c.endswith("_cd") else {
    "00010": "Water Temperature (°C)",
    "00020": "Air Temperature (°C)",
    "00036": "Specific Conductance (µS/cm)",
    "00045": "Precipitation (inches)",
    "00052": "Turbidity (NTU)",
    "00095": "Specific Conductance (µS/cm @25°C)",
    "00300": "Dissolved Oxygen (mg/L)",
    "00301": "Dissolved Oxygen Saturation (%)",
    "00400": "pH (std units)",
    "61727": "Salinity (ppt)",
    "62620": "Gage Height (ft)",
    "63680": "Wind Speed (mph)",
    "75969": "Chlorophyll a (µg/L)",
    "82127": "FDOM (ppb QSU)",
    "90860": "Battery Voltage (V)"
}.get(c.replace("_hrecos", "").replace("_cd", ""), c))

df = df.drop(columns=["site_no"])

df.to_json('data.json',indent=4)
