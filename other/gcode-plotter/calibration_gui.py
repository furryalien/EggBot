#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EggBot Calibration GUI
Draws test patterns and calculates correct STEPS_PER_MM values
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import time
from gcode_plotter import EggBotGCodePlotter

class CalibrationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EggBot Calibration Tool")
        self.root.geometry("500x550")
        
        self.plotter = None
        self.current_steps_per_mm = 100.5157  # Default from gcode_plotter.py
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="EggBot Calibration Tool", 
                                font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Instructions
        instructions = (
            "1. Enter test distances (mm)\n"
            "2. Click 'Draw Test Pattern'\n"
            "3. Measure the actual drawn sizes\n"
            "4. Enter measurements and click 'Calculate'\n"
            "Pattern includes: X line, Y line, 2 circles with crosshairs"
        )
        instr_label = ttk.Label(main_frame, text=instructions, justify=tk.LEFT,
                                foreground='blue')
        instr_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Test Pattern Input Section
        test_frame = ttk.LabelFrame(main_frame, text="Test Pattern Dimensions", 
                                     padding="10")
        test_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), 
                        pady=(0, 10))
        
        ttk.Label(test_frame, text="X Distance (mm):").grid(row=0, column=0, 
                                                              sticky=tk.W, pady=5)
        self.x_input = ttk.Entry(test_frame, width=15)
        self.x_input.grid(row=0, column=1, padx=(10, 0), pady=5)
        self.x_input.insert(0, "50")
        
        ttk.Label(test_frame, text="Y Distance (mm):").grid(row=1, column=0, 
                                                              sticky=tk.W, pady=5)
        self.y_input = ttk.Entry(test_frame, width=15)
        self.y_input.grid(row=1, column=1, padx=(10, 0), pady=5)
        self.y_input.insert(0, "50")
        
        ttk.Label(test_frame, text="Circle 1 Diameter (mm):").grid(row=2, column=0, 
                                                                   sticky=tk.W, pady=5)
        self.circle_input = ttk.Entry(test_frame, width=15)
        self.circle_input.grid(row=2, column=1, padx=(10, 0), pady=5)
        self.circle_input.insert(0, "40")
        
        ttk.Label(test_frame, text="Circle 2 Diameter (mm):").grid(row=3, column=0, 
                                                                   sticky=tk.W, pady=5)
        self.circle2_input = ttk.Entry(test_frame, width=15)
        self.circle2_input.grid(row=3, column=1, padx=(10, 0), pady=5)
        self.circle2_input.insert(0, "30")
        
        # Draw Button
        self.draw_button = ttk.Button(main_frame, text="Draw Test Pattern", 
                                       command=self.draw_pattern)
        self.draw_button.grid(row=3, column=0, columnspan=2, pady=(10, 20))
        
        # Measurement Input Section
        measure_frame = ttk.LabelFrame(main_frame, text="Actual Measurements", 
                                        padding="10")
        measure_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), 
                           pady=(0, 10))
        
        ttk.Label(measure_frame, text="Measured X (mm):").grid(row=0, column=0, 
                                                                 sticky=tk.W, pady=5)
        self.measured_x = ttk.Entry(measure_frame, width=15)
        self.measured_x.grid(row=0, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(measure_frame, text="Measured Y (mm):").grid(row=1, column=0, 
                                                                 sticky=tk.W, pady=5)
        self.measured_y = ttk.Entry(measure_frame, width=15)
        self.measured_y.grid(row=1, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(measure_frame, text="Measured Diameter 1 (mm):").grid(row=2, column=0, 
                                                                        sticky=tk.W, pady=5)
        self.measured_circle = ttk.Entry(measure_frame, width=15)
        self.measured_circle.grid(row=2, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(measure_frame, text="Measured Diameter 2 (mm):").grid(row=3, column=0, 
                                                                        sticky=tk.W, pady=5)
        self.measured_circle2 = ttk.Entry(measure_frame, width=15)
        self.measured_circle2.grid(row=3, column=1, padx=(10, 0), pady=5)
        
        # Calculate Button
        self.calc_button = ttk.Button(main_frame, text="Calculate Calibration", 
                                       command=self.calculate_calibration)
        self.calc_button.grid(row=5, column=0, columnspan=2, pady=(10, 20))
        
        # Results Section
        results_frame = ttk.LabelFrame(main_frame, text="Calibration Results", 
                                        padding="10")
        results_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Label(results_frame, text="Current STEPS_PER_MM:", 
                  font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.current_label = ttk.Label(results_frame, text=f"{self.current_steps_per_mm:.4f}")
        self.current_label.grid(row=0, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(results_frame, text="Correct X STEPS_PER_MM:", 
                  foreground='green', font=('Arial', 10, 'bold')).grid(row=1, column=0, 
                                                                         sticky=tk.W, pady=5)
        self.correct_x_label = ttk.Label(results_frame, text="--", foreground='green', 
                                          font=('Arial', 10, 'bold'))
        self.correct_x_label.grid(row=1, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(results_frame, text="Correct Y STEPS_PER_MM:", 
                  foreground='green', font=('Arial', 10, 'bold')).grid(row=2, column=0, 
                                                                         sticky=tk.W, pady=5)
        self.correct_y_label = ttk.Label(results_frame, text="--", foreground='green', 
                                          font=('Arial', 10, 'bold'))
        self.correct_y_label.grid(row=2, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(results_frame, text="Correct Circle 1 STEPS_PER_MM:", 
                  foreground='green', font=('Arial', 10, 'bold')).grid(row=3, column=0, 
                                                                         sticky=tk.W, pady=5)
        self.correct_circle_label = ttk.Label(results_frame, text="--", foreground='green', 
                                               font=('Arial', 10, 'bold'))
        self.correct_circle_label.grid(row=3, column=1, padx=(10, 0), pady=5)
        
        ttk.Label(results_frame, text="Correct Circle 2 STEPS_PER_MM:", 
                  foreground='green', font=('Arial', 10, 'bold')).grid(row=4, column=0, 
                                                                         sticky=tk.W, pady=5)
        self.correct_circle2_label = ttk.Label(results_frame, text="--", foreground='green', 
                                               font=('Arial', 10, 'bold'))
        self.correct_circle2_label.grid(row=4, column=1, padx=(10, 0), pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), 
                        pady=(10, 0))
        
    def draw_pattern(self):
        """Draw the calibration test pattern"""
        try:
            x_dist = float(self.x_input.get())
            y_dist = float(self.y_input.get())
            circle_diam = float(self.circle_input.get())
            circle2_diam = float(self.circle2_input.get())
            
            if x_dist <= 0 or y_dist <= 0 or circle_diam <= 0 or circle2_diam <= 0:
                messagebox.showerror("Error", "All dimensions must be positive numbers")
                return
                
            self.status_var.set("Connecting to EggBot...")
            self.root.update()
            
            # Initialize plotter
            if self.plotter is None:
                self.plotter = EggBotGCodePlotter()
                if not self.plotter.connect():
                    messagebox.showerror("Error", "Could not connect to EggBot")
                    self.plotter = None
                    self.status_var.set("Connection failed")
                    return
            
            self.status_var.set("Drawing test pattern...")
            self.root.update()
            
            # Get current STEPS_PER_MM from plotter
            from gcode_plotter import STEPS_PER_MM
            self.current_steps_per_mm = STEPS_PER_MM
            self.current_label.config(text=f"{self.current_steps_per_mm:.4f}")
            
            # Draw test pattern
            # 1. Move to start position
            self.plotter.move_to(10, 10, rapid=True)
            
            # 2. Draw horizontal line (X axis test)
            self.plotter.pen_down()
            time.sleep(0.5)
            self.plotter.move_to(10 + x_dist, 10, rapid=False)
            self.plotter.pen_up()
            time.sleep(0.5)
            
            # 3. Draw vertical line (Y axis test)
            self.plotter.move_to(20 + x_dist, 10, rapid=True)
            self.plotter.pen_down()
            time.sleep(0.5)
            self.plotter.move_to(20 + x_dist, 10 + y_dist, rapid=False)
            self.plotter.pen_up()
            time.sleep(0.5)
            
            # 4. Draw circle (combined axis test)
            circle_x = 10 + x_dist / 2
            circle_y = 20 + y_dist + circle_diam / 2
            radius = circle_diam / 2
            
            # Move to circle start
            self.plotter.move_to(circle_x + radius, circle_y, rapid=True)
            self.plotter.pen_down()
            time.sleep(0.5)
            
            # Draw circle with 32 segments
            import math
            segments = 32
            for i in range(segments + 1):
                angle = 2 * math.pi * i / segments
                x = circle_x + radius * math.cos(angle)
                y = circle_y + radius * math.sin(angle)
                self.plotter.move_to(x, y, rapid=False)
            
            self.plotter.pen_up()
            time.sleep(0.5)
            
            # 5. Draw second circle with crosshairs through center
            circle2_x = 30 + x_dist + circle2_diam / 2
            circle2_y = 20 + y_dist + circle2_diam / 2
            radius2 = circle2_diam / 2
            
            # Draw second circle
            self.plotter.move_to(circle2_x + radius2, circle2_y, rapid=True)
            self.plotter.pen_down()
            time.sleep(0.5)
            
            for i in range(segments + 1):
                angle = 2 * math.pi * i / segments
                x = circle2_x + radius2 * math.cos(angle)
                y = circle2_y + radius2 * math.sin(angle)
                self.plotter.move_to(x, y, rapid=False)
            
            self.plotter.pen_up()
            time.sleep(0.5)
            
            # Draw horizontal crosshair through circle 2 center
            crosshair_length = radius2 * 1.5
            self.plotter.move_to(circle2_x - crosshair_length, circle2_y, rapid=True)
            self.plotter.pen_down()
            time.sleep(0.3)
            self.plotter.move_to(circle2_x + crosshair_length, circle2_y, rapid=False)
            self.plotter.pen_up()
            time.sleep(0.3)
            
            # Draw vertical crosshair through circle 2 center
            self.plotter.move_to(circle2_x, circle2_y - crosshair_length, rapid=True)
            self.plotter.pen_down()
            time.sleep(0.3)
            self.plotter.move_to(circle2_x, circle2_y + crosshair_length, rapid=False)
            self.plotter.pen_up()
            
            # Return to origin
            self.plotter.move_to(0, 0, rapid=True)
            
            self.status_var.set("Pattern drawn! Measure and enter results.")
            messagebox.showinfo("Success", 
                               f"Test pattern drawn:\n"
                               f"- Horizontal line: {x_dist} mm\n"
                               f"- Vertical line: {y_dist} mm\n"
                               f"- Circle 1 diameter: {circle_diam} mm\n"
                               f"- Circle 2 diameter: {circle2_diam} mm (with crosshairs)\n\n"
                               f"Measure the actual sizes and enter them below.")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
            self.status_var.set("Error: Invalid input")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to draw pattern: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            
    def calculate_calibration(self):
        """Calculate the correct STEPS_PER_MM based on measurements"""
        try:
            intended_x = float(self.x_input.get())
            intended_y = float(self.y_input.get())
            intended_circle = float(self.circle_input.get())
            intended_circle2 = float(self.circle2_input.get())
            
            measured_x = float(self.measured_x.get())
            measured_y = float(self.measured_y.get())
            measured_circle = float(self.measured_circle.get())
            measured_circle2 = float(self.measured_circle2.get())
            
            if any(v <= 0 for v in [intended_x, intended_y, intended_circle, intended_circle2,
                                    measured_x, measured_y, measured_circle, measured_circle2]):
                messagebox.showerror("Error", "All values must be positive numbers")
                return
            
            # Calculate corrected STEPS_PER_MM for each axis
            # Formula: correct_steps = current_steps * (intended / measured)
            correct_x = self.current_steps_per_mm * (intended_x / measured_x)
            correct_y = self.current_steps_per_mm * (intended_y / measured_y)
            correct_circle = self.current_steps_per_mm * (intended_circle / measured_circle)
            correct_circle2 = self.current_steps_per_mm * (intended_circle2 / measured_circle2)
            
            # Update labels
            self.correct_x_label.config(text=f"{correct_x:.4f}")
            self.correct_y_label.config(text=f"{correct_y:.4f}")
            self.correct_circle_label.config(text=f"{correct_circle:.4f}")
            self.correct_circle2_label.config(text=f"{correct_circle2:.4f}")
            
            # Calculate percentage errors
            x_error = abs((measured_x - intended_x) / intended_x * 100)
            y_error = abs((measured_y - intended_y) / intended_y * 100)
            circle_error = abs((measured_circle - intended_circle) / intended_circle * 100)
            circle2_error = abs((measured_circle2 - intended_circle2) / intended_circle2 * 100)
            
            # Average of all four measurements
            avg_correct = (correct_x + correct_y + correct_circle + correct_circle2) / 4
            
            self.status_var.set("Calibration calculated successfully")
            
            messagebox.showinfo("Calibration Results",
                               f"Current STEPS_PER_MM: {self.current_steps_per_mm:.4f}\n\n"
                               f"Recommended STEPS_PER_MM:\n"
                               f"  X-axis: {correct_x:.4f} (error: {x_error:.1f}%)\n"
                               f"  Y-axis: {correct_y:.4f} (error: {y_error:.1f}%)\n"
                               f"  Circle 1: {correct_circle:.4f} (error: {circle_error:.1f}%)\n"
                               f"  Circle 2: {correct_circle2:.4f} (error: {circle2_error:.1f}%)\n\n"
                               f"Average: {avg_correct:.4f}\n\n"
                               f"Update STEPS_PER_MM in gcode_plotter.py (line ~51)\n"
                               f"to the average value or individual axis values if needed.")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for all measurements")
            self.status_var.set("Error: Invalid measurement input")
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            
    def on_closing(self):
        """Clean up when closing the window"""
        if self.plotter:
            try:
                self.plotter.disconnect()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = CalibrationGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
