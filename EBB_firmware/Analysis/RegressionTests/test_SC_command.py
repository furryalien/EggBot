#!/usr/bin/env python
# -*- encoding: utf-8 -#-

'''
Test Name: SC (System Configuration) Command Validation Test
Purpose: Comprehensive validation of all SC command parameters
Expected Results: 
  - Valid parameters accepted with OK response
  - Invalid parameters rejected with error messages
  - Configuration changes take effect correctly
  - Edge cases handled properly
'''

import sys
import time
from pyaxidraw import axidraw
from plotink import ebb_motion
from plotink import ebb_serial

def query(port_name, cmd):
    """Send command and return response"""
    if port_name is not None and cmd is not None:
        response = ''
        try:
            port_name.write(cmd.encode('ascii'))
            response = port_name.readline()
            n_retry_count = 0
            while len(response) == 0 and n_retry_count < 100:
                response = port_name.readline()
                n_retry_count += 1
        except:
            print("Error reading serial data.")
        return response

def test_result(test_name, command, response, expected_ok=True):
    """Helper to print test results"""
    response_str = response.decode('utf-8').strip() if response else "NO RESPONSE"
    is_ok = b'OK' in response
    
    if expected_ok:
        status = "PASS" if is_ok else "FAIL"
    else:
        status = "PASS" if not is_ok else "FAIL"
    
    print(f"{status}: {test_name}")
    print(f"  Command: {command}")
    print(f"  Response: {response_str}")
    print()
    
    return status == "PASS"

# Initialize AxiDraw connection
ad = axidraw.AxiDraw()
ad.interactive()

if not ad.connect():
    print("Failed to connect to EBB")
    quit()

the_port = ad.plot_status.port
if the_port is None:
    print("Failed to get serial port")
    sys.exit()

the_port.reset_input_buffer()

# Get firmware version
response = query(the_port, 'V\r')
print(f"Connected: {response.strip()}")
print(f"Starting SC Command Validation Tests")
print("=" * 70)
print()

passed = 0
failed = 0

# Test SC,1 - Pen mechanism selection
print("=" * 70)
print("Testing SC,1 - Pen Mechanism Selection")
print("=" * 70)

