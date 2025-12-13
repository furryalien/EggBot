#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EggBot Jog Control GUI

A standalone graphical interface for manual jog control of the EggBot hardware.
Features gamepad-style directional controls for precise positioning.

Features:
- Manual X/Y axis jogging with configurable step distances
- Gamepad-style directional button layout
- Pen toggle control (Z-axis servo)
- Adjustable servo positions for pen up/down
- Fan control (GPIO pin RB5)
- Real-time connection status indicator
- Comprehensive logging of all operations

Hardware Support:
- EggBot with EiBotBoard (EBB) controller
- H-bot differential drive kinematics
- 16X microstepping motor control
- Servo pen lift mechanism
- GPIO fan control

H-Bot Kinematics:
- X motion (egg rotation): both motors same direction
  Command: SM,time,steps,steps
- Y motion (pen arm): motors opposite directions
  Command: SM,time,-steps,steps

Servo Control:
- Configurable pen up/down positions (default: 15% up, 45% down)
- Formula: servo_value = 240 * (percentage + 25)
- Commands: SC,4 (pen up), SC,5 (pen down)
- Toggle command: TP (switches between up/down)

GPIO Control:
- Fan on/off via RB5 pin
- Commands: PO,B,5,1 (on), PO,B,5,0 (off)

Controls:
- X+/X-: Rotate egg left/right
- Y+/Y-: Move pen arm forward/backward
- Z: Toggle pen up/down
- Distance: Adjustable 0.1-100mm per jog
- Fan: ON/OFF buttons

Dependencies:
- plotink module (pip install plotink)
- tkinter (included with Python)

Usage:
  python eggbot_jog_gui.py

