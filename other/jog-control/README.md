# EggBot Jog Control GUI

A standalone graphical interface for manual jog control of the EggBot hardware.

## Features

- **Connect/Disconnect**: Easy connection management with visual status indicator
- **Gamepad-Style Layout**: Intuitive directional controls
  - X+/X- buttons for egg rotation (left/right)
  - Y+/Y- buttons for pen arm movement (forward/back)
  - Pen Up/Down buttons for Z-axis control
- **Adjustable Distance**: Configure jog distances for X and Y axes (0.1-100mm)
- **Real-Time Logging**: Timestamped log of all operations
- **Visual Feedback**: Color-coded status indicator
  - Red: Disconnected
  - Yellow: Connecting
  - Green: Connected

## Usage

### Running the Application

```bash
python3 eggbot_jog_gui.py
```

Or make it executable:

```bash
chmod +x eggbot_jog_gui.py
./eggbot_jog_gui.py
```

### Control Layout

```
        Egg Rotation & Pen Arm              Pen Control
        
              Forward                           Pen Up
                 ▲                                ▲
                Y+                              (Z+)
                
    Left   ◄   ⊕   ►   Right                     ✎
          X-       X+
                                               Pen Down
                 ▼                                ▼
                Y-                              (Z-)
                Back
```

### Workflow

1. **Connect**: Click "Connect" button to establish connection with EggBot
2. **Set Distance**: Adjust X and Y distances as needed
3. **Jog**: Click directional buttons to move the EggBot
   - X+/X-: Rotate egg clockwise/counter-clockwise
   - Y+/Y-: Move pen arm forward/backward
   - Pen Up/Down: Raise/lower pen
4. **Disconnect**: Click "Disconnect" when finished

## Requirements

- Python 3.x
- tkinter (usually included with Python)
- plotink library: `pip3 install plotink`
- Connected EggBot with EBB firmware 2.5.1+

## Technical Details

- **Steps per mm**: 40 (configurable in code)
- **Step scale**: 2
- **Default jog speed**: 200 steps/second
- **Motor microstepping**: 16X enabled on connection

## Notes

- Motors are automatically enabled when connecting
- Motors are disabled when disconnecting
- Distance inputs support decimal values (e.g., 0.5mm, 2.3mm)
- All movements use the configured distances from the settings
- Pen up/down movements are independent of distance settings
