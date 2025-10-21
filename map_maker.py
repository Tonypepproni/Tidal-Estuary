import folium 

m = folium.Map(tiles='Cartodb Positron',zoom_start=9,location=[41.17132855417239, -73.93206265158021])

folium.GeoJson('geoJsonData/Hudson_River_NERR_Vegetation_Maps_-3673596371128117337.geojson',
               name="hudson",
               fill_color='blue', #the color inside
               color='purple' #line color
               ).add_to(m)

m.save("footprint.html")