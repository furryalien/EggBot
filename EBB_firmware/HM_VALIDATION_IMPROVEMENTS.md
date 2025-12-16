# HM (Home Motor) Command Validation Improvements

**Date:** December 13, 2025  
**Firmware Version:** 3.0.3  
**Command:** HM (Home Motor / Absolute Move)  
**Status:** ✅ Active Command with Validation Improvements

---

## Executive Summary

The HM (Home Motor) command has been enhanced with improved parameter validation, replacing silent error correction with proper error reporting, enforcing documented parameter constraints, and adding parameter pairing validation. These improvements ensure robust command handling and better user feedback for invalid inputs.

---

## Command Overview

### Syntax
```
HM,<StepFrequency>[,<Position1>,<Position2>]<CR>
```

### Parameters

| Parameter | Type | Range | Required | Description |
|-----------|------|-------|----------|-------------|
| StepFrequency | uint32 | 2-25000 Hz | Yes | Step rate for primary axis |
| Position1 | int32 | ±2,147,483,647 | Optional* | Target position for motor 1 (relative to home) |
| Position2 | int32 | ±2,147,483,647 | Optional* | Target position for motor 2 (relative to home) |

**\*Parameter Pairing:** If Position1 is provided, Position2 MUST also be provided (and vice versa). Both present or both absent.

### Purpose
The HM command moves motors either to home position (0,0) or to an absolute position specified relative to home. It is the only EBB motion command that accepts absolute positions; all others use relative movement. The command blocks until all previous motion completes, then computes the required steps based on current global position and executes the move at the specified step frequency.

---

## Validation Improvements

### 1. Replaced Silent Clamping with Error Reporting

**Issue:** Original code silently clamped invalid StepFrequency values to valid range, providing no feedback to user.

**Before:**
```c
// StepRate must be from 1 to 25000
if (gHM_StepRate < 1u)
{
  gHM_StepRate = 1;
}
else if (gHM_StepRate > 25000u)
{
  gHM_StepRate = 25000;
}
```

**After:**
```c
// Validate StepFrequency: must be from 2 to 25000 Hz
// Note: Documentation specifies minimum is 2 Hz, not 1 Hz
// Changed from silent clamping to proper error reporting for invalid values
if (gLimitChecks)
{
  if (gHM_StepRate < 2u)
  {
    ErrorSet(kERROR_PARAMETER_OUTSIDE_LIMIT);
    return;
  }
  if (gHM_StepRate > 25000u)
  {
    ErrorSet(kERROR_PARAMETER_OUTSIDE_LIMIT);
    return;
  }
  ...
}
```

**Rationale:** 
- **User Feedback:** Users now receive clear error messages for invalid frequencies
- **Debugging:** Makes it obvious when host software generates invalid commands
- **Consistency:** Matches error handling pattern used by other commands (SC, CM, etc.)
- **Documentation Compliance:** Silent clamping was not documented behavior

---

### 2. Frequency Minimum Corrected (1 Hz → 2 Hz)

**Issue:** Code allowed frequency of 1 Hz, but documentation states minimum is 2 Hz.

**Before:**
- Code checked: `frequency >= 1`
- Documentation stated: "from 2 to 25000"
- Inconsistency between code and docs

**After:**
- Code checks: `frequency >= 2`
- Matches documentation specification exactly

**Rationale:** The documentation across multiple sources (ebb.html, ebb2.html) consistently states minimum is 2 Hz. Frequencies below 2 Hz may cause timing issues or result in excessively slow motion unsuitable for practical use.

---

### 3. Position Parameter Pairing Validation

**Issue:** No validation that Position1 and Position2 must be provided together.

**New Validation:**
```c
// Validate Position parameter pairing
// If Position1 is present, Position2 must also be present (and vice versa)
// This is enforced by the command specification
if (Pos1_Present != Pos2_Present)
{
  ErrorSet(kERROR_MISSING_PARAMETER);
  return;
}
```

