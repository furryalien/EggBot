#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
G-Code to EggBot Plotter

Converts G-code files into EggBot motor commands and plots them
on the EggBot hardware using H-bot differential drive kinematics.

The EggBot uses H-bot kinematics where:
- X motion (egg rotation): both motors move in same direction
- Y motion (pen carriage): motors move in opposite directions
- Combined motion requires: motor1 = X - Y, motor2 = X + Y

Z-Axis Pen Control:
- Z=0: Pen down (drawing)
- Z≠0: Pen up (travel moves)

Servo Configuration:
- Configurable pen up/down positions (default: 15% up, 45% down)
- Formula: servo_value = 240 * (percentage + 25)
- Commands: SC,4 (pen up position), SC,5 (pen down position)

Supported G-Code Commands:
- G0/G00: Rapid positioning (pen up)
- G1/G01: Linear interpolation (drawing)
- G2/G02, G3/G03: Arc interpolation (basic support)
- M3/M03: Spindle on / Pen down
- M5/M05: Spindle off / Pen up
- M2/M02, M30: Program end
- F: Feedrate setting
- X, Y: Cartesian coordinates in mm
- Z: Pen up/down (Z=0 for down, Z>0 for up)

Usage:
  python gcode_plotter.py <gcode_file>

Example:
  python gcode_plotter.py drawing.gcode

