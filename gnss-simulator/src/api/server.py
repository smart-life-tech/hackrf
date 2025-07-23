#!/usr/bin/env python3
"""
FastAPI Server for GNSS Simulator

Provides REST API endpoints for controlling the GNSS signal generator.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import os

from gnss.signal_generator import GNSSSignalGenerator, GNSSConfig

# API Models
class LocationRequest(BaseModel):
    """Request model for setting location"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    altitude: float = Field(100.0, ge=-1000, description="Altitude in meters above WGS84 ellipsoid")

class LocationResponse(BaseModel):
    """Response model for location operations"""
    latitude: float
    longitude: float
    altitude: float
    status: str

class SystemStatus(BaseModel):
    """System status response model"""
    is_transmitting: bool
    hackrf_connected: bool
    ephemeris_available: bool
    data_directory: str
    gps_sdr_sim_available: bool
    current_location: Optional[Dict[str, float]] = None
    transmission_pid: Optional[int] = None

class TransmissionRequest(BaseModel):
    """Request model for starting transmission"""
    duration: int = Field(300, ge=1, le=3600, description="Transmission duration in seconds")
    frequency: int = Field(1575420000, description="Carrier frequency in Hz")
    sample_rate: int = Field(2600000, description="Sample rate in Hz")
    tx_gain: int = Field(40, ge=0, le=47, description="TX gain for HackRF")
    power_level: int = Field(1, ge=0, le=1, description="Signal power level")

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Security
security = HTTPBearer(auto_error=False)

class APIKeyAuth:
    """API Key authentication"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GNSS_API_KEY', 'gnss-simulator-key-2024')
        
    def __call__(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
        if not self.api_key:
            return True  # No authentication required
            
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if credentials.credentials != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return True

def create_app(signal_generator: GNSSSignalGenerator, api_key: Optional[str] = None) -> FastAPI:
    """
    Create and configure FastAPI application
    
    Args:
        signal_generator: Initialized GNSS signal generator instance
        api_key: Optional API key for authentication
        
    Returns:
        Configured FastAPI application
    """
    
    app = FastAPI(
        title="GNSS Simulator API",
        description="Laboratory-grade GNSS constellation simulator API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware for web interface
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Authentication dependency
    auth = APIKeyAuth(api_key)
    
    # Logger
    logger = logging.getLogger(__name__)
    
    @app.get("/", response_model=Dict[str, str])
    async def root():
        """Root endpoint with API information"""
        return {
            "name": "GNSS Simulator API",
            "version": "1.0.0",
            "status": "operational",
            "documentation": "/docs"
        }
    
    @app.get("/api/v1/status", response_model=SystemStatus)
    async def get_status():
        """Get system status and health information"""
        try:
            status = signal_generator.get_status()
            return SystemStatus(**status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/location", response_model=LocationResponse)
    async def get_location(authenticated: bool = Depends(auth)):
        """Get current simulated location"""
        try:
            status = signal_generator.get_status()
            
            if 'current_location' not in status or not status['current_location']:
                raise HTTPException(status_code=404, detail="No location configured")
                
            location = status['current_location']
            return LocationResponse(
                latitude=location['latitude'],
                longitude=location['longitude'],
                altitude=location['altitude'],
                status="configured"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting location: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/location", response_model=APIResponse)
    async def set_location(location: LocationRequest, authenticated: bool = Depends(auth)):
        """Set simulated location coordinates"""
        try:
            logger.info(f"Setting location to: {location.latitude}, {location.longitude}, {location.altitude}")
            
            success = signal_generator.update_location(
                latitude=location.latitude,
                longitude=location.longitude,
                altitude=location.altitude
            )
            
            if success:
                return APIResponse(
                    success=True,
                    message="Location updated successfully",
                    data={
                        "latitude": location.latitude,
                        "longitude": location.longitude,
                        "altitude": location.altitude
                    }
                )
            else:
                raise HTTPException(status_code=400, detail="Failed to update location")
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error setting location: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/start", response_model=APIResponse)
    async def start_transmission(
        transmission: TransmissionRequest = TransmissionRequest(),
        authenticated: bool = Depends(auth)
    ):
        """Start GNSS signal transmission"""
        try:
            if signal_generator.is_transmitting:
                return APIResponse(
                    success=False,
                    message="Transmission already in progress"
                )
            
            # Check if location is configured
            status = signal_generator.get_status()
            if 'current_location' not in status or not status['current_location']:
                raise HTTPException(status_code=400, detail="Location must be set before starting transmission")
            
            # Create configuration from current location and transmission parameters
            location = status['current_location']
            config = GNSSConfig(
                latitude=location['latitude'],
                longitude=location['longitude'],
                altitude=location['altitude'],
                duration=transmission.duration,
                frequency=transmission.frequency,
                sample_rate=transmission.sample_rate,
                tx_gain=transmission.tx_gain,
                power_level=transmission.power_level
            )
            
            logger.info(f"Starting transmission with config: {config}")
            
            success = signal_generator.start_transmission(config)
            
            if success:
                return APIResponse(
                    success=True,
                    message="Signal transmission started",
                    data={
                        "location": location,
                        "duration": transmission.duration,
                        "frequency": transmission.frequency
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to start transmission")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting transmission: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/stop", response_model=APIResponse)
    async def stop_transmission(authenticated: bool = Depends(auth)):
        """Stop GNSS signal transmission"""
        try:
            if not signal_generator.is_transmitting:
                return APIResponse(
                    success=True,
                    message="No transmission in progress"
                )
            
            success = signal_generator.stop_transmission()
            
            if success:
                return APIResponse(
                    success=True,
                    message="Signal transmission stopped"
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to stop transmission")
                
        except Exception as e:
            logger.error(f"Error stopping transmission: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint for monitoring"""
        try:
            status = signal_generator.get_status()
            
            # Check critical components
            health_status = {
                "status": "healthy",
                "checks": {
                    "hackrf_connected": status['hackrf_connected'],
                    "gps_sdr_sim_available": status['gps_sdr_sim_available'],
                    "ephemeris_data": status['ephemeris_available']
                }
            }
            
            # Determine overall health
            if not all(health_status["checks"].values()):
                health_status["status"] = "degraded"
                
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Error handlers
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return {"success": False, "message": "Endpoint not found"}
    
    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        logger.error(f"Internal server error: {exc}")
        return {"success": False, "message": "Internal server error"}
    
    return app

# Standalone server for testing
if __name__ == "__main__":
    import uvicorn
    from gnss.signal_generator import GNSSSignalGenerator
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create signal generator
    generator = GNSSSignalGenerator()
    
    # Create app
    app = create_app(generator)
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
