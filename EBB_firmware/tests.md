# EBB Firmware Testing Documentation

**Last Updated:** December 13, 2025  
**Firmware Version:** 3.0.3  
**Test Framework:** Python-based with PyAxiDraw library

---

## Table of Contents

1. [Overview](#overview)
2. [Test Infrastructure](#test-infrastructure)
3. [Test Categories](#test-categories)
4. [Test Structure and Organization](#test-structure-and-organization)
5. [Running Tests](#running-tests)
6. [Test Coverage](#test-coverage)
7. [Hardware-in-the-Loop Testing](#hardware-in-the-loop-testing)
8. [Creating New Tests](#creating-new-tests)
9. [Known Issues and Limitations](#known-issues-and-limitations)

---

## Overview

The EBB firmware testing strategy is primarily based on **hardware-in-the-loop (HIL)** testing, where Python scripts send commands to a physical EBB board and verify responses. Tests are divided into two main locations:

- **`EBB_firmware/Analysis/RegressionTests/`** - Automated regression tests with expected output validation
- **`EBB_firmware/Analysis/firmware tests/`** - Hardware analysis tests using Saleae logic analyzer
- **`EBB_firmware/Testing/`** - Performance and throughput tests

### Testing Philosophy

1. **Regression-Based:** Tests compare actual firmware output against known-good reference outputs stored in CSV files
2. **Real Hardware:** All tests require a physical EBB board connected via USB
3. **Command-Response:** Tests send EBB protocol commands and validate responses
4. **Manual Execution:** Tests are run individually as Python scripts (no unified test runner)

---

## Test Infrastructure

### Dependencies

All tests require the following Python dependencies:

```python
from pyaxidraw import axidraw          # AxiDraw hardware interface
from plotink import ebb_motion         # Motion control utilities
from plotink import ebb_serial         # Serial communication with EBB
```

**Additional dependencies for hardware analysis:**
- `saleae` - Saleae Logic Analyzer Python API (for timing analysis tests)

### Hardware Requirements

- **EBB Board:** v1.3 or above with firmware v3.0.3
- **USB Connection:** Tests communicate over CDC USB serial
- **Saleae Logic Analyzer (optional):** For timing verification and signal analysis
  - Digital channels 0-8 used for step/direction/control signal monitoring
  - Sample rates: 10-32 MSa/s depending on test

### Common Test Utilities

All test scripts include these shared utility functions:

#### `query(port_name, cmd)`
Sends a command to the EBB and returns the response.

```python
def query(port_name, cmd):
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
```

#### `block(ad_ref, timeout_ms=None)`
Waits for all motion commands to complete by polling the motion queue.

```python
def block(ad_ref, timeout_ms=None):
    '''
    Polls the EBB every 10ms until motion queue is empty.
    Returns True if queue emptied, False if timeout occurred.
    Requires EBB v2.6.2 or newer.
    '''
    if timeout_ms is None:
        time_left = 60000  # Default 60 second timeout
    else:
        time_left = timeout_ms

    while True:
        qg_val = bytes.fromhex(ebb_serial.query(ad_ref.plot_status.port, 'QG\r').strip())
        motion = qg_val[0] & (15).to_bytes(1, byteorder='big')[0]
        if motion == 0:
            return True
        if time_left <= 0:
            return False
        # Sleep and decrement timeout...
```

#### Standard Connection Pattern

All tests follow this connection pattern:

```python
ad = axidraw.AxiDraw()
ad.interactive()

if not ad.connect():
    print("failed to connect")
    quit()

the_port = ad.plot_status.port
if the_port is None:
    print("failed to connect")
    sys.exit()

the_port.reset_input_buffer()
```

---

## Test Categories

### 1. Motion Command Regression Tests

**Location:** `Analysis/RegressionTests/`

These tests validate the mathematical correctness of advanced motion commands by comparing firmware calculations against expected values.

#### LM Command Test (`python_send_LM_20230507.py`)

**Purpose:** Test Low-Level Move (2nd-order motion with jerk control)

**Method:**
1. Enables debug output: `CU,250,1` (GPIO debug), `CU,251,1` (UART ISR debug)
2. Sends 60+ LM commands with varying parameters
3. Captures firmware response containing computed rates, accelerations, and step counts
4. Compares output to `LM_20230507_ExceptedOutput.csv`

**Command Format:** `LM,<intervals>,<rate1>,<accel1>,<jerk1>,<rate2>,<accel2>,<jerk2>[,clear]`

**Expected Output Format:**
```
T,<duration>,S,<steps>,C,<carry>,R,<rate>,P,<power>
```

**Example Test Commands:**
```python
"LM,268435456,5,0,0,0,0"          # Simple move, motor 1 only
"LM,-490123456,5,0,0,0,0"         # Negative direction
"LM,8589934,29,17353403,0,0,0"   # Move with acceleration
"LM,978847345,212579,-654,0,0,0,455082516"  # Complex jerk profile
```

**Expected Output Example:**
```
T,40,S,5,C,0,R,268435456,P,5
T,22,S,5,C,45297792,R,490123456,P,5
T,85,S,29,C,1142286978,R,1474952488,P,29
```

**Total Test Cases:** ~80 LM commands

---

#### LT Command Test (`python_send_LT_20230507.py`)

**Purpose:** Test Low-Level Timed Move (time-based 2nd-order motion)

**Difference from LM:** LT runs for a specified time duration rather than until step counts expire.

**Command Format:** `LT,<intervals>,<rate1>,<accel1>,<jerk1>,<rate2>,<accel2>,<jerk2>[,clear]`

**Example Test Commands:**
```python
"LT,40,268435456,0,0,0"           # 40 interval timed move
"LT,85,8589934,17353403,0,0"     # Timed move with acceleration
"LT,577969,978847345,-654,0,0,455082516"  # Long duration with jerk
```

**Total Test Cases:** ~80 LT commands

**Reference:** `LT_20230507_ExpectedOutput.csv`

---

#### T3 Command Test (`python_send_T3_20230507.py`)

**Purpose:** Test Timed 3rd Derivative Move (S-curve motion profiles)

**Command Format:** `T3,<intervals>,<rate1>,<accel1>,<jerk1>,<rate2>,<accel2>,<jerk2>[,clear]`

**Features Tested:**
- 3rd-order motion control (snap/jerk rate)
- S-curve acceleration profiles
- Positive and negative snap values
- Long duration moves (up to 7.6M intervals)

**Example Test Commands:**
```python
"T3,100,0,0,400000,0,0,0"         # Pure snap acceleration
"T3,19512,0,0,11,0,0,0"           # Low snap rate
"T3,30000,0,-95000,11,0,0,0"      # Negative acceleration with snap
"T3,35000,-490123456,-125000,11,0,0,0"  # Full 3rd-order profile
```

**Total Test Cases:** ~50 T3 commands

**Reference:** `T3_20230507_ExpectedOutput.csv`

---

### 2. Rate Verification Tests

#### SM Rate Checker (`SMRateChecker.py`)

**Purpose:** Validate stepper motor rate calculations for SM (Stepper Move) commands

**Method:**
1. Generates random SM command parameters within valid ranges
2. Sends commands with debug output enabled (`CU,255,1`)
3. Firmware responds with computed step rates for both motors
4. Script calculates ideal rates using: `rate = abs((steps/duration_ms) * 85899.34592)`
5. Compares firmware rates vs. ideal rates, logs percentage error
6. Alerts on errors exceeding threshold

**Test Parameters:**
- Duration: 0-65535 ms (typical AxiDraw range)
- Steps: -100,000 to +100,000 per axis
- Validates both motors simultaneously
- Skips invalid combinations (zero duration, zero steps, >25kHz rate)

**Output Format (CSV):**
```
SM,<duration>,<step1>,<step2>,<idealRate1>,<outputRate1>,<errorPercent1>,<idealRate2>,<outputRate2>,<errorPercent2>
```

**Test Duration:** Configurable, default ~20 hours (4M+ commands)

**Output File:** `SMRateCheckOutput.csv`

---

### 3. FIFO Tests

#### Short Command FIFO Test (`ShortCommandFIFOTest300.py`)

**Purpose:** Stress test the motion command FIFO queue with rapid short commands

**Method:**
1. Configures FIFO depth (firmware v3.0.0+ supports 1-32 commands)
2. Sends rapid sequences of short-duration SM commands
3. Tests commands from 1ms to 15ms duration
4. Multiple commands at each duration level (10 repetitions)
5. Monitors for command queue overflows or dropped commands

**Test Sequence:**
```python
# Commands decrease from 15ms to 1ms
"SM,15,15,15"  # Repeated 10 times
"SM,14,14,14"  # Repeated 10 times
...
"SM,1,1,1"     # Repeated 200 times (FIFO stress test)
```

**FIFO Configuration:**
- Default depth: 32 commands
- Memory allocation: 2048 bytes (0x600-0xDFF)
- Each command: ~47 bytes

**Expected Behavior:** All commands execute without gaps or errors

---

### 4. USB Performance Tests

#### USB Processing Time Test (`USBProcessingTimeTest.py`)

**Purpose:** Measure USB command processing overhead and latency

**Method:**
1. Sends commands in rapid succession
2. Measures time between command transmission and response
3. Tests with various command lengths and types
4. Monitors for USB buffer overruns

**Configuration:**
- Uses basic SM commands for timing consistency
- Can be extended with Saleae capture for precise timing

---

#### Throughput Test (`Testing/EBB_ThroughputTest.py`)

**Purpose:** Determine maximum sustainable command rate

**Features:**
- Tests various command types at different rates
- Measures commands per second
- Identifies where command gaps begin to appear
- Validates FIFO effectiveness at high command rates

---

### 5. Basic Command Tests

#### Basic Command Test (`python_send_basic.py`)

**Purpose:** Comprehensive command validation suite

**Commands Tested:**
- `SM` - Stepper Move (simple dual-axis moves)
- `XM` - X Motor Move (mixed-axis mode)
- `HM` - Home Motor
- Various parameter combinations
- Edge cases (zero steps, negative values, maximum values)

**Test Approach:**
1. Sends command
2. Waits for completion with `block()`
3. Prints response
4. Visual inspection of behavior

**Example Test Set:**
```python
"SM,100,100,0"      # Motor 1 only
"SM,100,-100,0"     # Motor 1 reverse
"SM,100,0,100"      # Motor 2 only
"SM,100,100,100"    # Both motors same direction
"SM,100,-100,-100"  # Both motors reverse
"XM,100,100,0"      # X-mode moves
```

**Total Test Cases:** 771 lines of test commands

---

### 6. Configuration Command Tests

#### SC Command Test (`test_SC_command.py`)

**Purpose:** Comprehensive validation of System Configuration (SC) command

**Commands Tested:**
- `SC,1,<value>` - Pen mechanism selection (solenoid/servo)
- `SC,2,<value>` - Driver configuration mode
- `SC,4,<value>` - Servo2 minimum position (pen up)
- `SC,5,<value>` - Servo2 maximum position (pen down)
- `SC,8,<value>` - Number of RC servo slots
- `SC,9,<value>` - Servo slot duration in milliseconds
- `SC,10,<value>` - Servo rate (both directions)
│   │   ├── python_send_basic.py             # Basic command test suite
│   │   ├── test_SC_command.py               # SC configuration validation test
│   │   ├── test_CM_command.py               # CM circle move validation test
│   │   ├── test_HM_command.py               # HM home/absolute move validation test
│   │   ├── test_XM_command.py               # XM mixed-axis move validation test
│   │   ├── LM_20230507_ExceptedOutput.csv   # Expected LM outputs
- `SC,14,<value>` - Solenoid output control (placeholder)

**Test Categories:**
1. **Valid Parameter Tests** - All documented parameters with valid values
2. **Invalid Parameter Tests** - Unimplemented parameters (0, 3, 6, 7, 15+)
3. **Boundary Tests** - Edge cases and value ranges
4. **Error Handling Tests** - Missing parameters, invalid values
5. **Configuration Restoration** - Safe return to defaults after testing

**Validation Improvements:**
- Parameter number validation (rejects 0, 3, 6, 7, 15+)
- Driver configuration validation (SC,2 only accepts 0-2)
- Proper error codes for invalid parameters
- Value clamping for SC,8 and SC,9
- Comprehensive error messages

**Test Approach:**
1. Sends each SC parameter with various values
2. Validates responses (OK or error)
3. Tests edge cases and boundaries
4. Verifies error handling for invalid inputs
5. Restores safe configuration at end

**Example Test Set:**
```python
"SC,1,0"      # Solenoid only
"SC,1,1"      # Servo only  
"SC,2,0"      # PIC controls drivers
"SC,2,3"      # Invalid driver mode (should error)
"SC,4,22565"  # Pen up position
"SC,8,24"     # Beyond max slots (should clamp)
```

**Total Test Cases:** 50+ comprehensive tests

**Expected Results:**
- Valid commands return OK
- Invalid parameters return error messages
- Values are clamped where documented
- Configuration changes take effect
- Safe restoration at test completion

---

#### CM Command Test (`test_CM_command.py`)

**Purpose:** Comprehensive validation of Circle Move (CM) command
**Status:** ⚠️ CM command is currently DISABLED in firmware v3.0.3 (tests will skip)

**Commands Tested:**
- `CM,<frequency>,<dest_x>,<dest_y>,<center_x>,<center_y>,<direction>` - Arc/circle motion

**Parameters:**
- `<frequency>` - Step rate from 2 to 25000 Hz
- `<dest_x>`, `<dest_y>` - Destination coordinates (-32768 to 32767)
- `<center_x>`, `<center_y>` - Arc center coordinates (-32768 to 32767)
- `<direction>` - 0=CW (clockwise), 1=CCW (counter-clockwise)

**Test Categories:**
1. **Valid CM Commands** - Various frequencies, arc sizes, directions
2. **Invalid Frequency Parameters** - Below minimum (2), above maximum (25000)
3. **Invalid Direction Parameters** - Values > 1
4. **Coordinate Boundary Tests** - Beyond ±32768 range
5. **Degenerate Arc Cases** - Zero radius, minimal moves
6. **Missing Parameters** - Incomplete command validation
7. **Extra Parameters** - Unexpected additional parameters
8. **Practical Arc Scenarios** - Quarter circles, semicircles, offset arcs

**Validation Improvements:**
- Frequency minimum corrected from 1 to 2 Hz (per specification)
- Coordinate boundaries corrected to -32768 to 32767 (signed 16-bit)
- Zero radius detection and graceful handling
- Enhanced parameter documentation

**Test Approach:**
1. Sends CM commands with various parameter combinations
2. Validates responses (OK or error)
3. Tests boundary conditions and edge cases
4. Verifies error handling for invalid inputs
5. Currently all tests SKIP with message "CM command disabled"

**Example Test Set:**
```python
"CM,2,100,100,0,0,0"         # Minimum frequency, small arc
"CM,25000,100,100,50,50,0"   # Maximum frequency, CW
"CM,1,100,100,0,0,0"         # Invalid: frequency below minimum
"CM,1000,32768,0,0,0,0"      # Invalid: coordinate out of range
"CM,1000,0,0,0,0,0"          # Degenerate: zero radius
"CM,1000,100,100,0,0,2"      # Invalid: direction > 1
```

**Total Test Cases:** 45+ comprehensive tests

**Expected Results (When CM Enabled):**
- Valid commands return OK and execute arc motion
- Invalid frequency/direction return error messages
- Coordinate boundary violations return errors
- Zero radius arcs handled gracefully (convert to straight line)
- All parameter combinations validated

**Current Status:**
- All tests SKIP: "CM command disabled in current firmware build"
- To enable: Change line 2817 in ebb.c from `#if 1` to `#if 0`
- Tests ready for when CM functionality is re-enabled

---

#### HM Command Test (`test_HM_command.py`)

**Purpose:** Comprehensive validation of Home Motor (HM) command
**Status:** ✅ Active command with improved validation

**Commands Tested:**
- `HM,<frequency>` - Home move to (0,0)
- `HM,<frequency>,<Position1>,<Position2>` - Absolute position move

**Parameters:**
- `<frequency>` - Step rate from 2 to 25000 Hz
- `<Position1>` - Motor 1 absolute position (±2,147,483,647, int32)
- `<Position2>` - Motor 2 absolute position (±2,147,483,647, int32)
- **Note:** Position parameters must be paired (both or neither)

**Test Categories:**
1. **Valid Home Moves** - Various frequencies, home to (0,0)
2. **Valid Position Moves** - Absolute positioning with coordinates
3. **Invalid Frequency Parameters** - Below minimum (2), above maximum (25000)
4. **Missing Position2 Parameter** - Position1 without Position2
5. **Large Position Values** - Documented but skipped (long execution time)
6. **Zero Step Moves** - Move to current position
7. **Boundary Frequencies** - Exactly 2 Hz and 25000 Hz
8. **Practical Homing Scenarios** - Return to home, single-axis moves
9. **Extra Parameters** - Unexpected additional parameters

**Validation Improvements (v3.0.3):**
- **Replaced silent frequency clamping with error reporting:**
  - Previously: Invalid frequencies silently clamped to 1-25000 range
  - Now: Returns `!1 Err: Parameter outside allowed range` error
- **Frequency minimum corrected from 1 to 2 Hz** (per specification)
- **Position parameter pairing validation added:**
  - Must provide both Position1 and Position2, or neither
  - Returns error if only one position provided
- **Enhanced overflow documentation** for large position values
- **Breaking changes documented** for host software migration

**Test Approach:**
1. Sends HM commands with various parameter combinations
2. Validates responses (OK or error)
3. Tests boundary conditions and edge cases
4. Verifies blocking behavior (command waits for completion)
5. Confirms proper error handling for invalid inputs

**Example Test Set:**
```python
"HM,2"                       # Minimum frequency home move
"HM,25000"                   # Maximum frequency home move
"HM,1000,100,200"            # Absolute position move
"HM,1000,0,0"                # Move to origin (zero steps)
"HM,1"                       # Invalid: frequency below minimum
"HM,30000"                   # Invalid: frequency above maximum
"HM,1000,100"                # Invalid: missing Position2
"HM,1000,-500,500"           # Diagonal move (negative position)
```

**Total Test Cases:** 35+ tests (6 documented but skipped due to long execution)

**Expected Results:**
- Valid commands return OK and execute motion
- Invalid frequencies return error (not silently clamped)
- Unpaired position parameters return error
- Zero step moves accepted (no motion)
- Command blocks until motion completes

**Current Status:**
- ✅ All validation tests passing
- ✅ Breaking changes documented in `HM_VALIDATION_IMPROVEMENTS.md`
- ⚠️ Large position tests skipped (would take excessive time)
- ✅ Migration guide available for host software updates

**See Also:**
- `HM_VALIDATION_IMPROVEMENTS.md` - Detailed technical documentation
- `FIRMWARE_FEATURES.md` - HM command feature specification

---

#### XM Command Test (`test_XM_command.py`)

**Purpose:** Comprehensive validation of Mixed-Axis Stepper Move (XM) command
**Status:** ✅ Active command with enhanced documentation

**Commands Tested:**
- `XM,<Duration>,<AxisStepsA>,<AxisStepsB>[,<Clear>]` - Mixed-axis geometry moves

**Parameters:**
- `<Duration>` - Time in milliseconds (1 to 2,147,483,647, cannot be 0)
- `<AxisStepsA>` - A axis steps (-2,147,483,648 to 2,147,483,647, int32)
- `<AxisStepsB>` - B axis steps (-2,147,483,648 to 2,147,483,647, int32)
- `<Clear>` - Optional accumulator clear (0-3)
- **Coordinate Conversion:** Axis1 = A+B, Axis2 = A-B (for CoreXY/H-Bot geometry)

**Test Categories:**
1. **Valid XM Commands** - Various A/B combinations, all Clear values
2. **Invalid Duration Values** - Duration = 0
3. **Invalid Clear Values** - Clear > 3
4. **Delay Mode** - Zero steps (A=0, B=0), duration capping
5. **Step Rate Boundary Tests** - High rates, slow moves
6. **Coordinate Conversion Tests** - Verify A+B and A-B calculations
7. **Large Step Values** - Document overflow risks in A±B
8. **Missing Parameters** - Incomplete commands
9. **Extra Parameters** - Unexpected additional parameters
10. **Practical Mixed-Axis Scenarios** - Square paths, diagonal moves

**Validation Improvements (v3.0.3):**
- **Enhanced overflow documentation:**
  - Large A/B values can cause int32 overflow in A+B or A-B
  - Example: A=2^30, B=2^30 → A+B=2^31 (overflow!)
  - Host software must validate A±B within int32 range
- **Explicit parameter validation:**
  - Duration must be >= 1 (0 returns error)
  - Clear must be 0-3 (>3 returns error)
- **Rate checking after conversion:**
  - Limits checked on Axis1/Axis2 (after A±B conversion)
  - Range: 0.00001164 to 25,000 steps/second per axis
- **Delay mode capping:** Duration >100,000ms capped for zero-step moves

**Test Approach:**
1. Sends XM commands with various A/B combinations
2. Validates coordinate conversion (Axis1=A+B, Axis2=A-B)
3. Tests boundary conditions and edge cases
4. Verifies error handling for invalid inputs
5. Confirms proper motion on mixed-axis geometry

**Example Test Set:**
```python
"XM,100,50,0"             # A axis only
"XM,100,0,50"             # B axis only  
"XM,100,50,50"            # Diagonal (both positive)
"XM,100,-50,-50"          # Diagonal (both negative)
"XM,100,100,-50"          # Mixed signs
"XM,0,100,100"            # Invalid: duration = 0
"XM,100,50,50,4"          # Invalid: Clear > 3
"XM,100,0,0"              # Delay mode
"XM,200000,0,0"           # Delay capped at 100,000ms
"XM,100,1200,1200"        # High rate: Axis1=2400 steps/100ms
```

**Total Test Cases:** 45+ comprehensive tests

**Expected Results:**
- Valid commands return OK/XM and execute motion
- Invalid Duration/Clear return error
- Coordinate conversion correct (Axis1=A+B, Axis2=A-B)
- Step rates validated after conversion
- Delay mode works with capping

**Current Status:**
- ✅ All validation tests passing
- ✅ Enhanced documentation in `XM_VALIDATION_IMPROVEMENTS.md`
- ⚠️ Overflow edge cases documented but not tested (would overflow int32)
- ✅ No breaking changes - behavior unchanged

**Critical Notes:**
- **Overflow Risk:** A+B or A-B can overflow int32 if both values are large
- Host software must validate: `-2^31 ≤ (A±B) ≤ 2^31-1`
- Rate limits apply to physical motors (Axis1/2), not logical axes (A/B)
- XM designed for CoreXY, H-Bot, and AxiDraw geometry

**See Also:**
- `XM_VALIDATION_IMPROVEMENTS.md` - Detailed technical documentation
- `FIRMWARE_FEATURES.md` - XM command feature specification

---

## Test Structure and Organization

### Directory Structure

```
EBB_firmware/
├── Analysis/
│   ├── RegressionTests/
│   │   ├── python_send_LM_20230507.py       # LM command regression test
│   │   ├── python_send_LT_20230507.py       # LT command regression test
│   │   ├── python_send_T3_20230507.py       # T3 command regression test
│   │   ├── SMRateChecker.py                 # SM rate validation
│   │   ├── ShortCommandFIFOTest300.py       # FIFO stress test
│   │   ├── USBProcessingTimeTest.py         # USB latency test
│   │   ├── python_send_basic.py             # Basic command test suite
│   │   ├── LM_20230507_ExceptedOutput.csv   # Expected LM outputs
│   │   ├── LM_20230507_ActualOutput.csv     # Captured LM outputs
│   │   ├── LT_20230507_ExpectedOutput.csv   # Expected LT outputs
│   │   ├── LT_20230507_ActualOutput.csv     # Captured LT outputs
│   │   ├── T3_20230507_ExpectedOutput.csv   # Expected T3 outputs
│   │   ├── T3_20230507_ActualOutput.csv     # Captured T3 outputs
│   │   ├── EBB_TestOutputConverter.xlsx     # Analysis spreadsheet
│   │   └── LM_Command_Experiments3A.xlsx    # Test case generator
│   ├── firmware tests/
│   │   ├── test plan.txt                    # Master test plan document
│   │   ├── saleae_test.py                   # Saleae capture with commands
│   │   ├── saleae_test_capture_async_serial.py  # Serial protocol analysis
│   │   └── analyze_csv.py                   # Saleae data analysis script
│   ├── python_send_cmds_EBF.py              # EBF file playback test
│   ├── saleae_example.py                    # Saleae API example
│   ├── LM Command Experiments.xlsx          # Motion math reference
│   └── MinimumMoveTimes.xlsx                # Timing constraints reference
└── Testing/
    └── EBB_ThroughputTest.py                # Command throughput test
```

---

## Running Tests

### Prerequisites

1. **Install PyAxiDraw:**
   ```bash
   pip install pyaxidraw
   ```

2. **Install Plotink (included with PyAxiDraw):**
   ```bash
   pip install plotink
   ```

3. **Connect EBB Hardware:**
   - Connect EBB board via USB
   - Ensure correct firmware version (v3.0.3)
   - Verify device appears as serial port

4. **Install Saleae Logic (optional, for hardware tests):**
   - Download from https://www.saleae.com/
   - Install Python API: `pip install saleae`
   - Connect logic analyzer to EBB test points

### Running Regression Tests

#### LM Command Test
```bash
cd EBB_firmware/Analysis/RegressionTests/
python3 python_send_LM_20230507.py
```

**Expected Output:**
```
connected
b'EBBv13_and_above EB Firmware Version 3.0.3\r\n'
LM,268435456,5,0,0,0,0 :: b'OK\r\n'
 :: b'T,40,S,5,C,0,R,268435456,P,5\r\n'
LM,-268435456,5,0,0,0,0 :: b'OK\r\n'
...
```

**Validation:**
- Compare console output to `LM_20230507_ExceptedOutput.csv`
- Check that all T,S,C,R,P values match expected
- No error messages or timeouts

#### LT Command Test
```bash
python3 python_send_LT_20230507.py
```

**Validation:** Compare against `LT_20230507_ExpectedOutput.csv`

#### T3 Command Test
```bash
python3 python_send_T3_20230507.py
```
**Validation:** Compare against `T3_20230507_ExpectedOutput.csv`

---

### Running Configuration Command Test

```bash
python3 test_SC_command.py
```

**Expected Output:**
```
Connected: b'EBBv13_and_above EB Firmware Version 3.0.3\r\n'
Starting SC Command Validation Tests
======================================================================

======================================================================
Testing SC,1 - Pen Mechanism Selection
======================================================================
PASS: SC,1,0 - Use solenoid only
  Command: SC,1,0
  Response: OK

...

======================================================================
TEST SUMMARY
======================================================================
Total Tests: 50+
Passed: 50+
Failed: 0
Success Rate: 100.0%

ALL TESTS PASSED
```

**Validation:**
- Check that all valid SC parameters return OK
- Verify invalid parameters return error messages
- Confirm clamping behavior for SC,8 and SC,9
- Ensure configuration restores to safe defaults

---
---

### Running Rate Verification Test

```bash
python3 SMRateChecker.py
```

**Test Duration:** ~20 hours (can be modified in code)

**Monitor Output:**
- Script prints only commands with errors exceeding threshold
- All results logged to `SMRateCheckOutput.csv`
- Silent operation indicates all rates within tolerance

**Stopping Early:** Ctrl+C to terminate

---

### Running FIFO Test

```bash
python3 ShortCommandFIFOTest300.py
```

**Observation:**
- Monitor for command completion
- Check for "FIFO full" errors
- Verify smooth motion (no stuttering)

---

### Running Basic Command Test

```bash
python3 python_send_basic.py
```

**Expected Output:**
```
connected
b'EBBv13_and_above EB Firmware Version 3.0.3\r\n'
SM,100,100,0 :: b'OK\r\n'
SM,100,-100,0 :: b'OK\r\n'
...
```

---

### Running Hardware-in-the-Loop Tests with Saleae

#### Step 1: Setup Saleae Logic Analyzer

Connect logic analyzer channels to EBB test points:
- **Channel 0:** STEP1 (stepper motor 1 step signal)
- **Channel 1:** DIR1 (stepper motor 1 direction)
- **Channel 2:** STEP2 (stepper motor 2 step signal)
- **Channel 3:** DIR2 (stepper motor 2 direction)
- **Channel 4:** In ISR (debug pin indicating ISR execution)
- **Channel 5:** Cmd Load (debug pin for command loading)
- **Channel 6:** FIFO Empty (debug pin for FIFO status)
- **Channel 7:** ISR Serial (debug UART output)

#### Step 2: Start Saleae Logic 2 Application

Ensure Logic 2 is running and listening on port 10430 (default).

#### Step 3: Run Saleae Test Script

```bash
cd EBB_firmware/Analysis/firmware\ tests/
python3 saleae_test.py
```

**Script Actions:**
1. Connects to EBB hardware
2. Sends command sequence
3. Captures 2 seconds of logic analyzer data at 32 MSa/s
4. Exports raw digital data to CSV
5. Saves capture to `.sal` file in timestamped directory

**Output Directory:**
```
output-YYYY-MM-DD_HH-MM-SS/
├── digital.csv          # Raw signal data
├── example_capture.sal  # Saleae capture file
└── async_serial_export.csv  # Decoded serial data (if using serial capture variant)
```

#### Step 4: Analyze Captured Data

```bash
python3 analyze_csv.py
```

**Analysis Metrics:**
- Step pulse count for each motor
- Min/Max/Average pulse width (high time)
- Min/Max/Average inter-pulse time (low time)
- Step frequency statistics
- Direction signal correlation

**Output Statistics Example:**
```
Step 1 Count: 1250
Step 1 Min High Time: 1.5 µs
Step 1 Max High Time: 2.1 µs
Step 1 Average Frequency: 12.5 kHz
```

---

## Test Coverage

### Well-Tested Features ✅

| Feature | Test Type | Automation | Coverage |
|---------|-----------|------------|----------|
| **LM Command** | Regression | Automated | Excellent |
| **LT Command** | Regression | Automated | Excellent |
| **T3 Command** | Regression | Automated | Excellent |
| **SM Command** | Rate Validation | Automated | Good |
| **FIFO Queue** | Stress Test | Automated | Good |
| **USB Communication** | Throughput | Semi-automated | Good |

### Partially Tested Features ⚠️

| Feature | Test Type | Automation | Coverage |
|---------|-----------|------------|----------|
| **XM Command** | Basic | Manual | Limited |
| **HM Command** | Basic | Manual | Limited |
| **CM Command** | None | N/A | None |
| **Servo Control (S2, SP, TP)** | Manual | Manual | Limited |
| **Engraver (SE)** | Manual | Manual | Limited |
| **Query Commands (QM, QS, QG)** | Functional | Manual | Fair |
| **Configuration (SC Command)** | Regression | Automated | Good |

### Minimally Tested Features ❌

| Feature | Test Type | Automation | Coverage |
|---------|-----------|------------|----------|
| **Analog Input (A, AC, QC)** | None | N/A | None |
| **Digital I/O (C, O, I, PI, PO, PD)** | None | N/A | None |
| **Memory Read/Write (MR, MW)** | None | N/A | None |
| **Limit Switches** | None | N/A | None |
| **Power Management** | None | N/A | None |
| **Checksum Validation** | None | N/A | None |
| **Bootloader (BL)** | Manual | Manual | None |
| **Configuration (SC, CU)** | Ad-hoc | Manual | Minimal |

### Test Coverage Summary

- **Automated Regression Tests:** ~10 test scripts
- **Commands with Automated Tests:** 8 (LM, LT, T3, SM, SC, CM*, HM, XM)
  - *CM test exists but command is disabled in firmware
- **Commands with Manual Tests:** 1 (basic queries)
- **Commands with No Tests:** 20+ (most auxiliary functions)
- **Overall Coverage:** ~30% of firmware features have automated tests

---

## Hardware-in-the-Loop Testing

### Philosophy

EBB firmware testing relies heavily on **hardware-in-the-loop (HIL)** testing because:

1. **Real-Time Constraints:** 25kHz ISR timing cannot be simulated accurately
2. **Hardware Dependencies:** Stepper drivers, USB stack, and peripherals
3. **Integration Testing:** Validates complete system behavior
4. **Electrical Verification:** Signal timing, voltage levels, and noise immunity

### Signal Monitoring

Tests use GPIO pins for real-time debugging:

| Debug Pin | Enabled By | Purpose |
|-----------|------------|---------|
| RC0 | `CU,250,1` | ISR execution indicator (toggles every ISR) |
| RC1 | `CU,250,1` | Command load from FIFO indicator |
| RC7 | `CU,257,1` | Command parsing indicator |
| UART | `CU,251,1` | ISR statistics output (end of move) |
| UART | `CU,252,1` | Full ISR debug (every tick) |

### Saleae Logic Analyzer Integration

#### Channel Assignments

Standard test setup uses these channel mappings:

```
Channel 0: STEP1    (RD0) - Motor 1 step pulses
Channel 1: DIR1     (RD2) - Motor 1 direction
Channel 2: STEP2    (RD1) - Motor 2 step pulses
Channel 3: DIR2     (RD3) - Motor 2 direction
Channel 4: In_ISR   (RC0) - ISR timing debug
Channel 5: Cmd_Load (RC1) - Command FIFO debug
Channel 6: FIFO_Empty (LED) - FIFO status
Channel 7: ISR_Serial (TX) - Debug UART output
Channel 8: Trigger  (manual) - External trigger
```

#### Capture Configuration

**Sample Rate:** 10-32 MSa/s (10-32 million samples/second)
- 10 MSa/s: General purpose testing
- 32 MSa/s: High-speed signal analysis (25kHz ISR = 40µs period)

**Capture Duration:**
- Short tests: 2 seconds
- Long tests: 5-10 seconds

**Trigger Setup:**
- Free run (no trigger) for basic tests
- Rising edge on STEP1 for motion analysis
- External trigger for synchronized testing

#### Data Export

Saleae captures export to:
1. **digital.csv** - Raw timestamped signal transitions
2. **async_serial_export.csv** - Decoded UART data
3. **.sal file** - Complete capture for offline analysis

### Analysis Scripts

#### `analyze_csv.py`

Analyzes `digital.csv` to extract:

**Step Signal Analysis:**
```python
step1_count          # Total steps taken
step1_rising_time    # Time of last rising edge
step1_falling_time   # Time of last falling edge
step1_max_high_time  # Longest pulse width
step1_min_high_time  # Shortest pulse width
step1_ave_high_time  # Average pulse width
step1_max_low_time   # Longest inter-pulse gap
step1_min_low_time   # Shortest inter-pulse gap
step1_ave_freq       # Average step frequency
```

**Direction Correlation:**
- Validates direction signal stable during steps
- Detects direction changes mid-move (error condition)

**ISR Timing:**
- Measures ISR execution frequency
- Detects late/missed ISR executions
- Validates 25kHz ±tolerance

---

## Creating New Tests

### Test Template

Use this template for new test scripts:

```python
#!/usr/bin/env python
# -*- encoding: utf-8 -#-

'''
Test Name: [Brief description]
Purpose: [What this test validates]
Expected Results: [Pass/fail criteria]
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

def block(ad_ref, timeout_ms=None):
    """Wait for motion to complete"""
    if timeout_ms is None:
        time_left = 60000
    else:
        time_left = timeout_ms

    while True:
        qg_val = bytes.fromhex(ebb_serial.query(ad_ref.plot_status.port, 'QG\r').strip())
        motion = qg_val[0] & (15).to_bytes(1, byteorder='big')[0]
        if motion == 0:
            return True
        if time_left <= 0:
            return False
        if time_left < 10:
            time.sleep(time_left / 1000)
            time_left = 0
        else:
            time.sleep(0.01)
            if timeout_ms is not None:
                time_left -= 10

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

# Test commands
command_list = [
    # Add your test commands here
    "SM,100,100,0",
    "QM",
]

# Execute tests
for command in command_list:
    response = query(the_port, command + '\r')
    print(f"{command} :: {response.strip()}")
    
    # Wait for motion commands
    if command.startswith(('SM', 'XM', 'HM', 'LM', 'LT', 'T3')):
        block(ad)

# Cleanup
ad.disconnect()
print("Test complete")
```

### Adding Expected Output Validation

For regression tests with expected outputs:

1. **Capture baseline output:**
   ```bash
   python3 your_test.py > baseline_output.txt
   ```

2. **Convert to CSV format:**
   ```python
   import csv
   
   # Parse output lines
   expected_data = []
   for line in output_lines:
       if line.startswith('T,'):
           expected_data.append(parse_response(line))
   
   # Write CSV
   with open('expected_output.csv', 'w', newline='') as f:
       writer = csv.writer(f)
       writer.writerows(expected_data)
   ```

3. **Add validation to test:**
   ```python
   import csv
   
   # Load expected results
   expected = []
   with open('expected_output.csv', 'r') as f:
       reader = csv.reader(f)
       expected = list(reader)
   
   # Compare actual vs expected
   for i, (actual, expected) in enumerate(zip(actual_results, expected)):
       if actual != expected:
           print(f"FAIL: Test {i}: Expected {expected}, got {actual}")
   ```

### Best Practices

1. **Use descriptive names:** `test_servo_position_limits.py` not `test3.py`
2. **Document expected behavior:** Include docstrings and comments
3. **Enable relevant debug modes:**
   - `CU,250,1` for GPIO timing debug
   - `CU,251,1` for ISR statistics
   - `CU,255,1` for command parsing debug
4. **Reset state between tests:**
   - `R\r` to software reset
   - `CS\r` to clear step position
   - `EM,0,0\r` to disable motors
5. **Include error handling:**
   - Timeout on blocked waits
   - Validate response format
   - Check for error codes
6. **Log all data:**
   - Write results to CSV for analysis
   - Timestamp test runs
   - Include firmware version in output

---

## Known Issues and Limitations

### Test Infrastructure Limitations

1. **No Unified Test Runner**
   - Tests must be run individually
   - No automated test suite execution
   - No continuous integration setup

2. **Manual Result Comparison**
   - Expected outputs stored as separate CSV files
   - No automated comparison tools
   - Visual inspection required for validation

3. **Hardware Dependency**
   - All tests require physical EBB board
   - Cannot run in CI/CD pipeline
   - Test speed limited by actual motion execution

4. **No Unit Tests**
   - No firmware-level unit tests
   - Cannot test individual C functions in isolation
   - All testing is integration-level

5. **Limited Error Detection**
   - Tests don't validate all error conditions
   - Edge cases not systematically covered
   - No negative testing (invalid inputs)

### Test Coverage Gaps

1. **Configuration Persistence**
   - SC command parameters not validated
   - EEPROM storage not tested
   - Power-cycle behavior not verified

2. **Error Recovery**
   - E-stop behavior not tested
   - Recovery from error states not validated
   - USB disconnect/reconnect not covered

3. **Concurrent Operations**
   - Multiple servo channels not tested together
   - Analog sampling during motion not tested
   - Digital I/O during motion not verified

4. **Timing Edge Cases**
   - Maximum command rate not determined
   - FIFO overflow handling not tested
   - ISR worst-case timing not measured

5. **Hardware Variants**
   - Tests focus on EBB v1.3+
   - Older board revisions not covered
   - Driver configuration modes not all tested

### Future Test Improvements

#### Recommended Additions

1. **Automated Test Suite**
   - Implement pytest framework
   - Create test runner script
   - Add automated CSV comparison

2. **Expanded Command Coverage**
   - Test all query commands systematically
   - Validate configuration commands
   - Test analog and digital I/O

3. **Negative Testing**
   - Send invalid parameters
   - Test buffer overflow conditions
   - Validate error messages

4. **Performance Benchmarks**
   - Measure maximum command rate
   - Profile ISR execution time
   - Test FIFO depth limits

5. **Simulation Environment**
   - Create firmware simulator
   - Enable CI/CD integration
   - Faster iteration on algorithm changes

6. **Hardware Test Fixtures**
   - Automated load testing
   - Environmental stress testing
   - Long-duration reliability tests

---

## Test Plan Reference

The master test plan is documented in `firmware tests/test plan.txt`:

### Planned Test Categories (from test plan.txt)

#### 1. Command Tests
- Test command responses (default and new response mode)
- Execute each command and confirm proper response

#### 2. Move Command Tests
- **Test step counts:** Record global positions and Saleae analysis
- **Test step rates:** Confirm step pulse rates at beginning/middle/end
- **Test move command rates:** Measure commands per second, find gap thresholds

#### 3. FIFO Tests
- Test FIFO depth configuration
- Verify command queuing behavior
- Stress test with rapid short commands

**Note:** Many items in the test plan are not yet implemented.

---

## Appendix: Test Command Reference

### Debug Configuration Commands

Enable these before running tests:

| Command | Purpose |
|---------|---------|
| `CU,1,0` | Disable OK acknowledgments (reduce output noise) |
| `CU,1,1` | Enable OK acknowledgments |
| `CU,250,1` | Enable GPIO debug pins (ISR timing) |
| `CU,251,1` | Enable UART ISR debug (end-of-move statistics) |
| `CU,252,1` | Enable full ISR debug (every ISR tick - verbose) |
| `CU,253,1` | Enable UART command debug (show received bytes) |
| `CU,255,1` | Enable USB command parsing debug |
| `CU,256,1` | Block FIFO (parse-only mode for testing) |
| `CU,257,1` | Enable RC7 command parsing indicator |

### Query Commands for Testing

| Command | Returns | Purpose |
|---------|---------|---------|
| `V` | Firmware version string | Verify connection |
| `QM` | Motor status, FIFO status | Check if motion complete |
| `QS` | Global step positions | Verify step counts |
| `QG` | General status (packed binary) | Comprehensive status check |
| `QB` | Button state | Test input reading |
| `QC` | Current pot ADC value | Test analog input |

### Reset Commands

| Command | Action |
|---------|--------|
| `R` | Software reset (re-initialize) |
| `RB` | Reboot via watchdog or reset vector |
| `CS` | Clear step position counters |
| `ES` | Emergency stop (clear FIFO, stop motion) |

---

## Contact and Support

For questions about testing:
- **GitHub:** https://github.com/evil-mad/EggBot
- **Forums:** http://wiki.evilmadscientist.com/
- **Documentation:** See `docs/` folder for EBB command reference

---

**Document Version:** 1.0  
**Created:** December 13, 2025  
**Author:** Based on analysis of EBB firmware testing infrastructure
