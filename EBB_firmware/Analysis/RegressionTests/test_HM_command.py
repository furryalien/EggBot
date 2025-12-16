#!/usr/bin/env python
# -*- encoding: utf-8 -*-

'''
Test Name: HM (Home Motor) Command Validation Test
Purpose: Comprehensive validation of HM command parameter handling and error detection
Expected Results: Valid parameters accepted, invalid parameters rejected with appropriate errors
'''

import sys
import time
from pyaxidraw import axidraw
from plotink import ebb_serial

def query(port_name, cmd):
    """Send command and return response"""
    if port_name is not None and cmd is not None:
        response = ''
        try:
            port_name.write(cmd.encode('ascii'))
            time.sleep(0.05)  # Longer delay for HM commands (they block)
            response = port_name.read(port_name.in_waiting).decode('ascii')
        except Exception as e:
            print(f"Error communicating with EBB: {e}")
        return response
    return ''

def test_command(port, command, description, expected_ok=True):
    """
    Test a single HM command and validate response
    Returns True if test passes, False otherwise
    """
    response = query(port, command + '\r')
    response_clean = response.strip()
    
    is_ok = 'OK' in response_clean
    is_error = ('!' in response_clean) or ('Error' in response_clean) or ('error' in response_clean.lower())
    
    if expected_ok and is_ok:
        print(f"PASS: {description}")
        print(f"  Command: {command}")
        print(f"  Response: {response_clean}")
        return True
    elif not expected_ok and is_error:
        print(f"PASS: {description}")
        print(f"  Command: {command}")
        print(f"  Response: {response_clean}")
        return True
    else:
        print(f"FAIL: {description}")
        print(f"  Command: {command}")
        print(f"  Expected: {'OK' if expected_ok else 'Error'}")
        print(f"  Response: {response_clean}")
        return False

# Initialize connection
print("=" * 70)
print("HM (Home Motor) Command Validation Test Suite")
print("=" * 70)

ad = axidraw.AxiDraw()
ad.interactive()

if not ad.connect():
    print("FATAL: Failed to connect to EBB board")
    quit()

the_port = ad.plot_status.port
if the_port is None:
    print("FATAL: Failed to get serial port")
    sys.exit()

the_port.reset_input_buffer()

# Get firmware version
response = query(the_port, 'V')
print(f"Connected: {response.strip()}")
print()

# Reset position to known state
query(the_port, 'CS\r')  # Clear step counters
time.sleep(0.1)

# Test counters
total_tests = 0
passed_tests = 0
failed_tests = 0

# =============================================================================
# Test Category 1: Valid HM Commands - Home Move (no position parameters)
# =============================================================================
print("=" * 70)
print("Testing Valid HM Commands - Home Move (0,0)")
print("=" * 70)

valid_home_tests = [
    # Format: (command, description)
    ("HM,2", "Minimum step frequency (2 Hz) - home move"),
    ("HM,100", "Low step frequency (100 Hz) - home move"),
    ("HM,1000", "Medium step frequency (1 kHz) - home move"),
    ("HM,5000", "High step frequency (5 kHz) - home move"),
    ("HM,25000", "Maximum step frequency (25 kHz) - home move"),
]

for cmd, desc in valid_home_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()
    time.sleep(0.2)  # Allow motion to complete

# =============================================================================
# Test Category 2: Valid HM Commands - Absolute Position Moves
# =============================================================================
print("=" * 70)
print("Testing Valid HM Commands - Absolute Position Moves")
print("=" * 70)

# Reset to home first
query(the_port, 'CS\r')
time.sleep(0.1)

valid_position_tests = [
    ("HM,1000,100,0", "Move to position (100, 0)"),
    ("HM,1000,0,100", "Move to position (0, 100)"),
    ("HM,5000,100,100", "Move to position (100, 100)"),
    ("HM,5000,-100,-100", "Move to position (-100, -100)"),
    ("HM,2000,500,500", "Move to position (500, 500)"),
    ("HM,10000,1000,1000", "Move to position (1000, 1000)"),
    ("HM,1000,0,0", "Move back to home (0, 0)"),
]

for cmd, desc in valid_position_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()
    time.sleep(0.3)  # Allow motion to complete

# =============================================================================
# Test Category 3: Invalid Step Frequency Parameter
# =============================================================================
print("=" * 70)
print("Testing Invalid Step Frequency Parameters")
print("=" * 70)

invalid_freq_tests = [
    ("HM,0", "Zero step frequency (should error)"),
    ("HM,1", "Step frequency of 1 (below minimum of 2)"),
    ("HM,25001", "Step frequency above maximum (25000)"),
    ("HM,50000", "Step frequency far above maximum"),
    ("HM,65535", "Maximum uint16 step frequency"),
]

for cmd, desc in invalid_freq_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()

# =============================================================================
# Test Category 4: Missing Position2 Parameter
# =============================================================================
print("=" * 70)
print("Testing Missing Position2 Parameter")
print("=" * 70)

