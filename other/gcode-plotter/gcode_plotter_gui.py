#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
G-Code to EggBot Plotter - GUI Version

A graphical interface for plotting G-code files on the EggBot hardware.

Features:
- Browse and load G-code files (.gcode, .nc, .ngc, .txt)
- Parse G-code and display command count
- Connect/disconnect to EggBot via USB
- Start/stop plotting with progress tracking
- Real-time plotting status and command progress
- Comprehensive logging of operations
- Background threading for non-blocking plot execution

Hardware Support:
- EggBot with EiBotBoard (EBB) controller
- H-bot kinematics for X/Y motion
- Servo-controlled pen lift (Z-axis)
- Configurable servo positions (15% up, 45% down default)

G-Code Interpretation:
- X/Y coordinates mapped to egg rotation and pen carriage
- Z=0 for pen down, Z≠0 for pen up
- Feedrate control for drawing speed
- G0/G1 movement commands
- M3/M5 spindle commands for pen control

Dependencies:
- plotink module (pip install plotink)
- tkinter (included with Python)

Usage:
  python gcode_plotter_gui.py

Copyright (C) 2025
License: GNU GPL v2+
"""

import sys
import os
import threading
import time
import math

# Python 2/3 compatibility
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
    from tkinter import ttk
except ImportError:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import ScrolledText as scrolledtext
    import ttk

# Try to import the plotter modules
try:
    from gcode_plotter import GCodeParser, EggBotGCodePlotter
    from gcode_plotter import STEPS_PER_MM, STEP_SCALE, DEFAULT_SPEED, MAX_SPEED
    from plotink import ebb_serial
    PLOTTER_AVAILABLE = True
except ImportError as e:
    PLOTTER_AVAILABLE = False
    IMPORT_ERROR = str(e)
    ebb_serial = None  # Set to None if not available
    # Fallback values if import fails
    STEPS_PER_MM = 40.0
    STEP_SCALE = 2
    DEFAULT_SPEED = 1000
    MAX_SPEED = 24000
    
    # Create dummy classes for GUI to work
    class GCodeParser:
        def parse_file(self, filename):
            raise ImportError("plotink module not available")
    
    class EggBotGCodePlotter:
        def __init__(self):
            raise ImportError("plotink module not available")


class GCodePlotterGUI:
    """GUI application for G-code plotting"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EggBot G-Code Plotter")
        self.root.geometry("900x600")
        
        # Application state
        self.gcode_file = None
        self.commands = []
        self.plotter = None
        self.plot_thread = None
        self.is_plotting = False
        self.stop_requested = False
        self.is_paused = False
        self.pause_requested = False
        self.paused_position = None
        
        # Metrics tracking
        self.estimated_distance_mm = 0.0
        self.actual_distance_mm = 0.0
        self.estimated_time_sec = 0.0
        self.plot_start_time = None
        self.current_x = 0.0
        self.current_y = 0.0
        self.pen_state_changes = 0
        self.plot_size_x = 0.0
        self.plot_size_y = 0.0
        self.start_position = ""
        self.executed_commands = 0
        self.total_commands = 0
        
        # Create UI
        self.create_ui()
        
        # Check for plotink availability
        if not PLOTTER_AVAILABLE:
            self.log("WARNING: plotink module not available")
            self.log("ERROR: " + IMPORT_ERROR)
            self.log("")
            self.log("To use this tool, you need to install plotink:")
            self.log("  pip install plotink")
            self.log("  or")
            self.log("  pip3 install plotink")
            self.log("")
            messagebox.showwarning(
                "Missing Dependencies",
                "The plotink module is not installed.\n\n" +
                "To use this tool, install it with:\n" +
                "  pip3 install plotink\n\n" +
                "The GUI will remain open for reference."
            )
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
    def create_ui(self):
        """Create the user interface"""
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="EggBot G-Code Plotter",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="G-Code File", padding="10")
        file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        self.file_label = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.file_label.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(
            file_frame,
            text="Browse...",
            command=self.browse_file
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        
        self.command_count_label = ttk.Label(file_frame, text="Commands: 0")
        self.command_count_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 10))
        
        self.plot_size_label = ttk.Label(file_frame, text="Size: -- x -- mm", foreground="gray")
        self.plot_size_label.grid(row=1, column=2, sticky=tk.W, padx=(0, 10))
        
        self.start_position_label = ttk.Label(file_frame, text="Start: --", foreground="gray")
        self.start_position_label.grid(row=1, column=3, sticky=tk.W)
        
        # Control buttons section
        control_frame = ttk.LabelFrame(main_frame, text="Control", padding="10")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.connect_btn = ttk.Button(
            control_frame,
            text="Connect",
            command=self.connect_eggbot,
            width=15
        )
        self.connect_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.disconnect_btn = ttk.Button(
            control_frame,
            text="Disconnect",
            command=self.disconnect_eggbot,
            state=tk.DISABLED,
            width=15
        )
        self.disconnect_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.start_btn = ttk.Button(
            control_frame,
            text="Start Plot",
            command=self.start_plot,
            state=tk.DISABLED,
            width=15
        )
        self.start_btn.grid(row=0, column=2, padx=5, pady=5)
        
        self.pause_btn = ttk.Button(
            control_frame,
            text="Pause Plot",
            command=self.toggle_pause,
            state=tk.DISABLED,
            width=15
        )
        self.pause_btn.grid(row=0, column=3, padx=5, pady=5)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop Plot",
            command=self.stop_plot,
            state=tk.DISABLED,
            width=15
        )
        self.stop_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # Pen toggle button (only enabled when paused)
        self.pen_toggle_btn = ttk.Button(
            control_frame,
            text="Toggle Pen",
            command=self.toggle_pen,
            state=tk.DISABLED,
            width=15
        )
        self.pen_toggle_btn.grid(row=1, column=3, padx=5, pady=5)
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        # Status indicator
        indicator_frame = ttk.Frame(status_frame)
        indicator_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.status_canvas = tk.Canvas(indicator_frame, width=20, height=20, bg='white', highlightthickness=1)
        self.status_canvas.grid(row=0, column=0, padx=(0, 10))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, fill='gray', outline='darkgray')
        
        self.status_label = ttk.Label(indicator_frame, text="Disconnected", font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=300)
        self.progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 5))
        
        self.progress_label = ttk.Label(status_frame, text="0 / 0 commands")
        self.progress_label.grid(row=2, column=0, sticky=tk.W)
        
        # Metrics section
        metrics_frame = ttk.LabelFrame(main_frame, text="Plot Metrics", padding="10")
        metrics_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        metrics_frame.columnconfigure(0, weight=1)
        
        # Commands counter
        commands_display_frame = ttk.Frame(metrics_frame)
        commands_display_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        commands_display_frame.columnconfigure(1, weight=1)
        
        ttk.Label(commands_display_frame, text="Commands:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.commands_counter_label = ttk.Label(commands_display_frame, text="0 / 0 (0%)", font=('Courier', 9))
        self.commands_counter_label.grid(row=0, column=1, sticky=tk.W)
        
        self.commands_progress_bar = ttk.Progressbar(commands_display_frame, mode='determinate', length=400)
        self.commands_progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Time display
        time_display_frame = ttk.Frame(metrics_frame)
        time_display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 5))
        time_display_frame.columnconfigure(1, weight=1)
        
        ttk.Label(time_display_frame, text="Time:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.time_label = ttk.Label(time_display_frame, text="00:00:00 / 00:00:00 (0%)", font=('Courier', 9))
        self.time_label.grid(row=0, column=1, sticky=tk.W)
        
        self.time_progress_bar = ttk.Progressbar(time_display_frame, mode='determinate', length=400)
        self.time_progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Distance display
        distance_display_frame = ttk.Frame(metrics_frame)
        distance_display_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        distance_display_frame.columnconfigure(1, weight=1)
        
        ttk.Label(distance_display_frame, text="Distance:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.distance_label = ttk.Label(distance_display_frame, text="0.0 / 0.0 mm (0%)", font=('Courier', 9))
        self.distance_label.grid(row=0, column=1, sticky=tk.W)
        
        self.distance_progress_bar = ttk.Progressbar(distance_display_frame, mode='determinate', length=400)
        self.distance_progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        try:
            # Python 3
            self.log_text = scrolledtext.ScrolledText(
                log_frame,
                height=15,
                state=tk.DISABLED,
                wrap=tk.WORD,
                font=('Courier', 9)
            )
        except:
            # Python 2
            self.log_text = scrolledtext.ScrolledText(
                log_frame,
                height=15,
                state=tk.DISABLED,
                wrap=tk.WORD
            )
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        ttk.Button(
            log_frame,
            text="Clear Log",
            command=self.clear_log
        ).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
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
        self.status_canvas.itemconfig(self.status_indicator, fill=color)
        self.status_label.config(text=status)
    
    def format_time(self, seconds):
        """Format seconds as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)
    
    def update_metrics_display(self):
        """Update the metrics display labels"""
        # Update commands counter
        if self.total_commands > 0:
            cmd_percent = (self.executed_commands / self.total_commands) * 100
            self.commands_counter_label.config(text="{} / {} ({:.1f}%)".format(
                self.executed_commands, self.total_commands, cmd_percent
            ))
            self.commands_progress_bar['value'] = cmd_percent
        else:
            self.commands_counter_label.config(text="0 / 0 (0%)")
            self.commands_progress_bar['value'] = 0
        
        # Calculate actual elapsed time
        if self.plot_start_time and self.is_plotting:
            actual_time = time.time() - self.plot_start_time
        elif self.plot_start_time:
            # Plot finished but we have final time
            actual_time = self.actual_time_sec if hasattr(self, 'actual_time_sec') else 0
        else:
            actual_time = 0
        
        # Calculate time percentage
        time_percent = 0
        if self.estimated_time_sec > 0:
            time_percent = (actual_time / self.estimated_time_sec) * 100
            # Cap progress bar at 100% but show actual percentage in text
            time_progress_bar_value = min(100, time_percent)
        else:
            time_progress_bar_value = 0
        
        # Format time display (show actual percentage even if > 100%)
        time_str = "{} / {} ({:.1f}%)".format(
            self.format_time(actual_time),
            self.format_time(self.estimated_time_sec),
            time_percent
        )
        self.time_label.config(text=time_str)
        self.time_progress_bar['value'] = time_progress_bar_value
        
        # Calculate distance percentage
        distance_percent = 0
        if self.estimated_distance_mm > 0:
            distance_percent = min(100, (self.actual_distance_mm / self.estimated_distance_mm) * 100)
        
        # Format distance display
        distance_str = "{:.1f} / {:.1f} mm ({:.1f}%)".format(
            self.actual_distance_mm,
            self.estimated_distance_mm,
            distance_percent
        )
        self.distance_label.config(text=distance_str)
        self.distance_progress_bar['value'] = distance_percent
    
    def calculate_estimated_metrics(self):
        """Calculate estimated time and distance from parsed commands"""
        if not self.commands:
            return
        
        total_distance = 0.0
        total_time = 0.0
        pen_changes = 0
        
        # Track position and state
        x, y, z = 0.0, 0.0, 0.0
        pen_down = False
        feedrate = 1000.0  # mm/min default
        
        # Use constants from gcode_plotter.py
        steps_per_mm = STEPS_PER_MM
        step_scale = STEP_SCALE
        default_speed = DEFAULT_SPEED
        max_speed = MAX_SPEED
        
        for cmd in self.commands:
            cmd_type = cmd.get('type', '')
            params = cmd.get('params', {})
            
            # Update feedrate if specified
            if 'F' in params:
                feedrate = params['F']
            
            # Handle pen up/down
            old_pen_state = pen_down
            if 'Z' in params:
                z = params['Z']
                pen_down = (z == 0)
            elif cmd_type in ['M3', 'M03']:
                pen_down = True
            elif cmd_type in ['M5', 'M05']:
                pen_down = False
            
            # Count pen state changes
            if pen_down != old_pen_state:
                pen_changes += 1
                total_time += 0.3  # 300ms per pen change (matches gcode_plotter.py)
            
            # Calculate movement distance and time
            if cmd_type in ['G0', 'G00', 'G1', 'G01']:
                new_x = params.get('X', x)
                new_y = params.get('Y', y)
                
                dx = new_x - x
                dy = new_y - y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0.001:
                    total_distance += distance
                    
                    # Use EXACT calculation as gcode_plotter.py move_to() function
                    # n_time = int(1000.0 * abs(distance) / (1.0 / STEPS_PER_MM * STEP_SCALE) / speed)
                    # This simplifies to: n_time = int((distance * STEPS_PER_MM / STEP_SCALE / speed) * 1000)
                    speed = default_speed
                    n_time = int((abs(distance) * steps_per_mm / step_scale / speed) * 1000.0)
                    
                    # Apply minimum time per move (matches gcode_plotter.py)
                    n_time = max(10, n_time)
                    
                    # Add actual sleep time used in gcode_plotter.py: time.sleep(n_time / 1000.0 + 0.02)
                    move_time_sec = (n_time / 1000.0) + 0.02
                    
                    # Add realistic overhead for each command:
                    # - Python processing: ~2-5ms
                    # - USB communication: ~5-10ms
                    # - EBB command processing: ~1-3ms
                    # Total overhead per command: ~10-20ms average
                    overhead_per_command = 0.015  # 15ms average overhead
                    
                    total_time += move_time_sec + overhead_per_command
                
                x, y = new_x, new_y
        
        self.estimated_distance_mm = total_distance
        self.estimated_time_sec = total_time
        self.pen_state_changes = pen_changes
        
        self.log("Estimated distance: {:.1f} mm".format(total_distance))
        self.log("Estimated time: {} ({} pen changes)".format(
            self.format_time(total_time), pen_changes))
        
        self.update_metrics_display()
    
    def calculate_plot_size(self):
        """Calculate the bounding box size of the plot from G-code commands"""
        if not self.commands:
            self.plot_size_x = 0.0
            self.plot_size_y = 0.0
            self.start_position = ""
            return
        
        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')
        
        # Track position through commands
        x, y = 0.0, 0.0
        first_move_x = None
        first_move_y = None
        
        for cmd in self.commands:
            cmd_type = cmd.get('type', '')
            params = cmd.get('params', {})
            
            # Update position for movement commands
            if cmd_type in ['G0', 'G00', 'G1', 'G01']:
                x = params.get('X', x)
                y = params.get('Y', y)
                
                # Capture first movement position
                if first_move_x is None:
                    first_move_x = x
                    first_move_y = y
                
                # Update bounds
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
        
        # Calculate size
        if min_x != float('inf'):
            self.plot_size_x = max_x - min_x
            self.plot_size_y = max_y - min_y
            
            # Determine start position quadrant
            if first_move_x is not None:
                mid_x = (min_x + max_x) / 2.0
                mid_y = (min_y + max_y) / 2.0
                
                if first_move_y >= mid_y:
                    if first_move_x <= mid_x:
                        self.start_position = "Upper Left"
                    else:
                        self.start_position = "Upper Right"
                else:
                    if first_move_x <= mid_x:
                        self.start_position = "Lower Left"
                    else:
                        self.start_position = "Lower Right"
            else:
                self.start_position = "Unknown"
        else:
            self.plot_size_x = 0.0
            self.plot_size_y = 0.0
            self.start_position = ""
        
        # Update display
        if self.plot_size_x > 0 or self.plot_size_y > 0:
            self.plot_size_label.config(
                text="Size: {:.1f} x {:.1f} mm".format(self.plot_size_x, self.plot_size_y),
                foreground="black"
            )
            self.log("Plot size: {:.1f} x {:.1f} mm".format(self.plot_size_x, self.plot_size_y))
            
            if self.start_position:
                self.start_position_label.config(
                    text="Start: {}".format(self.start_position),
                    foreground="black"
                )
                self.log("Start position: {}".format(self.start_position))
        else:
            self.plot_size_label.config(text="Size: -- x -- mm", foreground="gray")
            self.start_position_label.config(text="Start: --", foreground="gray")
        
    def browse_file(self):
        """Open file browser dialog and parse G-code file"""
        filename = filedialog.askopenfilename(
            title="Select G-Code File",
            filetypes=[
                ("G-Code files", "*.gcode *.nc *.ngc *.txt"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.gcode_file = filename
            self.file_label.config(text=os.path.basename(filename), foreground="black")
            self.log("Selected file: {}".format(filename))
            self.commands = []
            
            # Reset metrics
            self.estimated_distance_mm = 0.0
            self.actual_distance_mm = 0.0
            self.estimated_time_sec = 0.0
            self.plot_start_time = None
            self.executed_commands = 0
            self.total_commands = 0
            self.time_label.config(text="00:00:00 / 00:00:00 (0%)")
            self.distance_label.config(text="0.0 / 0.0 mm (0%)")
            self.commands_counter_label.config(text="0 / 0 (0%)")
            self.plot_size_label.config(text="Size: -- x -- mm", foreground="gray")
            self.start_position_label.config(text="Start: --", foreground="gray")
            
            # Automatically parse the file
            if not PLOTTER_AVAILABLE:
                self.command_count_label.config(text="Commands: 0 (plotink not available)")
                messagebox.showerror("Missing Dependencies", "Cannot parse file: plotink module not installed.")
                return
            
            try:
                self.log("Parsing G-code file...")
                parser = GCodeParser()
                self.commands = parser.parse_file(self.gcode_file)
                
                self.total_commands = len(self.commands)
                self.command_count_label.config(text="Commands: {}".format(len(self.commands)))
                self.log("Successfully parsed {} commands".format(len(self.commands)))
                self.update_metrics_display()
                
                # Calculate plot size
                self.calculate_plot_size()
                
                # Calculate estimated metrics
                self.calculate_estimated_metrics()
                
                if self.plotter and self.plotter.serial_port:
                    self.start_btn.config(state=tk.NORMAL)
                    
            except Exception as e:
                messagebox.showerror("Parse Error", "Failed to parse G-code file:\n{}".format(str(e)))
                self.log("ERROR: Failed to parse file - {}".format(str(e)))
                self.command_count_label.config(text="Commands: 0 (parse error)")
            
    def connect_eggbot(self):
        """Connect to EggBot hardware"""
        if not PLOTTER_AVAILABLE:
            messagebox.showerror("Missing Dependencies", "Cannot connect: plotink module not installed.")
            return
        
        if self.plotter and self.plotter.serial_port:
            # Already connected
            messagebox.showinfo("Already Connected", "Already connected to EggBot.")
            return
        
        try:
            self.log("Connecting to EggBot...")
            self.set_status("Connecting...", "yellow")
            
            self.plotter = EggBotGCodePlotter()
            # Use default servo positions (15% up, 45% down) matching jog GUI
            if self.plotter.connect(pen_up_pct=15, pen_down_pct=45):
                self.set_status("Connected", "green")
                self.log("Successfully connected to EggBot")
                self.log("Servo positions configured (up: 15%, down: 45%)")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                
                if self.commands:
                    self.start_btn.config(state=tk.NORMAL)
            else:
                self.set_status("Connection Failed", "red")
                self.log("ERROR: Failed to connect to EggBot")
                self.plotter = None
                messagebox.showerror("Connection Error", "Failed to connect to EggBot.\n\nMake sure the EggBot is connected via USB.")
                
        except Exception as e:
            self.set_status("Connection Failed", "red")
            self.log("ERROR: {}".format(str(e)))
            self.plotter = None
            messagebox.showerror("Connection Error", "Failed to connect:\n{}".format(str(e)))
            
    def disconnect_eggbot(self):
        """Disconnect from EggBot hardware"""
        if not self.plotter or not self.plotter.serial_port:
            messagebox.showinfo("Not Connected", "Not currently connected to EggBot.")
            return
        
        if self.is_plotting:
            if not messagebox.askokcancel("Plotting in Progress", "Plotting is currently in progress. Stop plotting and disconnect?"):
                return
            self.stop_requested = True
        
        try:
            self.log("Disconnecting from EggBot...")
            self.plotter.disconnect()
            self.plotter = None
            
            self.set_status("Disconnected", "red")
            self.log("Disconnected from EggBot")
            
            # Update button states
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log("ERROR during disconnect: {}".format(str(e)))
            messagebox.showerror("Disconnect Error", "Error during disconnect:\n{}".format(str(e)))
            
    def start_plot(self):
        """Start plotting in a background thread"""
        if not self.plotter or not self.plotter.serial_port:
            messagebox.showwarning("Not Connected", "Please connect to EggBot first.")
            return
        
        if not self.commands:
            messagebox.showwarning("No Commands", "Please parse a G-code file first.")
            return
        
        if self.is_plotting:
            messagebox.showwarning("Already Plotting", "A plot is already in progress.")
            return
        
        # Start plotting thread
        self.is_plotting = True
        self.stop_requested = False
        self.is_paused = False
        self.pause_requested = False
        self.paused_position = None
        self.actual_distance_mm = 0.0
        self.current_x = 0.0
        self.current_y = 0.0
        self.executed_commands = 0
        self.plot_start_time = time.time()
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.set_status("Plotting...", "blue")
        
        self.plot_thread = threading.Thread(target=self.plot_worker)
        self.plot_thread.daemon = True
        self.plot_thread.start()
        
        # Start progress monitor
        self.monitor_progress()
        
    def plot_worker(self):
        """Worker thread for plotting"""
        try:
            total = len(self.commands)
            self.log("Starting plot of {} commands...".format(total))
            
            for i, cmd in enumerate(self.commands):
                if self.stop_requested:
                    self.log("Plot stopped by user at command {}/{}".format(i, total))
                    break
                
                # Handle pause request
                if self.pause_requested and not self.is_paused:
                    self.log("Pausing plot at command {}/{}...".format(i, total))
                    # Save current position
                    self.paused_position = (self.current_x, self.current_y)
                    # Raise pen
                    if self.plotter and self.plotter.serial_port:
                        self.plotter.pen_up()
                        self.log("Pen raised to up position")
                    self.is_paused = True
                    self.root.after(0, self.update_pause_state, True)
                    
                # Wait while paused
                while self.is_paused and not self.stop_requested:
                    time.sleep(0.1)
                
                # Resume from pause
                if self.pause_requested and not self.is_paused:
                    self.log("Resuming plot from command {}/{}".format(i, total))
                    # Lower pen back down
                    if self.plotter and self.plotter.serial_port:
                        self.plotter.pen_down()
                        self.log("Pen lowered to down position")
                    self.pause_requested = False
                
                # Update progress (thread-safe)
                progress_pct = int((i / float(total)) * 100)
                self.root.after(0, self.update_progress, i, total, progress_pct)
                
                # Track distance for movement commands
                cmd_type = cmd.get('type', '')
                if cmd_type in ['G0', 'G00', 'G1', 'G01']:
                    params = cmd.get('params', {})
                    new_x = params.get('X', self.current_x)
                    new_y = params.get('Y', self.current_y)
                    
                    dx = new_x - self.current_x
                    dy = new_y - self.current_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    self.actual_distance_mm += distance
                    self.current_x = new_x
                    self.current_y = new_y
                
                # Process command
                self.plotter.process_command(cmd)
                self.executed_commands = i + 1
                
            if not self.stop_requested:
                self.root.after(0, self.update_progress, total, total, 100)
                # Store final time
                if self.plot_start_time:
                    self.actual_time_sec = time.time() - self.plot_start_time
                    self.log("Plot completed successfully!")
                    self.log("Actual time: {}".format(self.format_time(self.actual_time_sec)))
                    self.log("Actual distance: {:.1f} mm".format(self.actual_distance_mm))
                self.root.after(0, lambda: messagebox.showinfo("Complete", "Plot completed successfully!"))
            
        except Exception as e:
            self.log("ERROR during plotting: {}".format(str(e)))
            self.root.after(0, lambda: messagebox.showerror("Plot Error", "Error during plotting:\n{}".format(str(e))))
            
        finally:
            self.is_plotting = False
            self.root.after(0, self.plot_finished)
            
    def update_progress(self, current, total, pct):
        """Update progress bar and label"""
        self.progress['value'] = pct
        self.progress_label.config(text="{} / {} commands ({:.1f}%)".format(current, total, pct))
        
    def monitor_progress(self):
        """Monitor plotting progress"""
        if self.is_plotting:
            self.update_metrics_display()
            self.root.after(100, self.monitor_progress)
        else:
            # Final update when done
            self.update_metrics_display()
            
    def plot_finished(self):
        """Clean up after plotting finishes"""
        self.stop_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.DISABLED)
        self.pen_toggle_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL)
        self.is_paused = False
        self.pause_requested = False
        self.set_status("Connected", "green")
        
    def toggle_pause(self):
        """Toggle between pause and resume"""
        if self.is_plotting:
            if self.is_paused:
                # Resume
                self.resume_plot()
            else:
                # Pause
                self.pause_plot()
        
    def pause_plot(self):
        """Pause the plot and raise the pen"""
        if self.is_plotting and not self.is_paused:
            self.pause_requested = True
            self.log("Pause requested...")
    
    def update_pause_state(self, paused):
        """Update UI for pause state (called from plot thread)"""
        if paused:
            self.pause_btn.config(text="Resume Plot")
            self.pen_toggle_btn.config(state=tk.NORMAL)
            self.set_status("Paused", "orange")
            self.log("Plot paused - pen toggle enabled for pen changes")
        else:
            self.pause_btn.config(text="Pause Plot")
            self.pen_toggle_btn.config(state=tk.DISABLED)
            self.set_status("Plotting...", "blue")
    
    def resume_plot(self):
        """Resume the paused plot"""
        if self.is_paused:
            self.is_paused = False
            self.log("Resume requested...")
    
    def toggle_pen(self):
        """Toggle pen up/down while paused (for pen changes)"""
        if not self.is_paused:
            return
        
        if self.plotter and self.plotter.serial_port:
            try:
                # Query current pen state and toggle it
                if self.plotter.pen_is_down:
                    self.plotter.pen_up()
                    self.log("Pen moved to UP position")
                else:
                    self.plotter.pen_down()
                    self.log("Pen moved to DOWN position")
            except Exception as e:
                self.log("Error toggling pen: {}".format(str(e)))
    
    def stop_plot(self):
        """Request plot to stop and immediately halt all motor movement"""
        if self.is_plotting:
            self.stop_requested = True
            self.is_paused = False  # Exit pause state if paused
            self.log("EMERGENCY STOP - Halting all movement")
            
            # Immediately send emergency stop command to halt motors
            if self.plotter and self.plotter.serial_port and ebb_serial:
                try:
                    ebb_serial.command(self.plotter.serial_port, 'ES\r')
                    self.log("Motors stopped immediately")
                except Exception as e:
                    self.log(f"Error sending emergency stop: {e}")
            
            self.stop_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.pen_toggle_btn.config(state=tk.DISABLED)
            
    def on_closing(self):
        """Handle window close event"""
        if self.is_plotting:
            if messagebox.askokcancel("Quit", "Plotting is in progress. Stop and quit?"):
                self.stop_requested = True
                if self.plotter:
                    try:
                        self.plotter.disconnect()
                    except:
                        pass
                self.root.destroy()
        else:
            if self.plotter:
                try:
                    self.plotter.disconnect()
                except:
                    pass
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = GCodePlotterGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    width = 900  # Use fixed width
    height = 600  # Use fixed height
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