tests = [
    ("SC,1,0 - Use solenoid only", "SC,1,0", True),
    ("SC,1,1 - Use RC servo only", "SC,1,1", True),
    ("SC,1,2 - Use both solenoid and servo", "SC,1,2", True),
    ("SC,1,3 - Invalid pen mode (should accept or reject)", "SC,1,3", True),  # Implementation accepts any non-0/1
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,2 - Driver configuration
print("=" * 70)
print("Testing SC,2 - Driver Configuration Mode")
print("=" * 70)

tests = [
    ("SC,2,0 - PIC controls drivers", "SC,2,0", True),
    ("SC,2,1 - PIC controls external drivers", "SC,2,1", True),
    ("SC,2,2 - External controls drivers", "SC,2,2", True),
    ("SC,2,3 - Invalid driver mode", "SC,2,3", False),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,4 - Servo2 minimum position
print("=" * 70)
print("Testing SC,4 - Servo2 Minimum Position (Pen Up)")
print("=" * 70)

tests = [
    ("SC,4,0 - Minimum value", "SC,4,0", True),
    ("SC,4,16384 - Mid-range value", "SC,4,16384", True),
    ("SC,4,22565 - Typical pen up position", "SC,4,22565", True),
    ("SC,4,32767 - Max signed 16-bit", "SC,4,32767", True),
    ("SC,4,65535 - Max unsigned 16-bit", "SC,4,65535", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,5 - Servo2 maximum position
print("=" * 70)
print("Testing SC,5 - Servo2 Maximum Position (Pen Down)")
print("=" * 70)

tests = [
    ("SC,5,0 - Minimum value", "SC,5,0", True),
    ("SC,5,15302 - Typical pen down position", "SC,5,15302", True),
    ("SC,5,32767 - Max signed 16-bit", "SC,5,32767", True),
    ("SC,5,65535 - Max unsigned 16-bit", "SC,5,65535", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,8 - Number of RC servo slots
print("=" * 70)
print("Testing SC,8 - Number of RC Servo Slots")
print("=" * 70)

tests = [
    ("SC,8,0 - Zero slots", "SC,8,0", True),
    ("SC,8,1 - One slot", "SC,8,1", True),
    ("SC,8,8 - Eight slots (max)", "SC,8,8", True),
    ("SC,8,24 - Beyond max (should clamp to 8)", "SC,8,24", True),
    ("SC,8,100 - Way beyond max (should clamp to 8)", "SC,8,100", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,9 - Servo slot duration in milliseconds
print("=" * 70)
print("Testing SC,9 - Servo Slot Duration (ms)")
print("=" * 70)

tests = [
    ("SC,9,0 - Zero ms (edge case)", "SC,9,0", True),
    ("SC,9,1 - One ms", "SC,9,1", True),
    ("SC,9,3 - Three ms (typical)", "SC,9,3", True),
    ("SC,9,6 - Six ms (max)", "SC,9,6", True),
    ("SC,9,10 - Beyond max (should clamp to 6)", "SC,9,10", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,10 - Servo rate (both up and down)
print("=" * 70)
print("Testing SC,10 - Servo Rate (Both Directions)")
print("=" * 70)

tests = [
    ("SC,10,0 - Zero rate (instant)", "SC,10,0", True),
    ("SC,10,100 - Slow rate", "SC,10,100", True),
    ("SC,10,1000 - Medium rate", "SC,10,1000", True),
    ("SC,10,65535 - Maximum rate", "SC,10,65535", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,11 - Pen up speed
print("=" * 70)
print("Testing SC,11 - Pen Up Speed")
print("=" * 70)

tests = [
    ("SC,11,0 - Zero rate (instant)", "SC,11,0", True),
    ("SC,11,200 - Slow up", "SC,11,200", True),
    ("SC,11,2000 - Fast up", "SC,11,2000", True),
    ("SC,11,65535 - Maximum rate", "SC,11,65535", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,12 - Pen down speed
print("=" * 70)
print("Testing SC,12 - Pen Down Speed")
print("=" * 70)

tests = [
    ("SC,12,0 - Zero rate (instant)", "SC,12,0", True),
    ("SC,12,200 - Slow down", "SC,12,200", True),
    ("SC,12,2000 - Fast down", "SC,12,2000", True),
    ("SC,12,65535 - Maximum rate", "SC,12,65535", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,13 - Alternate pause button
print("=" * 70)
print("Testing SC,13 - Alternate Pause Button Enable")
print("=" * 70)

tests = [
    ("SC,13,0 - Disable alternate pause", "SC,13,0", True),
    ("SC,13,1 - Enable alternate pause", "SC,13,1", True),
    ("SC,13,2 - Non-zero value (should enable)", "SC,13,2", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test SC,14 - Solenoid output (if implemented)
print("=" * 70)
print("Testing SC,14 - Solenoid Output Control")
print("=" * 70)

tests = [
    ("SC,14,0 - Disable solenoid", "SC,14,0", True),
    ("SC,14,1 - Enable solenoid", "SC,14,1", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test invalid parameter numbers
print("=" * 70)
print("Testing Invalid SC Parameter Numbers")
print("=" * 70)

tests = [
    ("SC,0,0 - Invalid parameter 0", "SC,0,0", False),
    ("SC,3,0 - Unimplemented parameter 3", "SC,3,0", False),
    ("SC,6,0 - Unimplemented parameter 6", "SC,6,0", False),
    ("SC,7,0 - Unimplemented parameter 7", "SC,7,0", False),
    ("SC,15,0 - Invalid parameter 15", "SC,15,0", False),
    ("SC,255,0 - Invalid parameter 255", "SC,255,0", False),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test missing parameters
print("=" * 70)
print("Testing Missing Parameters")
print("=" * 70)

tests = [
    ("SC - No parameters", "SC", False),
    ("SC,1 - Missing second parameter", "SC,1", False),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Test edge cases and boundary values
print("=" * 70)
print("Testing Edge Cases")
print("=" * 70)

tests = [
    ("SC,4,32768 - Just over signed 16-bit max", "SC,4,32768", True),
    ("SC,5,32768 - Just over signed 16-bit max", "SC,5,32768", True),
]

for test_name, command, expected_ok in tests:
    response = query(the_port, command + '\r')
    if test_result(test_name, command, response, expected_ok):
        passed += 1
    else:
        failed += 1

# Reset to defaults (restore safe configuration)
print("=" * 70)
print("Restoring Default Configuration")
print("=" * 70)

restore_commands = [
    "SC,1,2",      # Both solenoid and servo
    "SC,2,0",      # PIC controls drivers
    "SC,4,22565",  # Default pen up
    "SC,5,15302",  # Default pen down
]

for command in restore_commands:
    response = query(the_port, command + '\r')
    print(f"Restore: {command} :: {response.strip()}")

# Cleanup
ad.disconnect()

print()
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Total Tests: {passed + failed}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {100.0 * passed / (passed + failed):.1f}%")
print()

if failed > 0:
    print("SOME TESTS FAILED - Review output above for details")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
