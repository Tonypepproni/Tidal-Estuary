#!/usr/bin/env python3
"""
USGS Water Grid Setup Script
This script helps set up the water grid application on any system.
"""

import os
import sys
import subprocess
import urllib.request
import json

def check_python():
    """Check if Python version is adequate."""
    if sys.version_info < (3, 6):
        print("❌ Python 3.6 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python {sys.version.split()[0]} detected")
    return True

def install_flask():
    """Install Flask if not already installed."""
    try:
        import flask
        print("✓ Flask is already installed")
        return True
    except ImportError:
        print("📦 Installing Flask...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
            print("✓ Flask installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Flask")
            return False

def download_sample_data():
    """Download sample USGS data if no data file exists."""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    data_file = os.path.join(data_dir, "waterservices.usgs.gov.json")
    
    if os.path.exists(data_file):
        print("✓ Data file already exists")
        return True
    
    print("📡 Downloading sample USGS water data...")
    try:
        # Download fresh data from USGS API
        url = "https://waterservices.usgs.gov/nwis/iv/?format=json&stateCd=ny&siteStatus=active&siteType=ES&altMax=0"
        
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        print("✓ Sample data downloaded successfully")
        return True
    except Exception as e:
        print(f"⚠ Could not download sample data: {e}")
        print("You can manually place a USGS JSON file in the data/ directory")
        return False

def main():
    print("USGS Water Grid Setup")
    print("====================")
    
    # Check Python version
    if not check_python():
        sys.exit(1)
    
    # Install Flask
    if not install_flask():
        sys.exit(1)
    
    # Download sample data
    download_sample_data()
    
    print("\n🎉 Setup complete!")
    print("\nTo start the application:")
    print("  1. Run: python app.py")
    print("  2. Open: http://127.0.0.1:5000")
    print("\nTo use your own data:")
    print("  - Place USGS JSON files in the data/ directory")
    print("  - Or put them in Downloads/Desktop with supported filenames")

if __name__ == "__main__":
    main()