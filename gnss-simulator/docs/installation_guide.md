# GNSS Simulator Installation Guide

Complete step-by-step installation and deployment guide for the GNSS Simulator Laboratory Implementation.

## Prerequisites

### Hardware Requirements

- **Raspberry Pi 5** (8GB RAM recommended)
- **HackRF One SDR** with USB cable
- **MicroSD card** (32GB+, Class 10 or better)
- **USB-C power supply** (5V, 5A for Pi 5)
- **SMA antenna** or RF connector for HackRF
- **Network connection** (Ethernet or Wi-Fi)

### Software Requirements

- Raspberry Pi OS Lite (64-bit) - Latest version
- Internet connection for downloads
- SSH access to Raspberry Pi

## Installation Steps

### Step 1: Prepare Raspberry Pi

1. **Flash Raspberry Pi OS**
   ```bash
   # Download Raspberry Pi Imager
   # Flash Raspberry Pi OS Lite (64-bit) to SD card
   # Enable SSH during imaging process
   ```

2. **Initial Boot and Configuration**
   ```bash
   # Boot Pi and connect via SSH
   ssh pi@<raspberry_pi_ip>
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Configure locale and timezone
   sudo raspi-config
   # Select: 5 Localisation Options
   # Configure timezone and locale as needed
   ```

### Step 2: Run Automated Installation

1. **Download and Extract Project**
   ```bash
   cd /home/pi
   
   # If you have the project files, extract them:
   # tar -xzf gnss-simulator.tar.gz
   
   # Or clone from repository:
   # git clone <repository_url> gnss-simulator
   
   cd gnss-simulator
   ```

2. **Run Installation Script**
   ```bash
   chmod +x scripts/install.sh
   ./scripts/install.sh
   ```

   The installation script will:
   - Install all required packages
   - Set up HackRF permissions
   - Compile GPS-SDR-SIM
   - Configure system optimizations
   - Download sample GNSS data
   - Create systemd service

3. **Reboot System**
   ```bash
   sudo reboot
   ```

### Step 3: Hardware Setup

1. **Connect Hardware**
   - Connect HackRF One to Raspberry Pi via USB
   - Connect SMA antenna to HackRF RF output
   - Ensure Pi is powered with adequate power supply

2. **Verify Hardware Detection**
   ```bash
   # Test HackRF detection
   hackrf_info
   
   # Should show:
   # Found HackRF
   # Index: 0
   # Serial number: [serial_number]
   # Board ID Number: 2 (HackRF One)
   ```

### Step 4: System Validation

1. **Run System Test**
   ```bash
   cd /home/pi/gnss-simulator
   ./test-system.sh
   ```

   Expected output:
   ```
   === GNSS Simulator System Test ===
   1. Testing HackRF connection...
   ✓ HackRF detected
   2. Testing GPS-SDR-SIM...
   ✓ GPS-SDR-SIM available
   3. Testing GNSS data...
   ✓ GNSS data available
   4. Testing Python dependencies...
   ✓ Python dependencies OK
   5. System status...
   === Test Complete ===
   ```

2. **Run Quick Start Test**
   ```bash
   ./quick-start.sh
   ```

   This will:
   - Generate a test signal for London coordinates
   - Transmit for 60 seconds
   - Verify signal generation works

### Step 5: API Server Setup

1. **Manual Server Start**
   ```bash
   cd /home/pi/gnss-simulator
   python3 src/main.py server
   ```

   Server will start on port 8000:
   ```
   Starting GNSS Simulator API Server
   ========================================
   Host: 0.0.0.0
   Port: 8000
   API Documentation: http://0.0.0.0:8000/docs
   ========================================
   ```

2. **Enable Automatic Startup (Optional)**
   ```bash
   # Enable systemd service
   sudo systemctl enable gnss-simulator
   sudo systemctl start gnss-simulator
   
   # Check service status
   sudo systemctl status gnss-simulator
   ```

### Step 6: API Testing

1. **Test API Health**
   ```bash
   # Replace IP with your Pi's IP address
   curl http://192.168.1.100:8000/api/v1/health
   ```

2. **Test Location Setting**
   ```bash
   # Set London coordinates
   curl -X POST http://192.168.1.100:8000/api/v1/location \
     -H "Authorization: Bearer gnss-simulator-key-2024" \
     -H "Content-Type: application/json" \
     -d '{"latitude": 51.5074, "longitude": -0.1278, "altitude": 100}'
   ```

3. **Start Test Transmission**
   ```bash
   # Start 60-second transmission
   curl -X POST http://192.168.1.100:8000/api/v1/start \
     -H "Authorization: Bearer gnss-simulator-key-2024" \
     -H "Content-Type: application/json" \
     -d '{"duration": 60}'
   ```

## Configuration

### API Configuration

Edit `/home/pi/gnss-simulator/config.yaml`:

```yaml
gnss:
  data_directory: "/home/pi/gnss-data"
  gps_sdr_sim_path: "/home/pi/gps-sdr-sim/gps-sdr-sim"
  
hackrf:
  frequency: 1575420000  # L1 band
  sample_rate: 2600000
  tx_gain: 40
  power_level: 1

api:
  host: "0.0.0.0"
  port: 8000
  api_key: "your-secure-api-key-here"  # Change this!

logging:
  level: "INFO"
  file: "/home/pi/gnss-simulator/logs/gnss-simulator.log"
```

### Network Configuration

1. **Static IP (Recommended)**
   ```bash
   sudo nano /etc/dhcpcd.conf
   
   # Add:
   interface eth0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=8.8.8.8
   ```