**Implementation:**
```c
ExtractReturnType Pos1_Present, Pos2_Present;

Pos1_Present = extract_number(kLONG,  &gHM_Pos1,     kOPTIONAL);
Pos2_Present = extract_number(kLONG,  &gHM_Pos2,     kOPTIONAL);
```

**Behavior:**
- `HM,1000` ✅ Valid - home move to (0,0)
- `HM,1000,100,200` ✅ Valid - absolute move to (100,200)
- `HM,1000,100` ❌ Invalid - Position2 missing
- `HM,1000,,200` ❌ Invalid - Position1 missing

**Rationale:**
- **Command Specification:** Documentation implies both positions required if any provided
- **User Error Prevention:** Catches typos and incomplete commands
- **Semantic Correctness:** A 2D move requires both X and Y coordinates

---

### 4. Enhanced Documentation and Comments

**Improvements:**
- Added detailed inline comments explaining validation rules
- Documented the blocking behavior of HM command
- Noted overflow risk (though unlikely in practice)
- Clarified frequency range and rationale

**Example:**
```c
// HM command always waits for all previous motion to complete
// This blocking behavior ensures accurate global step position reading

// Make a local copy of the things we care about. This is how far we need to move.
// Check for potential overflow when computing move distance
// gSteps = -globalStepCounter + gHM_Pos
// Maximum safe values to avoid overflow in 32-bit signed arithmetic:
// If globalStepCounter and gHM_Pos have opposite signs and large magnitudes,
// the subtraction could overflow. However, this is extremely unlikely in practice
// as it would require 0x7FFFFFFF steps (23 hours at 25kHz).
```

---

## Test Coverage

A comprehensive test suite has been created: `test_HM_command.py`

### Test Categories

1. **Valid HM Commands - Home Move** (5 tests)
   - Minimum frequency (2 Hz)
   - Various frequencies up to maximum (25 kHz)
   - Home move format (no position parameters)

2. **Valid HM Commands - Absolute Position** (7 tests)
   - Positive positions
   - Negative positions
   - Single-axis moves (X-only, Y-only)
   - Diagonal moves
   - Return to home from offset

3. **Invalid Step Frequency Parameters** (5 tests)
   - Zero frequency
   - Frequency of 1 (below minimum)
   - Frequencies above 25000 Hz
   - Maximum uint16 frequency

4. **Missing Position2 Parameter** (3 tests)
   - Position1 present but Position2 missing
   - Various Position1 values without Position2
   - Validates error reporting

5. **Large Position Values** (6 tests - documented but skipped)
   - Very large position values (would take excessive time)
   - Maximum/minimum int32 values
   - Overflow risk scenarios

6. **Zero Steps Moves** (1 test)
   - Move to current position (should complete instantly)

7. **Boundary Frequency Values** (2 tests)
   - Minimum valid frequency (2 Hz) at home
   - Maximum valid frequency (25 kHz) at home

8. **Practical Homing Scenarios** (4 tests)
   - Return to home from various positions
   - Horizontal-only moves
   - Vertical-only moves

9. **Extra Parameters** (2 tests)
   - Three position parameters (should error)
   - Multiple extra parameters

**Total Tests:** 35+ (29 executable + 6 documented for large positions)

---

## Validation Rules Summary

| Validation | Rule | Error Type |
|------------|------|------------|
| Frequency minimum | StepFrequency >= 2 | kERROR_PARAMETER_OUTSIDE_LIMIT |
| Frequency maximum | StepFrequency <= 25000 | kERROR_PARAMETER_OUTSIDE_LIMIT |
| Position pairing | Both present OR both absent | kERROR_MISSING_PARAMETER |
| Position1 range | -2147483648 to 2147483647 | (Implicit in int32 type) |
| Position2 range | -2147483648 to 2147483647 | (Implicit in int32 type) |

---

## Implementation Details

