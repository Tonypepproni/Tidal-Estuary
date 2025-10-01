# USGS Water Grid Application

A Flask web application for visualizing USGS water quality data in a clean, organized grid format.

## Features

- 📊 Clean tabular display of water monitoring station data
- 🌊 Consolidated view showing key measurements per site (temperature, pH, dissolved oxygen, salinity, water elevation)
- � Automatically downloads fresh USGS readings at startup and every 15 minutes
- �📱 Responsive design with horizontal scrolling for wide data
- 🔍 No duplicate sites - each monitoring station appears once with all its measurements
- 🌐 Works on any device with Python and a web browser

## Quick Start

1. **Install Python** (3.10 or higher recommended)

2. **Install dependencies**:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Run the application**:

   ```bash
   python app.py
   ```

4. **Open your browser** to: `http://127.0.0.1:5000`

The Flask app automatically downloads the latest USGS instantaneous values for site `01376520` when it starts, writes them to `data/waterservices.usgs.gov.json`, and refreshes that file every 15 minutes. If you need a different site or time window, edit the `SITE_NUMBER`, `PARAMETER_CODES`, or the logic inside `fetch_usgs_dataframe` in `app.py`.

## Data Format

The generated dataset is a list of JSON records produced from the USGS Water Services `iv` API. Each record contains the timestamp and the latest values for the configured parameter codes. The data file is regenerated on every refresh, so you do not have to download JSON manually anymore.

## Project Structure

```text
watergrid/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── data/               # Data files directory
│   └── *.json          # Auto-generated USGS JSON data files
├── static/
│   └── js/
│       └── grid.js     # Frontend JavaScript
└── templates/
   └── index.html      # HTML template
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

- Ensure the app can reach the USGS API (firewall/proxy considerations)
- Check the terminal output—any download errors are logged there
- The app retries every 15 minutes; you can also delete `data/waterservices.usgs.gov.json` and refresh the page to trigger a new fetch

**Empty table?**

- Check the browser console (F12) for JavaScript errors
- Verify in the terminal that data was downloaded successfully
- Confirm the configured parameter codes exist for the selected site

**Can't access the website?**

- Make sure Flask is running (you should see "Running on <http://127.0.0.1:5000>")
- Try `http://localhost:5000` instead
- Check that port 5000 isn't blocked by firewall

## License

This project is open source and available under the MIT License.
