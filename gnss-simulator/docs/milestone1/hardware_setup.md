# Hardware Setup Guide

## GNSS Simulator Hardware Installation and Configuration

### Prerequisites

- Raspberry Pi 5 (8GB RAM)
- HackRF One SDR
- MicroSD card (32GB+, Class 10)
- USB-C power supply (5V, 5A for Pi 5)
- USB cable for HackRF
- SMA antenna or RF connector
- Network connection (Ethernet or Wi-Fi)

### 1. Raspberry Pi 5 Setup

#### 1.1 Operating System Installation

```bash
# Download Raspberry Pi OS Lite (64-bit)
# Use Raspberry Pi Imager to flash to SD card
# Enable SSH during imaging process
```

#### 1.2 Initial System Configuration

```bash
# Boot the Pi and connect via SSH
ssh pi@<raspberry_pi_ip>

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git python3-pip python3-venv cmake build-essential \
    libusb-1.0-0-dev pkg-config libtool autoconf automake \
    libfftw3-dev librtlsdr-dev libhackrf-dev

# Configure system for real-time processing
sudo nano /boot/firmware/config.txt
# Add the following lines:
# gpu_mem=64
# force_turbo=1
# over_voltage=6

# Set CPU governor to performance
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl enable cpufrequtils
```

#### 1.3 USB Configuration for HackRF

```bash
# Create udev rules for HackRF
sudo nano /etc/udev/rules.d/53-hackrf.rules

# Add the following content:
ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", SYMLINK+="hackrf-one", MODE="0666", GROUP="plugdev"
ATTR{idVendor}=="1d50", ATTR{idProduct}=="cc15", SYMLINK+="hackrf-one", MODE="0666", GROUP="plugdev"

# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 2. HackRF One Setup and Testing

#### 2.1 HackRF Software Installation

```bash
# Install HackRF tools and libraries
sudo apt install -y hackrf libhackrf-dev

# Test HackRF connection
hackrf_info

# Expected output should show:
# hackrf_device_list_open() failed: HACKRF_ERROR_NOT_FOUND (-5)
# (This is normal if HackRF is not connected yet)

# Connect HackRF via USB and test again
hackrf_info
# Should now show device information including:
# Found HackRF
# Index: 0
# Serial number: 0000000000000000457863c8220e2d4f
# Board ID Number: 2 (HackRF One)
```

#### 2.2 HackRF Firmware Update

```bash
# Download latest firmware
cd /tmp
wget https://github.com/greatscottgadgets/hackrf/releases/download/v2023.01.1/hackrf-2023.01.1.tar.xz
tar -xf hackrf-2023.01.1.tar.xz
cd hackrf-2023.01.1

# Update firmware (if needed)
sudo hackrf_spiflash -w firmware-bin/hackrf_one_usb.bin

# Verify firmware
hackrf_info
```

#### 2.3 HackRF Performance Testing

```bash
# Test signal generation capability
hackrf_transfer -t test_signal.bin -f 1575420000 -s 2600000 -a 1 -x 40

# Test signal reception (optional)
timeout 10s hackrf_transfer -r /tmp/test_capture.bin -f 1575420000 -s 2600000 -a 1 -l 40 -g 20

# Check if files were created successfully
ls -la test_signal.bin /tmp/test_capture.bin
```

### 3. GPS-SDR-SIM Installation

#### 3.1 Download and Compile GPS-SDR-SIM

```bash
# Clone GPS-SDR-SIM repository
cd /home/pi
git clone https://github.com/osqzss/gps-sdr-sim.git
cd gps-sdr-sim

# Compile the software
gcc -O3 -o gps-sdr-sim gpssim.c -lm

# Verify compilation
./gps-sdr-sim
# Should show usage information
```

#### 3.2 Download GNSS Data

```bash
# Create data directory
mkdir -p /home/pi/gnss-data

# Download current GPS almanac (automated script)
cd /home/pi/gnss-data

# Download RINEX navigation file (current day)
wget -O brdc$(date +%j)0.$(date +%y)n.Z ftp://cddis.gsfc.nasa.gov/gnss/data/daily/$(date +%Y)/brdc/brdc$(date +%j)0.$(date +%y)n.Z
gunzip brdc$(date +%j)0.$(date +%y)n.Z

# Alternative: Use sample data for testing
wget https://raw.githubusercontent.com/osqzss/gps-sdr-sim/master/brdc3540.14n
```

### 4. GNU Radio Installation

#### 4.1 Install GNU Radio Framework

```bash
# Install GNU Radio and dependencies
sudo apt install -y gnuradio gnuradio-dev gr-osmosdr liblog4cpp5-dev

# Verify GNU Radio installation
gnuradio-config-info --version
# Should show version 3.10.x or later

# Test GNU Radio Companion (if X11 forwarding is available)
gnuradio-companion
```

#### 4.2 Install Additional GNU Radio Modules

```bash
# Install OsmoSDR support for HackRF
sudo apt install -y gr-osmosdr