### Files Modified
- **ebb.c** - `parse_HM_packet()` function (lines 3205-3260)

### Key Changes

1. **Variable Additions:**
   ```c
   ExtractReturnType Pos1_Present, Pos2_Present;
   ```

2. **Parameter Extraction with Return Values:**
   ```c
   Pos1_Present = extract_number(kLONG,  &gHM_Pos1,     kOPTIONAL);
   Pos2_Present = extract_number(kLONG,  &gHM_Pos2,     kOPTIONAL);
   ```

3. **Validation Block:**
   ```c
   if (gLimitChecks)
   {
     if (gHM_StepRate < 2u) { ... }
     if (gHM_StepRate > 25000u) { ... }
     if (Pos1_Present != Pos2_Present) { ... }
   }
   ```

### Behavior Changes

| Scenario | Before | After |
|----------|--------|-------|
| `HM,0` | Silently clamped to `HM,1` | Error: Parameter outside limit |
| `HM,1` | Accepted (clamped) | Error: Parameter outside limit |
| `HM,50000` | Silently clamped to `HM,25000` | Error: Parameter outside limit |
| `HM,1000,100` | Moved to (100, ?) | Error: Missing parameter |
| `HM,5000` | Moved to (0,0) | ✅ No change |
| `HM,5000,100,200` | Moved to (100,200) | ✅ No change |

---

## Breaking Changes

### Minor Breaking Changes

1. **Frequency Clamping Removed**
   - **Before:** Invalid frequencies silently clamped to 1-25000 range
   - **After:** Invalid frequencies cause error
   - **Migration:** Ensure host software generates frequencies in range 2-25000 Hz

2. **Frequency Minimum Changed**
   - **Before:** Minimum 1 Hz accepted (after clamping)
   - **After:** Minimum 2 Hz enforced
   - **Migration:** Change any `HM,1,...` commands to `HM,2,...` or higher

3. **Position Parameter Pairing Enforced**
   - **Before:** Single position parameter might be accepted (undefined behavior)
   - **After:** Single position parameter causes error
   - **Migration:** Ensure both Position1 and Position2 provided or neither

### Non-Breaking Changes

- Validation only active when `gLimitChecks` is enabled (default: ON)
- Valid command formats unchanged
- All documented command usage remains supported

---

## Command Behavior Notes

### Blocking Behavior

The HM command is **blocking** at the parsing stage:
1. Waits until FIFO is completely empty
2. Waits until any executing motion command completes
3. Reads current global step position
4. Computes required move distance
5. Executes move

**Typical Delay:** ~5ms between command reception and motion start (after FIFO empty)

### Motion Characteristics

- **Primary Axis:** Whichever axis has more steps to move
- **Secondary Axis:** The other axis
- **Step Frequency:** Applied to primary axis only
- **Secondary Rate:** Calculated to maintain straight line motion
- **Move Linearity:** Generally straight, but may break into segments if secondary axis rate would be < 1.3 Hz

### Overflow Risk

**Theoretical Issue:** Computing `gSteps = -globalStepCounter + gHM_Pos` could overflow if:
- Global counter and position have opposite signs
- Both have large magnitudes near ±2^31

**Practical Reality:** Extremely unlikely because:
- 0x7FFFFFFF steps = ~2.1 billion steps
- At 25 kHz max rate = 23 hours continuous motion
- Typical plots use << 1 million steps

**Current Handling:** Documented but not explicitly checked (overflow would manifest as incorrect move direction/distance)

---

## Testing Instructions

### Running Test Suite

```bash
cd /home/david/code/EggBot-1/EBB_firmware/Analysis/RegressionTests/
python3 test_HM_command.py
```

### Expected Results

**With Validation Improvements:**
```
Testing Invalid Step Frequency Parameters:
PASS: Zero step frequency (should error)
PASS: Step frequency of 1 (below minimum of 2)
PASS: Step frequency above maximum (25000)

Testing Missing Position2 Parameter:
PASS: Position1 present but Position2 missing (should error)

Success Rate: 100%
ALL TESTS PASSED
```

