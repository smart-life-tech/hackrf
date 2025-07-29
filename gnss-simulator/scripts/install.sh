#!/bin/bash
# GNSS Simulator Installation Script
# For Raspberry Pi 5 with HackRF One

set -e  # Exit on any error

echo "======================================"
echo "GNSS Simulator Installation Script"
echo "======================================"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install basic dependencies
echo "Installing basic dependencies..."
sudo apt install -y git python3-pip python3-venv cmake build-essential \
    libusb-1.0-0-dev pkg-config libtool autoconf automake \
    libfftw3-dev librtlsdr-dev wget curl unzip

# Install HackRF support
echo "Installing HackRF support..."
sudo apt install -y hackrf libhackrf-dev

# Install GNU Radio
echo "Installing GNU Radio..."
sudo apt install -y gnuradio gnuradio-dev gr-osmosdr liblog4cpp5-dev

# Create directories
echo "Creating directories..."
mkdir -p /home/erez/gnss-data
mkdir -p /home/erez/gnss-simulator/logs

# Clone and build GPS-SDR-SIM
echo "Installing GPS-SDR-SIM..."
if [ ! -d "/home/erez/gps-sdr-sim" ]; then
    cd /home/erez
    git clone https://github.com/osqzss/gps-sdr-sim.git
    cd gps-sdr-sim
    gcc -O3 -o gps-sdr-sim gpssim.c -lm
    echo "GPS-SDR-SIM compiled successfully"
else
    echo "GPS-SDR-SIM already exists"
fi

# Setup USB permissions for HackRF
echo "Setting up HackRF USB permissions..."
sudo tee /etc/udev/rules.d/53-hackrf.rules > /dev/null <<EOF
ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", SYMLINK+="hackrf-one", MODE="0666", GROUP="plugdev"
ATTR{idVendor}=="1d50", ATTR{idProduct}=="cc15", SYMLINK+="hackrf-one", MODE="0666", GROUP="plugdev"
EOF

# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$(dirname "$0")/.."  # Go to project root
pip3 install --user -r requirements.txt --break-system-packages

# Download sample GNSS data
echo "Downloading sample GNSS data..."
cd /home/erez/gnss-data
if [ ! -f "brdc3540.14n" ]; then
    echo "not existing Downloading sample GNSS data..."
    wget -q https://github.com/Nuand/gps-sdr-sim/blob/master/brdc3540.14n
    echo "Sample GNSS data downloaded"
fi

# Create configuration file
echo "Creating configuration..."
cat > /home/erez/gnss-simulator/config.yaml <<EOF
# GNSS Simulator Configuration
gnss:
  data_directory: "/home/erez/gnss-data"
  gps_sdr_sim_path: "/home/erez/gps-sdr-sim/gps-sdr-sim"
  
hackrf:
  frequency: 1575420000  # L1 band
  sample_rate: 2600000
  tx_gain: 40
  power_level: 1

api:
  host: "0.0.0.0"
  port: 8000
  api_key: "gnss-simulator-key-2024"

logging:
  level: "INFO"
  file: "/home/erez/gnss-simulator/logs/gnss-simulator.log"
EOF

# Create systemd service (optional)
echo "Creating systemd service..."
sudo tee /etc/systemd/system/gnss-simulator.service > /dev/null <<EOF
[Unit]
Description=GNSS Simulator Service
After=network.target

[Service]
Type=simple
User=erez
WorkingDirectory=/home/erez/gnss-simulator
ExecStart=/usr/bin/python3 src/main.py server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# System optimizations
echo "Applying system optimizations..."

# CPU performance mode
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils > /dev/null
#sudo systemctl enable cpufrequtils

# Increase USB memory
if ! grep -q "usbcore.usbfs_memory_mb" /boot/firmware/cmdline.txt; then
    sudo sed -i '$ s/$/ usbcore.usbfs_memory_mb=1000/' /boot/firmware/cmdline.txt
fi

# Kernel parameters for real-time processing
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# GNSS Simulator optimizations
kernel.sched_rt_runtime_us=-1
vm.swappiness=10
net.core.rmem_max=134217728
net.core.wmem_max=134217728
EOF

# Boot configuration optimizations
if ! grep -q "gpu_mem=64" /boot/firmware/config.txt; then
    echo "gpu_mem=64" | sudo tee -a /boot/firmware/config.txt > /dev/null
fi

# Create helper scripts
echo "Creating helper scripts..."

# Test script
cat > /home/erez/gnss-simulator/test-system.sh <<'EOF'
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
EOF

chmod +x /home/erez/gnss-simulator/test-system.sh

# Quick start script
cat > /home/erez/gnss-simulator/quick-start.sh <<'EOF'
#!/bin/bash
# Quick start script for GNSS simulator

echo "Starting GNSS Simulator..."

# Set default location (London)
python3 src/main.py test --lat 51.5074 --lon -0.1278 --duration 60

echo "Test complete. To start API server:"
echo "python3 src/main.py server"
EOF

chmod +x /home/erez/gnss-simulator/quick-start.sh

# Set permissions
sudo chown -R erez:erez /home/erez/gnss-simulator
sudo chown -R erez:erez /home/erez/gnss-data

echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo
echo "Next steps:"
echo "1. Reboot the system: sudo reboot"
echo "2. Connect HackRF One via USB"
echo "3. Test the system: ./test-system.sh"
echo "4. Quick test: ./quick-start.sh"
echo "5. Start API server: python3 src/main.py server"
echo
echo "API will be available at: http://$(hostname -I | cut -d' ' -f1):8000"
echo "Documentation: http://$(hostname -I | cut -d' ' -f1):8000/docs"
echo
echo "To enable auto-start:"
echo "sudo systemctl enable gnss-simulator"
echo "sudo systemctl start gnss-simulator"
echo
EOF
