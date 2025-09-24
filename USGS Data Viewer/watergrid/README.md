# USGS Water Grid Application

A Flask web application for visualizing USGS water quality data in a clean, organized grid format.

## Features

- 📊 Clean tabular display of water monitoring station data
- 🌊 Consolidated view showing key measurements per site (temperature, pH, dissolved oxygen, salinity, water elevation)
- 📱 Responsive design with horizontal scrolling for wide data
- 🔍 No duplicate sites - each monitoring station appears once with all its measurements
- 🌐 Works on any device with Python and a web browser

## Quick Start

1. **Install Python** (3.6 or higher)

2. **Install Flask**:
   ```bash
   pip install flask
   ```

3. **Place your data file** in one of these locations:
   - Application directory (same folder as app.py)
   - `data/` subdirectory
   - Your Downloads folder
   - Your Desktop

   The app looks for these filenames:
   - `waterservices.usgs.gov.json`
   - `usgs_data.json`
   - `water_data.json`

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** to: `http://127.0.0.1:5000`

## Data Format

The application expects USGS water services JSON data in the timeSeriesResponseType format. You can get this data from the USGS Water Services API:

```
https://waterservices.usgs.gov/nwis/iv/?format=json&stateCd=ny&siteStatus=active&siteType=ES&altMax=0
```

## Project Structure

```
watergrid/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── data/              # Data files directory
│   └── *.json        # USGS JSON data files
├── static/
│   └── js/
│       └── grid.js   # Frontend JavaScript
└── templates/
    └── index.html    # HTML template
```

## What You'll See

The application displays a table with these columns:
- **Site Name**: Monitoring station name
- **Site Code**: USGS identifier
- **Latitude/Longitude**: Location coordinates
- **# Variables**: Number of measurements available
- **Temperature**: Water temperature in °C
- **pH**: pH level
- **Dissolved O₂**: Dissolved oxygen (mg/L)
- **Salinity**: Salinity (PSU)
- **Water Level**: Water elevation (ft)
- **Last Update**: Date of latest measurement

## Troubleshooting

**"Data file not found" error?**
- Make sure your JSON file is in one of the supported locations
- Check that the filename matches one of the expected names
- Verify the file isn't corrupted or empty

**Empty table?**
- Check the browser console (F12) for JavaScript errors
- Verify your JSON file contains valid USGS timeSeriesResponseType data

**Can't access the website?**
- Make sure Flask is running (you should see "Running on http://127.0.0.1:5000")
- Try `http://localhost:5000` instead
- Check that port 5000 isn't blocked by firewall

## License

This project is open source and available under the MIT License.