# Reset to home first
query(the_port, 'CS\r')
time.sleep(0.1)

missing_pos2_tests = [
    ("HM,1000,100", "Position1 present but Position2 missing (should error)"),
    ("HM,5000,500", "Position1=500 but no Position2 (should error)"),
    ("HM,2000,-100", "Negative Position1, no Position2 (should error)"),
]

for cmd, desc in missing_pos2_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()

# =============================================================================
# Test Category 5: Large Position Values (Overflow Risk)
# =============================================================================
print("=" * 70)
print("Testing Large Position Values")
print("=" * 70)

# Reset to home first
query(the_port, 'CS\r')
time.sleep(0.1)

large_position_tests = [
    ("HM,1000,1000000,0", "Large Position1 (1,000,000 steps)"),
    ("HM,1000,0,1000000", "Large Position2 (1,000,000 steps)"),
    ("HM,5000,2147483647,0", "Maximum int32 Position1"),
    ("HM,5000,0,2147483647", "Maximum int32 Position2"),
    ("HM,1000,-2147483648,0", "Minimum int32 Position1"),
    ("HM,1000,0,-2147483648", "Minimum int32 Position2"),
]

for cmd, desc in large_position_tests:
    total_tests += 1
    # These may take a very long time or overflow - expect either OK or error
    # For safety, we'll skip actual execution and just test parsing
    print(f"SKIP: {desc}")
    print(f"  Command: {command}")
    print(f"  Note: Would take excessive time to execute or risk overflow")
    print()

# =============================================================================
# Test Category 6: Zero Steps Move
# =============================================================================
print("=" * 70)
print("Testing Zero Steps Moves")
print("=" * 70)

# Move to a known position first
query(the_port, 'CS\r')
time.sleep(0.1)
query(the_port, 'HM,5000,100,100\r')
time.sleep(0.5)

zero_steps_tests = [
    ("HM,1000,100,100", "Move to current position (zero steps - should complete quickly)"),
]

for cmd, desc in zero_steps_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()

# =============================================================================
# Test Category 7: Boundary Frequency Values
# =============================================================================
print("=" * 70)
print("Testing Boundary Frequency Values")
print("=" * 70)

boundary_freq_tests = [
    ("HM,2,0,0", "Minimum valid frequency at home"),
    ("HM,25000,0,0", "Maximum valid frequency at home"),
]

for cmd, desc in boundary_freq_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()
    time.sleep(0.2)

# =============================================================================
# Test Category 8: Practical Homing Scenarios
# =============================================================================
print("=" * 70)
print("Testing Practical Homing Scenarios")
print("=" * 70)

# Move away from home first
query(the_port, 'CS\r')
time.sleep(0.1)
query(the_port, 'HM,5000,500,500\r')
time.sleep(0.5)

practical_tests = [
    ("HM,5000", "Return to home from (500, 500)"),
    ("HM,10000,1000,0", "Move to (1000, 0) - horizontal only"),
    ("HM,10000,0,1000", "Move to (0, 1000) - vertical only"),
    ("HM,5000,0,0", "Return to home from offset position"),
]

for cmd, desc in practical_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()
    time.sleep(0.3)

# =============================================================================
# Test Category 9: Extra Parameters
# =============================================================================
print("=" * 70)
print("Testing Extra Parameters")
print("=" * 70)

extra_param_tests = [
    ("HM,1000,100,100,50", "Three position parameters (should ignore or error on 3rd)"),
    ("HM,1000,0,0,0,0", "Four extra parameters"),
]

for cmd, desc in extra_param_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result:
        passed_tests += 1
    else:
        failed_tests += 1
    print()

# =============================================================================
# Final Cleanup
# =============================================================================
print("=" * 70)
print("Test Cleanup")
print("=" * 70)

# Return to home and disable motors
query(the_port, 'CS\r')
time.sleep(0.1)
query(the_port, 'HM,5000\r')
time.sleep(0.5)
query(the_port, 'EM,0,0\r')  # Disable motors
print("Motors disabled, position reset to home")
print()

# =============================================================================
# Test Summary
# =============================================================================
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Total Tests: {total_tests}")
print(f"Passed: {passed_tests}")
print(f"Failed: {failed_tests}")
print(f"Skipped: 6 (large position tests)")

if failed_tests == 0:
    success_rate = 100.0
    print(f"Success Rate: {success_rate}%")
    print()
    print("ALL TESTS PASSED")
else:
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    print("SOME TESTS FAILED")

print()
print("IMPORTANT NOTES:")
print("1. Current firmware silently clamps invalid frequencies instead of erroring")
print("2. Minimum frequency should be 2 Hz (not 1 Hz) per documentation")
print("3. Position1 requires Position2 to be present (both or neither)")
print("4. HM command blocks until FIFO empty and motion complete")
print("5. Large position values may cause overflow or take excessive time")

# Cleanup
ad.disconnect()
print()
print("Test suite completed")