**Without Validation Improvements (Old Firmware):**
```
Testing Invalid Step Frequency Parameters:
FAIL: Zero step frequency (should error)
  Expected: Error
  Response: OK (silently clamped)
  
FAIL: Step frequency of 1 (below minimum of 2)
  Expected: Error
  Response: OK (silently clamped)
```

---

## Comparison with Other Commands

### Similar Improvements

| Command | Improvement Type | Status |
|---------|------------------|--------|
| **SC** | Parameter validation, range checking | ✅ Complete |
| **CM** | Frequency/coordinate validation | ✅ Complete |
| **HM** | Frequency validation, parameter pairing | ✅ Complete |

### Common Pattern

All three commands now follow the same validation pattern:
1. ✅ Replace silent correction with error reporting
2. ✅ Enforce documented parameter ranges exactly
3. ✅ Add parameter relationship validation
4. ✅ Provide comprehensive test suites
5. ✅ Create detailed technical documentation

---

## Known Limitations

### 1. Overflow Not Explicitly Detected

**Issue:** Large position values combined with large global counters could theoretically overflow.

**Current Handling:** Documented but not checked.

**Mitigation:** 
- Extremely unlikely in practice (23+ hours at max rate)
- Would manifest as incorrect move direction/distance
- User would notice and correct

**Future Enhancement:** Could add overflow detection:
```c
// Pseudocode for future enhancement
INT32 max_safe = 2147483647 - abs(globalStepCounter1);
if (abs(gHM_Pos1) > max_safe) {
  ErrorSet(kERROR_PARAMETER_OUTSIDE_LIMIT);
  return;
}
```

### 2. Long Execution Time

**Issue:** Commands with very large position differences take a long time to execute.

**Example:** Move from (0,0) to (1000000, 1000000) at 2 Hz:
- Primary axis: 1,000,000 steps
- Rate: 2 steps/second
- Time: 500,000 seconds = 138 hours

**Current Handling:** Test suite documents but skips these tests.

**Mitigation:** User responsibility to avoid impractical moves.

### 3. Secondary Axis Rate Limitation

**Issue:** When primary/secondary step ratio is very large, secondary rate may drop below 1.3 Hz, causing move to break into segments.

**Example:** Move from (0,0) to (10000, 1)
- Primary axis: 10,000 steps
- Secondary axis: 1 step
- Secondary would need to move 1 step over entire duration

**Current Handling:** Firmware automatically breaks move into multiple segments.

**Effect:** Move may not be perfectly straight line.

---

## Documentation References

### Official Documentation

- **ebb.html:** HM command specification (lines 949-1020)
- **ebb2.html:** Extended HM documentation (lines 666-710)
- **FIRMWARE_FEATURES.md:** Feature analysis and status

### Key Quotes from Documentation

**ebb2.html (line 673):**
> "StepFrequency is an unsigned integer in the range from **2 to 25000**. It represents the step frequency, in steps per second..."

**ebb2.html (line 696):**
> "Take note that the move may not be a straight line. There are circumstances (where one axis has many steps to take, and the other has very few) where the homing operation is broken down into to move segments to prevent a step rate on the small axis from being lower than 1.3Hz."

**ebb.html (line 987):**
> "There is a limitation to Position1 and Position2. When they are each added to the negative of the respective current global positions to compute the number of steps necessary to complete this HM move, the sum must not overflow a signed 32 bit number."

---

## Impact Assessment

### Code Quality Impact
- ✅ **Improved Error Handling:** Proper error reporting instead of silent correction
- ✅ **Better User Experience:** Clear feedback on invalid commands
- ✅ **Documentation Compliance:** Code matches documented behavior exactly
- ✅ **Consistency:** Follows validation patterns from SC and CM commands

