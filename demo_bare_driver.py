"""
Demo: LCD2004 Driver

Demonstrates core LCD2004 driver functions
- Initialization
- Clearing
- Backlight control
- Writing text at specific positions
- Cursor and blink visibility toggling
- Horizontal scrolling
- Custom character creation
- Display on/off (contents, not backlight)
"""

import time

from lcd2004.driver import LCD2004  # adjust import path as needed

# --- Init display ---
lcd = LCD2004(sda=0, scl=1)  # change pins for your board

print("Clearing display...")
lcd.clear()
time.sleep(0.5)

print("Backlight ON...")
lcd.set_backlight(True)
time.sleep(0.5)

print("Writing first line...")
lcd.set_cursor(0, 0)  # set cursor to top left
lcd.write("    LCD2004 Demo")
time.sleep(2)

print("Writing text")
lcd.clear()
lcd.write("First line")
time.sleep(1)
lcd.set_cursor(0, 1)  # set cursor to second line
lcd.write("Second line")
time.sleep(1)
lcd.set_cursor(0, 2)
lcd.write("1")  # Successive writes take place where the cursor is
time.sleep(0.6)
lcd.write("2")
time.sleep(0.6)
lcd.write("3")
time.sleep(0.6)
lcd.write("4")
time.sleep(0.6)
lcd.write("5")
time.sleep(1.5)

lcd.set_cursor(8, 4)  # set cursor to last line, slightly to the right
lcd.write("Bottom right")
time.sleep(2)

print("Cursor and blink demo...")
lcd.clear()
lcd.write("Cursor on:")
lcd.set_cursor_visible(True)  # Turn on cursor underscore
time.sleep(2)

lcd.clear()
lcd.write("Cursor off:")
lcd.set_cursor_visible(False)  # Turn off cursor underscore
time.sleep(2)

# Clear, and write "Blink on:"
lcd.clear()
lcd.write("Blink on:")
lcd.set_blink(True)
time.sleep(2)

print("Turning blink OFF, cursor OFF...")
lcd.set_blink(False)  # Turn off cursor rectangle blink
lcd.set_cursor_visible(False)  # Turn off cursor underscore
time.sleep(0.5)

lcd.clear()
lcd.set_cursor(0, 0)
lcd.write("+------------------+")
lcd.set_cursor(0, 1)
lcd.write("|   Scroll test    |")
lcd.set_cursor(0, 2)
lcd.write("|   Scroll test    |")
lcd.set_cursor(0, 3)
lcd.write("+------------------+")
time.sleep(1.5)

print("Scrolling left...")
for _ in range(5):
    lcd.scroll_left()
    time.sleep(0.2)
time.sleep(1.5)

print("Scrolling right...")
for _ in range(5):
    lcd.scroll_right()
    time.sleep(0.2)
time.sleep(1.5)
lcd.clear()


print("Creating custom characters...")
lcd.clear()
lcd.write("Custom characters:")
time.sleep(1)

# Degree symbol in slot 0
DEG_SYMBOL = [
    0b00110,  # ··██·
    0b01001,  # ·█··█
    0b00110,  # ··██·
    0b00000,  # ·····
    0b00000,  # ·····
    0b00000,  # ·····
    0b00000,  # ·····
    0b00000,  # ·····
]
lcd.create_char(0, DEG_SYMBOL)

# Smiley in slot 1
SMILEY = [
    0b00000,  # ·····
    0b01010,  # ·█·█·
    0b01010,  # ·█·█·
    0b00000,  # ·····
    0b10001,  # █···█
    0b01110,  # ·███·
    0b00000,  # ·····
    0b00000,  # ·····
]
lcd.create_char(1, SMILEY)

# Show both characters
lcd.set_cursor(0, 1)
lcd.write("Degree symbol: 23")
lcd.write(chr(0))  # degree symbol
lcd.write("C  ")
time.sleep(1)
lcd.set_cursor(0, 2)
lcd.write("Smiley face: ")
lcd.write(chr(1))  # smiley
time.sleep(2)


lcd.clear()
lcd.write("Backlight test")
time.sleep(1.5)

print("Backlight OFF...")
lcd.set_backlight(False)
time.sleep(1)

print("Backlight ON...")
lcd.set_backlight(True)
time.sleep(1)

print("Display OFF (content preserved)...")
lcd.clear()
lcd.write("Display OFF test")
time.sleep(1.5)
lcd.set_display(False)
time.sleep(1)

print("Display ON...")
lcd.set_display(True)
time.sleep(1)

print("Demo complete.")
lcd.clear()
lcd.set_cursor(3, 1)
lcd.write("Demo complete.")
