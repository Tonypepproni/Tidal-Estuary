from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# Try to find the data file in common locations
def find_data_file():
    # Possible data file names
    possible_names = [
        "waterservices.usgs.gov.json",
        "usgs_data.json", 
        "water_data.json"
    ]
    
    # Search locations in order of preference
    search_paths = [
        ".",  # Current directory
        "data",  # data subdirectory
        os.path.expanduser("~/Downloads"),  # User's Downloads folder
        os.path.expanduser("~/Desktop"),    # User's Desktop
    ]
    
    for search_path in search_paths:
        for filename in possible_names:
            filepath = os.path.join(search_path, filename)
            if os.path.exists(filepath):
                return filepath
    
    return None

DATA_FILE = find_data_file()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    if not DATA_FILE or not os.path.exists(DATA_FILE):
        return jsonify({
            "error": "Data file not found", 
            "message": "Please place 'waterservices.usgs.gov.json' in the application directory, data folder, Downloads, or Desktop"
        }), 404
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({
            "error": "Failed to load data file",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    print("Water Grid Application")
    print("=====================")
    if DATA_FILE:
        print(f"✓ Data file found: {DATA_FILE}")
    else:
        print("⚠ Warning: No data file found!")
        print("Please place 'waterservices.usgs.gov.json' in one of these locations:")
        print("  - Current directory")
        print("  - data/ subdirectory")
        print("  - Downloads folder")
        print("  - Desktop")
    print("\nStarting server...")
    app.run(debug=True)
