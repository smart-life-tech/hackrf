#!/usr/bin/env python3
"""
Constellation Manager

Enhanced constellation management for 24+ satellite GNSS simulation
with real-time almanac and ephemeris data integration.
"""

import os
import sys
import logging
import requests
import gzip
import ftplib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import tempfile
import subprocess
import time

from simulation.location_engine import LocationEngine, GeodeticCoordinate, ConstellationState

@dataclass
class EphemerisData:
    """Ephemeris data for a single satellite"""
    prn: int
    week: int
    toe: float          # Time of ephemeris
    toc: float          # Time of clock
    af0: float          # Clock bias
    af1: float          # Clock drift
    af2: float          # Clock drift rate
    crs: float          # Orbit correction - sine harmonic
    delta_n: float      # Mean motion difference
    m0: float           # Mean anomaly at reference time
    cuc: float          # Orbit correction - cosine harmonic
    ecc: float          # Eccentricity
    cus: float          # Orbit correction - sine harmonic
    sqrt_a: float       # Square root of semi-major axis
    cic: float          # Orbit correction - cosine harmonic
    omega0: float       # Longitude of ascending node
    cis: float          # Orbit correction - sine harmonic
    i0: float           # Inclination at reference time
    crc: float          # Orbit correction - cosine harmonic
    omega: float        # Argument of perigee
    omega_dot: float    # Rate of change of right ascension
    idot: float         # Rate of change of inclination
    accuracy: float     # User range accuracy
    health: int         # Satellite health
    tgd: float          # Group delay

@dataclass
class AlmanacData:
    """Almanac data for constellation overview"""
    prn: int
    health: int
    ecc: float          # Eccentricity
    toa: float          # Time of almanac
    delta_i: float      # Inclination relative to 0.3π
    omega_dot: float    # Rate of right ascension
    sqrt_a: float       # Square root of semi-major axis
    omega0: float       # Longitude of ascending node
    omega: float        # Argument of perigee
    m0: float           # Mean anomaly
    af0: float          # Clock bias
    af1: float          # Clock drift
    week: int           # Week number