Copyright (C) 2025
License: GNU GPL v2+
"""

import sys
import time

# Python 2/3 compatibility
try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    import Tkinter as tk
    import tkMessageBox as messagebox
    import ttk

# Try to import EggBot control modules
try:
    from plotink import ebb_serial, ebb_motion
    plotink_available = True
    import_error = None
except ImportError as e:
    plotink_available = False
    import_error = f"plotink module not installed: {e}"
    print(f"ERROR: {import_error}", file=sys.stderr)

# Set constants after try/except
PLOTINK_AVAILABLE = plotink_available
IMPORT_ERROR = import_error


# Hardware constants
STEPS_PER_MM = 40.0  # Approximately 40 steps per mm
STEP_SCALE = 2       # Step scaling factor
DEFAULT_JOG_SPEED = 200  # Steps per second


class EggBotJogGUI:
    """GUI application for EggBot jog control"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EggBot Jog Control")
        self.root.geometry("600x850")
        self.root.resizable(False, False)
        
        # Application state
        self.serial_port = None
        self.is_connected = False
        self.x_distance = 25.0  # mm
        self.y_distance = 25.0  # mm
        self.servo_position = 16000  # Current servo position (center position)
        self.movement_in_progress = False  # Track if movement is ongoing
        self.movement_start_time = None
        self.movement_total_time = 0
        self.movement_update_callback = None
        
        # Create UI
        self.create_ui()
        
        # Check for plotink availability
        if not PLOTINK_AVAILABLE:
            messagebox.showwarning(
                "Missing Dependencies",
                "The plotink module is not installed.\n\n" +
                "To use this tool, install it with:\n" +
                "  pip3 install plotink"
            )
            self.log("ERROR: plotink module not available")
            self.log("Install with: pip3 install plotink")
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure button styles
        self.style.configure('Direction.TButton', font=('Arial', 14, 'bold'), padding=10)
        self.style.configure('Pen.TButton', font=('Arial', 12, 'bold'), padding=10)
        self.style.configure('Stop.TButton', font=('Arial', 12, 'bold'), padding=10, background='red')
        
    def create_ui(self):
        """Create the user interface"""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="EggBot Jog Control",
            font=('Arial', 18, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 15))
        
        # Connection section
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        conn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        conn_frame.columnconfigure(0, weight=1)
        
        # Status indicator
        status_container = ttk.Frame(conn_frame)
        status_container.grid(row=0, column=0, pady=(0, 10))
        
        self.status_canvas = tk.Canvas(status_container, width=20, height=20, bg='white', highlightthickness=1)
        self.status_canvas.grid(row=0, column=0, padx=(0, 10))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, fill='red', outline='darkred')
        
        self.status_label = ttk.Label(status_container, text="Disconnected", font=('Arial', 11, 'bold'))
        self.status_label.grid(row=0, column=1)
        
        # Connection buttons
        btn_container = ttk.Frame(conn_frame)
        btn_container.grid(row=1, column=0)
        
        self.connect_btn = ttk.Button(
            btn_container,
            text="Connect",
            command=self.connect_eggbot,
            width=15
        )
        self.connect_btn.grid(row=0, column=0, padx=5)
        
        self.disconnect_btn = ttk.Button(
            btn_container,
            text="Disconnect",
            command=self.disconnect_eggbot,
            state=tk.DISABLED,
            width=15
        )
        self.disconnect_btn.grid(row=0, column=1, padx=5)
        
        # Container for side-by-side settings
        settings_container = ttk.Frame(main_frame)
        settings_container.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        settings_container.columnconfigure(0, weight=1)
        settings_container.columnconfigure(1, weight=1)
        settings_container.columnconfigure(2, weight=1)
        
        # Distance settings section (left side)
        settings_frame = ttk.LabelFrame(settings_container, text="Jog Distance Settings", padding="10")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        settings_frame.columnconfigure(1, weight=1)
        
        # X distance
        ttk.Label(settings_frame, text="X Distance (mm):", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.x_distance_var = tk.DoubleVar(value=25.0)
        x_spinbox = ttk.Spinbox(
            settings_frame,
            from_=0.1,
            to=100.0,
            increment=0.1,
            textvariable=self.x_distance_var,
            width=10
        )
        x_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Y distance
        ttk.Label(settings_frame, text="Y Distance (mm):", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.y_distance_var = tk.DoubleVar(value=25.0)
        y_spinbox = ttk.Spinbox(
            settings_frame,
            from_=0.1,
            to=100.0,
            increment=0.1,
            textvariable=self.y_distance_var,
            width=10
        )
        y_spinbox.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Pen servo settings section (middle)
        servo_frame = ttk.LabelFrame(settings_container, text="Pen Servo Settings", padding="10")
        servo_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 5))
        servo_frame.columnconfigure(1, weight=1)
        
        # Pen up position
        ttk.Label(servo_frame, text="Pen Up Position (%):", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pen_up_pos_var = tk.IntVar(value=15)
        pen_up_spinbox = ttk.Spinbox(
            servo_frame,
            from_=0,
            to=100,
            increment=1,
            textvariable=self.pen_up_pos_var,
            width=10
        )
        pen_up_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Pen down position
        ttk.Label(servo_frame, text="Pen Down Position (%):", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pen_down_pos_var = tk.IntVar(value=45)
        pen_down_spinbox = ttk.Spinbox(
            servo_frame,
            from_=0,
            to=100,
            increment=1,
            textvariable=self.pen_down_pos_var,
            width=10
        )
        pen_down_spinbox.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Apply servo settings button
        ttk.Button(
            servo_frame,
            text="Apply Servo Settings",
            command=self.apply_servo_settings
        ).grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # Fan control section (right side)
        fan_frame = ttk.LabelFrame(settings_container, text="Fan Control", padding="10")
        fan_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        # Fan control buttons
        ttk.Button(
            fan_frame,
            text="ON",
            command=self.fan_on,
            width=6
        ).grid(row=0, column=0, pady=5)
        
        ttk.Button(
            fan_frame,
            text="OFF",
            command=self.fan_off,
            width=6
        ).grid(row=1, column=0, pady=5)
        
        # Gamepad control section
        gamepad_frame = ttk.LabelFrame(main_frame, text="Jog Controls", padding="15")
        gamepad_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Create gamepad layout
        control_container = ttk.Frame(gamepad_frame)
        control_container.grid(row=0, column=0, padx=20)
        
        # XY Movement controls (left side)
        xy_frame = ttk.Frame(control_container)
        xy_frame.grid(row=0, column=0, padx=(0, 40))
        
        ttk.Label(xy_frame, text="Egg Rotation & Pen Arm", font=('Arial', 11, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 5))
        
        # Forward label
        ttk.Label(xy_frame, text="Forward", font=('Arial', 9, 'italic')).grid(row=1, column=1, pady=(0, 5))
        
        # Y+ button (top)
        self.y_plus_btn = ttk.Button(
            xy_frame,
            text="▲\nY+",
            command=self.jog_y_plus,
            style='Direction.TButton',
            width=8
        )
        self.y_plus_btn.grid(row=2, column=1, padx=5, pady=5)
        
        # X- button (left), center space, X+ button (right)
        self.x_minus_btn = ttk.Button(
            xy_frame,
            text="◄\nX-",
            command=self.jog_x_minus,
            style='Direction.TButton',
            width=8
        )
        self.x_minus_btn.grid(row=3, column=0, padx=5, pady=5)
        
        # Left label (below X- button)
        ttk.Label(xy_frame, text="Left", font=('Arial', 9, 'italic')).grid(row=4, column=0, pady=(0, 5))
        
        # Center label
        ttk.Label(xy_frame, text="⊕", font=('Arial', 20)).grid(row=3, column=1)
        
        self.x_plus_btn = ttk.Button(
            xy_frame,
            text="►\nX+",
            command=self.jog_x_plus,
            style='Direction.TButton',
            width=8
        )
        self.x_plus_btn.grid(row=3, column=2, padx=5, pady=5)
        
        # Right label (below X+ button)
        ttk.Label(xy_frame, text="Right", font=('Arial', 9, 'italic')).grid(row=4, column=2, pady=(0, 5))
        
        # Y- button (bottom)
        self.y_minus_btn = ttk.Button(
            xy_frame,
            text="▼\nY-",
            command=self.jog_y_minus,
            style='Direction.TButton',
            width=8
        )
        self.y_minus_btn.grid(row=5, column=1, padx=5, pady=5)
        
        # Back label
        ttk.Label(xy_frame, text="Back", font=('Arial', 9, 'italic')).grid(row=6, column=1, pady=(5, 0))
        
        # Pen Toggle control (right side)
        z_frame = ttk.Frame(control_container)
        z_frame.grid(row=0, column=1, padx=(15, 0))
        
        ttk.Label(z_frame, text="Pen Toggle", font=('Arial', 11, 'bold')).grid(row=0, column=0, pady=(0, 10))
        
        self.z_toggle_btn = ttk.Button(
            z_frame,
            text="Pen\n(Z)",
            command=self.toggle_pen,
            style='Pen.TButton',
            width=8
        )
        self.z_toggle_btn.grid(row=1, column=0, pady=10)
        
        ttk.Label(z_frame, text="✎", font=('Arial', 20)).grid(row=2, column=0, pady=10)
        
        # Stop button
        ttk.Label(z_frame, text="Emergency Stop", font=('Arial', 9, 'bold')).grid(row=3, column=0, pady=(20, 5))
        self.stop_btn = ttk.Button(
            z_frame,
            text="STOP",
            command=self.stop_movement,
            style='Pen.TButton',
            width=8
        )
        self.stop_btn.grid(row=4, column=0, pady=5)
        
        # Disable jog buttons initially
        self.set_jog_buttons_state(tk.DISABLED)
        
        # Movement Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Movement Progress", padding="10")
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.movement_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.movement_progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.movement_status_label = ttk.Label(progress_frame, text="Idle", font=('Arial', 9))
        self.movement_status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Create text widget with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(
            log_container,
            height=5,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=('Courier', 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Clear log button
        ttk.Button(
            log_frame,
            text="Clear Log",
            command=self.clear_log
        ).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Configure grid weights
        main_frame.rowconfigure(5, weight=1)
        
    def log(self, message):
        """Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, "[{}] {}\n".format(timestamp, message))
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def clear_log(self):
        """Clear the log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def set_status(self, status, color):
        """Update status indicator"""
        # Map colors to their dark variants for outline
        dark_colors = {
            'red': 'darkred',
            'green': 'darkgreen',
            'blue': 'darkblue',
            'yellow': 'orange',  # darkyellow doesn't exist, use orange
            'gray': 'darkgray'
        }
        outline_color = dark_colors.get(color, 'black')
        self.status_canvas.itemconfig(self.status_indicator, fill=color, outline=outline_color)
        self.status_label.config(text=status)
        
    def set_jog_buttons_state(self, state):
        """Enable or disable all jog buttons"""
        self.x_plus_btn.config(state=state)
        self.x_minus_btn.config(state=state)
        self.y_plus_btn.config(state=state)
        self.y_minus_btn.config(state=state)
        self.z_toggle_btn.config(state=state)
        
    def connect_eggbot(self):
        """Connect to EggBot hardware"""
        if not PLOTINK_AVAILABLE:
            messagebox.showerror("Missing Dependencies", "Cannot connect: plotink module not installed.")
            return
        
        if self.is_connected:
            messagebox.showinfo("Already Connected", "Already connected to EggBot.")
            return
        
        try:
            self.log("Connecting to EggBot...")
            self.set_status("Connecting...", "yellow")
            
            self.serial_port = ebb_serial.openPort()
            
            if self.serial_port is None:
                self.set_status("Connection Failed", "red")
                self.log("ERROR: Could not connect to EggBot")
                messagebox.showerror(
                    "Connection Error",
                    "Failed to connect to EggBot.\n\n" +
                    "Make sure the EggBot is connected via USB."
                )
                return
            
            self.is_connected = True
            self.set_status("Connected", "green")
            self.log("Successfully connected to EggBot")
            
            # Query firmware version
            firmware = ebb_serial.query(self.serial_port, 'V\r')
            if firmware:
                self.log("EBB Firmware: " + firmware.strip())
            
            # Enable motors
            ebb_motion.sendEnableMotors(self.serial_port, 1)  # 16X microstepping
            self.log("Motors enabled")
            
            # Configure servo positions (pen up/down)
            # Position formula: 240 * (percentage + 25)
            pen_up_pct = self.pen_up_pos_var.get()
            pen_down_pct = self.pen_down_pos_var.get()
            pen_up_pos = int(240 * (pen_up_pct + 25))
            ebb_serial.command(self.serial_port, 'SC,4,{}\r'.format(pen_up_pos))
            pen_down_pos = int(240 * (pen_down_pct + 25))
            ebb_serial.command(self.serial_port, 'SC,5,{}\r'.format(pen_down_pos))
            self.log("Servo positions configured (up: {}%, down: {}%)".format(pen_up_pct, pen_down_pct))
            
            # Raise pen to up position on connect
            ebb_motion.sendPenUp(self.serial_port, 400)
            self.log("Pen raised to up position")
            
            # Configure fan pin (RB5) as output
            ebb_serial.command(self.serial_port, 'PD,B,5,0\r')
            self.log("Fan pin configured as output")
            
            # Update button states
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.set_jog_buttons_state(tk.NORMAL)
            
        except Exception as e:
            self.set_status("Connection Failed", "red")
            self.log("ERROR: {}".format(str(e)))
            self.serial_port = None
            self.is_connected = False
            messagebox.showerror("Connection Error", "Failed to connect:\n{}".format(str(e)))
            
    def disconnect_eggbot(self):
        """Disconnect from EggBot hardware"""
        if not self.is_connected:
            return
        
        try:
            self.log("Disconnecting from EggBot...")
            
            # Disable motors
            ebb_motion.sendDisableMotors(self.serial_port)
            self.log("Motors disabled")
            
            # Close port
            ebb_serial.closePort(self.serial_port)
            
            self.serial_port = None
            self.is_connected = False
            
            self.set_status("Disconnected", "red")
            self.log("Disconnected from EggBot")
            
            # Update button states
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.set_jog_buttons_state(tk.DISABLED)
            
        except Exception as e:
            self.log("ERROR during disconnect: {}".format(str(e)))
            messagebox.showerror("Disconnect Error", "Error during disconnect:\n{}".format(str(e)))
            
    def jog_x_plus(self):
        """Jog X+ (rotate egg right/clockwise)"""
        self.jog_x(self.x_distance_var.get())
        
    def jog_x_minus(self):
        """Jog X- (rotate egg left/counter-clockwise)"""
        self.jog_x(-self.x_distance_var.get())
        
    def jog_y_plus(self):
        """Jog Y+ (move pen arm forward)"""
        self.jog_y(self.y_distance_var.get())
        
    def jog_y_minus(self):
        """Jog Y- (move pen arm backward)"""
        self.jog_y(-self.y_distance_var.get())
        
    def jog_x(self, distance_mm):
        """Jog X axis by distance in mm"""
        if not self.is_connected:
            return
        
        if self.movement_in_progress:
            self.log("Movement already in progress, ignoring command")
            return
        
        try:
            self.movement_in_progress = True
            steps = int(distance_mm * STEPS_PER_MM / STEP_SCALE)
            n_time = int(1000.0 * abs(distance_mm) / (1.0 / STEPS_PER_MM * STEP_SCALE) / DEFAULT_JOG_SPEED)
            n_time = max(1, n_time)
            
            self.log("Jog X: {:.2f}mm ({} steps)".format(distance_mm, steps))
            # EggBot H-bot kinematics: both motors same direction for X (egg rotation)
            # SM command: SM,time,motor1_steps,motor2_steps
            str_output = 'SM,{0},{1},{1}\r'.format(n_time, steps)
            ebb_serial.command(self.serial_port, str_output)
            
            # Start movement progress tracking
            self.start_movement_progress("X Jog: {:.1f}mm ({} steps)".format(distance_mm, steps), n_time)
            
            # Schedule movement completion
            self.root.after(n_time, self.clear_movement_flag)
            
        except Exception as e:
            self.movement_in_progress = False
            self.log("ERROR during X jog: {}".format(str(e)))
            messagebox.showerror("Jog Error", "Error during X jog:\n{}".format(str(e)))
            
    def jog_y(self, distance_mm):
        """Jog Y axis by distance in mm"""
        if not self.is_connected:
            return
        
        if self.movement_in_progress:
            self.log("Movement already in progress, ignoring command")
            return
        
        try:
            self.movement_in_progress = True
            steps = int(distance_mm * STEPS_PER_MM / STEP_SCALE)
            n_time = int(1000.0 * abs(distance_mm) / (1.0 / STEPS_PER_MM * STEP_SCALE) / DEFAULT_JOG_SPEED)
            n_time = max(1, n_time)
            
            self.log("Jog Y: {:.2f}mm ({} steps)".format(distance_mm, steps))
            # EggBot H-bot kinematics: motors opposite direction for Y (pen carriage)
            # SM command: SM,time,motor1_steps,motor2_steps  
            str_output = 'SM,{0},{1},{2}\r'.format(n_time, -steps, steps)
            ebb_serial.command(self.serial_port, str_output)
            
            # Start movement progress tracking
            self.start_movement_progress("Y Jog: {:.1f}mm ({} steps)".format(distance_mm, steps), n_time)
            
            # Schedule movement completion
            self.root.after(n_time, self.clear_movement_flag)
            
        except Exception as e:
            self.movement_in_progress = False
            self.log("ERROR during Y jog: {}".format(str(e)))
            messagebox.showerror("Jog Error", "Error during Y jog:\n{}".format(str(e)))
            
    def stop_movement(self):
        """Emergency stop - immediately halt all motor movement"""
        if not self.is_connected:
            self.log("Cannot stop: Not connected")
            return
        
        try:
            self.log("EMERGENCY STOP - Halting all movement")
            # Use ES command (Emergency Stop) to immediately halt all motors
            ebb_serial.command(self.serial_port, 'ES\r')
            self.movement_in_progress = False
            self.log("All motors stopped")
        except Exception as e:
            self.log("ERROR during emergency stop: {}".format(str(e)))
            messagebox.showerror("Stop Error", "Error during emergency stop:\n{}".format(str(e)))
    
    def clear_movement_flag(self):
        """Clear the movement in progress flag"""
        self.movement_in_progress = False
        if self.movement_update_callback:
            self.root.after_cancel(self.movement_update_callback)
            self.movement_update_callback = None
        self.movement_progress['value'] = 0
        self.movement_status_label.config(text="Idle")
    
    def start_movement_progress(self, description, total_time_ms):
        """Start tracking movement progress"""
        self.movement_start_time = time.time()
        self.movement_total_time = total_time_ms / 1000.0  # Convert to seconds
        self.movement_progress['maximum'] = 100
        self.movement_progress['value'] = 0
        self.movement_status_label.config(text=description)
        self.update_movement_progress()
    
    def update_movement_progress(self):
        """Update the movement progress indicator"""
        if not self.movement_in_progress or self.movement_start_time is None:
            return
        
        elapsed = time.time() - self.movement_start_time
        remaining = max(0, self.movement_total_time - elapsed)
        progress = min(100, (elapsed / self.movement_total_time) * 100)
        
        self.movement_progress['value'] = progress
        
        # Update status text with remaining time
        if remaining > 0:
            self.movement_status_label.config(
                text="{} - Remaining: {:.1f}s".format(
                    self.movement_status_label.cget('text').split(' - ')[0],
                    remaining
                )
            )
            # Schedule next update (every 50ms)
            self.movement_update_callback = self.root.after(50, self.update_movement_progress)
        else:
            self.movement_status_label.config(
                text="{} - Complete".format(
                    self.movement_status_label.cget('text').split(' - ')[0]
                )
            )
    
    def apply_servo_settings(self):
        """Apply the current servo position settings."""
        print("apply_servo_settings called!")  # Debug
        if not self.is_connected:
            self.log("Cannot apply servo settings: Not connected")
            return
        
        try:
            pen_up_pct = self.pen_up_pos_var.get()
            pen_down_pct = self.pen_down_pos_var.get()
            
            self.log(f"Applying servo settings: Up={pen_up_pct}%, Down={pen_down_pct}%")
            
            # Configure pen up position (servo channel 4)
            pen_up_value = int(240 * (pen_up_pct + 25))
            self.log(f"Sending SC,4,{pen_up_value}")
            ebb_serial.command(self.serial_port, f'SC,4,{pen_up_value}\r')
            
            # Configure pen down position (servo channel 5)
            pen_down_value = int(240 * (pen_down_pct + 25))
            self.log(f"Sending SC,5,{pen_down_value}")
            ebb_serial.command(self.serial_port, f'SC,5,{pen_down_value}\r')
            
            self.log(f"Servo settings applied successfully")
            
            # Move servo to up position to demonstrate the new setting
            self.log("Moving pen to up position to test new setting...")
            ebb_motion.sendPenUp(self.serial_port, 400)
            
        except Exception as e:
            self.log(f"Error applying servo settings: {e}")
    
    def toggle_pen(self):
        """Toggle pen servo position"""
        if not self.is_connected:
            return
        
        try:
            self.log("Toggle pen")
            # Use TP command - toggles servo between up and down positions
            str_output = 'TP,400\r'  # 400ms delay
            ebb_serial.command(self.serial_port, str_output)
            
        except Exception as e:
            self.log("ERROR during pen toggle: {}".format(str(e)))
            messagebox.showerror("Toggle Error", "Error during pen toggle:\n{}".format(str(e)))
        except Exception as e:
            self.log("ERROR during pen down: {}".format(str(e)))
            messagebox.showerror("Pen Error", "Error during pen down:\n{}".format(str(e)))
    
    def fan_on(self):
        """Turn fan on using GPIO pin RB5"""
        if not self.is_connected:
            self.log("Cannot control fan: Not connected")
            return
        
        try:
            # Set pin RB5 (Port B, Pin 5) to output high
            ebb_serial.command(self.serial_port, 'PO,B,5,1\r')
            self.log("Fan turned ON")
        except Exception as e:
            self.log("ERROR turning fan on: {}".format(str(e)))
            messagebox.showerror("Fan Error", "Error turning fan on:\n{}".format(str(e)))
    
    def fan_off(self):
        """Turn fan off using GPIO pin RB5"""
        if not self.is_connected:
            self.log("Cannot control fan: Not connected")
            return
        
        try:
            # Set pin RB5 (Port B, Pin 5) to output low
            ebb_serial.command(self.serial_port, 'PO,B,5,0\r')
            self.log("Fan turned OFF")
        except Exception as e:
            self.log("ERROR turning fan off: {}".format(str(e)))
            messagebox.showerror("Fan Error", "Error turning fan off:\n{}".format(str(e)))
            
    def on_closing(self):
        """Handle window close event"""
        if self.is_connected:
            if messagebox.askokcancel("Quit", "Disconnect from EggBot and quit?"):
                self.disconnect_eggbot()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = EggBotJogGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
