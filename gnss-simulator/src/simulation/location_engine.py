#!/usr/bin/env python3
"""
Location Setting Engine

Advanced coordinate validation, conversion, and satellite visibility calculation
for GNSS simulation with full constellation management.
"""

import math
import logging
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np

@dataclass
class GeodeticCoordinate:
    """Geodetic coordinate in WGS84 system"""
    latitude: float   # degrees
    longitude: float  # degrees
    altitude: float   # meters above WGS84 ellipsoid

@dataclass
class ECEFCoordinate:
    """Earth-Centered Earth-Fixed coordinate"""
    x: float  # meters
    y: float  # meters
    z: float  # meters

@dataclass
class SatellitePosition:
    """Satellite position and visibility information"""
    prn: int          # Satellite PRN number
    azimuth: float    # degrees
    elevation: float  # degrees
    distance: float   # meters
    visible: bool     # Above horizon mask
    ecef_pos: ECEFCoordinate

@dataclass
class ConstellationState:
    """Complete constellation state at a given time"""
    timestamp: datetime
    observer_position: GeodeticCoordinate
    satellites: List[SatellitePosition]
    visible_count: int
    pdop: float       # Position Dilution of Precision

class LocationEngine:
    """
    Advanced location setting engine with coordinate validation,
    coordinate system conversion, and satellite visibility calculation.
    """
    
    # WGS84 ellipsoid parameters
    WGS84_A = 6378137.0          # Semi-major axis (meters)
    WGS84_F = 1 / 298.257223563  # Flattening
    WGS84_E2 = 2 * WGS84_F - WGS84_F ** 2  # First eccentricity squared
    
    # GPS constellation parameters
    GPS_ORBITAL_RADIUS = 26560000  # meters (approximate)
    ELEVATION_MASK = 5.0          # degrees (minimum elevation for visibility)
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_coordinates(self, latitude: float, longitude: float, altitude: float) -> Tuple[bool, str]:
        """
        Validate geodetic coordinates
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            altitude: Altitude in meters above WGS84 ellipsoid
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []
        
        # Latitude validation
        if not isinstance(latitude, (int, float)):
            errors.append("Latitude must be a number")
        elif not (-90.0 <= latitude <= 90.0):
            errors.append("Latitude must be between -90 and 90 degrees")
            
        # Longitude validation  
        if not isinstance(longitude, (int, float)):
            errors.append("Longitude must be a number")
        elif not (-180.0 <= longitude <= 180.0):
            errors.append("Longitude must be between -180 and 180 degrees")
            
        # Altitude validation
        if not isinstance(altitude, (int, float)):
            errors.append("Altitude must be a number")
        elif altitude < -1000:
            errors.append("Altitude must be greater than -1000 meters")
        elif altitude > 100000:
            errors.append("Altitude must be less than 100,000 meters")
            
        # Special location checks
        if abs(latitude) < 0.001 and abs(longitude) < 0.001:
            errors.append("Coordinates too close to (0,0) - likely invalid")
            
        if len(errors) == 0:
            return True, "Valid coordinates"
        else:
            return False, "; ".join(errors)
            
    def geodetic_to_ecef(self, coord: GeodeticCoordinate) -> ECEFCoordinate:
        """
        Convert geodetic coordinates to ECEF coordinates
        
        Args:
            coord: Geodetic coordinate
            
        Returns:
            ECEF coordinate
        """
        lat_rad = math.radians(coord.latitude)
        lon_rad = math.radians(coord.longitude)
        
        # Calculate radius of curvature in prime vertical
        N = self.WGS84_A / math.sqrt(1 - self.WGS84_E2 * math.sin(lat_rad)**2)
        
        # Convert to ECEF
        x = (N + coord.altitude) * math.cos(lat_rad) * math.cos(lon_rad)
        y = (N + coord.altitude) * math.cos(lat_rad) * math.sin(lon_rad)
        z = (N * (1 - self.WGS84_E2) + coord.altitude) * math.sin(lat_rad)
        
        return ECEFCoordinate(x, y, z)
        
    def ecef_to_geodetic(self, ecef: ECEFCoordinate) -> GeodeticCoordinate:
        """
        Convert ECEF coordinates to geodetic coordinates
        
        Args:
            ecef: ECEF coordinate
            
        Returns:
            Geodetic coordinate
        """
        # Iterative algorithm for ECEF to geodetic conversion
        x, y, z = ecef.x, ecef.y, ecef.z
        
        # Longitude is straightforward
        longitude = math.degrees(math.atan2(y, x))
        
        # Latitude and altitude require iteration
        p = math.sqrt(x**2 + y**2)
        lat = math.atan2(z, p * (1 - self.WGS84_E2))
        
        for _ in range(10):  # Usually converges in 2-3 iterations
            N = self.WGS84_A / math.sqrt(1 - self.WGS84_E2 * math.sin(lat)**2)
            altitude = p / math.cos(lat) - N
            lat_new = math.atan2(z, p * (1 - self.WGS84_E2 * N / (N + altitude)))
            
            if abs(lat_new - lat) < 1e-12:
                break
            lat = lat_new
            
        latitude = math.degrees(lat)
        
        return GeodeticCoordinate(latitude, longitude, altitude)
        
    def calculate_distance_bearing(self, pos1: GeodeticCoordinate, pos2: GeodeticCoordinate) -> Tuple[float, float]:
        """
        Calculate distance and bearing between two geodetic positions
        
        Args:
            pos1: First position
            pos2: Second position
            
        Returns:
            Tuple of (distance_meters, bearing_degrees)
        """
        lat1 = math.radians(pos1.latitude)
        lon1 = math.radians(pos1.longitude)
        lat2 = math.radians(pos2.latitude)
        lon2 = math.radians(pos2.longitude)
        
        # Haversine formula for distance
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = 6371000 * c  # Earth radius in meters
        
        # Bearing calculation
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(y, x))
        bearing = (bearing + 360) % 360  # Normalize to 0-360
        
        return distance, bearing
        
    def generate_gps_constellation(self, observer_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Generate GPS constellation positions for a given time
        
        Args:
            observer_time: Time for constellation calculation (default: current UTC)
            
        Returns:
            List of satellite orbital parameters
        """
        if observer_time is None:
            observer_time = datetime.now(timezone.utc)
            
        # Simplified GPS constellation model
        # In a real implementation, this would use precise ephemeris data
        satellites = []
        
        # GPS constellation has 6 orbital planes with 4 satellites each (nominally)
        # Orbital period is approximately 12 hours (43200 seconds)
        orbital_period = 43200  # seconds
        inclination = 55.0      # degrees
        
        for plane in range(6):
            plane_raan = plane * 60.0  # Right Ascension of Ascending Node (degrees)
            
            for slot in range(4):
                prn = plane * 4 + slot + 1  # PRN 1-24 for basic constellation
                if prn > 32:  # Limit to 32 satellites maximum
                    break
                    
                # Mean anomaly progresses with time
                time_since_epoch = (observer_time.timestamp() % orbital_period) / orbital_period
                mean_anomaly = (slot * 90.0 + time_since_epoch * 360.0) % 360.0
                
                satellite = {
                    'prn': prn,
                    'orbital_plane': plane,
                    'slot': slot,
                    'semi_major_axis': self.GPS_ORBITAL_RADIUS,
                    'eccentricity': 0.02,  # Typical GPS eccentricity
                    'inclination': inclination,
                    'raan': plane_raan,
                    'argument_of_perigee': 0.0,
                    'mean_anomaly': mean_anomaly,
                    'time_of_ephemeris': observer_time.timestamp()
                }
                
                satellites.append(satellite)
                
        return satellites
        
    def calculate_satellite_position(self, sat_params: Dict[str, Any]) -> ECEFCoordinate:
        """
        Calculate satellite ECEF position from orbital parameters
        
        Args:
            sat_params: Satellite orbital parameters
            
        Returns:
            Satellite ECEF position
        """
        # Convert orbital elements to ECEF position
        # This is a simplified Keplerian orbit calculation
        
        a = sat_params['semi_major_axis']
        e = sat_params['eccentricity']
        i = math.radians(sat_params['inclination'])
        raan = math.radians(sat_params['raan'])
        w = math.radians(sat_params['argument_of_perigee'])
        M = math.radians(sat_params['mean_anomaly'])
        
        # Solve Kepler's equation for eccentric anomaly
        E = M
        for _ in range(10):  # Iterative solution
            E_new = M + e * math.sin(E)
            if abs(E_new - E) < 1e-12:
                break
            E = E_new
            
        # True anomaly
        nu = 2 * math.atan2(
            math.sqrt(1 + e) * math.sin(E/2),
            math.sqrt(1 - e) * math.cos(E/2)
        )
        
        # Distance from Earth center
        r = a * (1 - e * math.cos(E))
        
        # Position in orbital plane
        x_orb = r * math.cos(nu)
        y_orb = r * math.sin(nu)
        z_orb = 0
        
        # Rotate to ECEF frame
        x_ecef = (math.cos(raan) * math.cos(w) - math.sin(raan) * math.sin(w) * math.cos(i)) * x_orb + \
                 (-math.cos(raan) * math.sin(w) - math.sin(raan) * math.cos(w) * math.cos(i)) * y_orb
                 
        y_ecef = (math.sin(raan) * math.cos(w) + math.cos(raan) * math.sin(w) * math.cos(i)) * x_orb + \
                 (-math.sin(raan) * math.sin(w) + math.cos(raan) * math.cos(w) * math.cos(i)) * y_orb
                 
        z_ecef = (math.sin(w) * math.sin(i)) * x_orb + (math.cos(w) * math.sin(i)) * y_orb
        
        return ECEFCoordinate(x_ecef, y_ecef, z_ecef)
        
    def calculate_satellite_visibility(self, observer: GeodeticCoordinate, 
                                     satellite_ecef: ECEFCoordinate) -> Tuple[float, float, float, bool]:
        """
        Calculate satellite azimuth, elevation, and visibility from observer location
        
        Args:
            observer: Observer geodetic position
            satellite_ecef: Satellite ECEF position
            
        Returns:
            Tuple of (azimuth_deg, elevation_deg, distance_m, is_visible)
        """
        # Convert observer to ECEF
        observer_ecef = self.geodetic_to_ecef(observer)
        
        # Vector from observer to satellite
        dx = satellite_ecef.x - observer_ecef.x
        dy = satellite_ecef.y - observer_ecef.y
        dz = satellite_ecef.z - observer_ecef.z
        
        # Distance
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # Convert to local East-North-Up (ENU) coordinates
        lat_rad = math.radians(observer.latitude)
        lon_rad = math.radians(observer.longitude)
        
        # ENU transformation matrix
        east = -math.sin(lon_rad) * dx + math.cos(lon_rad) * dy
        north = -math.sin(lat_rad) * math.cos(lon_rad) * dx - \
                math.sin(lat_rad) * math.sin(lon_rad) * dy + \
                math.cos(lat_rad) * dz
        up = math.cos(lat_rad) * math.cos(lon_rad) * dx + \
             math.cos(lat_rad) * math.sin(lon_rad) * dy + \
             math.sin(lat_rad) * dz
             
        # Calculate azimuth and elevation
        azimuth = math.degrees(math.atan2(east, north))
        azimuth = (azimuth + 360) % 360  # Normalize to 0-360
        
        elevation = math.degrees(math.asin(up / distance))
        
        # Visibility check
        is_visible = elevation >= self.ELEVATION_MASK
        
        return azimuth, elevation, distance, is_visible
        
    def calculate_constellation_state(self, observer: GeodeticCoordinate, 
                                    observer_time: datetime = None) -> ConstellationState:
        """
        Calculate complete constellation state for observer location and time
        
        Args:
            observer: Observer geodetic position
            observer_time: Observation time (default: current UTC)
            
        Returns:
            Complete constellation state
        """
        if observer_time is None:
            observer_time = datetime.now(timezone.utc)
            
        # Generate constellation
        constellation = self.generate_gps_constellation(observer_time)
        
        satellites = []
        visible_satellites = []
        
        for sat_params in constellation:
            # Calculate satellite ECEF position
            sat_ecef = self.calculate_satellite_position(sat_params)
            
            # Calculate visibility
            azimuth, elevation, distance, visible = self.calculate_satellite_visibility(
                observer, sat_ecef
            )
            
            satellite = SatellitePosition(
                prn=sat_params['prn'],
                azimuth=azimuth,
                elevation=elevation,
                distance=distance,
                visible=visible,
                ecef_pos=sat_ecef
            )
            
            satellites.append(satellite)
            
            if visible:
                visible_satellites.append(satellite)
                
        # Calculate Position Dilution of Precision (PDOP)
        pdop = self.calculate_pdop(visible_satellites, observer)
        
        return ConstellationState(
            timestamp=observer_time,
            observer_position=observer,
            satellites=satellites,
            visible_count=len(visible_satellites),
            pdop=pdop
        )
        
    def calculate_pdop(self, visible_satellites: List[SatellitePosition], 
                      observer: GeodeticCoordinate) -> float:
        """
        Calculate Position Dilution of Precision for visible satellites
        
        Args:
            visible_satellites: List of visible satellites
            observer: Observer position
            
        Returns:
            PDOP value
        """
        if len(visible_satellites) < 4:
            return 999.9  # Invalid PDOP
            
        # Build geometry matrix (simplified calculation)
        observer_ecef = self.geodetic_to_ecef(observer)
        
        H = []
        for sat in visible_satellites[:8]:  # Use up to 8 satellites for PDOP calculation
            # Unit vector from observer to satellite
            dx = sat.ecef_pos.x - observer_ecef.x
            dy = sat.ecef_pos.y - observer_ecef.y
            dz = sat.ecef_pos.z - observer_ecef.z
            
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # Line of sight unit vector
            ux = dx / distance
            uy = dy / distance
            uz = dz / distance
            
            H.append([ux, uy, uz, 1.0])  # [x, y, z, clock]
            
        if len(H) < 4:
            return 999.9
            
        try:
            # Convert to numpy array for calculation
            H_matrix = np.array(H)
            
            # Calculate covariance matrix: (H^T * H)^(-1)
            HTH = np.dot(H_matrix.T, H_matrix)
            covariance = np.linalg.inv(HTH)
            
            # PDOP is sqrt of trace of position covariance (first 3x3)
            pdop = math.sqrt(np.trace(covariance[:3, :3]))
            
            return min(pdop, 99.9)  # Cap at reasonable maximum
            
        except np.linalg.LinAlgError:
            return 999.9  # Singular matrix
            
    def get_location_info(self, latitude: float, longitude: float, altitude: float = 100.0) -> Dict[str, Any]:
        """
        Get comprehensive location information
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            altitude: Altitude in meters
            
        Returns:
            Dictionary with location information and constellation state
        """
        # Validate coordinates
        is_valid, validation_message = self.validate_coordinates(latitude, longitude, altitude)
        
        if not is_valid:
            return {
                'valid': False,
                'error': validation_message
            }
            
        # Create coordinate objects
        geodetic = GeodeticCoordinate(latitude, longitude, altitude)
        ecef = self.geodetic_to_ecef(geodetic)
        
        # Calculate constellation state
        constellation_state = self.calculate_constellation_state(geodetic)
        
        # Prepare satellite information
        visible_satellites = [sat for sat in constellation_state.satellites if sat.visible]
        satellite_info = []
        
        for sat in visible_satellites:
            satellite_info.append({
                'prn': sat.prn,
                'azimuth': round(sat.azimuth, 1),
                'elevation': round(sat.elevation, 1),
                'distance_km': round(sat.distance / 1000, 1)
            })
            
        return {
            'valid': True,
            'coordinates': {
                'geodetic': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'altitude': altitude
                },
                'ecef': {
                    'x': round(ecef.x, 2),
                    'y': round(ecef.y, 2),
                    'z': round(ecef.z, 2)
                }
            },
            'constellation': {
                'timestamp': constellation_state.timestamp.isoformat(),
                'total_satellites': len(constellation_state.satellites),
                'visible_satellites': constellation_state.visible_count,
                'pdop': round(constellation_state.pdop, 2),
                'satellite_details': satellite_info
            },
            'quality_assessment': {
                'excellent': constellation_state.visible_count >= 8 and constellation_state.pdop < 2.0,
                'good': constellation_state.visible_count >= 6 and constellation_state.pdop < 3.0,
                'adequate': constellation_state.visible_count >= 4 and constellation_state.pdop < 6.0,
                'poor': constellation_state.visible_count < 4 or constellation_state.pdop >= 6.0
            }
        }


