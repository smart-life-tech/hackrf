# System Architecture Document

## GNSS Simulator Laboratory Architecture

### 1. System Overview

The GNSS Simulator consists of three main layers:
1. **Hardware Layer**: HackRF One SDR + Raspberry Pi 5
2. **Signal Processing Layer**: GPS-SDR-SIM + GNU Radio
3. **Application Layer**: FastAPI REST interface + Web management

### 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────┬───────────────────┬───────────────────┤
│    FastAPI REST     │   Web Interface   │   Configuration   │
│      Server         │     (Optional)    │    Management     │
└─────────────────────┴───────────────────┴───────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Signal Processing Layer                      │
├─────────────────────┬───────────────────┬───────────────────┤
│   GNSS Signal Gen   │   GNU Radio       │   Constellation   │
│   (GPS-SDR-SIM)     │   Framework       │   Management      │
└─────────────────────┴───────────────────┴───────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Hardware Layer                           │
├─────────────────────┬───────────────────┬───────────────────┤
│   Raspberry Pi 5    │    HackRF One     │   RF Output       │
│   (8GB RAM)         │      SDR          │   (~1575 MHz)     │
└─────────────────────┴───────────────────┴───────────────────┘
```

### 3. Component Specifications

#### 3.1 Hardware Layer

**Raspberry Pi 5 Configuration:**
- **RAM**: 8GB (optimized for real-time processing)
- **OS**: Raspberry Pi OS Lite (minimal overhead)
- **CPU Optimization**: Real-time kernel patches for low-latency processing
- **Storage**: High-speed SD card (Class 10 or better)

**HackRF One SDR:**
- **Frequency Range**: 1 MHz to 6 GHz
- **GNSS Target**: L1 band (1575.42 MHz)
- **Sample Rate**: 20 MSPS (configurable)
- **Bandwidth**: 20 MHz maximum
- **Interface**: USB 2.0 to Raspberry Pi

#### 3.2 Signal Processing Layer

**GPS-SDR-SIM:**
- **Purpose**: Generate GPS L1 C/A signals
- **Input**: RINEX navigation data, static location
- **Output**: Complex IQ samples for HackRF
- **Satellite Support**: 24+ GPS satellites
- **Signal Types**: L1 C/A code (1023-chip Gold codes)

**GNU Radio Framework:**
- **Signal Flow**: IQ sample processing and modulation
- **Real-time Processing**: Continuous signal streaming
- **Monitoring**: Spectrum analysis and signal quality metrics
- **Flowgraph**: Custom GNSS signal processing chain

#### 3.3 Application Layer

**FastAPI REST Server:**
- **Port**: 8000 (configurable)
- **Authentication**: API key-based
- **Endpoints**: Location, control, status, constellation
- **Response Format**: JSON
- **Logging**: Structured logging for debugging

### 4. Signal Generation Flow

```
1. [Location Input] → [Coordinate Validation] → [WGS84 Conversion]
                                ↓
2. [Almanac Data] → [Satellite Visibility] → [Ephemeris Calculation]
                                ↓
3. [Signal Timing] → [C/A Code Generation] → [Navigation Message]
                                ↓
4. [IQ Modulation] → [GNU Radio Processing] → [HackRF Transmission]
                                ↓
5. [RF Output @ 1575.42 MHz] → [GNSS Receivers]
```

### 5. Data Flow Architecture

#### 5.1 Input Data Sources
- **Static Location**: Latitude/longitude coordinates (WGS84)
- **GNSS Almanac**: Current GPS constellation data
- **Ephemeris Data**: Precise satellite orbital parameters
- **System Configuration**: Timing, power levels, frequency offsets

#### 5.2 Processing Pipeline
1. **Location Processing**: Coordinate validation and conversion
2. **Satellite Selection**: Visibility calculation and satellite choice
3. **Signal Generation**: C/A code and navigation message creation
4. **Modulation**: BPSK modulation and carrier frequency synthesis
5. **Transmission**: Real-time streaming via HackRF

#### 5.3 Output Signals
- **L1 C/A Signal**: 1575.42 MHz carrier
- **Signal Power**: Adjustable (-130 to -125 dBm typical)
- **Coverage**: Laboratory environment (10-30m range)

### 6. Real-time Processing Requirements

#### 6.1 Timing Constraints
- **Signal Generation**: 1 ms navigation frame timing
- **Sample Rate**: 2.6 MSPS minimum for L1 bandwidth
- **Latency**: <100ms for location updates
- **Synchronization**: GPS time alignment

#### 6.2 Memory Requirements
- **RAM Usage**: 2-4 GB for signal processing buffers
- **Storage**: 1 GB for almanac/ephemeris data and logs
- **Buffer Size**: 10-20 seconds of IQ samples

### 7. System Interfaces

#### 7.1 Hardware Interfaces
- **USB**: HackRF One to Raspberry Pi
- **SMA Connector**: RF output from HackRF
- **Ethernet**: Network connectivity for API access
- **GPIO**: Optional status LEDs and controls

#### 7.2 Software Interfaces
- **REST API**: HTTP/JSON for external control
- **Configuration Files**: YAML/JSON for system settings
- **Log Files**: Structured logging for monitoring
- **Data Files**: RINEX format for almanac/ephemeris

### 8. Performance Specifications

#### 8.1 Signal Quality Metrics
- **C/N0 Ratio**: >35 dB-Hz (typical GNSS receiver threshold)
- **Position Accuracy**: 5-10 meters (laboratory environment)
- **Acquisition Time**: <30 seconds cold start
- **Signal Availability**: 6+ satellites visible

#### 8.2 System Performance
- **CPU Usage**: <70% during signal generation
- **Memory Usage**: <4 GB RAM
- **Power Consumption**: <15W total system
- **Thermal Management**: Passive cooling sufficient

### 9. Security and Safety

#### 9.1 Security Features
- **API Authentication**: Bearer token or API key
- **Input Validation**: Coordinate and parameter bounds checking
- **Rate Limiting**: API request throttling
- **Logging**: Security event monitoring

#### 9.2 Safety Considerations
- **RF Power Limits**: Compliant with local regulations
- **Laboratory Use Only**: Not for outdoor/aviation use
- **Signal Identification**: Clear marking as simulated signals
- **Emergency Shutdown**: Immediate signal termination capability

### 10. Scalability and Extensions

#### 10.1 Future Enhancements
- **Multi-Constellation**: GLONASS, Galileo, BeiDou support
- **Dynamic Scenarios**: Moving platform simulation
- **Interference Simulation**: Jamming and spoofing scenarios
- **Multi-Frequency**: L1, L2, L5 signal support

#### 10.2 Integration Points
- **External Systems**: Test equipment and analyzers
- **Database Integration**: Real-time almanac updates
- **Cloud Connectivity**: Remote monitoring and control
- **Automation**: Scripted test scenarios
