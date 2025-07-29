# GNSS Simulator Project Information for AI Assistant

## Project Overview
This is a complete GNSS (GPS) signal simulator implementation for laboratory use, built for Raspberry Pi 5 and HackRF One SDR.

## Frequently Used Commands

### Development and Testing
```bash
# Start the API server
python3 src/main.py server

# Run system tests
./test-system.sh

# Run quick signal test
./quick-start.sh

# Test signal generation only (no transmission)
python3 src/main.py generate --lat 51.5074 --lon -0.1278 --duration 60

# Test transmission with specific location
python3 src/main.py test --lat 40.7128 --lon -74.0060 --duration 30

# Check system status
python3 src/main.py status

# Run comprehensive signal validation
python3 validation/signal_validator.py comprehensive

# Monitor signal transmission
python3 validation/signal_validator.py monitor --duration 30
```

### API Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Set location (requires API key)
curl -X POST http://localhost:8000/api/v1/location \
  -H "Authorization: Bearer gnss-simulator-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 51.5074, "longitude": -0.1278, "altitude": 100}'

# Start transmission
curl -X POST http://localhost:8000/api/v1/start \
  -H "Authorization: Bearer gnss-simulator-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"duration": 300}'

# Stop transmission
curl -X POST http://localhost:8000/api/v1/stop \
  -H "Authorization: Bearer gnss-simulator-key-2024"
```

### Hardware Testing
```bash
# Test HackRF connection
hackrf_info

# Test GPS-SDR-SIM
/home/erez/gps-sdr-sim/gps-sdr-sim

# Check GNSS data files
ls -la /home/erez/gnss-data/

# Monitor system resources
htop
free -h
df -h
```

### Service Management
```bash
# Start/stop systemd service
sudo systemctl start gnss-simulator
sudo systemctl stop gnss-simulator
sudo systemctl status gnss-simulator

# View service logs
sudo journalctl -u gnss-simulator -f

# Enable/disable auto-start
sudo systemctl enable gnss-simulator
sudo systemctl disable gnss-simulator
```

## Code Style and Conventions

### Python
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Use dataclasses for structured data
- Implement proper error handling with try/catch blocks
- Use logging instead of print statements
- Format with black: `black src/`
- Lint with flake8: `flake8 src/`

### Documentation
- Use docstrings for all classes and functions
- Follow Google or NumPy docstring format
- Update README.md when adding new features
- Document API changes in api_documentation.md

### Configuration
- Store configuration in config.yaml
- Use environment variables for sensitive data
- Validate configuration parameters at startup

## Project Structure

```
gnss-simulator/
├── src/                    # Source code
│   ├── main.py            # Main application entry point
│   ├── api/               # FastAPI REST interface
│   │   └── server.py      # API server implementation
│   ├── gnss/              # GNSS signal generation
│   │   └── signal_generator.py
│   └── simulation/        # Location and constellation management
│       ├── location_engine.py
│       └── constellation_manager.py
├── docs/                  # Documentation
│   ├── installation_guide.md
│   ├── milestone1/        # Milestone 1 docs
│   └── milestone2/        # Milestone 2 docs
├── scripts/               # Installation and utility scripts
│   └── install.sh         # Main installation script
├── validation/            # Signal validation tools
│   └── signal_validator.py
├── tests/                 # Test suite
│   └── test_integration.py
├── config/                # Configuration files
├── data/                  # GNSS data storage
└── config.yaml           # Main configuration file
```

## Testing Approach

### Unit Tests
- Use pytest framework
- Test individual functions and classes
- Mock external dependencies (HackRF, file system)

### Integration Tests
- Test complete workflows
- Verify API endpoints
- Test hardware integration (when available)

### Validation Tests
- Signal quality validation
- Device compatibility testing
- Performance benchmarking

### Test Commands
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_integration.py -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html
```

## Dependencies

### System Packages
- hackrf libhackrf-dev (HackRF One support)
- gnuradio gnuradio-dev (GNU Radio framework)
- gr-osmosdr (OsmoSDR support)
- build-essential cmake (Compilation tools)

### Python Packages (requirements.txt)
- fastapi uvicorn (Web API framework)
- pydantic (Data validation)
- numpy scipy (Scientific computing)
- httpx (HTTP client for testing)
- pytest (Testing framework)

### External Software
- GPS-SDR-SIM (GNSS signal generation)
- RINEX navigation data (Satellite ephemeris)

## Hardware Setup

### Required Hardware
- Raspberry Pi 5 (8GB RAM)
- HackRF One SDR
- SMA antenna
- Quality USB-C power supply

### Important Notes
- HackRF requires proper USB permissions (handled by install script)
- Signal power must comply with local regulations
- Use only in laboratory environments
- Antenna placement affects signal quality

## Troubleshooting Common Issues

### HackRF Not Detected
1. Check USB connection and power
2. Verify udev rules: `ls -la /etc/udev/rules.d/*hackrf*`
3. Check user permissions: `groups $USER` (should include plugdev)
4. Try: `sudo hackrf_info`

### Signal Generation Fails
1. Check GPS-SDR-SIM binary exists and is executable
2. Verify GNSS data files exist in /home/erez/gnss-data/
3. Check available disk space
4. Review log files for specific errors

### API Server Issues
1. Check if port 8000 is available: `netstat -tulpn | grep 8000`
2. Verify firewall settings: `sudo ufw status`
3. Check service logs: `sudo journalctl -u gnss-simulator -n 50`

### Poor GPS Performance
1. Check antenna connection and placement
2. Verify signal power levels are appropriate
3. Ensure no RF interference
4. Try different test locations

## Security Considerations

### API Security
- Change default API key in production
- Use HTTPS for remote access
- Implement rate limiting if needed
- Monitor access logs

### RF Safety
- Ensure compliance with local regulations
- Use appropriate signal power levels
- Laboratory use only - not for outdoor deployment
- Proper antenna grounding and placement

## Performance Optimization

### System Tuning
- CPU governor set to "performance"
- Increased USB buffer memory
- Optimized kernel parameters for real-time processing
- Adequate cooling for continuous operation

### Memory Management
- Monitor RAM usage during operation
- Increase swap if needed for large signal files
- Clean up temporary files regularly

This file helps the AI assistant understand the project structure, common commands, and development practices for the GNSS Simulator.
