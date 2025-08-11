"""
LCD2004 Demo Script
Demonstrates core features of the LCD2004 driver over ~10 seconds.
"""

import time

from lcd2004 import LCD2004  # adjust import path as needed

# --- Init display ---
lcd = LCD2004(sda=0, scl=1)  # change pins for your board

print("Clearing display...")
lcd.clear()
time.sleep(0.5)

print("Backlight ON...")
lcd.set_backlight(True)
time.sleep(0.5)

print("Writing first line...")
lcd.set_cursor(0, 0)
lcd.write("Hello, World!")
time.sleep(0.5)

print("Writing second line...")
lcd.set_cursor(0, 1)
lcd.write("LCD2004 Demo")
time.sleep(0.5)

print("Turning cursor ON...")
lcd.set_cursor_visible(True)
time.sleep(0.5)

print("Turning blink ON...")
lcd.set_blink(True)
time.sleep(1)

print("Turning blink OFF, cursor OFF...")
lcd.set_blink(False)
lcd.set_cursor_visible(False)
time.sleep(0.5)

print("Scrolling left...")
for _ in range(5):
    lcd.scroll_left()
    time.sleep(0.2)

print("Scrolling right...")
for _ in range(5):
    lcd.scroll_right()
    time.sleep(0.2)

print("Clearing display for custom char test...")
lcd.clear()

print("Creating custom degree symbol in slot 0...")
DEG_SYMBOL = [0b00110, 0b01001, 0b00110, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000]  # ··██·  # ·█··█  # ··██·  # ·····  # ·····  # ·····  # ·····  # ·····
lcd.create_char(0, DEG_SYMBOL)

print("Displaying temperature with custom symbol...")
lcd.set_cursor(0, 0)
lcd.write("Temp: 23")
lcd.write(chr(0))  # degree symbol
lcd.write("C")
time.sleep(2)

print("Backlight OFF...")
lcd.set_backlight(False)
time.sleep(0.5)

print("Backlight ON...")
lcd.set_backlight(True)
time.sleep(0.5)

print("Display OFF (content preserved)...")
lcd.set_display(False)
time.sleep(1)

print("Display ON...")
lcd.set_display(True)
time.sleep(1)

print("Demo complete.")
lcd.clear()
lcd.write("Demo complete.")