### Performance Impact
- ✅ **Negligible:** Additional checks execute only during command parsing
- ✅ **No ISR Impact:** Validation occurs before motion starts
- ✅ **Minimal Overhead:** Simple integer comparisons

### User Impact
- ⚠️ **Breaking Changes:** Silent clamping removed, minimum frequency changed
- ✅ **Better Debugging:** Invalid commands now produce clear error messages
- ✅ **Parameter Safety:** Position pairing prevents incomplete commands
- ⚠️ **Migration Required:** Some host software may need frequency adjustments

---

## Migration Guide

### For Host Software Developers

#### Check 1: Frequency Range
```python
# Before (might have used frequency=1)
ebb.send_command(f"HM,1,0,0")

# After (use minimum 2 Hz)
ebb.send_command(f"HM,2,0,0")
```

#### Check 2: Parameter Pairing
```python
# Before (undefined behavior)
ebb.send_command(f"HM,5000,100")  # Missing Position2

# After (both or neither)
ebb.send_command(f"HM,5000,100,100")  # Both present
# OR
ebb.send_command(f"HM,5000")  # Neither present (home move)
```

#### Check 3: Error Handling
```python
# After improvements, check for errors
response = ebb.send_command("HM,50000")  # Invalid frequency
if "Error" in response or "!" in response:
    print(f"HM command failed: {response}")
    # Handle error appropriately
```

### Testing Migration

1. **Identify HM Usage:** Search codebase for "HM," commands
2. **Check Frequencies:** Ensure all ≥ 2 Hz and ≤ 25000 Hz
3. **Validate Positions:** Ensure Position1/Position2 always paired
4. **Test Error Paths:** Verify host software handles HM errors gracefully
5. **Update Documentation:** Note frequency minimum is 2 Hz, not 1 Hz

---

## Future Enhancements

### Recommended Additions

1. **Overflow Detection**
   - Explicitly check for overflow before computing move distance
   - Provide clear error message: "Position change too large"

2. **Estimated Time Reporting**
   - Calculate and optionally report estimated move duration
   - Warning if move would take > 60 seconds

3. **Position Validation**
   - Optional check that target position is reachable
   - Warning if move is unusually large

4. **Interrupt Support**
   - Allow HM command to be interrupted mid-execution
   - Currently must complete or use E-stop

5. **Progress Reporting**
   - Optional periodic progress updates for long HM moves
   - Query command to check HM completion percentage

---

## Conclusion

The HM command validation improvements bring it in line with modern firmware standards, replacing legacy silent error correction with proper error reporting and parameter validation. The changes ensure that the implementation matches the documentation exactly, provide better user feedback, and establish consistency with other recently improved commands (SC and CM).

While there are minor breaking changes (frequency minimum and parameter pairing), these align with documented behavior and improve overall system robustness. The comprehensive test suite validates all aspects of the command and provides a foundation for future regression testing.

**Overall Assessment:** The HM command is now well-validated, properly documented, and ready for production use with confidence in its error handling and parameter checking.

---

**Document Version:** 1.0  
**Author:** Based on analysis of EBB firmware and testing infrastructure  
**Status:** Complete and ready for review

---

## References

- **Implementation:** `/home/david/code/EggBot-1/EBB_firmware/app.X/source/ebb.c` (lines 3205-3260)
- **Test Suite:** `/home/david/code/EggBot-1/EBB_firmware/Analysis/RegressionTests/test_HM_command.py`
- **Documentation:** 
  - `docs/ebb.html` (HM command section)
  - `docs/ebb2.html` (HM extended documentation)
  - `FIRMWARE_FEATURES.md` (Feature analysis)
  - `tests.md` (Testing infrastructure)
- **Related Work:**
  - `SC_VALIDATION_IMPROVEMENTS.md` (Similar improvements for SC command)
  - `CM_VALIDATION_IMPROVEMENTS.md` (Similar improvements for CM command)
