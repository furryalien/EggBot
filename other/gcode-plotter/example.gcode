; Example G-code file for EggBot
; Simple square pattern

G21 ; Set units to millimeters
G90 ; Absolute positioning
F1000 ; Set feedrate to 1000 mm/min

; Move to start position
G0 X0 Y0
M3 ; Pen down

; Draw a 20mm square
G1 X20 Y0
G1 X20 Y20
G1 X0 Y20
G1 X0 Y0

M5 ; Pen up

; Move to new position and draw a circle approximation
G0 X40 Y10
M3 ; Pen down

; Approximate circle with line segments (radius 10mm)
G1 X46.18 Y13.82
G1 X50 Y20
G1 X50 Y26.18
G1 X46.18 Y33.82
G1 X40 Y40
G1 X33.82 Y36.18
G1 X30 Y30
G1 X30 Y23.82
G1 X33.82 Y16.18
G1 X40 Y10

M5 ; Pen up
M2 ; Program end
