# GNSS Simulator API Documentation

## Overview

The GNSS Simulator provides a RESTful API for controlling GPS signal generation and transmission using HackRF One SDR. This API enables laboratory testing and development of GNSS receivers.

### Base URL
```
http://<raspberry_pi_ip>:8000
```

### Authentication
API endpoints require Bearer token authentication (except health and status endpoints).

**Header:**
```
Authorization: Bearer gnss-simulator-key-2024
```

## API Endpoints

### 1. System Status and Health

#### GET /api/v1/status
Get complete system status information.

**Response:**
```json
{
  "is_transmitting": false,
  "hackrf_connected": true,
  "ephemeris_available": true,
  "data_directory": "/home/pi/gnss-data",
  "gps_sdr_sim_available": true,
  "current_location": {
    "latitude": 51.5074,
    "longitude": -0.1278,
    "altitude": 100.0
  },
  "transmission_pid": null
}
```

#### GET /api/v1/health
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "hackrf_connected": true,
    "gps_sdr_sim_available": true,
    "ephemeris_data": true
  }
}
```

### 2. Location Management

#### GET /api/v1/location
Get current simulated location.

**Authentication:** Required

**Response:**
```json
{
  "latitude": 51.5074,
  "longitude": -0.1278,
  "altitude": 100.0,
  "status": "configured"
}
```

**Error Responses:**
- `404` - No location configured

#### POST /api/v1/location
Set simulated location coordinates.

**Authentication:** Required

**Request Body:**
```json
{
  "latitude": 51.5074,
  "longitude": -0.1278,
  "altitude": 100.0
}
```

**Parameters:**
- `latitude` (float): Latitude in decimal degrees (-90 to 90)
- `longitude` (float): Longitude in decimal degrees (-180 to 180)
- `altitude` (float): Altitude in meters above WGS84 ellipsoid (optional, default: 100)

**Response:**
```json
{
  "success": true,
  "message": "Location updated successfully",
  "data": {
    "latitude": 51.5074,
    "longitude": -0.1278,
    "altitude": 100.0
  }
}
```

**Error Responses:**
- `400` - Invalid coordinates
- `401` - Authentication required

### 3. Signal Transmission Control

#### POST /api/v1/start
Start GNSS signal transmission.

**Authentication:** Required

**Request Body:**
```json
{
  "duration": 300,
  "frequency": 1575420000,
  "sample_rate": 2600000,
  "tx_gain": 40,
  "power_level": 1
}
```

**Parameters:**
- `duration` (int): Transmission duration in seconds (1-3600, default: 300)
- `frequency` (int): Carrier frequency in Hz (default: 1575420000)
- `sample_rate` (int): Sample rate in Hz (default: 2600000)
- `tx_gain` (int): HackRF TX gain 0-47 (default: 40)
- `power_level` (int): Signal power level 0-1 (default: 1)

**Response:**
```json
{
  "success": true,
  "message": "Signal transmission started",
  "data": {
    "location": {
      "latitude": 51.5074,
      "longitude": -0.1278,
      "altitude": 100.0
    },
    "duration": 300,
    "frequency": 1575420000
  }
}
```

**Error Responses:**
- `400` - Location not set or invalid parameters
- `401` - Authentication required
- `500` - Failed to start transmission

#### POST /api/v1/stop
Stop GNSS signal transmission.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "message": "Signal transmission stopped"
}
```

**Error Responses:**
- `401` - Authentication required
- `500` - Failed to stop transmission

### 4. Information Endpoints

#### GET /
Root endpoint with API information.

**Response:**
```json
{
  "name": "GNSS Simulator API",
  "version": "1.0.0",
  "status": "operational",
  "documentation": "/docs"
}
```

## Usage Examples

### Setting Location and Starting Transmission

```bash
# Set location to London
curl -X POST http://192.168.1.100:8000/api/v1/location \
  -H "Authorization: Bearer gnss-simulator-key-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 51.5074,
    "longitude": -0.1278,
    "altitude": 100
  }'

# Start transmission for 5 minutes
curl -X POST http://192.168.1.100:8000/api/v1/start \
  -H "Authorization: Bearer gnss-simulator-key-2024" \
  -H "Content-Type: application/json" \
  -d '{
    "duration": 300
  }'

# Check status
curl http://192.168.1.100:8000/api/v1/status

# Stop transmission
curl -X POST http://192.168.1.100:8000/api/v1/stop \
  -H "Authorization: Bearer gnss-simulator-key-2024"
```

