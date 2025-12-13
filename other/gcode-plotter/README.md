# G-Code to EggBot Plotter

This utility converts and plots G-code files on the EggBot hardware.

## Overview

Converts standard G-code commands (G0, G1, G2, G3, etc.) into EggBot motor control commands, allowing CNC-generated toolpaths to be plotted on spherical/egg-shaped objects.

## Features

- Parse standard G-code files
- Convert linear movements (G0/G1) to EggBot XY movements
- Handle pen up/down (M3/M5 or similar)
- Arc interpolation (G2/G3) support
- Coordinate system mapping (G-code XY → EggBot rotation/arm)
- **GUI version** with file browser, start/stop controls, and live status

## Usage

### Command Line Version

```bash
python gcode_plotter.py input.gcode
```

### GUI Version

```bash
python gcode_plotter_gui.py
```

**GUI Features:**
- File browser for selecting G-code files
- Parse button to load and validate commands
- Connect button to establish EggBot connection
- Start/Stop controls for plotting
- Real-time progress bar and status indicator
- Scrolling log with timestamps
- Status colors:
  - **Gray**: Disconnected
  - **Yellow**: Connecting
  - **Green**: Connected and ready
  - **Blue**: Plotting in progress
  - **Red**: Connection failed

## Requirements

- Connected EggBot with EBB firmware 2.5.1+
- Python 2.7 or Python 3.x
- plotink library (ebb_serial, ebb_motion)
- tkinter (included with most Python installations)
