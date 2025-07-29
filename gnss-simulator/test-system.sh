#!/bin/bash
echo "=== GNSS Simulator System Test ==="

echo "1. Testing HackRF connection..."
if hackrf_info | grep -q "Found HackRF"; then
    echo "✓ HackRF detected"
else
    echo "✗ HackRF not detected"
fi

echo "2. Testing GPS-SDR-SIM..."
if [ -x "/home/erez/gps-sdr-sim/gps-sdr-sim" ]; then
    echo "✓ GPS-SDR-SIM available"
else
    echo "✗ GPS-SDR-SIM not found"
fi

echo "3. Testing GNSS data..."
if ls /home/erez/gnss-data/*.n > /dev/null 2>&1; then
    echo "✓ GNSS data available"
else
    echo "✗ GNSS data missing"
fi

echo "4. Testing Python dependencies..."
cd /home/erez/gnss-simulator
if python3 -c "import fastapi, uvicorn; print('✓ Python dependencies OK')"; then
    true
else
    echo "✗ Python dependencies missing"
fi

echo "5. System status..."
echo "   Memory: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "   CPU temp: $(vcgencmd measure_temp)"
echo "   Disk: $(df -h / | awk 'NR==2{print $5}')"

echo "=== Test Complete ==="