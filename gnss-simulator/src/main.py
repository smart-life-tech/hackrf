#!/usr/bin/env python3
"""
GNSS Simulator Main Application

Entry point for the GNSS Simulator Laboratory Implementation.
Provides command-line interface and starts the FastAPI server.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from gnss.signal_generator import GNSSSignalGenerator, GNSSConfig
from api.server import create_app
import uvicorn

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Reduce noise from external libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="GNSS Simulator Laboratory Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start API server
  python main.py server

  # Test signal generation (London)  
  python main.py test --lat 51.5074 --lon -0.1278

  # Generate signal file only
  python main.py generate --lat 40.7128 --lon -74.0060 --duration 300

  # Check system status
  python main.py status
        """
    )
    
    parser.add_argument(
        'command',
        choices=['server', 'test', 'generate', 'status'],
        help='Command to execute'
    )
    
    # Location parameters
    parser.add_argument('--lat', '--latitude', type=float, help='Latitude in decimal degrees')
    parser.add_argument('--lon', '--longitude', type=float, help='Longitude in decimal degrees')
    parser.add_argument('--alt', '--altitude', type=float, default=100.0, help='Altitude in meters (default: 100)')
    
    # Signal parameters
    parser.add_argument('--duration', type=int, default=300, help='Signal duration in seconds (default: 300)')
    parser.add_argument('--frequency', type=int, default=1575420000, help='Carrier frequency in Hz (default: 1575420000)')
    parser.add_argument('--sample-rate', type=int, default=2600000, help='Sample rate in Hz (default: 2600000)')
    parser.add_argument('--tx-gain', type=int, default=40, help='TX gain for HackRF (default: 40)')
    
    # Server parameters
    parser.add_argument('--host', default='0.0.0.0', help='API server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='API server port (default: 8000)')
    
    # Configuration
    parser.add_argument('--config-dir', default='/home/pi/gnss-data', help='GNSS data directory')
    parser.add_argument('--gps-sdr-sim', default='/home/pi/gps-sdr-sim/gps-sdr-sim', help='GPS-SDR-SIM executable path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Log level')
    parser.add_argument('--log-file', help='Log file path (default: console only)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize signal generator
        generator = GNSSSignalGenerator(
            config_dir=args.config_dir,
            gps_sdr_sim_path=args.gps_sdr_sim
        )
        
        if args.command == 'status':
            # Show system status
            print("GNSS Simulator Status")
            print("=" * 40)
            
            status = generator.get_status()
            for key, value in status.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
                
        elif args.command == 'test':
            # Test signal generation and transmission
            if args.lat is None or args.lon is None:
                parser.error("--lat and --lon are required for test command")
                
            config = GNSSConfig(
                latitude=args.lat,
                longitude=args.lon,
                altitude=args.alt,
                duration=args.duration,
                frequency=args.frequency,
                sample_rate=args.sample_rate,
                tx_gain=args.tx_gain
            )
            
            print(f"Testing GNSS signal transmission")
            print(f"Location: {args.lat}, {args.lon}, {args.alt}m")
            print(f"Duration: {args.duration} seconds")
            print("=" * 40)
            
            if generator.start_transmission(config):
                print("✓ Signal transmission started")
                print("Use GNSS receiver or smartphone to test")
                
                import time
                try:
                    # Monitor transmission
                    start_time = time.time()
                    while generator.is_transmitting and (time.time() - start_time) < args.duration:
                        print(f"Transmitting... {int(time.time() - start_time)}s elapsed", end='\r')
                        time.sleep(1)
                        
                    generator.stop_transmission()
                    print(f"\n✓ Transmission completed ({args.duration}s)")
                    
                except KeyboardInterrupt:
                    print("\nStopping transmission...")
                    generator.stop_transmission()
                    print("✓ Transmission stopped")
            else:
                print("✗ Failed to start transmission")
                sys.exit(1)
                
        elif args.command == 'generate':
            # Generate signal file only (no transmission)
            if args.lat is None or args.lon is None:
                parser.error("--lat and --lon are required for generate command")
                
            config = GNSSConfig(
                latitude=args.lat,
                longitude=args.lon,
                altitude=args.alt,
                duration=args.duration
            )
            
            print(f"Generating GNSS signal file")
            print(f"Location: {args.lat}, {args.lon}, {args.alt}m")
            print(f"Duration: {args.duration} seconds")
            
            success, result = generator.generate_signal_file(config)
            if success:
                print(f"✓ Signal file generated: {result}")
            else:
                print(f"✗ Generation failed: {result}")
                sys.exit(1)
                
        elif args.command == 'server':
            # Start FastAPI server
            print("Starting GNSS Simulator API Server")
            print("=" * 40)
            print(f"Host: {args.host}")
            print(f"Port: {args.port}")
            print(f"API Documentation: http://{args.host}:{args.port}/docs")
            print("=" * 40)
            
            # Create FastAPI app with signal generator instance
            app = create_app(generator)
            
            # Start server
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                log_level=args.log_level.lower(),
                access_log=True
            )
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        if 'generator' in locals():
            generator.stop_transmission()
    except Exception as e:
        logger.error(f"Application error: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
