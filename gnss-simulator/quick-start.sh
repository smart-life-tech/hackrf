#!/bin/bash
# Quick start script for GNSS simulator

echo "Starting GNSS Simulator..."

# Set default location (London)
python3 src/main.py test --lat 51.5074 --lon -0.1278 --duration 60

echo "Test complete. To start API server:"
echo "python3 src/main.py server"