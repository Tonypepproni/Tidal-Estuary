from noaa_coops import Station
import pandas as pd

def noaa(station, start, end):
    st = Station(station)

    # pull  data ( columns are "t" and "v")
    water_level = st.get_data(product="water_level", begin_date=start, end_date=end, units="english", time_zone="gmt", datum="MLLW")[["t","v"]]
    water_temp = st.get_data(product="water_temperature", begin_date=start, end_date=end, units="metric", time_zone="gmt")[["t","v"]]
    water_salinity = st.get_data(product="salinity", begin_date=start, end_date=end,units="metric", time_zone="gmt")[["t","v"]]

    # helper to clean each one
    def tidy(df, name):
        
        #returns columns named time and value 
        df = df.rename(columns={"t": "datetime", "v": name})
        
        #converts datettime strings into datetime objects
        #if anything can't be parsed it becomes NaT meaning not-a-time instead of crashing
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        
        #removes rows, make a time level row index in order
        return df.dropna().set_index("datetime").sort_index()

   