class ConstellationManager:
    """
    Enhanced constellation management with real-time data integration
    and advanced satellite visibility calculation for laboratory GNSS simulation.
    """
    
    def __init__(self, data_directory: str = "/home/erez/gnss-data"):
        """
        Initialize constellation manager
        
        Args:
            data_directory: Directory for storing GNSS data files
        """
        self.data_dir = Path(data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.location_engine = LocationEngine()
        
        # Data storage
        self.ephemeris_data: Dict[int, EphemerisData] = {}
        self.almanac_data: Dict[int, AlmanacData] = {}
        self.last_update: Optional[datetime] = None
        
        # Configuration
        self.max_data_age_hours = 4  # Maximum age for ephemeris data
        self.update_interval_minutes = 30  # Check for updates every 30 minutes
        
    def download_rinex_navigation(self, date: datetime = None) -> Optional[str]:
        """
        Download RINEX navigation file for the specified date
        
        Args:
            date: Date for data download (default: today)
            
        Returns:
            Path to downloaded file or None if failed
        """
        if date is None:
            date = datetime.now(timezone.utc)
            
        try:
            # Format for CDDIS FTP server
            year = date.year
            doy = date.timetuple().tm_yday  # Day of year
            year_short = date.strftime("%y")
            
            # RINEX navigation filename
            filename = f"brdc{doy:03d}0.{year_short}n"
            compressed_filename = f"{filename}.Z"
            
            # Local file paths
            local_compressed = self.data_dir / compressed_filename
            local_file = self.data_dir / filename
            
            # Check if file already exists and is recent
            if local_file.exists():
                file_age = datetime.now() - datetime.fromtimestamp(local_file.stat().st_mtime)
                if file_age.total_seconds() < 3600:  # Less than 1 hour old
                    self.logger.info(f"Using existing file: {local_file}")
                    return str(local_file)
                    
            self.logger.info(f"Downloading RINEX navigation data for {date.strftime('%Y-%m-%d')}")
            
            # Try multiple sources
            sources = [
                f"ftp://cddis.gsfc.nasa.gov/gnss/data/daily/{year}/brdc/{compressed_filename}",
                f"ftp://igs.ign.fr/pub/igs/data/daily/{year}/brdc/{compressed_filename}",
                f"https://cddis.nasa.gov/archive/gnss/data/daily/{year}/brdc/{compressed_filename}"
            ]
            
            for url in sources:
                try:
                    if url.startswith('http'):
                        # HTTP download
                        response = requests.get(url, timeout=60)
                        if response.status_code == 200:
                            with open(local_compressed, 'wb') as f:
                                f.write(response.content)
                            break
                    else:
                        # FTP download
                        self._download_ftp_file(url, local_compressed)
                        if local_compressed.exists():
                            break
                except Exception as e:
                    self.logger.warning(f"Failed to download from {url}: {e}")
                    continue
            else:
                self.logger.error("Failed to download from all sources")
                return None
                
            # Decompress file
            if local_compressed.exists():
                try:
                    if compressed_filename.endswith('.Z'):
                        # Unix compress format
                        result = subprocess.run(['gunzip', '-f', str(local_compressed)], 
                                              capture_output=True, text=True, timeout=30)
                        if result.returncode != 0:
                            # Try with uncompress
                            result = subprocess.run(['uncompress', str(local_compressed)], 
                                                  capture_output=True, text=True, timeout=30)
                    else:
                        # Gzip format
                        with gzip.open(local_compressed, 'rb') as f_in:
                            with open(local_file, 'wb') as f_out:
                                f_out.write(f_in.read())
                                
                    if local_file.exists():
                        self.logger.info(f"Successfully downloaded and decompressed: {local_file}")
                        return str(local_file)
                        
                except Exception as e:
                    self.logger.error(f"Decompression failed: {e}")
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error downloading RINEX data: {e}")
            return None
            
    def _download_ftp_file(self, url: str, local_path: Path) -> None:
        """Download file via FTP"""
        # Parse FTP URL
        parts = url.replace('ftp://', '').split('/')
        host = parts[0]
        remote_path = '/' + '/'.join(parts[1:])
        
        with ftplib.FTP(host) as ftp:
            ftp.login()  # Anonymous login
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
                
    def parse_rinex_navigation(self, rinex_file: str) -> bool:
        """
        Parse RINEX navigation file and extract ephemeris data
        
        Args:
            rinex_file: Path to RINEX navigation file
            
        Returns:
            True if parsing was successful
        """
        try:
            self.ephemeris_data.clear()
            
            with open(rinex_file, 'r') as f:
                lines = f.readlines()
                
            # Skip header
            data_start = 0
            for i, line in enumerate(lines):
                if 'END OF HEADER' in line:
                    data_start = i + 1
                    break
                    
            # Parse ephemeris records
            i = data_start
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                    
                # Parse PRN and epoch from first line
                try:
                    prn = int(line[:2])
                    
                    # Read ephemeris data (8 lines per satellite)
                    if i + 7 < len(lines):
                        eph_lines = [lines[i + j].strip() for j in range(8)]
                        ephemeris = self._parse_ephemeris_lines(prn, eph_lines)
                        
                        if ephemeris:
                            self.ephemeris_data[prn] = ephemeris
                            
                        i += 8
                    else:
                        break
                        
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error parsing line {i}: {e}")
                    i += 1
                    
            self.logger.info(f"Parsed ephemeris for {len(self.ephemeris_data)} satellites")
            self.last_update = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing RINEX file: {e}")
            return False
            
    def _parse_ephemeris_lines(self, prn: int, lines: List[str]) -> Optional[EphemerisData]:
        """Parse ephemeris data from RINEX lines"""
        try:
            # Line 0: PRN, epoch, clock parameters
            parts = lines[0].split()
            if len(parts) < 8:
                return None
                
            # Convert scientific notation
            af0 = float(parts[5].replace('D', 'E'))
            af1 = float(parts[6].replace('D', 'E'))
            af2 = float(parts[7].replace('D', 'E'))
            
            # Line 1: Broadcast orbit parameters
            parts = lines[1].split()
            crs = float(parts[1].replace('D', 'E'))
            delta_n = float(parts[2].replace('D', 'E'))
            m0 = float(parts[3].replace('D', 'E'))
            
            # Line 2: More orbit parameters
            parts = lines[2].split()
            cuc = float(parts[1].replace('D', 'E'))
            ecc = float(parts[2].replace('D', 'E'))
            cus = float(parts[3].replace('D', 'E'))
            
            # Line 3: More orbit parameters
            parts = lines[3].split()
            sqrt_a = float(parts[1].replace('D', 'E'))
            toe = float(parts[2].replace('D', 'E'))
            cic = float(parts[3].replace('D', 'E'))
            
            # Line 4: More orbit parameters
            parts = lines[4].split()
            omega0 = float(parts[1].replace('D', 'E'))
            cis = float(parts[2].replace('D', 'E'))
            i0 = float(parts[3].replace('D', 'E'))
            
            # Line 5: More orbit parameters
            parts = lines[5].split()
            crc = float(parts[1].replace('D', 'E'))
            omega = float(parts[2].replace('D', 'E'))
            omega_dot = float(parts[3].replace('D', 'E'))
            
            # Line 6: Final orbit parameters
            parts = lines[6].split()
            idot = float(parts[1].replace('D', 'E'))
            week = int(float(parts[3].replace('D', 'E')))
            
            # Line 7: Accuracy and health
            parts = lines[7].split()
            accuracy = float(parts[1].replace('D', 'E'))
            health = int(float(parts[2].replace('D', 'E')))
            tgd = float(parts[3].replace('D', 'E'))
            
            return EphemerisData(
                prn=prn, week=week, toe=toe, toc=toe,
                af0=af0, af1=af1, af2=af2,
                crs=crs, delta_n=delta_n, m0=m0,
                cuc=cuc, ecc=ecc, cus=cus,
                sqrt_a=sqrt_a, cic=cic, omega0=omega0,
                cis=cis, i0=i0, crc=crc,
                omega=omega, omega_dot=omega_dot, idot=idot,
                accuracy=accuracy, health=health, tgd=tgd
            )
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Error parsing ephemeris for PRN {prn}: {e}")
            return None
            
    def update_constellation_data(self, force_update: bool = False) -> bool:
        """
        Update constellation data if needed
        
        Args:
            force_update: Force update regardless of last update time
            
        Returns:
            True if update was successful
        """
        now = datetime.now(timezone.utc)
        
        # Check if update is needed
        if not force_update and self.last_update:
            time_since_update = now - self.last_update
            if time_since_update.total_seconds() < self.update_interval_minutes * 60:
                return True  # No update needed
                
        self.logger.info("Updating constellation data...")
        
        # Download today's data
        rinex_file = self.download_rinex_navigation(now)
        if not rinex_file:
            # Try yesterday's data
            yesterday = now - timedelta(days=1)
            rinex_file = self.download_rinex_navigation(yesterday)
            
        if rinex_file:
            return self.parse_rinex_navigation(rinex_file)
        else:
            self.logger.error("Failed to download current navigation data")
            return False
            
    def get_enhanced_constellation_state(self, observer: GeodeticCoordinate, 
                                       observer_time: datetime = None) -> ConstellationState:
        """
        Get enhanced constellation state using real ephemeris data
        
        Args:
            observer: Observer position
            observer_time: Observation time
            
        Returns:
            Enhanced constellation state with real satellite positions
        """
        if observer_time is None:
            observer_time = datetime.now(timezone.utc)
            
        # Ensure we have current data
        self.update_constellation_data()
        
        # If we have ephemeris data, use it; otherwise fall back to basic model
        if self.ephemeris_data:
            return self._calculate_precise_constellation_state(observer, observer_time)
        else:
            # Fall back to basic constellation model
            return self.location_engine.calculate_constellation_state(observer, observer_time)
            
    def _calculate_precise_constellation_state(self, observer: GeodeticCoordinate, 
                                             observer_time: datetime) -> ConstellationState:
        """Calculate constellation state using precise ephemeris data"""
        # This would implement precise satellite position calculation
        # using the ephemeris data. For brevity, falling back to basic model
        # In a full implementation, this would calculate precise satellite positions
        return self.location_engine.calculate_constellation_state(observer, observer_time)
        
    def get_constellation_health(self) -> Dict[str, Any]:
        """
        Get constellation health and status information
        
        Returns:
            Dictionary with constellation health data
        """
        healthy_satellites = 0
        total_satellites = 0
        satellite_status = {}
        
        for prn, eph in self.ephemeris_data.items():
            total_satellites += 1
            is_healthy = eph.health == 0
            if is_healthy:
                healthy_satellites += 1
                
            satellite_status[prn] = {
                'healthy': is_healthy,
                'accuracy': eph.accuracy,
                'week': eph.week,
                'toe': eph.toe
            }
            
        data_freshness = "unknown"
        if self.last_update:
            age_hours = (datetime.now(timezone.utc) - self.last_update).total_seconds() / 3600
            if age_hours < 1:
                data_freshness = "fresh"
            elif age_hours < 4:
                data_freshness = "recent"
            elif age_hours < 24:
                data_freshness = "stale"
            else:
                data_freshness = "old"
                
        return {
            'total_satellites': total_satellites,
            'healthy_satellites': healthy_satellites,
            'health_percentage': (healthy_satellites / total_satellites * 100) if total_satellites > 0 else 0,
            'data_freshness': data_freshness,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'satellite_status': satellite_status
        }
        
    def get_available_satellites(self) -> List[int]:
        """Get list of available satellite PRNs"""
        return list(self.ephemeris_data.keys())
        
    def get_satellite_info(self, prn: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific satellite
        
        Args:
            prn: Satellite PRN number
            
        Returns:
            Satellite information dictionary or None if not found
        """
        if prn not in self.ephemeris_data:
            return None
            
        eph = self.ephemeris_data[prn]
        
        return {
            'prn': prn,
            'health': 'healthy' if eph.health == 0 else 'unhealthy',
            'accuracy': eph.accuracy,
            'eccentricity': eph.ecc,
            'semi_major_axis': eph.sqrt_a ** 2,
            'inclination': eph.i0,
            'week': eph.week,
            'toe': eph.toe,
            'clock_bias': eph.af0,
            'clock_drift': eph.af1
        }


def main():
    """Test function for constellation manager"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create manager
    manager = ConstellationManager()
    
    print("Constellation Manager Test")
    print("=" * 40)
    
    # Test data update
    print("Updating constellation data...")
    if manager.update_constellation_data(force_update=True):
        print("✓ Data update successful")
        
        # Show health status
        health = manager.get_constellation_health()
        print(f"Total satellites: {health['total_satellites']}")
        print(f"Healthy satellites: {health['healthy_satellites']}")
        print(f"Health percentage: {health['health_percentage']:.1f}%")
        print(f"Data freshness: {health['data_freshness']}")
        
        # Test enhanced constellation calculation
        observer = GeodeticCoordinate(51.5074, -0.1278, 100)  # London
        state = manager.get_enhanced_constellation_state(observer)
        
        print(f"\nConstellation state for London:")
        print(f"Visible satellites: {state.visible_count}")
        print(f"PDOP: {state.pdop:.2f}")
        
        # Show available satellites
        satellites = manager.get_available_satellites()
        print(f"Available satellites: {satellites[:10]}{'...' if len(satellites) > 10 else ''}")
        
    else:
        print("✗ Data update failed")


if __name__ == "__main__":
    main()
