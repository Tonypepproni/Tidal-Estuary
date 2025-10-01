 #import dataretrieval.nwis as nwis
import requests
import json
import pandas as pd 

#Goal : Pull real time hudson river data from USGS NWIS & export a JSON file per site 



# Base URL for USGS water data (instantaneous values)
url = "https://waterservices.usgs.gov/nwis/iv/"

# List of station IDs
stations = {
    "Poughkeepsie": "01376500",
    "Albany": "01358000",
    "Pier 25": "01392010"
}

# USGS parameter codes:
# 00065 = Gage height (water level)
# 00095 = Specific conductance (proxy for salinity)
parameters = ["00065", "00095"]

# Define time range (example: one day of data)
start_date = "2023-09-01T00:00-05:00"
end_date   = "2023-09-02T00:00-05:00"

# Dictionary to hold results
all_data = {}

# Loop through each station
for name, site_id in stations.items():
    print(f"Retrieving data for {name} (Site {site_id})...")
    
    # Query parameters
    params = {
        "format": "json",
        "sites": site_id,
        "parameterCd": ",".join(parameters),
        "startDT": start_date,
        "endDT": end_date
    }
    
    # Make the request
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        station_results = {}
        
        # Go through each parameter (water level, conductivity, etc.)
        for ts in data["value"]["timeSeries"]:
            param_desc = ts["variable"]["variableDescription"]
            readings = ts["values"][0]["value"]
            
            # Collect the time + value pairs
            station_results[param_desc] = [
                {"time": entry["dateTime"], "value": entry["value"]}
                for entry in readings
            ]
        
        # Store results in master dictionary
        all_data[name] = station_results
    else:
        print(f"Error retrieving data for {name}")

# Save all results into one JSON file
with open("hudson_estuary_data.json", "w") as outfile:
    json.dump(all_data, outfile, indent=4)

print("✅ Data saved to hudson_estuary_data.json")
