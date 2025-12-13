# G-Code Plotter Timer and Distance Tracking Feature Specification

## Overview
Add real-time and estimated tracking capabilities for plot time and distance to the EggBot G-Code Plotter GUI.

## Feature Components

### 1. Timer System
Track the actual elapsed time during plot execution.

**Requirements:**
- Start timer when plotting begins (user clicks "Start Plot")
- Stop timer when plotting ends (all commands completed or user stops)
- Display format: `HH:MM:SS` or `MM:SS` for shorter plots
- Show both:
  - **Actual Time**: Real elapsed time during current/last plot
  - **Estimated Time**: Calculated before plot starts based on distance and speed

### 2. Distance Tracking
Track the distance of pen movements in millimeters.

**Requirements:**
- Calculate total distance from G-code file when parsed
- Track actual distance plotted in real-time during execution
- Show both:
  - **Actual Distance**: Distance plotted so far (in mm)
  - **Estimated Distance**: Total distance calculated from G-code file (in mm)

### 3. Estimation Calculations

#### Estimated Distance
- Parse all G0/G1 commands in G-code file
- Calculate Euclidean distance between consecutive points: `sqrt((x2-x1)² + (y2-y1)²)`
- Sum all movement distances
- Only count pen-down movements (Z=0) or all movements (TBD)

#### Estimated Time
- Based on estimated distance and feedrate/speed settings
- Formula: `time = distance / feedrate`
- Account for pen up/down servo delays (if applicable)
- Speed settings source: (TBD - need to identify where speed is configured)

## User Interface Design

### Display Location
Add a new section in the Status frame showing:

```
┌─ Plot Metrics ─────────────────────┐
│                                     │
│ Time:     00:42 / 01:15 (est.)     │
│ Distance: 245.3 / 450.2 mm (est.)  │
│                                     │
└─────────────────────────────────────┘
```

Alternative vertical layout:
```
┌─ Plot Metrics ──────────┐
│ Time (Actual):     00:42 │
│ Time (Estimated): 01:15  │
│                          │
│ Distance (Actual): 245.3 │
│ Distance (Est.):   450.2 │
└──────────────────────────┘
```

### Display States
1. **Before parsing**: Show placeholders `-- / --`
2. **After parsing**: Show `0.0 / [estimated]`
3. **During plotting**: Update actual values in real-time
4. **After completion**: Show final values

### Reset Behavior
- Reset actual values when "Start Plot" is clicked
- Recalculate estimates when new file is parsed
- Preserve last values until new plot starts

## Technical Implementation Notes

### Timer Implementation
- Use `time.time()` to record start time
- Calculate elapsed time periodically in `monitor_progress()`
- Store start_time as instance variable
- Update display every 100-500ms (same as progress monitor)

### Distance Tracking
- **Estimated**: Calculate during `parse_file()` by analyzing all movement commands
- **Actual**: Track cumulative distance in `plot_worker()` as each command executes
- Store previous position to calculate incremental distances
- Use same coordinate system as plotter (need to understand EggBot coordinate mapping)

### Data Storage
Add instance variables to `GCodePlotterGUI`:
- `self.estimated_distance_mm` - calculated during parsing
- `self.actual_distance_mm` - accumulated during plotting
- `self.estimated_time_sec` - calculated from distance/speed
- `self.actual_time_sec` - measured during plotting
- `self.plot_start_time` - timestamp when plot starts

## Decisions Made

1. **Distance Calculation Scope**: ✅ Calculate ALL movements (both pen-up and pen-down)
   - X and Y movements are the primary indicators for time and distance
   - All travel moves contribute to overall plot metrics

2. **Speed Settings**: ✅ From G-code and plotter configuration
   - Feedrate specified in G-code (F parameter) - default 1000 mm/min
   - Rapid moves (G0) use DEFAULT_SPEED = 200 steps/second
   - Controlled moves (G1) use feedrate converted to steps/second
   - Formula: `speed = (feedrate_mm_per_min / 60) * STEPS_PER_MM / STEP_SCALE`

3. **Coordinate System**: ✅ G-code units are in millimeters
   - Direct mm coordinates from G-code
   - Conversion: STEPS_PER_MM = 40.0, STEP_SCALE = 2

4. **Servo Delays**: ✅ 400ms per pen up/down movement
   - Found in code: `sendPenUp(serial_port, 400)` and `sendPenDown(serial_port, 400)`
   - 400ms delay parameter used consistently

5. **UI Layout**: ✅ Option A - Horizontal format
   - `Time: 00:42:15 / 01:15:30 (est.)`
   - `Distance: 245.3 / 450.2 mm (est.)`

6. **Display Precision**: ✅
   - Distance: 1 decimal place (245.3 mm)
   - Time: Always HH:MM:SS format

7. **Time Estimation Components**:
   - Movement time based on distance and feedrate
   - Add 400ms for each pen state change
   - Account for rapid (G0) vs controlled (G1) moves

## Implementation Phases

### Phase 1: Basic Timer
- Add timer start/stop functionality
- Display actual elapsed time during plotting
- Test with existing plots

### Phase 2: Distance Estimation  
- Implement G-code parser for distance calculation
- Display estimated distance after file parse
- Validate distance calculations with known files

### Phase 3: Time Estimation
- Calculate estimated time from distance and speed
- Display estimated time after file parse
- Tune estimation accuracy

### Phase 4: Real-time Distance Tracking
- Track actual distance during plotting
- Update display in real-time
- Compare actual vs. estimated

### Phase 5: UI Polish
- Format display nicely
- Add proper state management
- Handle edge cases
- Add tooltips/help text

## Testing Scenarios

1. **Short plot** (~1 minute, simple geometry)
2. **Long plot** (>1 hour, complex geometry)  
3. **Stop and restart** during plotting
4. **Multiple files** in sequence
5. **Very large files** (performance testing)

## Dependencies

- No new external dependencies required
- Uses existing Python standard library (`time`, `math`)
- Integrates with existing threading and GUI update mechanisms

## Success Criteria

- Timer accuracy within 1 second
- Distance estimation within 10% of actual measured distance
- Time estimation within 20% of actual plot time
- UI updates smoothly without blocking plotting
- No performance degradation on large files
- All values reset properly between plots
