# GNSS Simulator Laboratory Implementation

A complete laboratory-grade GNSS constellation simulator using HackRF One SDR and Raspberry Pi 5 for GNSS research, testing, and development.

## Project Overview

This project implements a software-defined GNSS signal generator capable of simulating GPS/GNSS constellations for laboratory testing and development purposes.

### Hardware Requirements

- **Software Defined Radio**: HackRF One SDR
- **Processing Unit**: Raspberry Pi 5 (8GB RAM) with Raspberry Pi OS Lite
- **Coverage**: Laboratory environment (indoor, ~10-30m range)

### Software Stack

- **GNSS Signal Generation**: GPS-SDR-SIM for satellite signal synthesis
- **Signal Processing**: GNU Radio framework for real-time signal generation
- **Web Interface**: Python FastAPI for REST API implementation
- **Navigation Engine**: Custom positioning and timing simulation

## Quick Start

### Installation

1. **Hardware Setup**
   ```bash
   # Follow docs/milestone1/hardware_setup.md
   ```

2. **Software Installation**
   ```bash
   cd gnss-simulator
   ./scripts/install.sh
   ```

3. **Start the Simulator**
   ```bash
   python src/main.py
   ```

### API Usage

```bash
# Set location
curl -X POST http://localhost:8000/api/v1/location \
  -H "Content-Type: application/json" \
  -d '{"latitude": 51.5074, "longitude": -0.1278}'

# Start transmission
curl -X POST http://localhost:8000/api/v1/start

# Check status
curl http://localhost:8000/api/v1/status
```

## Project Structure

```
gnss-simulator/
├── src/                    # Source code
│   ├── api/               # FastAPI REST interface
│   ├── gnss/              # GNSS signal generation
│   ├── simulation/        # Location and timing simulation
│   └── utils/             # Utility functions
├── docs/                  # Documentation
│   ├── milestone1/        # Milestone 1 documentation
│   └── milestone2/        # Milestone 2 documentation
├── config/                # Configuration files
├── scripts/               # Installation and utility scripts
├── data/                  # GNSS almanac and ephemeris data
├── validation/            # Signal validation tools
└── tests/                 # Test suite
```

## Milestones

- **Milestone 1**: Core GNSS Signal Generation
- **Milestone 2**: API-driven Static Location Simulation

## Documentation

- [System Architecture](docs/milestone1/architecture.md)
- [Hardware Setup Guide](docs/milestone1/hardware_setup.md)
- [API Documentation](docs/milestone2/api_documentation.md)
- [Signal Validation](docs/milestone1/signal_validation.md)

## License

Open Source - See LICENSE file for details.
/home/erez/gps-sdr-sim/gps-sdr-sim -e /home/erez/gnss-data/brdc2130.25n  -l 30.286502,120.032669,100 -b 8