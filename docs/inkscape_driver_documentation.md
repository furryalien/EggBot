# EggBot Inkscape Driver Documentation

**Version:** 2.8.1  
**Date:** June 19, 2019  
**License:** GNU GPL v2+

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Code Style & Conventions](#code-style--conventions)
5. [User Interface Panels](#user-interface-panels)
6. [Main Driver: eggbot.py](#main-driver-eggbotpy)
7. [Configuration: eggbot_conf.py](#configuration-eggbot_confpy)
8. [Hatching: eggbot_hatch.py](#hatching-eggbot_hatchpy)
9. [Utilities](#utilities)
10. [Control Flow](#control-flow)
11. [Data Structures](#data-structures)
12. [Extension Points](#extension-points)

---

## Overview

The EggBot Inkscape driver is a collection of Python extensions for Inkscape that enable plotting SVG artwork on the EggBot hardware - a pen plotter designed to draw on spherical and egg-shaped objects. The driver translates SVG vector graphics into motor control commands sent to the EggBot hardware via serial communication.

### Key Features

- **SVG to Hardware Translation**: Converts Inkscape paths to stepper motor movements
- **Multi-layer Support**: Plot specific layers or all layers sequentially
- **Resume Functionality**: Pause and resume plots mid-execution
- **Hatch Filling**: Generate hatch patterns to fill closed shapes
- **Path Optimization**: Minimize pen lifts and optimize plot time
- **Transform Handling**: Properly applies all SVG transforms during plotting

---

## Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────┐
│         Inkscape Application                    │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        │   Extension System     │
        │   (.inx definitions)   │
        └───────────┬────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───┴─────┐  ┌─────┴─────┐  ┌─────┴──────┐
│eggbot.py│  │_hatch.py  │  │_stretch.py │
└───┬─────┘  └─────┬─────┘  └─────┬──────┘
    │              │               │
    └──────────────┼───────────────┘
                   │
        ┌──────────┴──────────┐
        │   eggbot_conf.py    │
        │   (Configuration)   │
        └──────────┬──────────┘
                   │
        ┌──────────┴──────────┐
        │   plotink Library    │
        │  (ebb_serial.py,     │
        │   ebb_motion.py,     │
        │   plot_utils.py)     │
        └──────────┬──────────┘
                   │
        ┌──────────┴──────────┐
        │   EBB Hardware       │
        │  (Serial Commands)   │
        └─────────────────────┘
```

### Design Patterns

1. **Effect Pattern**: All extensions inherit from `inkex.Effect`, following Inkscape's extension architecture
2. **Recursive Traversal**: SVG DOM tree is traversed recursively to process all elements
3. **Transform Composition**: Transforms are composed and applied as the tree is traversed
4. **State Machine**: Pen up/down states and plotting modes managed through instance variables
5. **Command Pattern**: Hardware commands abstracted through plotink library functions

---

## Core Components

### Python Files

| File | Purpose | Lines | Complexity |
|------|---------|-------|------------|
| `eggbot.py` | Main plotting driver | ~1170 | High |
| `eggbot_conf.py` | Configuration constants | ~50 | Low |
| `eggbot_hatch.py` | Hatch fill generation | ~1737 | Very High |
| `eggbot_stretch.py` | Path stretching utility | ~663 | Medium |
| `eggbot_presethatch.py` | Preset hatch modifier | ~58 | Low |
| `empty_eggbot.py` | Document template creator | ~42 | Low |

### INX Files (Extension Definitions)

- `eggbot.inx`: Main control interface
- `eggbot_hatch.inx`: Hatch fill interface
- `eggbot_stretch.inx`: Stretch tool interface
- `eggbot_presethatch.inx`: Preset hatch interface
- `empty_eggbot.inx`: New document interface
- `eggbot_reorder.inx`: Path reordering interface

---

## Code Style & Conventions

### Python Version
- **Target**: Python 2.7 (for Inkscape 0.9x compatibility)
- **Encoding**: UTF-8 (declared in headers)
- **String Handling**: Uses both unicode and ASCII encoding/decoding

### Naming Conventions

```python
# Classes: PascalCase
class EggBot(inkex.Effect):
    pass

# Methods: camelCase (influenced by Inkscape conventions)
def plotToEggBot(self):
    pass

def recursivelyTraverseSvg(self, node):
    pass

# Instance variables: camelCase with type prefix
self.bPenIsUp          # boolean
self.fX, self.fY       # float
self.nNodeCount        # integer (sometimes implicit)
self.sCurrentLayerName # string

# Constants: UPPER_SNAKE_CASE
N_PAGE_WIDTH = 3200
N_PEN_UP_POS = 50
F_DEFAULT_SPEED = 1
```

### Code Organization

1. **File Header**: License, version, description
2. **Imports**: Grouped by standard lib, Inkscape, plotink, local
3. **Constants**: Module-level constants
4. **Helper Functions**: Module-level utility functions
5. **Class Definition**: Main Effect class
6. **Main Execution**: `if __name__ == '__main__'` block

### Documentation Style

- **Module docstrings**: Comprehensive header comments
- **Method docstrings**: Present for complex methods
- **Inline comments**: Extensive, explaining logic and edge cases
- **Attribution**: Credits for significant contributions

---

## User Interface Panels

The EggBot extensions appear in Inkscape under **Extensions → EggBot** menu. Each extension presents a user-friendly dialog with controls for configuring and executing various operations.

### EggBot Control Panel

**Access:** `Extensions → EggBot → EggBot Control`

The main control panel uses a **tabbed interface** with 8 tabs for different functions:

#### Tab 1: Plot (Splash Tab)

The default landing page for quick plotting.

**Interface Elements:**
- **Header:** "Welcome to the EggBot interface!"
- **Instructions:** 
  - "Press 'Apply' to begin plotting"
  - Navigation hints to other tabs
  - Help link: http://wiki.evilmadscientist.com/eggbot
- **Action:** Single Apply button starts plotting all layers

**Purpose:** One-click plotting for beginners

---

#### Tab 2: Setup

Servo configuration and alignment controls.

**Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Pen up position | Integer slider | 0-100% | 55 | Servo position when pen raised |
| Pen down position | Integer slider | 0-100% | 50 | Servo position when pen lowered |
| Action on 'Apply' | Dropdown | - | toggle-pen | Action to perform |

**Action Options:**
- **Toggle pen up/down**: Test servo movement
- **Raise pen, turn off motors**: Prepare for manual alignment

**Instructions Shown:**
- "Raise and lower pen to check the pen-up and pen-down positions"
- "Raise pen and turn off stepper motors for aligning objects in the EggBot"

**Purpose:** Hardware calibration before plotting

---

#### Tab 3: Timing

Speed and delay configuration for optimal plotting quality.

**Movement Speed Section:**

| Control | Type | Range | Default | Units |
|---------|------|-------|---------|-------|
| Speed when pen is down | Integer | 1-10000 | 300 | steps/s |
| Speed when pen is up | Integer | 1-10000 | 400 | steps/s |

**Pen Lift/Lower Speed Section:**

| Control | Type | Range | Default | Units |
|---------|------|-------|---------|-------|
| Pen raising speed | Integer | 1-1600 | 50 | %/s |
| Delay after raising pen | Integer | 1-5000 | 200 | ms |
| Pen lowering speed | Integer | 1-1600 | 20 | %/s |
| Delay after lowering pen | Integer | 1-5000 | 400 | ms |

**Notes:**
- Lower speeds = higher quality, longer plot time
- Delays prevent pen bounce and ensure settling
- Reminder: "Press 'Apply' to save settings"

**Purpose:** Balance speed vs. quality for different media

---

#### Tab 4: Options

Advanced plotting configuration.

**Boolean Options (Checkboxes):**

| Option | Default | Description |
|--------|---------|-------------|
| Reverse motion of Motor 1 (pen) | ☑ true | Invert Y-axis direction |
| Reverse motion of Motor 2 (egg) | ☑ true | Invert X-axis direction |
| Egg (x) axis wraps around | ☑ true | Enable shortcuts on cylindrical axis |
| Return home when done | ☑ true | Return to start position after plot |
| Enable engraver, if attached | ☐ false | Activate engraver output |

**Numeric Option:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Curve smoothness | Float | 0.0001-5.0 | 0.2 | Lower = more detail, more points |

**Purpose:** Configure hardware behavior and rendering quality

---

#### Tab 5: Manual

Direct hardware control for testing and adjustments.

**Command Dropdown:**
- \- Select -
- **Raise the Pen** - Move servo to up position
- **Lower the Pen** - Move servo to down position
- **Walk Motor 2 (egg)** - Step X-axis motor
- **Walk Motor 1 (pen)** - Step Y-axis motor
- **Enable Motors** - Activate stepper drivers (16X microstepping)
- **Disable Motors** - Deactivate steppers for manual movement
- **Engraver On** - Turn on engraver (if enabled)
- **Engraver Off** - Turn off engraver
- **Check EBB Version** - Query firmware version
- **Strip plotter data from file** - Remove resume data from SVG

**Walk Distance Control:**
- Type: Integer
- Range: -32000 to +32000 steps
- Default: 5
- Note: "Walk distances may be positive or negative"

**Purpose:** Hardware testing, troubleshooting, and manual positioning

---

#### Tab 6: Resume

Pause/resume functionality for interrupted plots.

**Controls:**

| Control | Type | Default | Description |
|---------|------|---------|-------------|
| Cancel and return home only | Checkbox | ☐ false | Abort plot and home |

**Detailed Instructions:**
1. **To Pause:**
   - Press PRG button on EBB board during plotting
   - Can make adjustments or change settings
   
2. **To Resume:**
   - Press Apply in this tab
   - Can resume from pause point or after homing
   
3. **Important Notes:**
   - Plot progress stored in the SVG file itself
   - Must save document before quitting to preserve state
   - Can resume after restarting Inkscape

**Purpose:** Handle plot interruptions gracefully

**Technical Details:**
Progress tracked via `<eggbot>` element in SVG with attributes:
- `layer`: Current layer number
- `node`: Node count (progress marker)
- `lastpath`: Last completed path index
- `lastpathnc`: Node count at last path
- `totaldeltax`, `totaldeltay`: Accumulated movement

---

#### Tab 7: Layers

Selective layer plotting for multi-color workflows.

**Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Plot only layers beginning with | Integer | 0-100 | 1 | Layer number prefix |

**Instructions:**
- "Normally, we plot paths from all layers"
- "You can also choose to plot a single layer or group of layers"
- "For example to change pens between plotting layers"
- "Pressing 'Apply' from this frame will plot only layers whose names begin with the selected number"

**Usage Example:**
- Layers named "1 Red", "1 Details" → Plot with layernumber=1
- Layers named "2 Blue", "2 Background" → Plot with layernumber=2
- Change pen between layer groups

**Purpose:** Multi-pen/multi-color plotting workflows

---

#### Tab 8: * (Help/About)

Version information and known issues.

**Information Displayed:**
- **Extension Name:** EggBot Control Inkscape extension
- **Version:** Release 2.8.1, dated 2019-06-19
- **Firmware Requirement:** EBB Firmware 2.5.1 or newer recommended

**Known Issues:**
- Cancel button limitation (Inkscape core issue)
- Affects all extensions, not EggBot-specific

**Links:**
- Latest version: https://github.com/evil-mad/EggBot/
- Issue tracker available at repository

**Purpose:** Version verification and troubleshooting reference

---

### Hatch Fill Panel

**Access:** `Extensions → EggBot → Hatch fill`

Creates hatch patterns to fill closed shapes, using **2-tab interface**:

#### Tab 1: Hatch Fill (Main Controls)

**Description Text:**
"This extension fills each closed figure in your drawing with a path consisting of back and forth drawn 'hatch' lines. If any objects are selected, then only those selected objects will be filled. Hatched figures will be grouped with their fills."

**Pattern Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Hatch spacing (px) | Float | 0.1-1000 | 3.0 | Distance between hatch lines |
| Hatch angle (degrees) | Float | -360 to 360 | 45 | Angle from horizontal |
| Crosshatch? | Checkbox | - | ☐ false | Add perpendicular second set |

**Optimization Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Connect nearby ends? | Checkbox | - | ☑ true | Join segments with curves |
| Range of end connections | Float | 1.1-5.0 | 3.0 | Search radius in hatch widths |

**Inset Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Inset fill from edges? | Checkbox | - | ☑ true | Hold back from boundaries |
| Inset distance (px) | Float | 0.1-10.0 | 1.0 | Distance to inset |

**Quality Control:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Tolerance | Float | 0.1-100 | 3.0 | Path approximation precision |

**Version Info:** (v2.3.0, June 11, 2019)

**Purpose:** Fill closed shapes with plottable hatch patterns

---

#### Tab 2: More info...

**Detailed Parameter Explanations:**

**Hatch Spacing:**
- Measured in screen pixels (px)
- Distance between parallel hatch lines
- Smaller = denser fill, longer plot time

**Hatch Angle:**
- Degrees from horizontal (0° = horizontal)
- 90° = vertical hatches
- 45° = diagonal (common default)
- Negative values accepted

**Crosshatch:**
- Adds second set perpendicular to first
- Creates woven appearance
- Doubles plotting time

**Connect Nearby Ends:**
- Uses Bezier curves to join segments
- Reduces pen lifts dramatically
- Smoother plotting, fewer interruptions

**Range Parameter:**
- Measured in multiples of hatch width
- Recommended: 2-4 for best results
- Too large: unwanted connections
- Too small: many pen lifts

**Inset Option:**
- "Color inside the lines" mode
- Prevents overrun on boundaries
- Improves precision with physical pens
- Adjustable distance

**Tolerance:**
- Controls how precisely hatches follow paths
- Lower = more accurate, more points
- Higher = faster processing, less detail

**Output Notes:**
- Hatches inherit color/width from original object
- Grouped with original for easy manipulation

**Purpose:** Help users understand parameters for best results

---

### Stretch Panel

**Access:** `Extensions → EggBot → Stretch`

**Single-panel interface** for spherical surface compensation.

**Description (Large Text Block):**
"This extension will horizontally stretch your drawing. The amount of stretch increases towards the poles of your egg (i.e., increases with distance away from the equator). The stretching is such that when plotted, the resulting plot appears much like your original drawing. The stretching of the horizontal near the poles counters the decreasing circumference of lines of latitude as you approach the poles of a sphere or egg.

Apply this extension just before plotting. Note that it turns all objects into paths composed of line segments.

If no objects are selected, then the entire document is transformed. In this case, a vertical line passing through your document's center (width / 2) will remain unchanged. The farther a vertical line is from the center, the more it will be distorted.

If objects are selected then a vertical line passing through the horizontal midpoint of the bounding box containing the selected objects will remain unchanged.

The vertical smoothing is the vertical segment length to break non-horizontal lines into so that they are smoothly but continuously distorted.

The curve smoothing value is the same control as in the Eggbot Control extension. It needs to be applied here before plotting as all curves will be rendered to straight line segments by this extension."

**Controls:**

| Control | Type | Range | Default | Description |
|---------|------|-------|---------|-------------|
| Vertical smoothing | Float | 0.0001-999.0 | 5.0 | Lower = more segments |
| Curve smoothing | Float | 0.0001-5.0 | 0.2 | Lower = more detail |

**Technical Details:**
- Transforms rectangular artwork for spherical plotting
- Compensates for latitude circumference changes
- Non-reversible - apply just before plotting
- Converts everything to line segments

**Purpose:** Prepare artwork for spherical/egg-shaped surfaces

---

### UI Design Patterns

The EggBot extensions follow consistent design principles:

#### Layout Patterns

1. **Tab-based Navigation**
   - Used for complex multi-function panels (EggBot Control)
       |       
   - Logical grouping: Plot, Setup, Timing, Options, Manual, Resume, Layers, Help
   - Tab names descriptive and concise

2. **Single-page Focused**
   - Used for specialized tools (Hatch Fill, Stretch)
   - All controls visible at once
   - Minimal scrolling required

3. **Progressive Disclosure**
   - Basic controls on first tab
   - Advanced options in separate tabs
   - Help/documentation in dedicated tabs

#### Control Patterns

1. **Numeric Inputs**
   - Integer sliders for whole numbers (speeds, percentages)
   - Float sliders for precision (smoothness, angles, spacing)
   - Always show units (px, degrees, steps/s, %, ms)
   - Min/max constraints prevent invalid input

2. **Boolean Inputs**
   - Checkboxes for on/off options
   - Clear labels explaining effect
   - Sensible defaults (most checkboxes pre-configured)

3. **Selection Inputs**
   - Dropdown menus for mutually exclusive choices
   - First option often "\- Select -" prompt
   - Descriptive option labels

4. **Text Elements**
   - Headers in bold/larger font
   - Instructions indented for hierarchy
   - Version info at bottom
   - Links for external documentation

#### Information Architecture

**Grouping Strategy:**
- **Function-based tabs**: What user wants to accomplish
- **Logical flow**: Setup → Configure → Execute
- **Frequency of use**: Common functions prominent

**Visual Hierarchy:**
- Headers distinguish sections
- Related controls grouped together
- Indentation shows relationships
- Spacing separates logical groups

**User Guidance:**
- Inline instructions for complex features
- Default values shown in interface
- Help text explains parameters
- Version info for troubleshooting

#### Interaction Model

**Standard Flow:**
1. User opens extension via menu
2. Modal dialog appears (Inkscape standard)
3. User adjusts parameters
4. Click "Apply" to execute
5. Extension processes, provides feedback
6. Dialog remains open for repeated execution
7. Click "Close" or "Cancel" to dismiss

**State Management:**
- Settings persist within session
- Some settings saved to SVG (plot state)
- Preferences file stores user defaults

**Feedback Mechanisms:**
- Error messages via `inkex.errormsg()`
- Status shown in Inkscape message bar
- Progress visible through plot execution
- Hardware feedback via LED/button on EBB

---

### Accessibility Considerations

**Keyboard Navigation:**
- Standard Inkscape tab order
- All controls keyboard-accessible
- Apply/Cancel with Enter/Escape

**Visual Design:**
- High contrast labels
- Logical reading order
- Consistent spacing

**Error Prevention:**
- Input validation via min/max
- Sensible defaults reduce errors
- Clear labels prevent confusion

**Help & Documentation:**
- Inline instructions
- Dedicated help tabs
- External wiki links
- Version information for support

---

### Comparison with INX Definitions

The `.inx` XML files define these interfaces declaratively:

```xml
<!-- Example: Slider control -->
<param name="penUpSpeed" type="int" min="1" max="10000"
       _gui-text="Speed when pen is up (step/s):">400</param>

<!-- Example: Checkbox control -->
<param name="returnToHome" type="boolean"
       _gui-text="Return home when done">true</param>

<!-- Example: Dropdown control -->
<param name="manualType" type="optiongroup" appearance="minimal"
       _gui-text="Command: ">
    <_option value="none">- Select -</_option>
    <_option value="raise-pen">Raise the Pen</_option>
</param>

<!-- Example: Description text -->
<_param name="instructions" type="description" xml:space="preserve">
Detailed instructions here...
</_param>
```

**INX to UI Mapping:**
- `type="int|float"` → Numeric slider
- `type="boolean"` → Checkbox
- `type="optiongroup"` → Dropdown menu
- `type="description"` → Static text
- `type="notebook"` → Tabbed interface
- `appearance="header"` → Bold header text
- `indent="N"` → Visual indentation level

This declarative approach keeps UI separate from logic, following Inkscape extension conventions.

---

## Main Driver: eggbot.py

### Class: EggBot

The primary class that handles all plotting operations.

#### Key Responsibilities

1. **SVG Parsing**: Parse and interpret SVG elements
2. **Path Processing**: Convert shapes to plottable paths
3. **Transform Management**: Apply and compose SVG transforms
4. **Hardware Control**: Send motor and servo commands
5. **State Management**: Track plotting progress for resume functionality
6. **Layer Management**: Handle multi-layer plotting

### Initialization

```python
def __init__(self):
    inkex.Effect.__init__(self)
    
    # Command line options
    self.OptionParser.add_option("--smoothness", ...)
    self.OptionParser.add_option("--penUpSpeed", ...)
    # ... many more options
    
    # State variables
    self.bPenIsUp = None           # Pen state unknown initially
    self.virtualPenIsUp = False    # Virtual state for resume
    self.fX, self.fY = None, None  # Current position
    self.nodeCount = 0             # Progress tracking
    self.bStopped = False          # Stop flag
```

### Main Entry Point: effect()

```python
def effect(self):
    """Main entry point: check which tab selected, act accordingly"""
    
    self.svg = self.document.getroot()
    self.CheckSVGforEggbotData()
    
    # Route to appropriate handler based on active tab
    if self.options.tab == '"splash"':
        self.plotToEggBot()
    elif self.options.tab == '"resume"':
        self.resumePlotSetup()
        if self.resumeMode:
            self.plotToEggBot()
    elif self.options.tab == '"setup"':
        self.setupCommand()
    elif self.options.tab == '"manual"':
        self.manualCommand()
```

### SVG Traversal: recursivelyTraverseSvg()

The heart of the plotting system - recursively walks the SVG DOM tree.

```python
def recursivelyTraverseSvg(self, a_node_list, 
                          mat_current=None,
                          parent_visibility='visible'):
    """
    Recursively traverse SVG to plot all paths.
    Maintains composite transformation matrix.
    """
    
    for node in a_node_list:
        # Check visibility
        v = node.get('visibility', parent_visibility)
        if v in ['hidden', 'collapse']:
            continue
            
        # Compose transforms
        mat_new = composeTransform(mat_current, 
                                   parseTransform(node.get("transform")))
        
        # Handle different node types
        if node.tag in ['g', inkex.addNS('g', 'svg')]:
            # Recurse into groups
            if node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                self.DoWePlotLayer(...)
            self.recursivelyTraverseSvg(node, mat_new, v)
            
        elif node.tag == inkex.addNS('path', 'svg'):
            # Plot path directly
            self.plotPath(node, mat_new)
            
        elif node.tag in ['rect', 'line', 'polyline', ...]:
            # Convert to path and plot
            # ... element-specific conversion logic
```

### Path Plotting: plotPath()

Converts paths to motor movements.

```python
def plotPath(self, path, mat_transform):
    """Plot path with transformation applied"""
    
    # Parse path data
    d = path.get('d')
    p = cubicsuperpath.parsePath(d)
    
    # Apply transformation
    applyTransformToPath(mat_transform, p)
    
    # Subdivide curves into line segments
    for sp in p:
        plot_utils.subdivideCubicPath(sp, self.options.smoothness)
        
        for csp in sp:
            self.fX = 2 * float(csp[1][0]) / self.step_scaling_factor
            self.fY = 2 * float(csp[1][1]) / self.step_scaling_factor
            
            # Pen up for first point of subpath
            if n_index == 0:
                if distance(self.fX - self.fPrevX, ...) > MIN_GAP:
                    self.penUp()
            # Pen down for subsequent points
            elif n_index == 1:
                self.penDown()
            
            # Send movement command
            self.plotLineAndTime()
```

### Movement Execution: plotLineAndTime()

Sends actual motor commands to hardware.

```python
def plotLineAndTime(self):
    """Send line segment as motor command with timing"""
    
    if self.bStopped or self.fPrevX is None:
        return
        
    # Calculate delta
    n_delta_x = int(self.fX) - int(self.fPrevX)
    n_delta_y = int(self.fY) - int(self.fPrevY)
    
    # Handle wrap-around for cylindrical axis
    if self.bPenIsUp and self.options.wraparound:
        if n_delta_x > self.halfWrapSteps:
            n_delta_x -= self.wrapSteps
        elif n_delta_x < -self.halfWrapSteps:
            n_delta_x += self.wrapSteps
    
    # Calculate timing based on speed and distance
    n_time = int(math.ceil(1000.0 / self.fSpeed * 
                           plot_utils.distance(n_delta_x, n_delta_y)))
    
    # Apply motor direction settings
    if self.options.revPenMotor:
        yd2 = yd
    else:
        yd2 = -yd
    
    # Send command to hardware
    ebb_motion.doXYMove(self.serialPort, xd2, yd2, td)
    
    # Check for pause button
    str_button = ebb_motion.QueryPRGButton(self.serialPort)
    if str_button[0] == '1':
        self.bStopped = True
```

### Resume Functionality

The driver saves progress information in the SVG document itself:

```python
def CheckSVGforEggbotData(self):
    """Check for existing plot state data"""
    self.recursiveEggbotDataScan(self.svg)
    if not self.svgDataRead:
        # Create <eggbot> element with state
        eggbotlayer = inkex.etree.SubElement(self.svg, 'eggbot')
        eggbotlayer.set('layer', '0')
        eggbotlayer.set('node', '0')
        eggbotlayer.set('lastpath', '0')
        # ... more state tracking
```

### Element Conversion

The driver converts all SVG shapes to paths:

**Rectangle → Path**
```python
# <rect x="X" y="Y" width="W" height="H"/>
# becomes
# <path d="MX,Y lW,0 l0,H l-W,0 z"/>

a = [['M ', [x, y]],
     [' l ', [w, 0]],
     [' l ', [0, h]],
     [' l ', [-w, 0]],
     [' Z', []]]
newpath.set('d', simplepath.formatPath(a))
```

**Circle/Ellipse → Path**
```python
# Two 180° arcs
d = 'M {x1:f},{cy:f} ' \
    'A {rx:f},{ry:f} 0 1 0 {x2:f},{cy:f} ' \
    'A {rx:f},{ry:f} 0 1 0 {x1:f},{cy:f}'
```

---

## Configuration: eggbot_conf.py

Simple configuration module with key constants.

### Page Dimensions

```python
N_PAGE_HEIGHT = 800   # Default page height (pixels/steps)
N_PAGE_WIDTH = 3200   # Default page width (pixels/steps)
```

These define the working area in steps. Each step equals one pixel in the SVG coordinate system.

### Step Scaling

```python
STEP_SCALE = 2  # For 3200 steps/revolution motors
```

**Motor Resolution Configurations:**

| Motor Type | Microstepping | Steps/Rev | STEP_SCALE |
|------------|---------------|-----------|------------|
| 200 step/rev | 8X | 1600 | 4 |
| **200 step/rev** | **16X** | **3200** | **2** (default) |
| 400 step/rev | 16X | 6400 | 1 |

### Minimum Gap

```python
MIN_GAP = 1.0  # Minimum pen-up movement (steps)
```

Prevents unnecessary pen lifts for very small movements.

---

## Hatching: eggbot_hatch.py

The most complex component - generates hatch patterns to fill closed shapes.

### Algorithm Overview

1. **Path Decomposition**: Convert all shapes to vertex lists (polygons)
2. **Grid Generation**: Create potential hatch lines across bounding box
3. **Intersection Detection**: Find where hatch lines intersect polygon edges
4. **Odd/Even Rule**: Determine which segments are inside polygons
5. **Optimization**: Connect nearby segments to reduce pen lifts
6. **Output Generation**: Create SVG paths with hatch lines

### Class: Eggbot_Hatch

```python
class Eggbot_Hatch(inkex.Effect):
    def __init__(self):
        # Data structures
        self.paths = {}        # Polygons by node
        self.grid = []         # Hatch line grid
        self.hatches = {}      # Generated hatches by node
        self.transforms = {}   # Transform matrix per node
        
        # Options
        self.OptionParser.add_option("--hatchAngle", ...)
        self.OptionParser.add_option("--hatchSpacing", ...)
        self.OptionParser.add_option("--crossHatch", ...)
        self.OptionParser.add_option("--reducePenLifts", ...)
```

### Key Methods

#### addPathVertices()

Converts SVG elements to polygon vertex lists.

```python
def addPathVertices(self, path, node=None, transform=None):
    """Decompose path into vertex lists for each subpath"""
    
    # Parse and convert to cubic superpath
    sp = simplepath.parsePath(path)
    p = cubicsuperpath.CubicSuperPath(sp)
    
    # Apply transforms
    if transform is not None:
        simpletransform.applyTransformToPath(transform, p)
    
    # Extract vertices
    subpaths = []
    for sp in p:
        subdivideCubicPath(sp, tolerance)
        subpath_vertices = []
        for csp in sp:
            subpath_vertices.append(csp[1])
        
        # Keep only closed paths
        if distanceSquared(subpath_vertices[0], 
                          subpath_vertices[-1]) < 1:
            subpaths.append(subpath_vertices)
    
    # Store by node
    self.paths[node] = subpaths
    self.transforms[node] = transform
```

#### makeHatchGrid()

Generates the hatch line grid.

```python
def makeHatchGrid(self, angle, spacing, init=True):
    """Build grid of hatch lines encompassing bounding box"""
    
    if init:
        self.getBoundingBox()
        self.grid = []
    
    # Calculate bounding box diagonal
    w = self.xmax - self.xmin
    h = self.ymax - self.ymin
    r = math.sqrt(w * w + h * h) / 2.0
    
    # Rotation for hatch angle
    ca = math.cos(math.radians(90 - angle))
    sa = math.sin(math.radians(90 - angle))
    
    # Translation to center
    cx = self.xmin + (w / 2)
    cy = self.ymin + (h / 2)
    
    # Generate parallel lines
    i = -r
    while i <= r:
        # Rotate and translate line endpoints
        x1 = cx + (i * ca) + (r * sa)
        y1 = cy + (i * sa) - (r * ca)
        x2 = cx + (i * ca) - (r * sa)
        y2 = cy + (i * sa) + (r * ca)
        
        # Skip lines entirely outside bounding box
        if not (outside_bounds(x1, x2, y1, y2)):
            self.grid.append((x1, y1, x2, y2))
        
        i += spacing
```

#### interstices() Function

Finds intersections between hatch lines and polygon edges.

```python
def interstices(hatch_obj, pt1, pt2, paths, hatches, 
                hold_back_hatch, hold_back_steps):
    """
    Find intersections of hatch line (pt1, pt2) with all polygon edges.
    Store segments that lie within polygons.
    """
    
    # For each polygon
    for path in paths:
        for subpath in paths[path]:
            # For each edge in polygon
            for i in range(len(subpath)):
                v1 = subpath[i]
                v2 = subpath[(i + 1) % len(subpath)]
                
                # Find intersection
                intersect = lineSegmentIntersection(pt1, pt2, v1, v2)
                
                if intersect is not None:
                    # Store fractional distance along hatch line
                    d_and_a.append([intersect_fraction, path])
    
    # Sort intersections
    d_and_a.sort()
    
    # Apply odd/even rule
    i = 0
    while i < len(d_and_a) - 1:
        # Segments between odd/even pairs are inside
        if hold_back_hatch:
            # Inset from edges
            segment = inset_segment(d_and_a[i], d_and_a[i+1])
        else:
            segment = [d_and_a[i], d_and_a[i+1]]
        
        hatches[path].append(segment)
        i += 2
```

#### recursivelyAppendNearbySegments()

The optimization algorithm that connects nearby hatch segments.

```python
def recursivelyAppendNearbySegments(self, spacing, recursion_count,
                                   ref_segment, ref_end,
                                   segments, path, held_line):
    """
    Recursively connect nearby hatch segments with curves.
    Reduces pen lifts significantly.
    """
    
    # Find closest undrawn segment end near reference end
    f_closest = LARGE_NUMBER
    found_segment = None
    
    for seg_index, segment in enumerate(segments):
        if segment.drawn:
            continue
            
        for end_index in [0, 1]:
            distance = dist(segment[end_index], 
                          ref_segment[ref_end])
            
            if distance < neighborhood_radius:
                # Check direction compatibility
                if not AlternatingDirection(ref_angle, seg_angle):
                    continue
                
                # Check not colinear (from same grid line)
                if AreCoLinear(ref_angle, joiner_angle):
                    continue
                
                if distance < f_closest:
                    f_closest = distance
                    found_segment = (seg_index, end_index)
    
    if found_segment is None or recursion_count > RECURSION_LIMIT:
        # End recursion
        path += format_line_segment(held_line)
        return path
    
    # Connect with Bezier curve
    curve = generate_bezier_join(ref_segment, found_segment, 
                                 spacing)
    path += format_curve(curve)
    
    # Mark as drawn
    segments[found_segment[0]].drawn = True
    
    # Recurse
    return self.recursivelyAppendNearbySegments(
        spacing, recursion_count + 1,
        found_segment[0], found_segment[1],
        segments, path, next_held_line)
```

### Hatch Algorithm Constants

```python
F_MINGAP_SMALL_VALUE = 0.0000000001  # Intersection tolerance

BEZIER_OVERSHOOT_MULTIPLIER = 0.75  # Curve control point distance

RADIAN_TOLERANCE_FOR_COLINEAR = 0.1  # Colinearity detection

RADIAN_TOLERANCE_FOR_ALTERNATING_DIRECTION = 0.1  # Direction check

RECURSION_LIMIT = 500  # Maximum join attempts
```

---

## Utilities

### eggbot_stretch.py

Maps rectangular artwork onto spherical surfaces.

**Key Function: inverseTransform()**

```python
def inverseTransform(tran):
    """Compute inverse of SVG transform matrix"""
    # Matrix: [[a, c, e], [b, d, f]]
    D = tran[0][0] * tran[1][1] - tran[1][0] * tran[0][1]
    if D == 0:
        return None
    
    return [[tran[1][1] / D, -tran[0][1] / D,
             (tran[0][1] * tran[1][2] - tran[1][1] * tran[0][2]) / D],
            [-tran[1][0] / D, tran[0][0] / D,
             (tran[1][0] * tran[0][2] - tran[0][0] * tran[1][2]) / D]]
```

### eggbot_presethatch.py

Modifies Inkscape rough hatch effects for better plotting.

```python
def recursiveDefDataScan(self, aNodeList):
    """Find and modify path-effect parameters"""
    for node in aNodeList:
        if node.tag == inkex.addNS('path-effect', 'inkscape'):
            if node.get('effect') == 'rough_hatches':
                # Set parameters for smooth plotting
                node.set('dist_rdm', '0;1')
                node.set('growth', '0')
                node.set('scale_bf', '2')
                # ... more parameter adjustments
```

### empty_eggbot.py

Creates properly sized EggBot documents.

```python
def effect(self):
    """Set up document with correct dimensions"""
    width = self.options.generic_width  # Default 1920
    height = self.options.generic_height  # Default 1080
    
    root = self.document.getroot()
    root.set("width", str(width) + "px")
    root.set("height", str(height) + "px")
    root.set("viewBox", "0 0 " + str(width) + " " + str(height))
```

---

## Control Flow

### Standard Plot Flow

```
User Selects Plot Tab → Apply Button
    ↓
effect() dispatches to plotToEggBot()
    ↓
getDocProps() reads document dimensions
    ↓
ServoSetup() configures pen servo
    ↓
sendEnableMotors() activates steppers
    ↓
recursivelyTraverseSvg() walks DOM
    ↓
    For each element:
        ↓
        Check visibility and layer
        ↓
        Compose transforms
        ↓
        Convert to path (if needed)
        ↓
        plotPath()
            ↓
            subdivideCubicPath() linearizes curves
            ↓
            For each point:
                ↓
                penUp() or penDown() as needed
                ↓
                plotLineAndTime() sends motor commands
                ↓
                Check pause button
                ↓
                Update progress state
    ↓
penUp() (final)
    ↓
Return to home (if enabled)
    ↓
Save state to SVG
    ↓
Close serial port
```

### Resume Flow

```
User Selects Resume Tab → Apply Button
    ↓
effect() dispatches to resumePlotSetup()
    ↓
CheckSVGforEggbotData() reads saved state
    ↓
Set nodeTarget = saved nodeCount
    ↓
Set resumeMode = True
    ↓
plotToEggBot() begins
    ↓
recursivelyTraverseSvg() walks DOM
    ↓
    For each path:
        ↓
        If pathcount < svgLastPath: skip
        ↓
        If pathcount == svgLastPath:
            ↓
            Set nodeCount = svgLastPathNC
            ↓
            Begin plotting from this path
            ↓
            For each point:
                ↓
                Increment nodeCount
                ↓
                If nodeCount > nodeTarget:
                    ↓
                    resumeMode = False
                    ↓
                    Start actual plotting
```

### Hatch Fill Flow

```
User Selects Objects → Extensions → EggBot → Hatch Fill
    ↓
effect() in eggbot_hatch.py
    ↓
handleViewBox() sets up transforms
    ↓
recursivelyTraverseSvg() walks selection/document
    ↓
    For each object:
        ↓
        Initialize: paths = {}, grid = [], hatches = {}
        ↓
        addPathVertices() → extract polygons
        ↓
        makeHatchGrid() → generate hatch lines
        ↓
        If crossHatch: makeHatchGrid(angle + 90°)
        ↓
        For each grid line:
            ↓
            interstices() → find intersections
            ↓
            Store hatch segments in hatches{}
    ↓
For each object with hatches:
    ↓
    If reducePenLifts:
        ↓
        recursivelyAppendNearbySegments()
        ↓
        Connect segments with Bezier curves
    ↓
    Else:
        ↓
        Output segments with alternating direction
    ↓
    joinFillsWithNode() → create <path> element
    ↓
    Group with original object
```

---

## Data Structures

### Transform Matrix

SVG transforms stored as 2x3 matrix:

```python
# [[a, c, e],
#  [b, d, f]]
#
# Represents:
# [ a  c  e ]
# [ b  d  f ]
# [ 0  0  1 ]

mat_current = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]  # Identity
```

### Cubic Superpath

Bezier curves represented as nested lists:

```python
# Path = [subpath1, subpath2, ...]
# Subpath = [segment1, segment2, ...]  
# Segment = [[x1,y1], [x2,y2], [x3,y3]]
#   where:
#     [x1,y1] = previous endpoint / control point 1
#     [x2,y2] = control point 2
#     [x3,y3] = endpoint

p = [
    [  # Subpath 0
        [[x0,y0], [x1,y1], [x2,y2]],  # Segment 0
        [[x2,y2], [x3,y3], [x4,y4]],  # Segment 1
        # ...
    ],
    # More subpaths...
]
```

### Plot State (stored in SVG)

```xml
<svg>
    <eggbot 
        layer="0"           <!-- Current layer -->
        node="1234"         <!-- Node count (progress) -->
        lastpath="56"       <!-- Last completed path -->
        lastpathnc="1200"   <!-- Node count at last path -->
        totaldeltax="1500"  <!-- Accumulated X movement -->
        totaldeltay="300"   <!-- Accumulated Y movement -->
    />
    <!-- Document content -->
</svg>
```

### Hatch Data Structures

```python
# Polygon vertices by node
self.paths = {
    node1: [
        [(x1,y1), (x2,y2), ...],  # Subpath 1
        [(x1,y1), (x2,y2), ...],  # Subpath 2
    ],
    node2: [...],
}

# Hatch grid lines (absolute coordinates)
self.grid = [
    (x1, y1, x2, y2),  # Line 1
    (x1, y1, x2, y2),  # Line 2
    # ...
]

# Generated hatches by node
self.hatches = {
    node1: [
        [[x1,y1], [x2,y2]],  # Segment 1
        [[x3,y3], [x4,y4]],  # Segment 2
        # ...
    ],
    node2: [...],
}

# Transform matrices by node
self.transforms = {
    node1: [[a, c, e], [b, d, f]],
    node2: [[a, c, e], [b, d, f]],
    # ...
}
```

---

## Extension Points

### Adding New Commands

To add functionality to the Manual tab:

```python
elif self.options.manualType == "your-new-command":
    # Your command logic here
    # Access serial port via self.serialPort
    # Send commands via ebb_serial.command()
```

Register in `eggbot.inx`:

```xml
<page name="manual" _gui-text="Manual">
    <param name="manualType" type="optiongroup">
        <_option value="your-new-command">Your Description</_option>
    </param>
</page>
```

### Supporting New SVG Elements

Add to `recursivelyTraverseSvg()`:

```python
elif node.tag in [inkex.addNS('your-element', 'svg'), 'your-element']:
    # Convert to path representation
    newpath = inkex.etree.Element(inkex.addNS('path', 'svg'))
    # ... conversion logic
    newpath.set('d', path_data)
    self.plotPath(newpath, mat_new)
```

### Custom Hatch Patterns

Modify `makeHatchGrid()` in `eggbot_hatch.py`:

```python
def makeHatchGrid(self, angle, spacing, init=True):
    # Custom grid generation logic
    # Populate self.grid with (x1, y1, x2, y2) tuples
    
    # Example: concentric circles instead of lines
    for radius in range(0, max_radius, spacing):
        # Generate circle points
        # Add to self.grid as line segments
```

### Hardware Communication

All hardware commands go through plotink library:

```python
# In ebb_serial.py
def command(portName, cmd):
    """Send command, don't wait for response"""
    
def query(portName, cmd):
    """Send command, return response"""

# In ebb_motion.py  
def doXYMove(portName, deltaX, deltaY, duration):
    """Execute XY motor movement"""
    
def sendPenUp(portName, delay):
    """Raise pen servo"""
    
def sendPenDown(portName, delay):
    """Lower pen servo"""
```

---

## Best Practices

### For Users

1. **Always use pen up/down test** before plotting to verify servo positions
2. **Start with slow speeds** (150-200 steps/s) for new pens
3. **Use layers** for complex plots requiring pen changes
4. **Save frequently** when preparing artwork
5. **Convert text to paths** before plotting
6. **Group related objects** for better layer organization

### For Developers

1. **Preserve transform composition** when modifying traversal code
2. **Test with various SVG editors** (Inkscape, Illustrator exports, etc.)
3. **Handle edge cases**: empty paths, zero-length segments, degenerate shapes
4. **Maintain backward compatibility** with saved plot state
5. **Document units carefully** (steps, pixels, percentages, mm)
6. **Test resume functionality** after modifications
7. **Profile performance** on complex documents (>1000 paths)

### Performance Optimization

1. **Path simplification**: Higher smoothness = fewer points = faster plotting
2. **Layer planning**: Plot similar content together
3. **Pen lift reduction**: Use hatch fill's connection feature
4. **Speed tuning**: Balance quality vs. time
5. **Wrap-around**: Enable for cylindrical objects to reduce travel

---

## Troubleshooting

### Common Issues

**1. Text not plotting**
- **Cause**: Text elements not converted to paths
- **Solution**: Use "Object to Path" or Hershey Text extension

**2. Plot pauses unexpectedly**  
- **Cause**: Button pressed or communication error
- **Solution**: Check physical button, USB connection, use Resume

**3. Transforms not applied correctly**
- **Cause**: Viewbox or nested transform issues
- **Solution**: Flatten transforms before plotting

**4. Pen position incorrect**
- **Cause**: Servo position not calibrated
- **Solution**: Adjust in Setup tab, test thoroughly

**5. Hatches extend beyond boundaries**
- **Cause**: Tolerance too loose or inset too small
- **Solution**: Increase inset distance, reduce tolerance

### Debug Techniques

**Enable error messages:**
```python
inkex.errormsg("Debug info: " + str(variable))
```

**Trace execution:**
```python
import sys
sys.stderr.write("At function X, value=" + str(val) + "\n")
```

**Check node counts:**
```python
# Uncomment in plotToEggBot()
inkex.errormsg('Final node count: ' + str(self.svgNodeCount))
```

---

## Dependencies

### Python Modules (bundled with Inkscape)

- `inkex` - Inkscape extension base classes
- `simplepath` - SVG path parsing
- `simpletransform` - Transform utilities  
- `cubicsuperpath` - Bezier curve handling
- `cspsubdiv` - Curve subdivision
- `bezmisc` - Bezier mathematics
- `simplestyle` - SVG style parsing

### External Libraries (from plotink)

- `ebb_serial` - Serial port communication
- `ebb_motion` - Motion command abstraction
- `plot_utils` - Plotting utilities

### Hardware Requirements

- EggBot hardware with EiBotBoard (EBB)
- USB connection
- Firmware version 2.4.0 or later

---

## Version History Highlights

**2.8.1 (June 19, 2019)**
- Current release
- Stability improvements

**2.7.5 (May 1, 2016)**  
- Configuration refactoring
- Step scaling support

**2.3.1 (June 19, 2019)**
- Hatch improvements
- Better pen lift reduction

**Earlier versions**
- Initial releases
- Basic plotting functionality
- Resume feature added

---

## License & Credits

**License:** GNU General Public License v2 or later

**Primary Authors:**
- Windell H. Oskay (Evil Mad Scientist)
- Daniel C. Newman
- Sheldon B. Michaels
- Nathan Depew

**Repository:** https://github.com/evil-mad/EggBot

**Support:** http://wiki.evilmadscientist.com/eggbot

---

## Conclusion

The EggBot Inkscape driver is a sophisticated system that bridges the gap between vector graphics and physical plotting on spherical surfaces. Its architecture demonstrates several software engineering principles:

- **Separation of concerns**: Configuration, plotting, and hardware abstraction
- **Recursive algorithms**: For tree traversal and optimization
- **State management**: For resume functionality
- **Transform composition**: Proper handling of nested coordinate systems
- **Extensibility**: Plugin architecture via Inkscape extensions

The codebase reflects years of refinement, handling edge cases and optimizing for real-world plotting scenarios. Understanding this architecture enables both effective use of the tool and informed extension development.