2. **Firewall Setup**
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 8000
   sudo ufw --force enable
   ```

## Testing with Devices

### iPhone Testing

1. **Prepare iPhone**
   - Enable Location Services
   - Open Maps or GPS test app
   - Ensure Wi-Fi/cellular data is disabled (optional)

2. **Test Procedure**
   - Set simulator location via API
   - Start signal transmission
   - Wait 30-60 seconds for GPS acquisition
   - Verify location appears on device

### Android Testing

1. **Prepare Android Device**
   - Enable Developer Options
   - Enable "Mock location app" if needed
   - Install GPS test app (e.g., "GPS Test")

2. **Test Procedure**
   - Same as iPhone testing
   - Monitor satellite acquisition in GPS test app
   - Verify 4+ satellites are acquired

### Acceptance Criteria Validation

**Milestone 1:**
- ✅ HackRF One generates recognizable GNSS signals
- ✅ Signals can be received by smartphone devices

**Milestone 2:**
- ✅ Static location settable via API
- ✅ Full GNSS constellation with 6+ visible satellites
- ✅ Position accuracy within 5-10 meters
- ✅ iPhone and Android show accurate position fix

## Troubleshooting

### Common Issues

1. **HackRF Not Detected**
   ```bash
   # Check USB connection
   lsusb | grep 1d50
   
   # Check permissions
   ls -la /dev/bus/usb/*/
   
   # Reload udev rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

2. **Signal Generation Fails**
   ```bash
   # Check GPS-SDR-SIM
   /home/pi/gps-sdr-sim/gps-sdr-sim
   
   # Check GNSS data
   ls -la /home/pi/gnss-data/
   
   # Download fresh data
   cd /home/pi/gnss-data
   wget https://raw.githubusercontent.com/osqzss/gps-sdr-sim/master/brdc3540.14n
   ```

3. **No GPS Fix on Phone**
   - Check antenna connection
   - Verify signal power level
   - Ensure phone is close to antenna (1-5 meters)
   - Try different location coordinates
   - Check for interference sources

4. **API Not Responding**
   ```bash
   # Check service status
   sudo systemctl status gnss-simulator
   
   # Check logs
   tail -f /home/pi/gnss-simulator/logs/gnss-simulator.log
   
   # Restart service
   sudo systemctl restart gnss-simulator
   ```

### Performance Optimization

1. **CPU Performance**
   ```bash
   # Check CPU frequency
   cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
   
   # Set performance mode
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```

2. **Memory Usage**
   ```bash
   # Monitor memory during operation
   free -h
   htop
   
   # Increase swap if needed
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

### Log Files

Monitor these log files for troubleshooting:

- **System logs**: `/var/log/syslog`
- **API logs**: `/home/pi/gnss-simulator/logs/gnss-simulator.log`
- **Service logs**: `sudo journalctl -u gnss-simulator -f`

## Maintenance

### Regular Tasks

1. **Update GNSS Data**
   ```bash
   cd /home/pi/gnss-simulator
   python3 src/simulation/constellation_manager.py
   ```

2. **System Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Log Rotation**
   ```bash
   # Configure logrotate for API logs
   sudo nano /etc/logrotate.d/gnss-simulator
   ```

### Backup and Restore

1. **Backup Configuration**
   ```bash
   tar -czf gnss-simulator-backup.tar.gz \
     /home/pi/gnss-simulator/config.yaml \
     /home/pi/gnss-data/ \
     /etc/systemd/system/gnss-simulator.service
   ```

2. **Restore Configuration**
   ```bash
   tar -xzf gnss-simulator-backup.tar.gz -C /
   sudo systemctl daemon-reload
   sudo systemctl enable gnss-simulator
   ```

## Security Considerations

### Production Deployment

1. **Change API Key**
   ```bash
   # Generate secure API key
   openssl rand -hex 32
   
   # Update config.yaml
   nano /home/pi/gnss-simulator/config.yaml
   ```

2. **Enable HTTPS (Optional)**
   ```bash
   # Install certbot for SSL certificates
   sudo apt install certbot
   
   # Configure reverse proxy with nginx
   sudo apt install nginx
   ```

3. **Network Security**
   - Use VPN for remote access
   - Restrict API access to trusted networks
   - Monitor access logs regularly

### Legal Compliance

**Important:** Ensure compliance with local regulations:
- This system is for laboratory use only
- Do not use outdoors or near airports
- Comply with RF emission regulations
- Clearly mark all signals as simulated

## Support and Documentation

### Additional Resources

- **API Documentation**: `http://<pi_ip>:8000/docs`
- **System Architecture**: `docs/milestone1/architecture.md`
- **Hardware Setup**: `docs/milestone1/hardware_setup.md`
- **Signal Validation**: `validation/signal_validator.py`

### Getting Help

1. **Check System Status**
   ```bash
   ./test-system.sh
   python3 validation/signal_validator.py comprehensive
   ```

2. **Review Logs**
   ```bash
   tail -f /home/pi/gnss-simulator/logs/gnss-simulator.log
   sudo journalctl -u gnss-simulator -f
   ```

3. **Contact Support**
   - Provide system test output
   - Include relevant log files
   - Describe specific issue and steps to reproduce

## Installation Complete

After successful installation, you should have:

- ✅ Raspberry Pi 5 optimized for GNSS simulation
- ✅ HackRF One configured and tested
- ✅ GPS-SDR-SIM compiled and functional
- ✅ FastAPI server running on port 8000
- ✅ Complete API for location control
- ✅ Signal validation tools
- ✅ System monitoring and logging
- ✅ Device testing capabilities

**Next Steps:**
1. Test with iPhone/Android devices
2. Validate position accuracy
3. Customize for specific use cases
4. Set up automated monitoring

The GNSS Simulator is now ready for laboratory use and GNSS receiver development!