### Python Client Example

```python
import httpx
import asyncio

async def simulate_location():
    base_url = "http://192.168.1.100:8000"
    headers = {"Authorization": "Bearer gnss-simulator-key-2024"}
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        # Set location
        location_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10
        }
        
        response = await client.post(
            "/api/v1/location",
            json=location_data,
            headers=headers
        )
        print(f"Location set: {response.json()}")
        
        # Start transmission
        transmission_data = {"duration": 120}
        response = await client.post(
            "/api/v1/start",
            json=transmission_data,
            headers=headers
        )
        print(f"Transmission started: {response.json()}")
        
        # Wait and stop
        await asyncio.sleep(60)
        
        response = await client.post("/api/v1/stop", headers=headers)
        print(f"Transmission stopped: {response.json()}")

# Run the example
asyncio.run(simulate_location())
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const baseURL = 'http://192.168.1.100:8000';
const headers = {
  'Authorization': 'Bearer gnss-simulator-key-2024',
  'Content-Type': 'application/json'
};

async function simulateLocation() {
  try {
    // Set location to Tokyo
    const locationResponse = await axios.post(`${baseURL}/api/v1/location`, {
      latitude: 35.6762,
      longitude: 139.6503,
      altitude: 40
    }, { headers });
    
    console.log('Location set:', locationResponse.data);
    
    // Start transmission
    const transmissionResponse = await axios.post(`${baseURL}/api/v1/start`, {
      duration: 180
    }, { headers });
    
    console.log('Transmission started:', transmissionResponse.data);
    
    // Wait 30 seconds then stop
    setTimeout(async () => {
      const stopResponse = await axios.post(`${baseURL}/api/v1/stop`, {}, { headers });
      console.log('Transmission stopped:', stopResponse.data);
    }, 30000);
    
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

simulateLocation();
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (authentication required)
- `404` - Not Found (endpoint or resource not found)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "success": false,
  "message": "Error description",
  "details": "Additional error information"
}
```

### Common Error Scenarios

1. **Invalid Coordinates**
   ```json
   {
     "success": false,
     "message": "Latitude must be between -90 and 90 degrees"
   }
   ```

2. **Location Not Set**
   ```json
   {
     "success": false,
     "message": "Location must be set before starting transmission"
   }
   ```

3. **HackRF Not Connected**
   ```json
   {
     "success": false,
     "message": "HackRF not detected or not accessible"
   }
   ```

## Interactive API Documentation

The GNSS Simulator provides interactive API documentation using Swagger UI:

- **Swagger UI**: `http://<raspberry_pi_ip>:8000/docs`
- **ReDoc**: `http://<raspberry_pi_ip>:8000/redoc`

These interfaces allow you to:
- Explore all API endpoints
- Test API calls directly from the browser
- View request/response schemas
- Download OpenAPI specification

## Rate Limiting and Best Practices

### Recommended Usage Patterns

1. **Set location once** before starting multiple transmission sessions
2. **Check system status** before starting transmission
3. **Stop transmission** before changing location
4. **Monitor health endpoint** for system monitoring

### Performance Considerations

- Location changes require transmission restart
- Signal generation takes 10-30 seconds depending on duration
- Maximum transmission duration is 1 hour (3600 seconds)
- Minimum gap between transmissions: 5 seconds

### Security Notes

- Change default API key for production use
- Use HTTPS in production environments
- Restrict API access to trusted networks
- Monitor API usage logs

## Testing and Validation

### API Testing Tools

**HTTPie:**
```bash
# Check status
http GET :8000/api/v1/status

# Set location with authentication
http POST :8000/api/v1/location \
  Authorization:"Bearer gnss-simulator-key-2024" \
  latitude:=51.5074 longitude:=-0.1278 altitude:=100
```

**Postman Collection:**
Import the API endpoints into Postman for interactive testing.

**Automated Testing:**
```bash
# Run integration tests
cd gnss-simulator
python -m pytest tests/test_integration.py -v
```

### Validation Checklist

- [ ] API responds to health checks
- [ ] Location setting validates coordinates
- [ ] Transmission starts and stops successfully
- [ ] Error handling works correctly
- [ ] Authentication is enforced
- [ ] Documentation is accessible

## API Versioning

Current API version: **v1**

Future versions will be accessible via:
- `/api/v2/...` for version 2
- `/api/v3/...` for version 3

The v1 API will be maintained for backward compatibility.