# Test HackRF in GNU Radio
python3 -c "
import osmosdr
source = osmosdr.source()
source.set_sample_rate(2e6)
source.set_center_freq(1575.42e6)
source.set_freq_corr(0)
source.set_dc_offset_mode(0)
source.set_iq_balance_mode(0)
source.set_gain_mode(False)
source.set_gain(20)
print('HackRF GNU Radio integration successful')
"
```

### 5. System Optimization

#### 5.1 Memory and CPU Optimization

```bash
# Increase swap file size for large signal processing
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Set CPU frequency scaling
sudo nano /etc/rc.local
# Add before 'exit 0':
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Optimize kernel parameters for real-time processing
sudo nano /etc/sysctl.conf
# Add the following lines:
kernel.sched_rt_runtime_us=-1
vm.swappiness=10
net.core.rmem_max=134217728
net.core.wmem_max=134217728
```

#### 5.2 USB Performance Optimization

```bash
# Optimize USB for HackRF
sudo nano /boot/firmware/cmdline.txt
# Add to the end of the existing line:
usbcore.usbfs_memory_mb=1000

# Create HackRF optimization script
sudo nano /usr/local/bin/optimize-hackrf.sh
chmod +x /usr/local/bin/optimize-hackrf.sh

# Script content:
#!/bin/bash
echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb
echo 0 > /sys/bus/usb/devices/*/power/autosuspend
echo on > /sys/bus/usb/devices/*/power/control
```

### 6. Hardware Validation Tests

#### 6.1 Complete System Test

```bash
# Create test script
nano /home/pi/test-hardware.sh
chmod +x /home/pi/test-hardware.sh

# Test script content:
#!/bin/bash
echo "=== GNSS Simulator Hardware Validation ==="

echo "1. Testing HackRF connection..."
if hackrf_info | grep -q "Found HackRF"; then
    echo "✓ HackRF One detected successfully"
else
    echo "✗ HackRF One not detected"
    exit 1
fi

echo "2. Testing GPS-SDR-SIM..."
if [ -f "/home/pi/gps-sdr-sim/gps-sdr-sim" ]; then
    echo "✓ GPS-SDR-SIM compiled successfully"
else
    echo "✗ GPS-SDR-SIM not found"
    exit 1
fi

echo "3. Testing GNSS data availability..."
if ls /home/pi/gnss-data/*.n > /dev/null 2>&1; then
    echo "✓ GNSS navigation data available"
else
    echo "✗ GNSS navigation data missing"
    exit 1
fi

echo "4. Testing GNU Radio..."
if gnuradio-config-info --version > /dev/null 2>&1; then
    echo "✓ GNU Radio installed successfully"
else
    echo "✗ GNU Radio not properly installed"
    exit 1
fi

echo "5. Testing memory and CPU..."
TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
if [ $TOTAL_MEM -ge 7000 ]; then
    echo "✓ Sufficient memory available: ${TOTAL_MEM}MB"
else
    echo "! Warning: Low memory detected: ${TOTAL_MEM}MB"
fi

echo "=== Hardware validation complete ==="
```

#### 6.2 Signal Generation Test

```bash
# Generate test GPS signal
cd /home/pi/gps-sdr-sim

# Test signal generation for London coordinates
./gps-sdr-sim -e /home/pi/gnss-data/brdc3540.14n -l 51.5074,-0.1278,100 -d 10

# This should create gpssim.bin file
ls -la gpssim.bin

# Test transmission (10 seconds)
hackrf_transfer -t gpssim.bin -f 1575420000 -s 2600000 -a 1 -x 40

echo "Test signal transmitted for 10 seconds"
echo "Use GNSS receiver or smartphone to verify signal"
```

### 7. Network Configuration

#### 7.1 Static IP Configuration (Optional)

```bash
# Configure static IP for reliable API access
sudo nano /etc/dhcpcd.conf

# Add for Ethernet:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8

# Restart networking
sudo systemctl restart dhcpcd
```

#### 7.2 Firewall Configuration

```bash
# Install and configure UFW firewall
sudo apt install -y ufw

# Allow SSH
sudo ufw allow ssh

# Allow API port (8000)
sudo ufw allow 8000

# Enable firewall
sudo ufw --force enable
```

### 8. System Monitoring

#### 8.1 Create Monitoring Scripts

```bash
# System health monitoring
nano /home/pi/monitor-system.sh
chmod +x /home/pi/monitor-system.sh

# Monitoring script content:
#!/bin/bash
echo "=== System Status ==="
echo "CPU Temperature: $(vcgencmd measure_temp)"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "Memory Usage: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{print $5}')"
echo "USB Devices:"
lsusb | grep -i hackrf
echo "=== End Status ==="
```

### 9. Troubleshooting Common Issues

#### 9.1 HackRF Not Detected

```bash
# Check USB connection
lsusb | grep 1d50

# Check permissions
ls -la /dev/bus/usb/*

# Reset HackRF
sudo hackrf_spiflash -R

# Check dmesg for errors
dmesg | tail -20
```

#### 9.2 Performance Issues

```bash
# Check CPU frequency
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq

# Monitor system during signal generation
htop &
./test-signal-generation.sh
```

#### 9.3 Signal Quality Issues

```bash
# Check HackRF calibration
hackrf_calibrate

# Verify antenna connection
hackrf_transfer -r /tmp/noise_test.bin -f 1575420000 -s 2600000 -n 2600000

# Analyze captured data
hexdump -C /tmp/noise_test.bin | head -20
```

### 10. Installation Completion

After completing all steps, your system should have:

- ✓ Raspberry Pi 5 optimized for real-time processing
- ✓ HackRF One SDR properly configured and tested
- ✓ GPS-SDR-SIM compiled and functional
- ✓ GNU Radio framework installed
- ✓ Current GNSS data downloaded
- ✓ System monitoring and optimization
- ✓ Network configuration for API access

**Next Step**: Proceed to Milestone 1 implementation with basic GNSS signal generation.
