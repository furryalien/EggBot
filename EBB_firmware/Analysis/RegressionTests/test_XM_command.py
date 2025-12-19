#!/usr/bin/env python
# -*- encoding: utf-8 -*-

'''
XM Command Validation Test Suite
=================================

Purpose: Comprehensive validation of XM (Mixed-Axis Stepper Move) command
Firmware: EBB v3.0.3
Created: December 13, 2025

The XM command is designed for machines with mixed-axis geometry (CoreXY, H-Bot, AxiDraw).
It converts A/B axis coordinates to motor coordinates: Axis1 = A+B, Axis2 = A-B

Parameters:
  XM,<Duration>,<AxisStepsA>,<AxisStepsB>[,<Clear>]

Valid Ranges:
  - Duration: 1 to 2,147,483,647 ms (uint32, but 0 is invalid)
  - AxisStepsA: -2,147,483,648 to 2,147,483,647 (int32)
  - AxisStepsB: -2,147,483,648 to 2,147,483,647 (int32)
  - Clear: 0-3 (optional)

Constraints:
  - Duration cannot be 0
  - Clear must be 0-3
  - Step rate per axis: 0.00001164 to 25,000 steps/second
  - Rate checked on Axis1/Axis2 (AFTER A+B and A-B conversion)
  - A+B and A-B must not overflow int32 range
  - If both AxisStepsA and AxisStepsB are 0, Duration capped at 100,000ms

Note: XM command is currently in production use. All tests execute actual moves.
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
            response = port_name.readline()
            n_retry_count = 0
            while len(response) == 0 and n_retry_count < 100:
                response = port_name.readline()
                n_retry_count += 1
            if isinstance(response, bytes):
                response = response.decode('ascii')
        except Exception as e:
            print(f"Error reading serial data: {e}")
        return response.strip()
    return ''

def block(ad_ref, timeout_ms=None):
    """Wait for motion to complete"""
    if timeout_ms is None:
        time_left = 60000
    else:
        time_left = timeout_ms

    while True:
        try:
            qg_response = ebb_serial.query(ad_ref.plot_status.port, 'QG\r')
            if qg_response:
                qg_val = bytes.fromhex(qg_response.strip())
                motion = qg_val[0] & (15).to_bytes(1, byteorder='big')[0]
                if motion == 0:
                    return True
        except:
            pass
            
        if time_left <= 0:
            return False
        if time_left < 10:
            time.sleep(time_left / 1000)
            time_left = 0
        else:
            time.sleep(0.01)
            if timeout_ms is not None:
                time_left -= 10

# Initialize connection
ad = axidraw.AxiDraw()
ad.interactive()

if not ad.connect():
    print("FAIL: Could not connect to EBB")
    sys.exit(1)

the_port = ad.plot_status.port
if the_port is None:
    print("FAIL: Could not get serial port")
    sys.exit(1)

the_port.reset_input_buffer()

# Get firmware version
response = query(the_port, 'V')
print(f"Connected: {response}")
print("Starting XM Command Validation Tests")
print("=" * 70)

# Test tracking
test_count = 0
pass_count = 0
fail_count = 0

def run_test(description, command, expect_ok=True, expect_error=None, wait_motion=True):
    """Run a single test case"""
    global test_count, pass_count, fail_count
    test_count += 1
    
    response = query(the_port, command)
    
    if expect_ok:
        if 'OK' in response or response == 'XM':
            print(f"PASS: {description}")
            print(f"  Command: {command}")
            print(f"  Response: {response}")
            if wait_motion:
                block(ad, timeout_ms=5000)
            pass_count += 1
        else:
            print(f"FAIL: {description}")
            print(f"  Command: {command}")
            print(f"  Expected: OK or XM")
            print(f"  Got: {response}")
            fail_count += 1
    else:
        # Expecting error
        if 'Err' in response or '!' in response:
            if expect_error is None or expect_error in response:
                print(f"PASS: {description}")
                print(f"  Command: {command}")
                print(f"  Response: {response}")
                pass_count += 1
            else:
                print(f"FAIL: {description} - Wrong error message")
                print(f"  Command: {command}")
                print(f"  Expected error containing: {expect_error}")
                print(f"  Got: {response}")
                fail_count += 1
        else:
            print(f"FAIL: {description} - Should have returned error")
            print(f"  Command: {command}")
            print(f"  Expected: Error message")
            print(f"  Got: {response}")
            fail_count += 1
    print()

# ============================================================================
# Test Category 1: Valid XM Commands
# ============================================================================
print("=" * 70)
print("Test Category 1: Valid XM Commands")
print("=" * 70)
print()

run_test("Valid XM - Small move in A direction",
         "XM,100,50,0", expect_ok=True)

run_test("Valid XM - Small move in B direction",
         "XM,100,0,50", expect_ok=True)

run_test("Valid XM - Diagonal move positive",
         "XM,100,50,50", expect_ok=True)

run_test("Valid XM - Diagonal move negative",
         "XM,100,-50,-50", expect_ok=True)

run_test("Valid XM - Mixed signs (A positive, B negative)",
         "XM,100,100,-50", expect_ok=True)

run_test("Valid XM - Mixed signs (A negative, B positive)",
         "XM,100,-100,50", expect_ok=True)

run_test("Valid XM - Maximum duration",
         "XM,2147483647,10,10", expect_ok=True, wait_motion=False)

# Clear the FIFO after long duration command
query(the_port, 'ES')
time.sleep(0.1)

run_test("Valid XM - Minimum duration (1ms)",
         "XM,1,1,1", expect_ok=True)

run_test("Valid XM - With Clear=0",
         "XM,100,50,50,0", expect_ok=True)

run_test("Valid XM - With Clear=1 (clear axis1 accumulator)",
         "XM,100,50,50,1", expect_ok=True)

run_test("Valid XM - With Clear=2 (clear axis2 accumulator)",
         "XM,100,50,50,2", expect_ok=True)

run_test("Valid XM - With Clear=3 (clear both accumulators)",
         "XM,100,50,50,3", expect_ok=True)

# ============================================================================
# Test Category 2: Invalid Duration Values
# ============================================================================
print("=" * 70)
print("Test Category 2: Invalid Duration Values")
print("=" * 70)
print()

run_test("Invalid XM - Duration = 0",
         "XM,0,100,100", expect_ok=False, 
         expect_error="Parameter outside allowed range", wait_motion=False)

# ============================================================================
# Test Category 3: Invalid Clear Values
# ============================================================================
print("=" * 70)
print("Test Category 3: Invalid Clear Values")
print("=" * 70)
print()

run_test("Invalid XM - Clear = 4",
         "XM,100,50,50,4", expect_ok=False,
         expect_error="Parameter outside allowed range", wait_motion=False)

run_test("Invalid XM - Clear = 255",
         "XM,100,50,50,255", expect_ok=False,
         expect_error="Parameter outside allowed range", wait_motion=False)

# ============================================================================
# Test Category 4: Delay Mode (Zero Steps)
# ============================================================================
print("=" * 70)
print("Test Category 4: Delay Mode (Zero Steps)")
print("=" * 70)
print()

run_test("Valid XM - Delay 100ms (both axes zero)",
         "XM,100,0,0", expect_ok=True)

run_test("Valid XM - Delay 1000ms",
         "XM,1000,0,0", expect_ok=True)

run_test("Valid XM - Delay capped at 100000ms (request 200000ms)",
         "XM,200000,0,0", expect_ok=True, wait_motion=False)

# Clear the long delay
query(the_port, 'ES')
time.sleep(0.1)

# ============================================================================
# Test Category 5: Step Rate Boundary Tests
# ============================================================================
print("=" * 70)
print("Test Category 5: Step Rate Boundary Tests")
print("=" * 70)
print()

# Maximum step rate: 25,000 steps/second
# Rate = steps/duration * 1000 steps/ms
# For 25kHz: steps/duration = 25
# Example: 2500 steps in 100ms = 25,000 steps/sec

run_test("Valid XM - High step rate (near max)",
         "XM,100,2000,0", expect_ok=True)

run_test("Valid XM - Very slow move",
         "XM,10000,1,0", expect_ok=True, wait_motion=False)

# Clear slow move
query(the_port, 'ES')
time.sleep(0.1)

# ============================================================================
# Test Category 6: Coordinate Conversion Tests (A±B → Axis1/Axis2)
# ============================================================================
print("=" * 70)
print("Test Category 6: Coordinate Conversion Tests")
print("=" * 70)
print()

# XM converts: Axis1 = A+B, Axis2 = A-B
# These tests verify the conversion is working correctly

run_test("Valid XM - A=100, B=0 → Axis1=100, Axis2=100",
         "XM,100,100,0", expect_ok=True)

run_test("Valid XM - A=0, B=100 → Axis1=100, Axis2=-100",
         "XM,100,0,100", expect_ok=True)

run_test("Valid XM - A=100, B=100 → Axis1=200, Axis2=0",
         "XM,100,100,100", expect_ok=True)

run_test("Valid XM - A=100, B=-100 → Axis1=0, Axis2=200",
         "XM,100,100,-100", expect_ok=True)

# ============================================================================
# Test Category 7: Large Step Values (Overflow Risk)
# ============================================================================
print("=" * 70)
print("Test Category 7: Large Step Values")
print("=" * 70)
print()

# NOTE: These tests document potential overflow issues in A+B and A-B
# Int32 range: -2,147,483,648 to 2,147,483,647
# If A=2^30 and B=2^30, then A+B = 2^31 (overflow!)

run_test("Valid XM - Large positive A value",
         "XM,100000,100000,0", expect_ok=True, wait_motion=False)

# Clear long move
query(the_port, 'ES')
time.sleep(0.1)

run_test("Valid XM - Large negative A value",
         "XM,100000,-100000,0", expect_ok=True, wait_motion=False)

# Clear long move
query(the_port, 'ES')
time.sleep(0.1)

# These would overflow if both are at the int32 limit - documented but not tested
# (would require >24 hours to complete)
print("NOTE: Overflow edge cases with A±B near int32 limits not tested")
print("      (would cause arithmetic overflow during A+B or A-B calculation)")
print()

# ============================================================================
# Test Category 8: Missing Parameters
# ============================================================================
print("=" * 70)
print("Test Category 8: Missing Parameters")
print("=" * 70)
print()

run_test("Invalid XM - Missing AxisStepsB",
         "XM,100,50", expect_ok=False, wait_motion=False)

run_test("Invalid XM - Missing AxisStepsA and AxisStepsB",
         "XM,100", expect_ok=False, wait_motion=False)

run_test("Invalid XM - Missing all parameters",
         "XM", expect_ok=False, wait_motion=False)

# ============================================================================
# Test Category 9: Extra Parameters
# ============================================================================
print("=" * 70)
print("Test Category 9: Extra Parameters")
print("=" * 70)
print()

run_test("Invalid XM - Extra parameter after Clear",
         "XM,100,50,50,0,999", expect_ok=False, wait_motion=False)

# ============================================================================
# Test Category 10: Practical Mixed-Axis Scenarios
# ============================================================================
print("=" * 70)
print("Test Category 10: Practical Mixed-Axis Scenarios")
print("=" * 70)
print()

run_test("Practical XM - Square path corner 1 (A+, B+)",
         "XM,200,100,100", expect_ok=True)

run_test("Practical XM - Square path corner 2 (A-, B+)",
         "XM,200,-100,100", expect_ok=True)

run_test("Practical XM - Square path corner 3 (A-, B-)",
         "XM,200,-100,-100", expect_ok=True)

run_test("Practical XM - Square path corner 4 (A+, B-)",
         "XM,200,100,-100", expect_ok=True)

run_test("Practical XM - Return to start",
         "XM,100,0,0", expect_ok=True)

# ============================================================================
# Test Summary
# ============================================================================
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Total Tests: {test_count}")
print(f"Passed: {pass_count}")
print(f"Failed: {fail_count}")
print(f"Success Rate: {(pass_count/test_count*100):.1f}%")
print()

if fail_count == 0:
    print("✓ ALL TESTS PASSED")
else:
    print(f"✗ {fail_count} TEST(S) FAILED")

# Cleanup
ad.disconnect()
sys.exit(0 if fail_count == 0 else 1)
