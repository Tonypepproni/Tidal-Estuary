#!/bin/bash

echo "USGS Water Grid Application"
echo "==========================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "Error: Python is not installed"
        echo "Please install Python 3.6+ from https://python.org"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Using: $PYTHON_CMD"

# Run setup if needed
if [ ! -f "data/waterservices.usgs.gov.json" ]; then
    echo "Running first-time setup..."
    $PYTHON_CMD setup.py
    echo
fi

# Start the application
echo "Starting Water Grid Application..."
echo "Open your browser to: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo

$PYTHON_CMD app.py