def main():
    """Demo/test function for the Location Engine"""
    import json
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    engine = LocationEngine()
    
    # Test locations
    test_locations = [
        (51.5074, -0.1278, 100),  # London
        (40.7128, -74.0060, 10),  # New York
        (35.6762, 139.6503, 40), # Tokyo
        (-33.8688, 151.2093, 58) # Sydney
    ]
    
    print("Location Engine Test")
    print("=" * 50)
    
    for lat, lon, alt in test_locations:
        print(f"\nTesting location: {lat:.4f}, {lon:.4f}, {alt}m")
        
        info = engine.get_location_info(lat, lon, alt)
        
        if info['valid']:
            print(f"✓ Valid location")
            print(f"  ECEF: ({info['coordinates']['ecef']['x']:.0f}, "
                  f"{info['coordinates']['ecef']['y']:.0f}, "
                  f"{info['coordinates']['ecef']['z']:.0f}) m")
            print(f"  Visible satellites: {info['constellation']['visible_satellites']}")
            print(f"  PDOP: {info['constellation']['pdop']}")
            
            # Quality assessment
            quality = info['quality_assessment']
            if quality['excellent']:
                print(f"  Quality: Excellent")
            elif quality['good']:
                print(f"  Quality: Good")
            elif quality['adequate']:
                print(f"  Quality: Adequate")
            else:
                print(f"  Quality: Poor")
                
            # Show first few visible satellites
            satellites = info['constellation']['satellite_details'][:5]
            print(f"  Top satellites:")
            for sat in satellites:
                print(f"    PRN {sat['prn']}: {sat['elevation']:.1f}° elevation, "
                      f"{sat['azimuth']:.1f}° azimuth")
        else:
            print(f"✗ Invalid location: {info['error']}")


if __name__ == "__main__":
    main()