Copyright (C) 2025
License: GNU GPL v2+
"""

import sys
import math
import re
import time
from plotink import ebb_serial, ebb_motion

# EggBot hardware constants
# Standard EggBot: 3200 steps per revolution
# For typical egg circumference of ~145mm: 3200 / 145 = 22.07 steps/mm
# Speed limits: EBB supports 1.31Hz to 25,000 steps/second
STEPS_PER_MM = 100.0  # Steps per mm for G-code plotting (no STEP_SCALE applied)
STEP_SCALE = 1        # No scaling for G-code (unlike jog control which uses 2)
DEFAULT_SPEED = 1000  # Steps per second (increased for faster plotting)
MAX_SPEED = 24000     # Maximum steps/second (stay below 25K limit)

class GCodeParser:
    """Parse G-code commands"""
    
    def __init__(self):
        self.commands = []
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.pen_down = False
        
    def parse_file(self, filename):
        """Parse a G-code file and extract commands"""
        print("Parsing G-code file:", filename)
        
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('(') or line.startswith(';'):
                    continue
                
                # Remove inline comments
                if '(' in line:
                    line = line[:line.index('(')]
                if ';' in line:
                    line = line[:line.index(';')]
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse the command
                cmd = self.parse_line(line)
                if cmd:
                    self.commands.append(cmd)
        
        print("Parsed %d commands" % len(self.commands))
        return self.commands
    
    def parse_line(self, line):
        """Parse a single G-code line"""
        # Extract command and parameters
        parts = line.upper().split()
        if not parts:
            return None
        
        cmd_type = parts[0]
        params = {}
        
        # Parse parameters (X, Y, Z, F, etc.)
        for part in parts[1:]:
            if len(part) >= 2:
                letter = part[0]
                try:
                    value = float(part[1:])
                    params[letter] = value
                except ValueError:
                    pass
        
        # Create command dictionary
        command = {
            'type': cmd_type,
            'params': params,
            'raw': line
        }
        
        return command


class EggBotGCodePlotter:
    """Plot G-code on EggBot hardware"""
    
    def __init__(self):
        self.serial_port = None
        self.current_x = 0.0  # Current X position in mm
        self.current_y = 0.0  # Current Y position in mm
        self.pen_is_down = False
        self.feedrate = 1000.0  # mm/min
        
    def connect(self, pen_up_pct=15, pen_down_pct=45):
        """Connect to EggBot"""
        print("Connecting to EggBot...")
        self.serial_port = ebb_serial.openPort()
        
        if self.serial_port is None:
            print("ERROR: Could not connect to EggBot")
            return False
        
        print("Connected successfully")
        
        # Query firmware version
        firmware = ebb_serial.query(self.serial_port, 'V\r')
        if firmware:
            print("EBB Firmware:", firmware.strip())
        
        # Enable motors
        ebb_motion.sendEnableMotors(self.serial_port, 1)  # 16X microstepping
        print("Motors enabled")
        
        # Configure servo positions (pen up/down)
        # Position formula: 240 * (percentage + 25)
        pen_up_pos = int(240 * (pen_up_pct + 25))
        ebb_serial.command(self.serial_port, 'SC,4,{}\r'.format(pen_up_pos))
        pen_down_pos = int(240 * (pen_down_pct + 25))
        ebb_serial.command(self.serial_port, 'SC,5,{}\r'.format(pen_down_pos))
        print("Servo positions configured (up: {}%, down: {}%)".format(pen_up_pct, pen_down_pct))
        
        # Raise pen to up position on connect
        ebb_motion.sendPenUp(self.serial_port, 400)
        print("Pen raised to up position")
        
        return True
    
    def disconnect(self):
        """Disconnect from EggBot"""
        if self.serial_port:
            # Pen up before disconnecting
            if self.pen_is_down:
                print("Raising pen before disconnect...")
                self.pen_up()
            
            # Disable motors
            ebb_motion.sendDisableMotors(self.serial_port)
            print("Motors disabled")
            
            # Close port
            ebb_serial.closePort(self.serial_port)
            print("Disconnected from EggBot")
    
    def pen_up(self):
        """Raise pen"""
        if not self.pen_is_down:
            return
        
        ebb_motion.sendPenUp(self.serial_port, 400)
        self.pen_is_down = False
        time.sleep(0.3)  # Wait for servo to complete movement
    
    def pen_down(self):
        """Lower pen"""
        if self.pen_is_down:
            return
        
        ebb_motion.sendPenDown(self.serial_port, 400)
        self.pen_is_down = True
        time.sleep(0.3)  # Wait for servo to complete movement
    
    def move_to(self, x, y, rapid=False):
        """
        Move to absolute position (x, y) in mm using H-bot kinematics
        
        X maps to egg rotation (both motors same direction)
        Y maps to pen arm movement (motors opposite directions)
        """
        # Calculate delta
        dx = x - self.current_x
        dy = y - self.current_y
        
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return  # No movement needed
        
        # Calculate movement distance
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Use consistent speed calculation like jog_gui
        # time = distance * (STEPS_PER_MM / STEP_SCALE) / speed * 1000ms
        speed = DEFAULT_SPEED  # Always use default speed for smooth operation
        n_time = int(1000.0 * abs(distance) / (1.0 / STEPS_PER_MM * STEP_SCALE) / speed)
        
        # Enforce minimum time for smooth movement (avoid jitter)
        n_time = max(10, n_time)  # Minimum 10ms per move for smooth operation
        
        # Convert mm to steps (with STEP_SCALE)
        steps_x = int(dx * STEPS_PER_MM / STEP_SCALE)
        steps_y = int(dy * STEPS_PER_MM / STEP_SCALE)
        
        # Skip if no actual steps to move
        if steps_x == 0 and steps_y == 0:
            return
        
        # Execute movement using H-bot kinematics
        # H-bot differential drive:
        # - X motion (egg rotation): both motors same direction
        # - Y motion (pen carriage): motors opposite directions
        # Combined motion: motor1 = X - Y, motor2 = X + Y
        motor1_steps = steps_x - steps_y  # pen/Y axis motor
        motor2_steps = steps_x + steps_y  # egg/X axis motor
        
        # Ensure each motor meets minimum step rate (1.31 Hz)
        # Adjust time if necessary to keep step rates above minimum
        MIN_STEP_RATE = 1.31  # Hz (EBB hardware limit)
        if abs(motor1_steps) > 0:
            max_time_motor1 = int((abs(motor1_steps) / MIN_STEP_RATE) * 1000)
            n_time = min(n_time, max_time_motor1)
        if abs(motor2_steps) > 0:
            max_time_motor2 = int((abs(motor2_steps) / MIN_STEP_RATE) * 1000)
            n_time = min(n_time, max_time_motor2)
        
        # Ensure minimum 1ms
        n_time = max(1, n_time)
        
        # SM command: SM,time,motor1_steps,motor2_steps
        str_output = 'SM,{0},{1},{2}\r'.format(n_time, motor1_steps, motor2_steps)
        ebb_serial.command(self.serial_port, str_output)
        
        # Wait for movement to complete (convert ms to seconds, add small buffer)
        time.sleep(n_time / 1000.0 + 0.02)
        
        # Update current position
        self.current_x = x
        self.current_y = y
    
    def process_command(self, cmd):
        """Process a single G-code command"""
        cmd_type = cmd['type']
        params = cmd['params']
        
        # Check for Z axis commands (pen control)
        # Z=0 means pen down, any other Z value means pen up
        if 'Z' in params:
            z_value = params['Z']
            if abs(z_value) < 0.001:  # Z=0 (or very close to 0)
                if not self.pen_is_down:
                    print("Pen down (Z=0)")
                    self.pen_down()
            else:  # Z != 0
                if self.pen_is_down:
                    print("Pen up (Z={})".format(z_value))
                    self.pen_up()
        
        # Movement commands
        if cmd_type in ['G0', 'G00']:  # Rapid positioning
            x = params.get('X', self.current_x)
            y = params.get('Y', self.current_y)
            self.move_to(x, y, rapid=True)
        
        elif cmd_type in ['G1', 'G01']:  # Linear interpolation
            x = params.get('X', self.current_x)
            y = params.get('Y', self.current_y)
            if 'F' in params:
                self.feedrate = params['F']
            self.move_to(x, y, rapid=False)
        
        elif cmd_type in ['G2', 'G02', 'G3', 'G03']:  # Arc interpolation
            # TODO: Implement arc interpolation
            # For now, just move to end point
            x = params.get('X', self.current_x)
            y = params.get('Y', self.current_y)
            self.move_to(x, y, rapid=False)
        
        # Pen control (varies by G-code dialect)
        elif cmd_type in ['M3', 'M03']:  # Spindle on / Pen down
            self.pen_down()
        
        elif cmd_type in ['M5', 'M05']:  # Spindle off / Pen up
            self.pen_up()
        
        # Program control
        elif cmd_type in ['M2', 'M02', 'M30']:  # Program end
            self.pen_up()
        
        # Feedrate
        elif cmd_type == 'F':
            if params:
                self.feedrate = list(params.values())[0]
        
        # Ignore other commands for now
    
    def plot_gcode(self, commands):
        """Plot a list of G-code commands"""
        print("Plotting %d commands..." % len(commands))
        
        for i, cmd in enumerate(commands):
            if i % 100 == 0:
                print("Progress: %d/%d commands" % (i, len(commands)))
            
            self.process_command(cmd)
        
        print("Plotting complete!")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python gcode_plotter.py <gcode_file>")
        print("")
        print("Example: python gcode_plotter.py drawing.gcode")
        return 1
    
    gcode_file = sys.argv[1]
    
    # Parse G-code file
    parser = GCodeParser()
    try:
        commands = parser.parse_file(gcode_file)
    except IOError as e:
        print("ERROR: Could not read file:", e)
        return 1
    
    if not commands:
        print("ERROR: No valid G-code commands found")
        return 1
    
    # Connect to EggBot and plot
    plotter = EggBotGCodePlotter()
    
    if not plotter.connect():
        return 1
    
    try:
        plotter.plot_gcode(commands)
    except KeyboardInterrupt:
        print("\nPlotting interrupted by user")
    except Exception as e:
        print("ERROR during plotting:", e)
        import traceback
        traceback.print_exc()
    finally:
        plotter.disconnect()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
