#!/usr/bin/env python3
"""
GNSS Signal Generator Module

This module handles GPS signal generation using GPS-SDR-SIM and HackRF One.
It provides a Python interface for generating and transmitting GNSS signals.
"""

from datetime import datetime, timezone
import os
import sys
import subprocess
import tempfile
import logging
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import threading
import signal

@dataclass
class GNSSConfig:
    """Configuration for GNSS signal generation"""
    latitude: float
    longitude: float
    altitude: float = 100.0  # meters above WGS84 ellipsoid
    duration: int = 300      # seconds
    sample_rate: int = 2600000  # Hz
    frequency: int = 1575420000  # Hz (L1 band)
    tx_gain: int = 40        # HackRF TX gain
    power_level: int = 1     # Signal power level
    ephemeris_file: Optional[str] = None

class GNSSSignalGenerator:
    """
    GNSS Signal Generator using GPS-SDR-SIM and HackRF One
    
    This class provides methods to generate and transmit GPS L1 C/A signals
    for laboratory testing and GNSS receiver development.
    """
    
    def __init__(self, config_dir: str = "/home/erez/gnss-data", 
                 gps_sdr_sim_path: str = "/home/erez/gps-sdr-sim/gps-sdr-sim"):
        """
        Initialize the GNSS Signal Generator
        
        Args:
            config_dir: Directory containing GNSS data files
            gps_sdr_sim_path: Path to GPS-SDR-SIM executable
        """
        self.config_dir = Path(config_dir)
        self.gps_sdr_sim_path = Path(gps_sdr_sim_path)
        self.logger = logging.getLogger(__name__)
        self.transmission_process = None
        self.is_transmitting = False
        self.current_config = None
        
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Validate required tools
        self._validate_dependencies()
        
    def _validate_dependencies(self) -> None:
        """Validate that all required tools are available"""
        # Check GPS-SDR-SIM
        if not self.gps_sdr_sim_path.exists():
            raise FileNotFoundError(f"GPS-SDR-SIM not found at {self.gps_sdr_sim_path}")
            
        # Check HackRF tools
        try:
            result = subprocess.run(['hackrf_info'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError("HackRF not detected or not accessible")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError("HackRF tools not installed or not in PATH")
            
        # Check data directory
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created GNSS data directory: {self.config_dir}")
            
        self.logger.info("All dependencies validated successfully")
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_transmission()
        sys.exit(0)
        
    def get_latest_ephemeris_file(self) -> Optional[str]:
        """
        Find the latest RINEX navigation file in the data directory
        
        Returns:
            Path to the latest ephemeris file or None if not found
        """
        # Support .n, .25n, .yyYn, and .nav naming
        patterns = ["*.1n", "*.nav", "*.??1n", "*.???1n"]
        
        nav_files = []
        for pattern in patterns:
            nav_files.extend(self.config_dir.glob(pattern))
            #nav_files = list(self.config_dir.glob("*.n")) + list(self.config_dir.glob("*.nav"))
            
        if not nav_files:
            self.logger.warning("No ephemeris files found in data directory")
            return None
            
        # Sort by modification time, newest first
        latest_file = max(nav_files, key=lambda f: f.stat().st_mtime)
        self.logger.info(f"Using ephemeris file: {latest_file}")
        return str(latest_file)
        
    def download_current_ephemeris(self) -> Optional[str]:
        """
        Download current GNSS ephemeris data
        
        Returns:
            Path to downloaded file or None if download failed
        """
        try:
            import datetime
            today = datetime.datetime.now()
            doy = today.timetuple().tm_yday  # Day of year
            year = today.strftime("%y")
            
            # CDDIS FTP URL for current broadcast ephemeris
            today = datetime.datetime.utcnow()
            doy = today.timetuple().tm_yday
            year_full = today.year
            year_short = today.strftime("%y")

            filename = f"brdc{doy:03d}0.{year_short}n.gz"
            url = f"https://cddis.nasa.gov/archive/gnss/data/daily/{year_full}/{doy:03d}/25n/{filename}"
            output_path = self.config_dir / filename
            print(url,output_path)

            # Download using curl with .netrc authentication
            #download_cmd = ['curl', '-n', '-L', '-o', str(output_path), url]
            download_cmd = [
                'curl',
                '-n',  # use .netrc
                '-c', str(self.config_dir / 'cookies.txt'),  # save cookies
                '-b', str(self.config_dir / 'cookies.txt'),  # send cookies
                '-L',  # follow redirects
                '-o', str(output_path),  # output file
                url
            ]

            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=60)
            output_file = self.config_dir / filename
            if result.returncode != 0:
                self.logger.error(f"Decompression failed: {result.stderr}")
                return None

            # Check if decompressed file exists
            if output_file.exists():
                self.logger.info(f"Successfully downloaded: {output_file}")
                
                # Decompress the .gz file
                gz_file = output_file
                decompress_cmd = ['gunzip', '-f', str(gz_file)]
                result = subprocess.run(decompress_cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    self.logger.error(f"Decompression failed: {result.stderr}")
                    return None

                # Return the path to the uncompressed file (remove .gz)
                uncompressed_file = gz_file.with_suffix('')  # e.g., .gz → ''
                if uncompressed_file.exists():
                    self.logger.info(f"Decompressed to: {uncompressed_file}")
                    return str(uncompressed_file)
                else:
                    self.logger.error("Uncompressed file not found after gunzip.")
                    return None
      
        except Exception as e:
            self.logger.error(f"Error downloading ephemeris: {e}")
            return None
            
    def generate_signal_file(self, config: GNSSConfig) -> Tuple[bool, str]:
        """
        Generate GPS signal file using GPS-SDR-SIM
        
        Args:
            config: GNSS configuration parameters
            
        Returns:
            Tuple of (success, output_file_path)
        """
        try:
            # Get ephemeris file
            ephemeris_file = config.ephemeris_file or self.get_latest_ephemeris_file() #'/home/erez/johnFirmware/hackrf/gnss-simulator/brdc2120.25n'
            
            if not ephemeris_file:
                # Try to download current data
                ephemeris_file = self.download_current_ephemeris()
                
            if not ephemeris_file:
                return False, "No ephemeris data available"
                
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(suffix='.bin', delete=False)
            output_path = output_file.name
            output_file.close()
            # Get current time in UTC formatted for gps-sdr-sim
            now_utc = time.gmtime()
            t_param = time.strftime('%Y/%m/%d,%H:%M:%S', now_utc)
            # Build GPS-SDR-SIM command
            cmd = [
                str(self.gps_sdr_sim_path),
                '-e', ephemeris_file,
                '-l', f"{config.latitude},{config.longitude},{config.altitude}",
                '-d', str(config.duration),
                '-o', output_path,
                '-t', t_param,
                '-b', str(8)
            ]
            
            self.logger.info(f"Generating signal file with command: {' '.join(cmd)}")
            
            # Execute GPS-SDR-SIM
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                self.logger.error(f"GPS-SDR-SIM failed: {result.stderr}")
                # if os.path.exists(output_path):
                #     os.unlink(output_path)
                return False, result.stderr
                
            # Verify output file
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error("Generated signal file is empty or missing")
                return False, "Signal generation failed - empty output file"
                
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self.logger.info(f"Signal file generated successfully: {output_path} ({file_size_mb:.1f} MB)")
            
            #return True, output_path
            return True, "/johnFirmware/hackrf/gnss-simulator/gpssim.bin"
            
        except subprocess.TimeoutExpired:
            self.logger.error("GPS-SDR-SIM timeout - signal generation took too long")
            return False, "Signal generation timeout"
        except Exception as e:
            self.logger.error(f"Error during signal generation: {e}")
            return False, str(e)
            
    def start_transmission(self, config: GNSSConfig) -> bool:
        """
        Start GNSS signal transmission
        
        Args:
            config: GNSS configuration parameters
            
        Returns:
            True if transmission started successfully
        """
        if self.is_transmitting:
            self.logger.warning("Transmission already in progress")
            return False
            
        # Generate signal file True, "/home/erez/gps-sdr-sim/ramat_gan_nearby.bin" #
        success, signal_file = self.generate_signal_file(config)
        if not success:
            self.logger.error(f"Failed to generate signal file: {signal_file}")
            return False
            
        try:
            # Build HackRF transmission command
            cmd = [
                'hackrf_transfer',
                '-t', signal_file,
                '-f', str(config.frequency),
                '-s', str(config.sample_rate),
                '-a', str(config.power_level),
                '-x', str(config.tx_gain),
                "-C", "-11",
                '-R'  # Repeat transmission
            ]
            
            self.logger.info(f"Starting transmission with command: {' '.join(cmd)}")
            
            # Start transmission process
            self.transmission_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait a moment to check if process started successfully
            time.sleep(1)
            if self.transmission_process.poll() is not None:
                # Process has already terminated
                stdout, stderr = self.transmission_process.communicate()
                self.logger.error(f"Transmission failed to start: {stderr}")
                return False
                
            self.is_transmitting = True
            self.current_config = config
            self.signal_file = signal_file
            
            self.logger.info("GNSS signal transmission started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting transmission: {e}")
            # Clean up signal file
            # if os.path.exists(signal_file):
            #     os.unlink(signal_file)
            return False
            
    def stop_transmission(self) -> bool:
        """
        Stop GNSS signal transmission
        
        Returns:
            True if transmission stopped successfully
        """
        if not self.is_transmitting:
            self.logger.info("No transmission in progress")
            return True
            
        try:
            if self.transmission_process and self.transmission_process.poll() is None:
                # Gracefully terminate the process
                self.transmission_process.terminate()
                
                # Wait for process to terminate
                try:
                    self.transmission_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination failed
                    self.transmission_process.kill()
                    self.transmission_process.wait()
                    
            self.is_transmitting = False
            self.transmission_process = None
            
            # Clean up signal file
            if hasattr(self, 'signal_file') and os.path.exists(self.signal_file):
               os.unlink(self.signal_file)
                
            self.logger.info("GNSS signal transmission stopped")
            # Delete all .bin files in /tmp
            cleanup_cmd = ['rm', '-f', '/tmp/*.bin']
            subprocess.run(cleanup_cmd)
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping transmission: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get current transmission status
        
        Returns:
            Dictionary containing status information
        """
        status = {
            'is_transmitting': self.is_transmitting,
            'hackrf_connected': self._check_hackrf_status(),
            'ephemeris_available': self.get_latest_ephemeris_file() is not None,
            'data_directory': str(self.config_dir),
            'gps_sdr_sim_available': self.gps_sdr_sim_path.exists()
        }
        
        if self.current_config:
            status['current_location'] = {
                'latitude': self.current_config.latitude,
                'longitude': self.current_config.longitude,
                'altitude': self.current_config.altitude
            }
            
        if self.is_transmitting and self.transmission_process:
            status['transmission_pid'] = self.transmission_process.pid
            
        return status
        
    def _check_hackrf_status(self) -> bool:
        """Check if HackRF is connected and accessible"""
        try:
            result = subprocess.run(['hackrf_info'], capture_output=True, text=True, timeout=5)
            return "Found HackRF" in result.stdout
        except:
            return False
            
    def update_location(self, latitude: float, longitude: float, altitude: float = 100.0) -> bool:
        """
        Update the simulated location (requires transmission restart)
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees  
            altitude: Altitude in meters above WGS84 ellipsoid
            
        Returns:
            True if location update was successful
        """
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        if altitude < -1000:
            raise ValueError("Altitude must be greater than -1000 meters")
            
        was_transmitting = self.is_transmitting
        old_config = self.current_config
        
        # Stop current transmission if active
        if was_transmitting:
            self.stop_transmission()
            
        # Create new configuration
        if old_config:
            new_config = GNSSConfig(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                duration=old_config.duration,
                sample_rate=old_config.sample_rate,
                frequency=old_config.frequency,
                tx_gain=old_config.tx_gain,
                power_level=old_config.power_level,
                ephemeris_file=old_config.ephemeris_file
            )
        else:
            new_config = GNSSConfig(latitude=latitude, longitude=longitude, altitude=altitude)
            
        # Restart transmission if it was active
        if was_transmitting:
            return self.start_transmission(new_config)
        else:
            self.current_config = new_config
            return True


def main():
    """Demo/test function for the GNSS Signal Generator"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize generator
        generator = GNSSSignalGenerator()
        
        # Test configuration (London coordinates)
        config = GNSSConfig(
            latitude=51.5074,
            longitude=-0.1278,
            altitude=100.0,
            duration=60  # 1 minute for testing
        )
        
        print("GNSS Signal Generator Test")
        print("=" * 40)
        
        # Check status
        status = generator.get_status()
        print(f"HackRF Connected: {status['hackrf_connected']}")
        print(f"Ephemeris Available: {status['ephemeris_available']}")
        print(f"GPS-SDR-SIM Available: {status['gps_sdr_sim_available']}")
        
        if not status['hackrf_connected']:
            print("ERROR: HackRF not connected")
            return
            
        # Start transmission
        print(f"\nStarting transmission for location: {config.latitude}, {config.longitude}")
        if generator.start_transmission(config):
            print("✓ Transmission started successfully")
            print("Monitor with GNSS receiver or smartphone")
            
            # Run for 30 seconds then stop
            time.sleep(30)
            
            if generator.stop_transmission():
                print("✓ Transmission stopped successfully")
            else:
                print("✗ Error stopping transmission")
        else:
            print("✗ Failed to start transmission")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    main()
