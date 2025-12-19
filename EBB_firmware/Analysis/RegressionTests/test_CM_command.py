#!/usr/bin/env python
# -*- encoding: utf-8 -*-

'''
Test Name: CM (Circle Move) Command Validation Test
Purpose: Comprehensive validation of CM command parameter handling and error detection
Expected Results: Valid parameters accepted, invalid parameters rejected with appropriate errors
Note: CM command is currently DISABLED in firmware v3.0.3 - this test suite is prepared for when it's re-enabled
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
            time.sleep(0.01)  # Small delay for response
            response = port_name.read(port_name.in_waiting).decode('ascii')
        except Exception as e:
            print(f"Error communicating with EBB: {e}")
        return response
    return ''

def test_command(port, command, description, expected_ok=True):
    """
    Test a single CM command and validate response
    Returns True if test passes, False otherwise
    """
    response = query(port, command + '\r')
    response_clean = response.strip()
    
    # Since CM is disabled, we expect "CM command disabled in this build"
    # When enabled, we expect OK for valid commands, error messages for invalid
    is_ok = 'OK' in response_clean
    is_error = ('!' in response_clean) or ('Error' in response_clean)
    is_disabled = 'disabled' in response_clean
    
    if is_disabled:
        print(f"SKIP: {description}")
        print(f"  Command: {command}")
        print(f"  Response: {response_clean}")
        print(f"  Note: CM command is disabled in current firmware build")
        return None  # Skip test
    elif expected_ok and is_ok:
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
print("CM (Circle Move) Command Validation Test Suite")
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

# Test counters
total_tests = 0
passed_tests = 0
failed_tests = 0
skipped_tests = 0

# =============================================================================
# Test Category 1: Valid CM Commands
# =============================================================================
print("=" * 70)
print("Testing Valid CM Commands")
print("=" * 70)

valid_tests = [
    # Format: (command, description)
    ("CM,2,100,100,0,0,0", "Minimum frequency (2 Hz), small arc"),
    ("CM,100,100,100,0,0,0", "Normal frequency, small arc"),
    ("CM,1000,1000,0,500,0,1", "1kHz frequency, large arc, CCW"),
    ("CM,25000,100,100,50,50,0", "Maximum frequency (25kHz), CW direction"),
    ("CM,5000,500,-500,250,250,1", "Negative destination Y, CCW"),
    ("CM,5000,-500,500,250,250,0", "Negative destination X, CW"),
    ("CM,1000,-1000,-1000,-500,-500,1", "All negative coordinates"),
    ("CM,100,32767,32767,0,0,0", "Maximum positive coordinates"),
    ("CM,100,-32768,-32768,0,0,1", "Maximum negative coordinates"),
    ("CM,1000,1000,0,100,100,0", "Small radius arc"),
    ("CM,100,10000,10000,5000,5000,1", "Large radius arc"),
]

for cmd, desc in valid_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 2: Invalid Frequency Parameter
# =============================================================================
print("=" * 70)
print("Testing Invalid Frequency Parameters")
print("=" * 70)

invalid_freq_tests = [
    ("CM,0,100,100,0,0,0", "Zero frequency (should error)"),
    ("CM,1,100,100,0,0,0", "Frequency of 1 (below minimum of 2)"),
    ("CM,25001,100,100,0,0,0", "Frequency above maximum (25000)"),
    ("CM,50000,100,100,0,0,0", "Frequency far above maximum"),
    ("CM,65535,100,100,0,0,0", "Maximum uint16 frequency"),
]

for cmd, desc in invalid_freq_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 3: Invalid Direction Parameter
# =============================================================================
print("=" * 70)
print("Testing Invalid Direction Parameters")
print("=" * 70)

invalid_dir_tests = [
    ("CM,1000,100,100,0,0,2", "Direction = 2 (only 0 or 1 allowed)"),
    ("CM,1000,100,100,0,0,5", "Direction = 5"),
    ("CM,1000,100,100,0,0,255", "Direction = 255 (max uint8)"),
]

for cmd, desc in invalid_dir_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 4: Coordinate Boundary Tests
# =============================================================================
print("=" * 70)
print("Testing Coordinate Boundary Violations")
print("=" * 70)

boundary_tests = [
    ("CM,1000,32769,0,0,0,0", "dest_x above maximum (32768)"),
    ("CM,1000,-32769,0,0,0,0", "dest_x below minimum (-32768)"),
    ("CM,1000,0,32769,0,0,0", "dest_y above maximum"),
    ("CM,1000,0,-32769,0,0,0", "dest_y below minimum"),
    ("CM,1000,0,0,32769,0,0", "center_x above maximum"),
    ("CM,1000,0,0,-32769,0,0", "center_x below minimum"),
    ("CM,1000,0,0,0,32769,0", "center_y above maximum"),
    ("CM,1000,0,0,0,-32769,0", "center_y below minimum"),
]

for cmd, desc in boundary_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 5: Degenerate Arc Cases (Edge Cases)
# =============================================================================
print("=" * 70)
print("Testing Degenerate Arc Cases")
print("=" * 70)

edge_tests = [
    ("CM,1000,0,0,0,0,0", "Zero radius arc (center at origin, dest at origin)"),
    ("CM,1000,100,100,100,100,0", "Zero radius (dest equals center)"),
    ("CM,1000,1,0,0,0,0", "Minimal 1-step move X-axis"),
    ("CM,1000,0,1,0,0,0", "Minimal 1-step move Y-axis"),
    ("CM,2,5,0,0,0,0", "Minimum radius at minimum frequency"),
]

for cmd, desc in edge_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)  # Should handle gracefully
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 6: Missing Parameters
# =============================================================================
print("=" * 70)
print("Testing Missing Parameters")
print("=" * 70)

missing_param_tests = [
    ("CM", "No parameters"),
    ("CM,1000", "Only frequency"),
    ("CM,1000,100", "Missing dest_y and others"),
    ("CM,1000,100,100", "Missing center coordinates"),
    ("CM,1000,100,100,0", "Missing center_y and direction"),
    ("CM,1000,100,100,0,0", "Missing direction"),
]

for cmd, desc in missing_param_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 7: Extra Parameters
# =============================================================================
print("=" * 70)
print("Testing Extra Parameters")
print("=" * 70)

extra_param_tests = [
    ("CM,1000,100,100,0,0,0,5", "Extra parameter (7th parameter - should be ignored or error)"),
    ("CM,1000,100,100,0,0,0,1,2,3", "Multiple extra parameters"),
]

for cmd, desc in extra_param_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=False)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
    print()

# =============================================================================
# Test Category 8: Practical Arc Scenarios
# =============================================================================
print("=" * 70)
print("Testing Practical Arc Scenarios")
print("=" * 70)

practical_tests = [
    ("CM,5000,1000,0,500,0,0", "Quarter circle CW, horizontal start"),
    ("CM,5000,0,1000,0,500,1", "Quarter circle CCW, vertical start"),
    ("CM,3000,707,707,0,0,0", "45-degree arc (approximate quarter circle)"),
    ("CM,10000,2000,0,1000,0,0", "Semicircle CW"),
    ("CM,1000,100,100,200,200,1", "Small arc offset from origin"),
]

for cmd, desc in practical_tests:
    total_tests += 1
    result = test_command(the_port, cmd, desc, expected_ok=True)
    if result is True:
        passed_tests += 1
    elif result is False:
        failed_tests += 1
    else:
        skipped_tests += 1
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
print(f"Skipped: {skipped_tests}")

if skipped_tests > 0:
    print()
    print("NOTE: Tests were skipped because CM command is disabled in current firmware.")
    print("      This test suite is ready for when CM is re-enabled in a future version.")
    print("      To enable CM, modify ebb.c line ~2817: change '#if 1' to '#if 0'")

if failed_tests == 0 and passed_tests > 0:
    success_rate = 100.0
    print(f"Success Rate: {success_rate}%")
    print()
    print("ALL ACTIVE TESTS PASSED")
elif skipped_tests == total_tests:
    print()
    print("ALL TESTS SKIPPED - CM COMMAND DISABLED")
else:
    success_rate = (passed_tests / (total_tests - skipped_tests)) * 100 if (total_tests - skipped_tests) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    print("SOME TESTS FAILED")

# Cleanup
ad.disconnect()
print()
print("Test suite completed")
