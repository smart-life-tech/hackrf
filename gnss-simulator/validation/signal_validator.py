#!/usr/bin/env python3
"""
GNSS Signal Validation Tools

Tools for validating and monitoring GNSS signal quality and transmission.
"""

import os
import sys
import subprocess
import logging
import time
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
import tempfile

@dataclass
class SignalMetrics:
    """Signal quality metrics"""
    frequency: float
    power_level: float
    signal_to_noise: float
    bandwidth: float
    duration: float
    sample_rate: float
    file_size_mb: float

@dataclass
class ValidationResult:
    """Signal validation result"""
    passed: bool
    metrics: SignalMetrics
    errors: List[str]
    warnings: List[str]

class GNSSSignalValidator:
    """
    GNSS Signal Validation and Monitoring Tools
    
    Provides tools to validate signal generation, monitor transmission quality,
    and verify GNSS signal characteristics.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_signal_file(self, signal_file: str) -> ValidationResult:
        """
        Validate a generated GNSS signal file
        
        Args:
            signal_file: Path to the signal file to validate
            
        Returns:
            ValidationResult with metrics and validation status
        """
        errors = []
        warnings = []
        
        try:
            # Check file existence and size
            if not os.path.exists(signal_file):
                errors.append(f"Signal file not found: {signal_file}")
                return ValidationResult(False, None, errors, warnings)
                
            file_size = os.path.getsize(signal_file)
            if file_size == 0:
                errors.append("Signal file is empty")
                return ValidationResult(False, None, errors, warnings)
                
            file_size_mb = file_size / (1024 * 1024)
            
            # Basic file format validation
            if file_size % 8 != 0:  # IQ samples are 8 bytes (2 x int32)
                warnings.append("File size not aligned to IQ sample boundary")
                
            # Calculate expected metrics
            sample_rate = 2600000  # Default GPS-SDR-SIM sample rate
            duration = file_size / (sample_rate * 8)  # 8 bytes per complex sample
            
            # Read a sample of the file for analysis
            with open(signal_file, 'rb') as f:
                # Read first 1MB or entire file if smaller
                sample_size = min(1024 * 1024, file_size)
                data = f.read(sample_size)
                
            # Convert to complex samples (assuming int32 I/Q)
            samples = np.frombuffer(data, dtype=np.int32)
            if len(samples) % 2 != 0:
                samples = samples[:-1]  # Ensure even number for I/Q pairs
                
            complex_samples = samples[::2] + 1j * samples[1::2]
            
            # Calculate basic signal metrics
            power_level = np.mean(np.abs(complex_samples) ** 2)
            
            # FFT analysis for frequency content
            fft = np.fft.fft(complex_samples[:min(len(complex_samples), 65536)])
            power_spectrum = np.abs(fft) ** 2
            
            # Find peak frequency (should be around DC for baseband)
            peak_freq_bin = np.argmax(power_spectrum)
            freq_resolution = sample_rate / len(fft)
            peak_frequency = peak_freq_bin * freq_resolution
            if peak_frequency > sample_rate / 2:
                peak_frequency -= sample_rate
                
            # Estimate SNR (simplified)
            signal_power = np.max(power_spectrum)
            noise_floor = np.median(power_spectrum)
            snr_estimate = 10 * np.log10(signal_power / noise_floor) if noise_floor > 0 else 0
            
            # Estimate bandwidth (3dB bandwidth)
            half_power = signal_power / 2
            bandwidth_bins = np.sum(power_spectrum > half_power)
            bandwidth = bandwidth_bins * freq_resolution
            
            metrics = SignalMetrics(
                frequency=peak_frequency,
                power_level=float(power_level),
                signal_to_noise=snr_estimate,
                bandwidth=bandwidth,
                duration=duration,
                sample_rate=sample_rate,
                file_size_mb=file_size_mb
            )
            
            # Validation checks
            if duration < 1:
                warnings.append(f"Short signal duration: {duration:.1f}s")
            elif duration > 3600:
                warnings.append(f"Very long signal duration: {duration:.1f}s")
                
            if bandwidth < 1000000:  # Less than 1 MHz
                warnings.append(f"Narrow bandwidth: {bandwidth/1000:.0f} kHz")
            elif bandwidth > 20000000:  # More than 20 MHz
                warnings.append(f"Wide bandwidth: {bandwidth/1000000:.1f} MHz")
                
            if snr_estimate < 10:
                warnings.append(f"Low SNR estimate: {snr_estimate:.1f} dB")
                
            if abs(peak_frequency) > 100000:  # More than 100 kHz from DC
                warnings.append(f"Peak frequency offset: {peak_frequency/1000:.1f} kHz")
                
            passed = len(errors) == 0
            
            return ValidationResult(passed, metrics, errors, warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(False, None, errors, warnings)
            
    def test_hackrf_transmission(self, duration: int = 10) -> Tuple[bool, str]:
        """
        Test HackRF transmission capability
        
        Args:
            duration: Test duration in seconds
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Create a simple test signal
            with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
                test_signal_file = f.name
                
            # Generate a simple test tone (1 kHz)
            sample_rate = 2600000
            samples = int(sample_rate * duration)
            t = np.linspace(0, duration, samples)
            test_signal = np.exp(1j * 2 * np.pi * 1000 * t) * 32767  # 1 kHz tone
            
            # Convert to int32 I/Q format
            i_samples = np.real(test_signal).astype(np.int32)
            q_samples = np.imag(test_signal).astype(np.int32)
            iq_samples = np.empty(2 * len(i_samples), dtype=np.int32)
            iq_samples[::2] = i_samples
            iq_samples[1::2] = q_samples
            
            # Write test signal file
            with open(test_signal_file, 'wb') as f:
                f.write(iq_samples.tobytes())
                
            # Test transmission
            cmd = [
                'hackrf_transfer',
                '-t', test_signal_file,
                '-f', '1575420000',
                '-s', str(sample_rate),
                '-a', '1',
                '-x', '20'  # Lower gain for testing
            ]
            
            self.logger.info(f"Testing HackRF transmission: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
            
            # Clean up test file
            os.unlink(test_signal_file)
            
            if result.returncode == 0:
                return True, "HackRF transmission test successful"
            else:
                return False, f"HackRF transmission test failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "HackRF transmission test timeout"
        except Exception as e:
            return False, f"HackRF transmission test error: {str(e)}"
            
    def monitor_transmission(self, duration: int = 30) -> Dict[str, Any]:
        """
        Monitor active GNSS transmission
        
        Args:
            duration: Monitoring duration in seconds
            
        Returns:
            Dictionary with monitoring results
        """
        try:
            # Create temporary file for captured data
            with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
                capture_file = f.name
                
            # Capture signal using HackRF
            cmd = [
                'hackrf_transfer',
                '-r', capture_file,
                '-f', '1575420000',
                '-s', '2600000',
                '-n', str(2600000 * duration),  # Number of samples
                '-a', '1',
                '-l', '40',
                '-g', '20'
            ]
            
            self.logger.info(f"Monitoring transmission: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
            
            monitoring_result = {
                'capture_successful': result.returncode == 0,
                'duration': duration,
                'error_message': result.stderr if result.returncode != 0 else None
            }
            
            if result.returncode == 0 and os.path.exists(capture_file):
                # Analyze captured data
                file_size = os.path.getsize(capture_file)
                expected_size = 2600000 * duration * 8  # 8 bytes per complex sample
                
                monitoring_result.update({
                    'file_size_mb': file_size / (1024 * 1024),
                    'expected_size_mb': expected_size / (1024 * 1024),
                    'capture_complete': abs(file_size - expected_size) < (expected_size * 0.1)
                })
                
                # Basic signal analysis if file is reasonable size
                if file_size > 0 and file_size < 100 * 1024 * 1024:  # Less than 100MB
                    validation_result = self.validate_signal_file(capture_file)
                    if validation_result.passed:
                        monitoring_result['signal_metrics'] = {
                            'power_level': validation_result.metrics.power_level,
                            'snr_estimate': validation_result.metrics.signal_to_noise,
                            'bandwidth': validation_result.metrics.bandwidth
                        }
                    else:
                        monitoring_result['signal_errors'] = validation_result.errors
                        
            # Clean up capture file
            if os.path.exists(capture_file):
                os.unlink(capture_file)
                
            return monitoring_result
            
        except subprocess.TimeoutExpired:
            return {'capture_successful': False, 'error_message': 'Monitoring timeout'}
        except Exception as e:
            return {'capture_successful': False, 'error_message': str(e)}
            
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run comprehensive GNSS simulator validation test
        
        Returns:
            Dictionary with complete test results
        """
        test_results = {
            'timestamp': time.time(),
            'overall_passed': False,
            'tests': {}
        }
        
        # Test 1: HackRF detection
        try:
            result = subprocess.run(['hackrf_info'], capture_output=True, text=True, timeout=10)
            hackrf_detected = "Found HackRF" in result.stdout
            test_results['tests']['hackrf_detection'] = {
                'passed': hackrf_detected,
                'message': 'HackRF detected' if hackrf_detected else 'HackRF not detected'
            }
        except Exception as e:
            test_results['tests']['hackrf_detection'] = {
                'passed': False,
                'message': f'HackRF detection error: {str(e)}'
            }
            
        # Test 2: GPS-SDR-SIM availability
        gps_sdr_sim_path = Path('/home/erez/gps-sdr-sim/gps-sdr-sim')
        gps_sdr_sim_available = gps_sdr_sim_path.exists() and gps_sdr_sim_path.is_file()
        test_results['tests']['gps_sdr_sim'] = {
            'passed': gps_sdr_sim_available,
            'message': 'GPS-SDR-SIM available' if gps_sdr_sim_available else 'GPS-SDR-SIM not found'
        }
        
        # Test 3: GNSS data availability
        data_dir = Path('/home/erez/gnss-data')
        nav_files = list(data_dir.glob('*.n')) + list(data_dir.glob('*.nav'))
        gnss_data_available = len(nav_files) > 0
        test_results['tests']['gnss_data'] = {
            'passed': gnss_data_available,
            'message': f'{len(nav_files)} GNSS data files found' if gnss_data_available else 'No GNSS data files found'
        }
        
        # Test 4: Signal generation test (if previous tests passed)
        if hackrf_detected and gps_sdr_sim_available and gnss_data_available:
            try:
                # Generate a short test signal
                cmd = [
                    str(gps_sdr_sim_path),
                    '-e', str(nav_files[0]),
                    '-l', '51.5074,-0.1278,100',
                    '-d', '10'
                ]
                
                with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
                    test_output = f.name
                    cmd.extend(['-o', test_output])
                    
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and os.path.exists(test_output):
                    validation_result = self.validate_signal_file(test_output)
                    test_results['tests']['signal_generation'] = {
                        'passed': validation_result.passed,
                        'message': 'Signal generation successful' if validation_result.passed else 'Signal validation failed',
                        'metrics': validation_result.metrics.__dict__ if validation_result.metrics else None,
                        'errors': validation_result.errors,
                        'warnings': validation_result.warnings
                    }
                    os.unlink(test_output)
                else:
                    test_results['tests']['signal_generation'] = {
                        'passed': False,
                        'message': f'Signal generation failed: {result.stderr}'
                    }
                    
            except Exception as e:
                test_results['tests']['signal_generation'] = {
                    'passed': False,
                    'message': f'Signal generation test error: {str(e)}'
                }
        else:
            test_results['tests']['signal_generation'] = {
                'passed': False,
                'message': 'Skipped due to prerequisite failures'
            }
            
        # Test 5: HackRF transmission test (if HackRF detected)
        if hackrf_detected:
            transmission_success, transmission_message = self.test_hackrf_transmission(5)
            test_results['tests']['hackrf_transmission'] = {
                'passed': transmission_success,
                'message': transmission_message
            }
        else:
            test_results['tests']['hackrf_transmission'] = {
                'passed': False,
                'message': 'Skipped - HackRF not detected'
            }
            
        # Determine overall result
        test_results['overall_passed'] = all(
            test['passed'] for test in test_results['tests'].values()
        )
        
        return test_results


def main():
    """Command-line interface for signal validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GNSS Signal Validation Tools")
    parser.add_argument('command', choices=['validate', 'test', 'monitor', 'comprehensive'])
    parser.add_argument('--file', help='Signal file to validate')
    parser.add_argument('--duration', type=int, default=30, help='Test/monitor duration in seconds')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    validator = GNSSSignalValidator()
    
    if args.command == 'validate':
        if not args.file:
            print("Error: --file required for validate command")
            sys.exit(1)
            
        result = validator.validate_signal_file(args.file)
        
        print(f"Validation Result: {'PASSED' if result.passed else 'FAILED'}")
        
        if result.metrics:
            print(f"Duration: {result.metrics.duration:.1f}s")
            print(f"File Size: {result.metrics.file_size_mb:.1f} MB")
            print(f"Power Level: {result.metrics.power_level:.2e}")
            print(f"SNR Estimate: {result.metrics.signal_to_noise:.1f} dB")
            print(f"Bandwidth: {result.metrics.bandwidth/1000:.0f} kHz")
            
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
                
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
                
    elif args.command == 'test':
        success, message = validator.test_hackrf_transmission(args.duration)
        print(f"HackRF Test: {'PASSED' if success else 'FAILED'}")
        print(f"Message: {message}")
        
    elif args.command == 'monitor':
        print(f"Monitoring transmission for {args.duration} seconds...")
        result = validator.monitor_transmission(args.duration)
        
        print(f"Monitoring Result: {'SUCCESS' if result['capture_successful'] else 'FAILED'}")
        
        for key, value in result.items():
            if key not in ['capture_successful']:
                print(f"{key.replace('_', ' ').title()}: {value}")
                
    elif args.command == 'comprehensive':
        print("Running comprehensive validation test...")
        results = validator.run_comprehensive_test()
        
        print(f"\nOverall Result: {'PASSED' if results['overall_passed'] else 'FAILED'}")
        print("=" * 50)
        
        for test_name, test_result in results['tests'].items():
            status = "PASS" if test_result['passed'] else "FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            print(f"  {test_result['message']}")
            
            if 'metrics' in test_result and test_result['metrics']:
                print("  Metrics:")
                for metric, value in test_result['metrics'].items():
                    print(f"    {metric}: {value}")
                    
            if 'errors' in test_result and test_result['errors']:
                print("  Errors:")
                for error in test_result['errors']:
                    print(f"    - {error}")
                    
            if 'warnings' in test_result and test_result['warnings']:
                print("  Warnings:")
                for warning in test_result['warnings']:
                    print(f"    - {warning}")
            print()


if __name__ == "__main__":
    main()
